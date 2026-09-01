from __future__ import annotations

"""StrongOrc command agent via Puppetmaster CLI + OpenCode Go.

Pins a bare Go model (``ox-alpha-free``, ``minimax-m2.5``) through
``puppetmaster agentic --provider opencode-go``. Filesystem tools are
cwd-jailed to ``$STRONGORC_RUN_DIR``. Isolated ``--state-dir`` plus
``--disable-codegraph --disable-memory`` keeps the bench checkout out of
the worker context. That is the confinement claim.

Implement-mode ``run_terminal`` starts in this cwd but can read absolute
paths. Do not register the card as ``clean``. Stdlib only. Never prints
the key.

Auth: ``OPENCODE_GO_API_KEY``, else Marionette
``~/.pmharness/state/keys.json`` slot ``opencode-go``.
"""

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

MARIONETTE_KEYS = Path.home() / ".pmharness" / "state" / "keys.json"
DEFAULT_PUPPETMASTER = Path.home() / ".local" / "bin" / "puppetmaster"
DEFAULT_PROVIDER = "opencode-go"
DEFAULT_MODEL = "ox-alpha-free"
DEFAULT_MAX_TURNS = 64
DEFAULT_TIMEOUT = 2400
WAIT_CAP_SECONDS = 3600
PLAN_IN_PER_MTOK = 0.5
PLAN_OUT_PER_MTOK = 1.5


def env_first(*names: str, default: str = "") -> str:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return default


def load_opencode_key() -> tuple[str, str]:
    env_key = os.environ.get("OPENCODE_GO_API_KEY")
    if env_key:
        return env_key, "env"
    if MARIONETTE_KEYS.is_file():
        data = json.loads(MARIONETTE_KEYS.read_text(encoding="utf-8"))
        key = data.get("opencode-go")
        if key:
            return str(key), "marionette"
    raise SystemExit(
        "no OpenCode Go key in OPENCODE_GO_API_KEY or "
        "Marionette ~/.pmharness/state/keys.json"
    )


def resolve_run_dir() -> Path:
    raw = env_first("STRONGORC_RUN_DIR", "DURABLE_ORCH_RUN_DIR")
    if not raw:
        raise SystemExit("STRONGORC_RUN_DIR is required")
    return Path(raw).resolve()


def resolve_puppetmaster() -> str:
    override = env_first("STRONGORC_PUPPETMASTER", "PUPPETMASTER_BIN")
    if override:
        return override
    found = shutil.which("puppetmaster")
    if found:
        return found
    if DEFAULT_PUPPETMASTER.is_file():
        return str(DEFAULT_PUPPETMASTER)
    raise SystemExit("puppetmaster CLI not found on PATH or ~/.local/bin")


def log(run_dir: Path, message: str) -> None:
    line = message.rstrip()
    print(line, file=sys.stderr, flush=True)
    path = run_dir / ".harness" / "agentic_opencode.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def list_tree(run_dir: Path) -> str:
    lines: list[str] = []
    for path in sorted(run_dir.rglob("*")):
        if path.is_dir():
            continue
        relative = path.relative_to(run_dir).as_posix()
        if relative.startswith((".pm-state/", ".git/", ".harness/")):
            continue
        lines.append(relative)
        if len(lines) >= 400:
            lines.append("...truncated")
            break
    return "\n".join(lines) if lines else "(empty)"


def plan_nominal_usd(tokens_in: int, tokens_out: int) -> float:
    return (tokens_in / 1_000_000.0) * PLAN_IN_PER_MTOK + (
        tokens_out / 1_000_000.0
    ) * PLAN_OUT_PER_MTOK


def bare_go_model(model: str) -> str:
    """OpenCode Go is a flat namespace; strip registry / vendor prefixes."""
    return model.rsplit("/", 1)[-1].strip()


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

Stay inside this workspace. Do not read absolute paths outside it. The task
prompt and the tree are the spec. Follow them. Do not invent a shortcut that
skips a gate, lease, nonce, budget, or live test.

Contract:
- Outcome files and protocol both have to pass. The oracle re-runs hidden
  tests that are not in the seed. A visible console.log("ok") is not a pass.
- After a resume, re-read the workspace.
- Append protocol events to protocol.jsonl, one JSON object per line:
  {{"type":"<event>","payload":{{}}}}
- On orchestrator tasks, dispatch workers. Do not emit orchestrator_wrote_solution.
- Write receipts/job.json with status, model_id, usd, tokens_in, tokens_out,
  workers_ran. model_id must be exactly {model}.
- status=completed with workers_ran=0 is a dead-swarm fail.
- usd must not be 0 when tokens or workers are nonzero. If you have no better
  usage number, use plan-nominal $0.5 / $1.5 per MTok.
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


