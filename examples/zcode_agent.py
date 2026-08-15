from __future__ import annotations

"""StrongOrc command agent for Z.AI GLM Coding Plan.

Stdlib only. Talks to the Coding Plan OpenAI-compatible host, writes
protocol.jsonl and receipts/job.json into $STRONGORC_RUN_DIR, and never
prints the API key.

Key resolution: ZAI_API_KEY / GLM_API_KEY / Z_AI_API_KEY, else Marionette
~/.pmharness/state/keys.json slot \"zai\".
"""

import json
import os
import subprocess
import sys
import time
import traceback
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

CODING_URL = "https://api.z.ai/api/coding/paas/v4/chat/completions"
MARIONETTE_KEYS = Path.home() / ".pmharness" / "state" / "keys.json"
PLAN_IN_PER_MTOK = 1.0
PLAN_OUT_PER_MTOK = 3.5
MAX_TURNS = 48
REQUEST_TIMEOUT = 180
WAIT_CAP_SECONDS = 3600
READ_LIMIT = 80_000

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List files under a relative directory in the run workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative directory. Empty or '.' is the workspace root.",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a UTF-8 text file relative to the workspace.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write UTF-8 text, creating parent directories.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "Delete a file relative to the workspace.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "emit_event",
            "description": "Append one protocol.jsonl event.",
            "parameters": {
                "type": "object",
                "properties": {
                    "type": {"type": "string"},
                    "payload": {"type": "object"},
                },
                "required": ["type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_node",
            "description": "Run a workspace test with node --experimental-strip-types.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "wait",
            "description": (
                "Block this process. Use after writing the kill-resume checkpoint "
                "on the first spawn so the harness can SIGKILL you."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "seconds": {
                        "type": "integer",
                        "description": "Seconds to sleep. Capped at 3600.",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "measured_usage",
            "description": (
                "Return measured API tokens and the plan-nominal USD overlay "
                "($1 / $3.5 per MTok from Marionette agentic/glm-5.3). "
                "There is no published GLM-5.3 list price. Do not write usd=0 "
                "if tokens are nonzero."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_receipt",
            "description": "Write receipts/job.json. model_id must equal STRONGORC_MODEL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["completed", "failed", "refused", "dead"],
                    },
                    "usd": {"type": "number"},
                    "tokens_in": {"type": "integer"},
                    "tokens_out": {"type": "integer"},
                    "workers_ran": {"type": "integer"},
                },
                "required": ["status", "usd", "tokens_in", "tokens_out", "workers_ran"],
            },
        },
    },
]


def env_first(*names: str, default: str = "") -> str:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return default


def load_zai_key() -> str:
    for name in ("ZAI_API_KEY", "GLM_API_KEY", "Z_AI_API_KEY", "ANTHROPIC_AUTH_TOKEN"):
        value = os.environ.get(name)
        if value:
            return value
    if not MARIONETTE_KEYS.is_file():
        raise SystemExit("no Z.AI key in env or Marionette ~/.pmharness/state/keys.json")
    data = json.loads(MARIONETTE_KEYS.read_text(encoding="utf-8"))
    key = data.get("zai")
    if not key:
        raise SystemExit("Marionette keys.json has no zai slot")
    return str(key)


def plan_nominal_usd(tokens_in: int, tokens_out: int) -> float:
    return (tokens_in / 1_000_000.0) * PLAN_IN_PER_MTOK + (tokens_out / 1_000_000.0) * PLAN_OUT_PER_MTOK


def resolve_run_dir() -> Path:
    raw = env_first("STRONGORC_RUN_DIR", "DURABLE_ORCH_RUN_DIR")
    if not raw:
        raise SystemExit("STRONGORC_RUN_DIR is required")
    return Path(raw).resolve()


def confined(run_dir: Path, relative: str) -> Path:
    rel = (relative or ".").lstrip("/")
    path = (run_dir / rel).resolve()
    root = run_dir.resolve()
    if path != root and root not in path.parents:
        raise ValueError(f"path escapes workspace: {relative}")
    return path


