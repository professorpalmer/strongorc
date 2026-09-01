from __future__ import annotations

"""StrongOrc command agent for OpenRouter (OpenAI-compatible).

Stdlib only. Tools are confined to $STRONGORC_RUN_DIR — no parent-repo
reads. The default jail has no shell. ``--allow-shell`` adds
``run_command`` with cwd set to the run dir. Cursor SDK is not used.

Key: OPENROUTER_API_KEY, else Marionette ~/.pmharness/state/keys.json
slot \"openrouter\". Never prints the key.
"""

import json
import math
import os
import subprocess
import sys
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
GENERATION_URL = "https://openrouter.ai/api/v1/generation"
MODEL_CATALOG_URL = "https://openrouter.ai/api/v1/models"
MARIONETTE_KEYS = Path.home() / ".pmharness" / "state" / "keys.json"
DEFAULT_MODEL = "google/gemini-3.7-flash"
LIST_IN_PER_MTOK = 0.375
LIST_OUT_PER_MTOK = 1.875
MAX_TURNS = 120
REQUEST_TIMEOUT = 180
WAIT_CAP_SECONDS = 3600
READ_LIMIT = 80_000
COMMAND_TIMEOUT = 60
COMMAND_OUTPUT_LIMIT = 4000
GENERATION_USAGE_WAIT_SECONDS = 20

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
            "name": "dispatch_worker",
            "description": (
                "Dispatch one harness-backed worker. Returns a sealed dispatch id and "
                "report path; call consume_worker_report to read the result."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "worker_id": {"type": "string"},
                    "assignment": {"type": "object"},
                },
                "required": ["worker_id", "assignment"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consume_worker_report",
            "description": (
                "Read a harness-sealed worker report by dispatch id and record "
                "parent-verifiable artifact consumption."
            ),
            "parameters": {
                "type": "object",
                "properties": {"dispatch_id": {"type": "string"}},
                "required": ["dispatch_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_pytest",
            "description": "Run pytest on a relative path inside the workspace.",
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
                "Block this process. Use after writing the interruption checkpoint "
                "on the first spawn so the harness can restart the process."
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
                "Return measured tokens and USD. Prefer OpenRouter usage.cost. "
                "Do not write usd=0 if tokens are nonzero."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_receipt",
            "description": (
                "Write receipts/job.json. model_id must equal STRONGORC_MODEL. "
                "usd and token fields are overwritten with measured OpenRouter totals."
            ),
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

SHELL_TOOL = {
    "type": "function",
    "function": {
        "name": "run_command",
        "description": "Run a POSIX command with cwd set to the workspace root.",
        "parameters": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
    },
}


def env_first(*names: str, default: str = "") -> str:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return default


def load_openrouter_key() -> str:
    for name in ("OPENROUTER_API_KEY", "OR_API_KEY"):
        value = os.environ.get(name)
        if value:
            return value
    if not MARIONETTE_KEYS.is_file():
        raise SystemExit("no OpenRouter key in env or Marionette ~/.pmharness/state/keys.json")
    data = json.loads(MARIONETTE_KEYS.read_text(encoding="utf-8"))
    key = data.get("openrouter")
    if not key:
        raise SystemExit("Marionette keys.json has no openrouter slot")
    return str(key)


def list_usd(tokens_in: int, tokens_out: int) -> float:
    return (tokens_in / 1_000_000.0) * LIST_IN_PER_MTOK + (tokens_out / 1_000_000.0) * LIST_OUT_PER_MTOK


def resolve_run_dir() -> Path:
    raw = env_first("STRONGORC_RUN_DIR", "DURABLE_ORCH_RUN_DIR")
    if not raw:
        raise SystemExit("STRONGORC_RUN_DIR is required")
    return Path(raw).resolve()


def checkout_root() -> Path:
    return Path(__file__).resolve().parents[1]


def tools_for(allow_shell: bool) -> list[dict[str, Any]]:
    if not allow_shell:
        return list(TOOLS)
    return list(TOOLS) + [SHELL_TOOL]


def command_touches_checkout(command: str) -> bool:
    return str(checkout_root()) in command


def command_env(run_dir: Path) -> dict[str, str]:
    root = str(checkout_root())
    env = {key: value for key, value in os.environ.items() if root not in value}
    env["HOME"] = str(run_dir)
    env["TMPDIR"] = str(run_dir)
    return env


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
    path = run_dir / ".harness" / "openrouter_agent.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def write_usage(
    run_dir: Path,
    tokens_in: int,
    tokens_out: int,
    usd: float,
    source: str,
    input_per_mtok_usd: float = LIST_IN_PER_MTOK,
    output_per_mtok_usd: float = LIST_OUT_PER_MTOK,
) -> None:
    payload = {
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "usd": usd,
        "cost_source": source,
        "input_per_mtok_usd": input_per_mtok_usd,
        "output_per_mtok_usd": output_per_mtok_usd,
    }
    path = run_dir / ".harness" / "openrouter_usage.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_usage_file(run_dir: Path) -> dict[str, Any] | None:
    path = run_dir / ".harness" / "openrouter_usage.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def provider_cost(usage: dict[str, Any]) -> float | None:
    billed = usage.get("cost")
    if billed is None and isinstance(usage.get("cost_details"), dict):
        billed = usage["cost_details"].get("total_cost") or usage["cost_details"].get(
            "upstream_inference_cost"
        )
    return float(billed) if billed is not None else None


def fetch_generation_usage(
    api_key: str,
    generation_id: str,
) -> dict[str, Any] | None:
    """Recover authoritative cost when the chat response omits it."""
    query = urllib.parse.urlencode({"id": generation_id})
    request = urllib.request.Request(
        f"{GENERATION_URL}?{query}",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    deadline = time.monotonic() + GENERATION_USAGE_WAIT_SECONDS
    while True:
        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (
            TimeoutError,
            urllib.error.HTTPError,
            urllib.error.URLError,
            json.JSONDecodeError,
        ):
            payload = {}
        generation = payload.get("data") if isinstance(payload, dict) else None
        if isinstance(generation, dict):
            billed = generation.get("total_cost")
            if billed is None:
                billed = generation.get("usage")
            if billed is not None:
                return {
                    "prompt_tokens": int(
                        generation.get("tokens_prompt")
                        or generation.get("native_tokens_prompt")
                        or 0
                    ),
                    "completion_tokens": int(
                        generation.get("tokens_completion")
                        or generation.get("native_tokens_completion")
                        or 0
                    ),
                    "cost": float(billed),
                }
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return None
        time.sleep(min(5.0, remaining))


def fetch_model_rates(api_key: str, model: str) -> tuple[float, float] | None:
    request = urllib.request.Request(
        MODEL_CATALOG_URL,
        headers={"Authorization": f"Bearer {api_key}"},
    )
    payload: dict[str, Any] = {}
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
                payload = json.loads(response.read().decode("utf-8"))
            break
        except (
            TimeoutError,
            urllib.error.HTTPError,
            urllib.error.URLError,
            json.JSONDecodeError,
        ):
            if attempt == 2:
                return None
            time.sleep(2**attempt)
    entries = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(entries, list):
        return None
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("id") != model:
            continue
        pricing = entry.get("pricing")
        if not isinstance(pricing, dict):
            return None
        try:
            return float(pricing["prompt"]), float(pricing["completion"])
        except (KeyError, TypeError, ValueError):
            return None
    return None


def response_usage(
    api_key: str,
    model: str,
    response: dict[str, Any],
    messages: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    usage = response.get("usage")
    measured = dict(usage) if isinstance(usage, dict) else None
    if measured is not None and provider_cost(measured) is not None:
        return measured
    generation_id = response.get("id")
    if isinstance(generation_id, str) and generation_id:
        recovered = fetch_generation_usage(api_key, generation_id)
        if recovered is not None:
            return recovered
    rates = fetch_model_rates(api_key, model)
    if rates is None:
        return measured
    if measured is None:
        prompt_tokens = math.ceil(len(json.dumps(messages or [])) / 3)
        choices = response.get("choices") or []
        message = choices[0].get("message") if choices else {}
        completion_tokens = max(1, math.ceil(len(json.dumps(message or {})) / 3))
        measured = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cost_source": "openrouter_list_estimate",
        }
    else:
        prompt_tokens = int(measured.get("prompt_tokens") or 0)
        completion_tokens = int(measured.get("completion_tokens") or 0)
        measured["cost_source"] = "openrouter_list"
    measured["estimated_cost"] = (
        prompt_tokens * rates[0] + completion_tokens * rates[1]
    )
    measured["input_per_mtok_usd"] = rates[0] * 1_000_000
    measured["output_per_mtok_usd"] = rates[1] * 1_000_000
    return measured


def append_generation(run_dir: Path, usage: dict[str, Any]) -> None:
    billed = provider_cost(usage)
    estimated = usage.get("estimated_cost")
    line = {
        "prompt_tokens": int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0),
        "completion_tokens": int(usage.get("completion_tokens") or usage.get("output_tokens") or 0),
        "cost": billed if billed is not None else estimated,
        "cost_source": (
            "provider"
            if billed is not None
            else str(usage.get("cost_source") or "openrouter_list")
        ),
    }
    path = run_dir / ".harness" / "openrouter_generations.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(line, sort_keys=True) + "\n")


def list_tree(root: Path, run_dir: Path) -> str:
    if not root.exists():
        return "missing"
    if root.is_file():
        return root.relative_to(run_dir).as_posix()
    lines: list[str] = []
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(run_dir).as_posix()
        if path.is_dir() or rel.startswith(".harness/"):
            continue
        lines.append(rel)
        if len(lines) >= 400:
            lines.append("...truncated")
            break
    return "\n".join(lines) if lines else "(empty)"


class Workspace:
    def __init__(self, run_dir: Path, model: str, allow_shell: bool = False) -> None:
        self.run_dir = run_dir
        self.model = model
        self.allow_shell = allow_shell
        raw_budget = env_first("STRONGORC_MAX_USD", "DURABLE_ORCH_MAX_USD")
        self.max_usd = float(raw_budget) if raw_budget else None
        if self.max_usd is not None and (
            not math.isfinite(self.max_usd) or self.max_usd <= 0
        ):
            raise ValueError("STRONGORC_MAX_USD must be positive")
        self.tokens_in = 0
        self.tokens_out = 0
        self.usd = 0.0
        self.cost_source = "openrouter_list"
        self.input_per_mtok_usd = LIST_IN_PER_MTOK
        self.output_per_mtok_usd = LIST_OUT_PER_MTOK
        persisted = read_usage_file(run_dir)
        if persisted:
            self.tokens_in = int(persisted.get("tokens_in") or 0)
            self.tokens_out = int(persisted.get("tokens_out") or 0)
            self.usd = float(persisted.get("usd") or 0)
            source = str(persisted.get("cost_source") or "")
            if source:
                self.cost_source = source
            self.input_per_mtok_usd = float(
                persisted.get("input_per_mtok_usd") or self.input_per_mtok_usd
            )
            self.output_per_mtok_usd = float(
                persisted.get("output_per_mtok_usd") or self.output_per_mtok_usd
            )
        self.receipt_written = (run_dir / "receipts" / "job.json").is_file()

    def billed_usd(self) -> float:
        if self.usd > 0:
            return self.usd
        return (
            self.tokens_in * self.input_per_mtok_usd
            + self.tokens_out * self.output_per_mtok_usd
        ) / 1_000_000

    def budget_exhausted(self) -> bool:
        return self.max_usd is not None and self.billed_usd() >= self.max_usd

    def usage_payload(self) -> dict[str, Any]:
        return {
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "usd": self.billed_usd(),
            "cost_source": self.cost_source if self.usd > 0 else "openrouter_list",
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
        if name == "dispatch_worker":
            from strongorc.worker_broker import WorkerClient

            try:
                client = WorkerClient.from_environment(dict(os.environ))
                dispatched = client.dispatch(
                    str(args.get("worker_id") or ""),
                    args.get("assignment") or {},
                )
            except (RuntimeError, ValueError) as exc:
                return f"worker dispatch failed: {exc}"
            emit(
                self.run_dir,
                "worker_started",
                {
                    "worker": str(args.get("worker_id") or ""),
                    "dispatch_id": dispatched["dispatch_id"],
                },
            )
            emit(
                self.run_dir,
                "worker_finished",
                {
                    "worker": str(args.get("worker_id") or ""),
                    "dispatch_id": dispatched["dispatch_id"],
                    "report_path": dispatched["report_path"],
                },
            )
            return json.dumps(dispatched, sort_keys=True)
        if name == "consume_worker_report":
            from strongorc.worker_broker import WorkerClient

            dispatch_id = str(args.get("dispatch_id") or "")
            try:
                client = WorkerClient.from_environment(dict(os.environ))
                report = client.consume(dispatch_id)
            except (RuntimeError, ValueError) as exc:
                return f"worker report consume failed: {exc}"
            emit(
                self.run_dir,
                "artifact_consumed",
                {"dispatch_id": dispatch_id},
            )
            return json.dumps(report, sort_keys=True)
        if name == "run_pytest":
            target = confined(self.run_dir, str(args["path"]))
            env = os.environ.copy()
            env["PYTHONPATH"] = str(self.run_dir)
            completed = subprocess.run(
                [sys.executable, "-m", "pytest", str(target), "-q", "--tb=line"],
                cwd=self.run_dir,
                env=env,
                check=False,
                capture_output=True,
                text=True,
                timeout=60,
            )
            out = (completed.stdout or "") + (completed.stderr or "")
            return f"exit {completed.returncode}\n{out[:4000]}"
        if name == "run_node":
            target = confined(self.run_dir, str(args["path"]))
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
        if name == "run_command":
            if not self.allow_shell:
                return "unknown tool run_command"
            command = str(args.get("command") or "").strip()
            if not command:
                return "error: command is required"
            if command_touches_checkout(command):
                return "error: command may not reference the bench checkout"
            try:
                completed = subprocess.run(
                    command,
                    shell=True,
                    cwd=self.run_dir,
                    env=command_env(self.run_dir),
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=COMMAND_TIMEOUT,
                )
            except subprocess.TimeoutExpired:
                return f"error: command timed out after {COMMAND_TIMEOUT}s"
            out = (completed.stdout or "") + (completed.stderr or "")
            return f"exit {completed.returncode}\n{out[:COMMAND_OUTPUT_LIMIT]}"
        if name == "wait":
            if env_first("STRONGORC_EXPECT_INTERRUPT", "DURABLE_ORCH_EXPECT_INTERRUPT") != "1":
                log(self.run_dir, "wait skipped; this spawn is not interrupted")
                return "no harness interrupt on this spawn; finish the job"
            seconds = int(args.get("seconds") or WAIT_CAP_SECONDS)
            seconds = max(1, min(seconds, WAIT_CAP_SECONDS))
            log(self.run_dir, f"waiting {seconds}s for harness interrupt")
            time.sleep(seconds)
            return "wait finished without interruption"
        if name == "measured_usage":
            return json.dumps(self.usage_payload(), sort_keys=True)
        if name == "write_receipt":
            receipt = {
                "status": str(args["status"]),
                "model_id": self.model,
                "usd": self.billed_usd(),
                "tokens_in": self.tokens_in,
                "tokens_out": self.tokens_out,
                "workers_ran": int(args["workers_ran"]),
                "cost_source": self.cost_source if self.usd > 0 else "openrouter_list",
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


def add_usage(workspace: Workspace, usage: dict[str, Any] | None) -> bool:
    if not usage:
        return False
    if usage.get("input_per_mtok_usd") is not None:
        workspace.input_per_mtok_usd = float(usage["input_per_mtok_usd"])
    if usage.get("output_per_mtok_usd") is not None:
        workspace.output_per_mtok_usd = float(usage["output_per_mtok_usd"])
    workspace.tokens_in += int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
    workspace.tokens_out += int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
    billed = provider_cost(usage)
    priced = billed
    if priced is None and usage.get("estimated_cost") is not None:
        priced = float(usage["estimated_cost"])
    new_source = (
        "openrouter_usage"
        if billed is not None
        else str(usage.get("cost_source") or "openrouter_list")
    )
    if priced is not None and workspace.usd > 0 and workspace.cost_source != new_source:
        workspace.cost_source = "mixed"
    elif priced is not None:
        workspace.cost_source = new_source
    if priced is not None:
        workspace.usd += priced
    append_generation(workspace.run_dir, usage)
    write_usage(
        workspace.run_dir,
        workspace.tokens_in,
        workspace.tokens_out,
        workspace.billed_usd(),
        workspace.cost_source if workspace.usd > 0 else "openrouter_list",
        workspace.input_per_mtok_usd,
        workspace.output_per_mtok_usd,
    )
    return priced is not None


def chat(
    api_key: str,
    model: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    body = {
        "model": model,
        "messages": messages,
        "tools": tools if tools is not None else TOOLS,
        "tool_choice": "auto",
        "parallel_tool_calls": True,
        "usage": {"include": True},
        "max_tokens": 8192,
    }
    last_error: Exception | None = None
    for attempt in range(6):
        request = urllib.request.Request(
            env_first("OPENROUTER_CHAT_URL", default=CHAT_URL),
            data=json.dumps(body).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/professorpalmer/strongorc",
                "X-Title": "StrongOrc",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:800]
            last_error = RuntimeError(f"openrouter HTTP {exc.code}: {detail}")
            if exc.code not in {402, 408, 409, 429, 502, 503, 529} or attempt == 5:
                raise last_error from exc
            # 402 in-flight budget: OpenRouter asks for Retry-After ~120s.
            time.sleep(120 if exc.code == 402 else 2 ** attempt)
        except (TimeoutError, urllib.error.URLError) as exc:
            last_error = RuntimeError(f"openrouter transport: {exc}")
            if attempt == 5:
                raise last_error from exc
            time.sleep(2 ** attempt)
    raise last_error or RuntimeError("openrouter failed")


def system_prompt(
    track: str,
    model: str,
    resume: bool,
    allow_shell: bool = False,
    expect_interrupt: bool = False,
) -> str:
    if resume:
        resume_line = (
            "This process was respawned after a sealed harness interruption "
            "(STRONGORC_RESUME=1). "
            "Read durable state on disk. Do not replay finished work from memory."
        )
    elif expect_interrupt:
        resume_line = (
            "First spawn (STRONGORC_RESUME is not 1). This spawn is interrupted. "
            "If the task prompt says to checkpoint and wait, write the checkpoint "
            "then call wait. Finishing the whole job before the interrupt is a fail."
        )
    else:
        resume_line = (
            "This spawn is not interrupted. Do not call wait. Finish the job."
        )
    prompt = f"""You are a live StrongOrc command agent. Workspace is $STRONGORC_RUN_DIR.
Track={track}. Invoked model id: {model}.

{resume_line}

The task prompt and the workspace tree are the spec. Follow them.

Contract:
- Outcome files and protocol both have to pass. The oracle re-runs hidden tests that are not in the seed.
- After a resume, re-read the workspace. Files may have changed since the first spawn.
- Emit protocol events with emit_event. Forbidden events fail the trial even if files look green.
- On orchestrator tasks, dispatch workers. Do not emit orchestrator_wrote_solution.
- On orchestrator tasks, status=completed with workers_ran=0 is a dead-swarm fail.
- On worker tasks, workers_ran must be 0; you are the worker and do not spawn children.
- model_id in the receipt is written as {model}. usd must not be 0 when tokens are nonzero.
  Call measured_usage, then write_receipt.

Tools can only see this workspace. Use them. When the job is done, emit job_completed and write_receipt, then stop.
"""
    if allow_shell:
        return prompt + "\nrun_command runs a POSIX command with cwd set to this workspace.\n"
    return prompt


def user_prompt(run_dir: Path) -> str:
    prompt_path = Path(env_first("STRONGORC_PROMPT", "DURABLE_ORCH_PROMPT", default=str(run_dir / "PROMPT.md")))
    prompt = prompt_path.read_text(encoding="utf-8") if prompt_path.is_file() else ""
    tree = list_tree(run_dir, run_dir)
    return f"{prompt}\n\nWorkspace files:\n{tree}\n"


def run_loop(workspace: Workspace, api_key: str, api_model: str) -> None:
    track = env_first("STRONGORC_TRACK", "DURABLE_ORCH_TRACK")
    resume = env_first("STRONGORC_RESUME", "DURABLE_ORCH_RESUME") == "1"
    expect_interrupt = env_first("STRONGORC_EXPECT_INTERRUPT", "DURABLE_ORCH_EXPECT_INTERRUPT") == "1"
    initial_messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": system_prompt(
                track,
                workspace.model,
                resume,
                workspace.allow_shell,
                expect_interrupt,
            ),
        },
        {"role": "user", "content": user_prompt(workspace.run_dir)},
    ]
    messages = list(initial_messages)
    incomplete_stops = 0
    provider_refusals = 0
    for turn in range(1, MAX_TURNS + 1):
        if workspace.budget_exhausted():
            log(
                workspace.run_dir,
                f"budget exhausted at ${workspace.billed_usd():.6f} "
                f"(cap ${workspace.max_usd:.6f})",
            )
            emit(workspace.run_dir, "job_failed", {"reason": "budget_exhausted"})
            return
        log(workspace.run_dir, f"turn {turn}/{MAX_TURNS}")
        data = chat(api_key, api_model, messages, tools=tools_for(workspace.allow_shell))
        measured = add_usage(
            workspace,
            response_usage(api_key, api_model, data, messages),
        )
        if workspace.max_usd is not None and not measured:
            raise RuntimeError("budgeted OpenRouter response missing usage.cost")
        if workspace.budget_exhausted():
            log(
                workspace.run_dir,
                f"budget exhausted at ${workspace.billed_usd():.6f} "
                f"(cap ${workspace.max_usd:.6f})",
            )
            emit(workspace.run_dir, "job_failed", {"reason": "budget_exhausted"})
            return
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError(f"empty choices: {json.dumps(data)[:400]}")
        choice = choices[0]
        message = choice.get("message") or {}
        tool_calls = message.get("tool_calls") or []
        log(
            workspace.run_dir,
            "response "
            f"provider={data.get('provider')!r} "
            f"finish={choice.get('finish_reason')!r} "
            f"native_finish={choice.get('native_finish_reason')!r} "
            f"tools={len(tool_calls)}",
        )
        if choice.get("finish_reason") == "content_filter" and workspace.receipt_written:
            return
        if choice.get("finish_reason") == "content_filter":
            provider_refusals += 1
            if provider_refusals == 1:
                log(workspace.run_dir, "reset after transient provider refusal")
                messages = [
                    *initial_messages,
                    {
                        "role": "user",
                        "content": (
                            "The prior provider response was filtered before an authoritative "
                            "receipt. Re-read durable workspace state and finish the job."
                        ),
                    },
                ]
                incomplete_stops = 0
                continue
            emit(workspace.run_dir, "job_failed", {"reason": "provider_refusal"})
            return
        assistant: dict[str, Any] = {"role": "assistant", "content": message.get("content") or ""}
        if tool_calls:
            assistant["tool_calls"] = tool_calls
            incomplete_stops = 0
        messages.append(assistant)
        if not tool_calls:
            text = extract_text(message.get("content"))
            log(workspace.run_dir, f"model stop: {text[:240]}")
            if workspace.receipt_written:
                return
            incomplete_stops += 1
            wait_line = (
                "This spawn is interrupted; checkpoint then wait if the prompt says so."
                if expect_interrupt
                else "This spawn is not interrupted; do not call wait."
            )
            if incomplete_stops >= 3:
                log(workspace.run_dir, "reset stalled conversation")
                messages = [
                    *initial_messages,
                    {
                        "role": "user",
                        "content": (
                            "The prior response stream stalled before an authoritative receipt. "
                            f"{wait_line} Re-read durable workspace state and finish the job."
                        ),
                    },
                ]
                incomplete_stops = 0
                continue
            log(workspace.run_dir, "incomplete stop; nudge")
            messages.append(
                {
                    "role": "user",
                    "content": (
                        f"The job has no authoritative receipt yet. {wait_line} "
                        "Continue using tools until the outcome and receipt are complete."
                    ),
                }
            )
            continue
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
        if workspace.receipt_written:
            return
    log(workspace.run_dir, "hit MAX_TURNS")
    emit(workspace.run_dir, "job_failed", {"reason": "max_turns"})


def refresh_receipt_spend(workspace: Workspace) -> None:
    path = workspace.run_dir / "receipts" / "job.json"
    if not path.is_file():
        return
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if not isinstance(receipt, dict):
        return
    receipt["usd"] = workspace.billed_usd()
    receipt["tokens_in"] = workspace.tokens_in
    receipt["tokens_out"] = workspace.tokens_out
    receipt["cost_source"] = workspace.cost_source if workspace.usd > 0 else "openrouter_list"
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def finalize_if_needed(workspace: Workspace, status: str) -> None:
    if workspace.receipt_written:
        refresh_receipt_spend(workspace)
        return
    receipt = {
        "status": status,
        "model_id": workspace.model,
        "usd": workspace.billed_usd(),
        "tokens_in": workspace.tokens_in,
        "tokens_out": workspace.tokens_out,
        "workers_ran": 0,
        "cost_source": workspace.cost_source if workspace.usd > 0 else "openrouter_list",
    }
    path = workspace.run_dir / "receipts" / "job.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    emit(workspace.run_dir, "receipt_written", {"status": status, "model_id": workspace.model})


def probe(api_key: str, api_model: str) -> int:
    body = {
        "model": api_model,
        "messages": [{"role": "user", "content": "Reply with the single word pong."}],
        "max_tokens": 32,
    }
    request = urllib.request.Request(
        env_first("OPENROUTER_CHAT_URL", default=CHAT_URL),
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/professorpalmer/strongorc",
            "X-Title": "StrongOrc",
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
    print(
        f"probe_ok model={model} prompt_tokens={usage.get('prompt_tokens')} "
        f"completion_tokens={usage.get('completion_tokens')} cost={usage.get('cost')}"
    )
    return 0


def parse_agent_argv(argv: list[str]) -> tuple[bool, list[str]]:
    allow_shell = os.environ.get("STRONGORC_ALLOW_SHELL") == "1"
    kept: list[str] = []
    for item in argv:
        if item == "--allow-shell":
            allow_shell = True
        else:
            kept.append(item)
    return allow_shell, kept


def terminal_failure_reason(exc: Exception) -> str:
    message = str(exc)
    for status, reason in (
        ("401", "provider_authentication"),
        ("402", "provider_payment_required"),
        ("429", "provider_rate_limit"),
    ):
        if f"openrouter HTTP {status}:" in message:
            return reason
    return type(exc).__name__


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    allow_shell, argv = parse_agent_argv(argv)
    api_model = env_first(
        "OPENROUTER_MODEL",
        "OR_MODEL",
        "STRONGORC_MODEL",
        "DURABLE_ORCH_MODEL",
        default=DEFAULT_MODEL,
    )
    is_probe = argv == ["--probe"]
    if not is_probe and not env_first("STRONGORC_MAX_USD", "DURABLE_ORCH_MAX_USD"):
        raise SystemExit("STRONGORC_MAX_USD is required for paid OpenRouter runs")
    api_key = load_openrouter_key()
    if is_probe:
        return probe(api_key, api_model)
    run_dir = resolve_run_dir()
    model = env_first("STRONGORC_MODEL", "DURABLE_ORCH_MODEL", default=api_model)
    workspace = Workspace(run_dir, model, allow_shell=allow_shell)
    try:
        run_loop(workspace, api_key, api_model)
        finalize_if_needed(workspace, "failed")
        return 0
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        log(run_dir, f"agent_error {type(exc).__name__}: {exc}")
        log(run_dir, traceback.format_exc())
        emit(run_dir, "job_failed", {"reason": terminal_failure_reason(exc)})
        finalize_if_needed(workspace, "failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
