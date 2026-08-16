from __future__ import annotations

"""StrongOrc command agent for Composer 2.5 via the Cursor SDK.

The `agent` CLI on this Mac dies on a keychain gate even with CURSOR_API_KEY.
This wrapper talks to @cursor/sdk the same way Puppetmaster does: Node runner
+ API key, no keychain login.

Stdlib only. Never prints the key.

Auth: CURSOR_API_KEY, else Marionette ~/.pmharness/state/keys.json slot
\"cursor\".
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

MARIONETTE_KEYS = Path.home() / ".pmharness" / "state" / "keys.json"
RUNNER = Path("/Users/carypalmer/Projects/Puppetmaster/puppetmaster/cursor_sdk_runner.mjs")
NODE_MODULES = Path("/Users/carypalmer/Projects/Puppetmaster/node_modules")
PLAN_IN_PER_MTOK = 0.5
PLAN_OUT_PER_MTOK = 2.5
WAIT_CAP_SECONDS = 3600


def env_first(*names: str, default: str = "") -> str:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return default


def load_cursor_key() -> tuple[str, str]:
    if MARIONETTE_KEYS.is_file():
        data = json.loads(MARIONETTE_KEYS.read_text(encoding="utf-8"))
        key = data.get("cursor")
        if key:
            return str(key), "marionette"
    for name in ("CURSOR_API_KEY", "CURSOR_AUTH_TOKEN"):
        value = os.environ.get(name)
        if value:
            return value, "env"
    raise SystemExit("no Cursor API key in Marionette ~/.pmharness/state/keys.json or env")


def resolve_run_dir() -> Path:
    raw = env_first("STRONGORC_RUN_DIR", "DURABLE_ORCH_RUN_DIR")
    if not raw:
        raise SystemExit("STRONGORC_RUN_DIR is required")
    return Path(raw).resolve()


def log(run_dir: Path, message: str) -> None:
    line = message.rstrip()
    print(line, file=sys.stderr, flush=True)
    path = run_dir / ".harness" / "cursor_agent.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def list_tree(run_dir: Path) -> str:
    lines: list[str] = []
    for path in sorted(run_dir.rglob("*")):
        if path.is_dir():
            continue
        lines.append(path.relative_to(run_dir).as_posix())
        if len(lines) >= 400:
            lines.append("...truncated")
            break
    return "\n".join(lines) if lines else "(empty)"


def plan_nominal_usd(tokens_in: int, tokens_out: int) -> float:
    return (tokens_in / 1_000_000.0) * PLAN_IN_PER_MTOK + (tokens_out / 1_000_000.0) * PLAN_OUT_PER_MTOK


def build_prompt(run_dir: Path, model: str) -> str:
    task_id = env_first("STRONGORC_TASK_ID", "DURABLE_ORCH_TASK_ID")
    track = env_first("STRONGORC_TRACK", "DURABLE_ORCH_TRACK")
    resume = env_first("STRONGORC_RESUME", "DURABLE_ORCH_RESUME") == "1"
    prompt_path = Path(
        env_first("STRONGORC_PROMPT", "DURABLE_ORCH_PROMPT", default=str(run_dir / "PROMPT.md"))
    )
    task_prompt = prompt_path.read_text(encoding="utf-8") if prompt_path.is_file() else ""
    resume_line = (
        "Resume spawn (STRONGORC_RESUME=1). Re-read the workspace. Files may have "
        "changed since the first spawn. Do not replay the first read from memory."
        if resume
        else (
            "First spawn. If the task says to checkpoint and wait, write the "
            "checkpoint file and stop. The wrapper sleeps so the harness can SIGKILL. "
            "Finishing the whole job before the interrupt is a fail."
        )
    )
    return f"""You are a live StrongOrc command agent in this workspace.
Task {task_id} track={track}. Invoked model id: {model}.

{resume_line}

The task prompt and the tree are the spec. Follow them. Do not invent a shortcut
that skips a gate, lease, nonce, budget, or live test.

Contract:
- Outcome files and protocol both have to pass. The oracle re-runs hidden Node
  tests that are not in the seed. A visible console.log("ok") is not a pass.
- After a resume, re-read the workspace.
- Append protocol events to protocol.jsonl, one JSON object per line:
  {{"type":"<event>","payload":{{}}}}
- On orchestrator tasks, dispatch workers. Do not emit orchestrator_wrote_solution.
- Write receipts/job.json with status, model_id, usd, tokens_in, tokens_out,
  workers_ran. model_id must be exactly {model}.