def append_jsonl(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(obj, sort_keys=True) + "\n")


def emit(run_dir: Path, event_type: str, payload: dict[str, Any] | None = None) -> None:
    append_jsonl(run_dir / "protocol.jsonl", {"type": event_type, "payload": payload or {}})


def log(run_dir: Path, message: str) -> None:
    line = message.rstrip()
    print(line, file=sys.stderr, flush=True)
    path = run_dir / ".harness" / "zcode_agent.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def write_usage(run_dir: Path, tokens_in: int, tokens_out: int) -> None:
    payload = {
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "usd_plan_nominal": plan_nominal_usd(tokens_in, tokens_out),
        "cost_source": "marionette_plan_nominal",
        "input_per_mtok_usd": PLAN_IN_PER_MTOK,
        "output_per_mtok_usd": PLAN_OUT_PER_MTOK,
        "note": "GLM-5.3 has no published list price; overlay is Marionette agentic/glm-5.3 plan nominal.",
    }
    path = run_dir / ".harness" / "zai_usage.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def list_tree(root: Path, run_dir: Path) -> str:
    if not root.exists():
        return "missing"
    if root.is_file():
        return root.relative_to(run_dir).as_posix()
    lines: list[str] = []
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(run_dir).as_posix()
        if path.is_dir():
            continue
        lines.append(rel)
        if len(lines) >= 400:
            lines.append("...truncated")
            break
    return "\n".join(lines) if lines else "(empty)"


class Workspace:
    def __init__(self, run_dir: Path, model: str) -> None:
        self.run_dir = run_dir
        self.model = model
        self.tokens_in = 0
        self.tokens_out = 0
        self.receipt_written = (run_dir / "receipts" / "job.json").is_file()

    def usage_payload(self) -> dict[str, Any]:
        return {
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "usd_plan_nominal": plan_nominal_usd(self.tokens_in, self.tokens_out),
            "cost_source": "marionette_plan_nominal",
            "model_id_must_equal": self.model,
        }

    def dispatch(self, name: str, args: dict[str, Any]) -> str:
        if name == "list_dir":
            path = confined(self.run_dir, str(args.get("path") or "."))
            return list_tree(path, self.run_dir)
        if name == "read_file":
            path = confined(self.run_dir, str(args["path"]))
            if not path.is_file():
                return f"missing {args['path']}"
            text = path.read_text(encoding="utf-8")
            if len(text) > READ_LIMIT:
                return text[:READ_LIMIT] + "\n...truncated"
            return text
        if name == "write_file":
            path = confined(self.run_dir, str(args["path"]))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(str(args.get("content") or ""), encoding="utf-8")
            return f"wrote {args['path']} ({path.stat().st_size} bytes)"
        if name == "delete_file":
            path = confined(self.run_dir, str(args["path"]))
            if not path.is_file():
                return f"missing {args['path']}"
            path.unlink()
            return f"deleted {args['path']}"
        if name == "emit_event":
            event_type = str(args.get("type") or "")
            payload = args.get("payload") or {}
            if not isinstance(payload, dict):
                payload = {"value": payload}
            emit(self.run_dir, event_type, payload)
            return f"emitted {event_type}"
        if name == "run_node":
            rel = str(args["path"])
            target = confined(self.run_dir, rel)
            completed = subprocess.run(
                ["node", "--experimental-strip-types", "--no-warnings", str(target)],
                cwd=self.run_dir,
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )
            out = (completed.stdout or "") + (completed.stderr or "")
            return f"exit {completed.returncode}\n{out[:4000]}"
        if name == "wait":
            seconds = int(args.get("seconds") or WAIT_CAP_SECONDS)
            seconds = max(1, min(seconds, WAIT_CAP_SECONDS))
            log(self.run_dir, f"waiting {seconds}s for harness interrupt")
            time.sleep(seconds)
            return "wait finished without kill"
        if name == "measured_usage":
            return json.dumps(self.usage_payload(), sort_keys=True)
        if name == "write_receipt":
            receipt = {
                "status": str(args["status"]),
                "model_id": self.model,
                "usd": float(args["usd"]),
                "tokens_in": int(args["tokens_in"]),
                "tokens_out": int(args["tokens_out"]),
                "workers_ran": int(args["workers_ran"]),
                "cost_source": "marionette_plan_nominal",
            }
            path = self.run_dir / "receipts" / "job.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            emit(self.run_dir, "receipt_written", {"status": receipt["status"], "model_id": receipt["model_id"]})
            self.receipt_written = True
            return f"wrote receipts/job.json status={receipt['status']}"
        return f"unknown tool {name}"