def _int_env(*names: str, default: int) -> int:
    raw = env_first(*names)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def build_agentic_argv(
    *,
    puppetmaster: str,
    run_dir: Path,
    state_dir: Path,
    provider: str,
    go_model: str,
    prompt: str,
    max_turns: int,
    timeout_seconds: int,
    task_id: str,
) -> list[str]:
    """Pinned OpenCode Go invoke. No ``--auto-route``."""
    return [
        puppetmaster,
        "--state-dir",
        str(state_dir),
        "agentic",
        prompt,
        "--cwd",
        str(run_dir),
        "--mode",
        "implement",
        "--provider",
        provider,
        "--model",
        go_model,
        "--max-turns",
        str(max_turns),
        "--timeout-seconds",
        str(timeout_seconds),
        "--allow-dirty",
        "--disable-codegraph",
        "--disable-memory",
        "--label",
        f"strongorc-{task_id or 'task'}-{go_model}",
    ]


def isolate_state_dir(run_dir: Path) -> Path:
    """Keep Puppetmaster state outside the agent cwd so sqlite/logs are not the diff."""
    return run_dir.parent / f"{run_dir.name}.pm-state"


def ensure_git(run_dir: Path) -> None:
    ignore = run_dir / ".gitignore"
    if not ignore.is_file():
        ignore.write_text(".harness/\n.pm-state/\n", encoding="utf-8")
    if (run_dir / ".git").is_dir():
        return
    subprocess.run(["git", "init"], cwd=run_dir, check=False, capture_output=True)
    subprocess.run(
        ["git", "add", "-A"],
        cwd=run_dir,
        check=False,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "strongorc seed", "--allow-empty"],
        cwd=run_dir,
        check=False,
        capture_output=True,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "strongorc",
            "GIT_AUTHOR_EMAIL": "strongorc@local",
            "GIT_COMMITTER_NAME": "strongorc",
            "GIT_COMMITTER_EMAIL": "strongorc@local",
        },
    )


def parse_usage_from_logs(run_dir: Path, stdout: str) -> dict:
    text = stdout.strip()
    if text:
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = {}
        if isinstance(data, dict):
            usage = data.get("usage")
            if isinstance(usage, dict):
                return usage
    receipt = run_dir / "receipts" / "job.json"
    if receipt.is_file():
        try:
            data = json.loads(receipt.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
        if isinstance(data, dict):
            return {
                "inputTokens": data.get("tokens_in") or 0,
                "outputTokens": data.get("tokens_out") or 0,
            }
    return {}


def finalize_if_needed(run_dir: Path, model: str, usage: dict) -> None:
    path = run_dir / "receipts" / "job.json"
    if path.is_file():
        return
    tokens_in = int(usage.get("inputTokens") or usage.get("tokens_in") or 0)
    tokens_out = int(usage.get("outputTokens") or usage.get("tokens_out") or 0)
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
        "cost_source": "opencode_go_plan_nominal",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_agentic(run_dir: Path, model: str, go_model: str, api_key: str) -> dict:
    puppetmaster = resolve_puppetmaster()
    ensure_git(run_dir)
    state_dir = isolate_state_dir(run_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    prompt = build_prompt(run_dir, model)
    max_turns = _int_env("STRONGORC_MAX_TURNS", default=DEFAULT_MAX_TURNS)
    timeout_seconds = _int_env("STRONGORC_TIMEOUT_SECONDS", default=DEFAULT_TIMEOUT)
    task_id = env_first("STRONGORC_TASK_ID", "DURABLE_ORCH_TASK_ID")
    argv = build_agentic_argv(
        puppetmaster=puppetmaster,
        run_dir=run_dir,
        state_dir=state_dir,
        provider=env_first("STRONGORC_PROVIDER", default=DEFAULT_PROVIDER),
        go_model=go_model,
        prompt=prompt,
        max_turns=max_turns,
        timeout_seconds=timeout_seconds,
        task_id=task_id,
    )
    env = os.environ.copy()
    env["OPENCODE_GO_API_KEY"] = api_key
    env["PUPPETMASTER_AUTO_INVOKE_DISABLED"] = "1"
    log(
        run_dir,
        f"spawn agentic provider=opencode-go model={go_model} "
        f"turns={max_turns} timeout={timeout_seconds}",
    )
    completed = subprocess.run(
        argv,
        cwd=run_dir,
        env=env,
        check=False,
        text=True,
        capture_output=True,
    )
    out_path = run_dir / ".harness" / "agentic_opencode.stdout.log"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        (completed.stdout or "") + "\n--- stderr ---\n" + (completed.stderr or ""),
        encoding="utf-8",
    )
    log(run_dir, f"agentic_exit {completed.returncode}")
    if completed.returncode != 0 and completed.stderr:
        tail = completed.stderr.strip().splitlines()
        if tail:
            log(run_dir, tail[-1][:300])
    return parse_usage_from_logs(run_dir, completed.stdout or "")


def main() -> int:
    run_dir = resolve_run_dir()
    model = env_first(
        "STRONGORC_MODEL",
        "DURABLE_ORCH_MODEL",
        "OPENCODE_GO_MODEL",
        default=DEFAULT_MODEL,
    )
    go_model = bare_go_model(env_first("OPENCODE_GO_MODEL", default=model))
    api_key, key_source = load_opencode_key()
    log(run_dir, f"key_source {key_source}")
    try:
        usage = run_agentic(run_dir, model, go_model, api_key)
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