- status=completed with workers_ran=0 is a dead-swarm fail.
- usd must not be 0 when tokens or workers are nonzero. Composer 2.5 is
  plan-nominal $0.5 / $2.5 per MTok if you have no better usage number.
- Do not sleep forever. Write the checkpoint and stop; the wrapper waits.

Task prompt:
{task_prompt}

Workspace files:
{list_tree(run_dir)}
"""


def wait_markers(resume: bool, resume_step: int) -> list[str]:
    if not resume:
        return ["state/checkpoint.json", "state/checkpoint1.json"]
    if resume_step == 1:
        return ["state/checkpoint2.json"]
    return []


def maybe_wait_for_kill(run_dir: Path) -> None:
    if (run_dir / "receipts" / "job.json").is_file():
        return
    resume = env_first("STRONGORC_RESUME", "DURABLE_ORCH_RESUME") == "1"
    step_raw = env_first("STRONGORC_RESUME_STEP", "DURABLE_ORCH_RESUME_STEP", default="0")
    try:
        step = int(step_raw)
    except ValueError:
        step = 0
    for relative in wait_markers(resume, step):
        if (run_dir / relative).is_file():
            log(run_dir, f"checkpoint {relative} present; waiting for harness SIGKILL")
            time.sleep(WAIT_CAP_SECONDS)
            return


def parse_usage(stdout: str) -> dict:
    text = stdout.strip()
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start = text.rfind("{")
        if start < 0:
            return {}
        try:
            data = json.loads(text[start:])
        except json.JSONDecodeError:
            return {}
    usage = data.get("usage") if isinstance(data, dict) else None
    return usage if isinstance(usage, dict) else {}


def finalize_if_needed(run_dir: Path, model: str, usage: dict) -> None:
    path = run_dir / "receipts" / "job.json"
    if path.is_file():
        return
    tokens_in = int(usage.get("inputTokens") or 0)
    tokens_out = int(usage.get("outputTokens") or 0)
    events = []
    protocol = run_dir / "protocol.jsonl"
    if protocol.is_file():
        for line in protocol.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    types = [str(item.get("type") or "") for item in events]
    workers = types.count("worker_started")
    completed = "job_completed" in types
    receipt = {
        "status": "completed" if completed else "failed",
        "model_id": model,
        "usd": plan_nominal_usd(tokens_in, tokens_out),
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "workers_ran": workers,
        "cost_source": "marionette_plan_nominal",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def ensure_git(run_dir: Path) -> None:
    if (run_dir / ".git").is_dir():
        return
    subprocess.run(["git", "init"], cwd=run_dir, check=False, capture_output=True)


def run_cursor_sdk(run_dir: Path, model: str, api_model: str, api_key: str) -> dict:
    if not RUNNER.is_file():
        raise SystemExit(f"missing Cursor SDK runner: {RUNNER}")
    ensure_git(run_dir)
    payload = {
        "prompt": build_prompt(run_dir, model),
        "cwd": str(run_dir),
        "model": api_model,
    }
    env = os.environ.copy()
    env["CURSOR_API_KEY"] = api_key
    env["PUPPETMASTER_CURSOR_INPUT"] = json.dumps(payload, sort_keys=True)
    env["NODE_PATH"] = str(NODE_MODULES)
    log(run_dir, f"spawn cursor-sdk model={api_model}")
    completed = subprocess.run(
        ["node", str(RUNNER)],
        cwd=run_dir,
        env=env,
        check=False,
        text=True,
        capture_output=True,
    )
    out_path = run_dir / ".harness" / "cursor_agent.stdout.log"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        (completed.stdout or "") + "\n--- stderr ---\n" + (completed.stderr or ""),
        encoding="utf-8",
    )
    log(run_dir, f"sdk_exit {completed.returncode}")
    if completed.returncode != 0 and completed.stderr:
        tail = completed.stderr.strip().splitlines()
        if tail:
            log(run_dir, tail[-1][:300])
    return parse_usage(completed.stdout or "")


def main() -> int:
    run_dir = resolve_run_dir()
    api_model = env_first("CURSOR_MODEL", default="composer-2.5")
    model = env_first("STRONGORC_MODEL", "DURABLE_ORCH_MODEL", default=api_model)
    api_key, key_source = load_cursor_key()
    log(run_dir, f"key_source {key_source}")
    try:
        usage = run_cursor_sdk(run_dir, model, api_model, api_key)
        maybe_wait_for_kill(run_dir)
        finalize_if_needed(run_dir, model, usage)
        return 0
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        log(run_dir, f"agent_error {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