def extract_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if text:
                    parts.append(str(text))
        return "".join(parts)
    return str(content)


def add_usage(workspace: Workspace, usage: dict[str, Any] | None) -> None:
    if not usage:
        return
    workspace.tokens_in += int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
    workspace.tokens_out += int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
    write_usage(workspace.run_dir, workspace.tokens_in, workspace.tokens_out)


def chat(api_key: str, model: str, messages: list[dict[str, Any]], effort: str) -> dict[str, Any]:
    body = {
        "model": model,
        "messages": messages,
        "tools": TOOLS,
        "tool_choice": "auto",
        "thinking": {"type": "enabled"},
        "reasoning_effort": effort,
        "max_tokens": 8192,
    }
    request = urllib.request.Request(
        env_first("ZAI_CHAT_URL", default=CODING_URL),
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:800]
        raise RuntimeError(f"z.ai HTTP {exc.code}: {detail}") from exc


def system_prompt(task_id: str, track: str, model: str, resume: bool) -> str:
    resume_line = (
        "This process was respawned after a harness SIGKILL (STRONGORC_RESUME=1). "
        "Read durable state on disk. Do not replay finished work from memory."
        if resume
        else (
            "First spawn (STRONGORC_RESUME is not 1). If the task prompt says to checkpoint "
            "and wait, write the checkpoint then call wait. Finishing the whole job before "
            "the interrupt is a fail."
        )
    )
    return f"""You are a live StrongOrc command agent. Workspace is $STRONGORC_RUN_DIR.
Task {task_id} track={track}. Invoked model id: {model}.

{resume_line}

The task prompt and the tree are the spec. Follow them. Do not invent a shortcut that
skips a gate, lease, nonce, budget, or live test.

Contract:
- Outcome files and protocol both have to pass. The oracle re-runs hidden Node tests
  that are not in the seed. A visible console.log("ok") is not a pass.
- After a resume, re-read the workspace. Files may have changed since the first spawn.
- Emit protocol events with emit_event. Forbidden events fail the trial even if files look green.
- On orchestrator tasks, dispatch workers. Do not emit orchestrator_wrote_solution.
- status=completed with workers_ran=0 is a dead-swarm fail.
- model_id in the receipt is written as {model}. usd must not be 0 when tokens are nonzero.
  Call measured_usage, then write_receipt. Use the plan-nominal overlay; there is no
  published GLM-5.3 list price.

Use tools. When the job is done, emit job_completed and write_receipt, then stop.
"""


def user_prompt(run_dir: Path) -> str:
    prompt_path = Path(env_first("STRONGORC_PROMPT", "DURABLE_ORCH_PROMPT", default=str(run_dir / "PROMPT.md")))
    prompt = prompt_path.read_text(encoding="utf-8") if prompt_path.is_file() else ""
    tree = list_tree(run_dir, run_dir)
    return f"{prompt}\n\nWorkspace files:\n{tree}\n"


def run_loop(workspace: Workspace, api_key: str, api_model: str, effort: str) -> None:
    task_id = env_first("STRONGORC_TASK_ID", "DURABLE_ORCH_TASK_ID")
    track = env_first("STRONGORC_TRACK", "DURABLE_ORCH_TRACK")
    resume = env_first("STRONGORC_RESUME", "DURABLE_ORCH_RESUME") == "1"
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt(task_id, track, workspace.model, resume)},
        {"role": "user", "content": user_prompt(workspace.run_dir)},
    ]
    for turn in range(1, MAX_TURNS + 1):
        log(workspace.run_dir, f"turn {turn}/{MAX_TURNS}")
        data = chat(api_key, api_model, messages, effort)
        add_usage(workspace, data.get("usage") if isinstance(data.get("usage"), dict) else None)
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError(f"empty choices: {json.dumps(data)[:400]}")
        message = choices[0].get("message") or {}
        tool_calls = message.get("tool_calls") or []
        assistant: dict[str, Any] = {"role": "assistant", "content": message.get("content") or ""}
        if tool_calls:
            assistant["tool_calls"] = tool_calls
        messages.append(assistant)
        if not tool_calls:
            text = extract_text(message.get("content"))
            log(workspace.run_dir, f"model stop: {text[:240]}")
            return
        for call in tool_calls:
            fn = call.get("function") or {}
            name = str(fn.get("name") or "")
            raw_args = fn.get("arguments") or "{}"
            try:
                args = json.loads(raw_args) if isinstance(raw_args, str) else dict(raw_args)
            except json.JSONDecodeError:
                args = {}
            log(workspace.run_dir, f"tool {name}")
            try:
                result = workspace.dispatch(name, args)
            except Exception as exc:
                result = f"error: {exc}"
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.get("id") or name,
                    "content": result,
                }
            )
    log(workspace.run_dir, "hit MAX_TURNS")


def finalize_if_needed(workspace: Workspace, status: str) -> None:
    if workspace.receipt_written:
        return
    usd = plan_nominal_usd(workspace.tokens_in, workspace.tokens_out)
    receipt = {
        "status": status,
        "model_id": workspace.model,
        "usd": usd,
        "tokens_in": workspace.tokens_in,
        "tokens_out": workspace.tokens_out,
        "workers_ran": 0,
        "cost_source": "marionette_plan_nominal",
    }
    path = workspace.run_dir / "receipts" / "job.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    emit(workspace.run_dir, "receipt_written", {"status": status, "model_id": workspace.model})


def probe(api_key: str, api_model: str, effort: str) -> int:
    body = {
        "model": api_model,
        "messages": [{"role": "user", "content": "Reply with the single word pong."}],
        "thinking": {"type": "enabled"},
        "reasoning_effort": effort,
        "max_tokens": 64,
    }
    request = urllib.request.Request(
        env_first("ZAI_CHAT_URL", default=CODING_URL),
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        print(f"probe_http {exc.code}", file=sys.stderr)
        print(detail, file=sys.stderr)
        return 1
    usage = data.get("usage") or {}
    model = data.get("model") or api_model
    print(f"probe_ok model={model} prompt_tokens={usage.get('prompt_tokens')} completion_tokens={usage.get('completion_tokens')}")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    api_key = load_zai_key()
    api_model = env_first("ZAI_MODEL", default="glm-5.3")
    effort = env_first("STRONGORC_REASONING_EFFORT", default="high")
    if argv == ["--probe"]:
        return probe(api_key, api_model, effort)
    run_dir = resolve_run_dir()
    model = env_first("STRONGORC_MODEL", "DURABLE_ORCH_MODEL", default=api_model)
    workspace = Workspace(run_dir, model)
    try:
        run_loop(workspace, api_key, api_model, effort)
        finalize_if_needed(workspace, "failed")
        return 0
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        log(run_dir, f"agent_error {type(exc).__name__}: {exc}")
        log(run_dir, traceback.format_exc())
        emit(run_dir, "job_failed", {"reason": type(exc).__name__})
        finalize_if_needed(workspace, "failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
