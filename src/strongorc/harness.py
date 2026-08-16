from __future__ import annotations

import hashlib
import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from strongorc import __version__
from strongorc.adapters import get_adapter
from strongorc.adapters.command import CommandAdapter
from strongorc.adapters.scripted import ScriptedAdapter
from strongorc.catalog import TaskSpec, list_tasks
from strongorc.grade import collect_trial, grade_trial
from strongorc.env import bind_run, export
from strongorc.protocol import emit, receipt_path, write_receipt
from strongorc.schema import Grade, TrialRecord


def inject_run_nonce(task: TaskSpec, dest: Path) -> str:
    nonce = secrets.token_hex(8)
    harness_dir = dest / ".harness"
    harness_dir.mkdir(parents=True, exist_ok=True)
    (harness_dir / "nonce").write_text(nonce + "\n", encoding="utf-8")
    if task.bind:
        target = dest / task.bind["file"]
        field = task.bind.get("field", "nonce")
        if target.suffix == ".json" and target.is_file():
            data = json.loads(target.read_text(encoding="utf-8"))
            data[field] = nonce
            target.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return nonce


def seed_run(task: TaskSpec, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    if task.seed_dir.is_dir():
        shutil.copytree(task.seed_dir, dest, dirs_exist_ok=True)
    inject_run_nonce(task, dest)


def _adapter_env(task: TaskSpec, run_dir: Path, model: str, extra: dict[str, str] | None = None) -> dict[str, str]:
    env = os.environ.copy()
    src_root = Path(__file__).resolve().parents[1]
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(src_root) if not existing else f"{src_root}{os.pathsep}{existing}"
    bind_run(
        env,
        run_dir=str(run_dir),
        task_id=task.id,
        track=task.track,
        model=model,
        prompt=str(run_dir / "PROMPT.md"),
    )
    if extra:
        for suffix, value in extra.items():
            export(env, suffix, value)
    return env


def _spawn_adapter(adapter, task: TaskSpec, run_dir: Path, model: str, extra_env: dict[str, str] | None = None):
    env = _adapter_env(task, run_dir, model, extra_env)
    if isinstance(adapter, ScriptedAdapter):
        agent = task.agent_path(adapter.persona)
        if not agent.is_file():
            raise FileNotFoundError(f"missing scripted agent: {agent}")
        export(env, "AGENT", str(agent))
        return subprocess.Popen(
            [sys.executable, "-m", "strongorc.agent_driver"],
            cwd=run_dir,
            env=env,
        )
    if isinstance(adapter, CommandAdapter):
        if not adapter.cmd:
            raise ValueError("command adapter requires --cmd")
        (run_dir / "PROMPT.md").write_text(task.prompt(), encoding="utf-8")
        return subprocess.Popen(adapter.cmd, shell=True, cwd=run_dir, env=env)
    raise TypeError(f"adapter {adapter.name} cannot be spawned")


def _hash_globs(run_dir: Path, globs: list[str]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for pattern in globs:
        for path in sorted(run_dir.glob(pattern)):
            if path.is_file():
                relative = path.relative_to(run_dir).as_posix()
                hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


def _wait_and_kill(
    proc: subprocess.Popen,
    run_dir: Path,
    interrupt: dict,
    timeout: int,
    kill_index: int = 1,
) -> bool:
    marker = run_dir / interrupt["when_file"]
    deadline = time.time() + timeout
    while proc.poll() is None and time.time() < deadline:
        if marker.is_file():
            time.sleep(0.05)
            snapshot = _hash_globs(run_dir, interrupt.get("snapshot_globs") or [])
            harness_dir = run_dir / ".harness"
            harness_dir.mkdir(parents=True, exist_ok=True)
            payload = json.dumps(snapshot, indent=2, sort_keys=True) + "\n"
            (harness_dir / "pre_kill_hashes.json").write_text(payload, encoding="utf-8")
            (harness_dir / f"pre_kill_{kill_index}.json").write_text(payload, encoding="utf-8")
            (harness_dir / "killed").write_text(f"{kill_index}\n", encoding="utf-8")
            proc.kill()
            proc.wait(timeout=5)
            emit(
                run_dir,
                "harness_killed",
                signal="SIGKILL",
                marker=interrupt["when_file"],
                kill_index=kill_index,
            )
            _apply_after_kill(run_dir, interrupt)
            return True
        time.sleep(0.05)
    if proc.poll() is None:
        proc.kill()
        proc.wait(timeout=5)
    return False


def _apply_after_kill(run_dir: Path, step: dict) -> None:
    for relative, payload in (step.get("rewrite") or {}).items():
        path = run_dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(payload, (dict, list)):
            path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        else:
            path.write_text(str(payload), encoding="utf-8")
    for relative, text in (step.get("plant") or {}).items():
        path = run_dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(text), encoding="utf-8")
    for relative in step.get("delete") or []:
        path = run_dir / relative
        if path.is_file():
            path.unlink()


def _record_failure(run_dir: Path, model: str, reason: str) -> None:
    emit(run_dir, "job_failed", reason=reason)
    if receipt_path(run_dir).is_file():
        return
    write_receipt(
        run_dir,
        {
            "status": "failed",
            "model_id": model,
            "usd": 0.0,
            "tokens_in": 0,
            "tokens_out": 0,
            "workers_ran": 0,
        },
    )


def run_interruptible(task: TaskSpec, adapter, run_dir: Path, model: str) -> None:
    steps = task.interrupt_steps()
    if not steps:
        return
    proc = _spawn_adapter(adapter, task, run_dir, model, {"RESUME": "0"})
    for index, step in enumerate(steps, start=1):
        killed = _wait_and_kill(proc, run_dir, step, task.timeout_seconds, kill_index=index)
        if not killed:
            return
        if not step.get("resume", True):
            return
        proc = _spawn_adapter(
            adapter,
            task,
            run_dir,
            model,
            {"RESUME": "1", "RESUME_STEP": str(index)},
        )
    try:
        proc.wait(timeout=task.timeout_seconds)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)
        _record_failure(run_dir, model, "resume_timeout")


def run_task(
    task: TaskSpec,
    *,
    adapter_name: str,
    model: str,
    runs_root: Path,
    adapter_kwargs: dict | None = None,
) -> tuple[TrialRecord, Grade]:
    runs_root = isolated_runs_root(runs_root, adapter_name)
    run_dir = (Path(runs_root) / task.id).resolve()
    if run_dir.exists():
        shutil.rmtree(run_dir)
    seed_run(task, run_dir)
    adapter = get_adapter(adapter_name, **(adapter_kwargs or {}))
    try:
        if task.interrupt_steps():
            run_interruptible(task, adapter, run_dir, model)
        else:
            adapter.run(task, run_dir, model)
    except Exception as exc:
        _record_failure(run_dir, model, type(exc).__name__)
    trial = collect_trial(task, run_dir, model, adapter_name, __version__)
    return trial, grade_trial(trial, task)


def run_slice(
    slice_name: str,
    *,
    adapter_name: str,
    model: str,
    runs_root: Path,
    adapter_kwargs: dict | None = None,
) -> list[tuple[TrialRecord, Grade]]:
    results: list[tuple[TrialRecord, Grade]] = []
    for task in list_tasks(slice_name):
        results.append(
            run_task(
                task,
                adapter_name=adapter_name,
                model=model,
                runs_root=runs_root,
                adapter_kwargs=adapter_kwargs,
            )
        )
    return results


def write_trials(path: Path, trials: list[TrialRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for trial in trials:
            handle.write(json.dumps(trial.to_dict(), sort_keys=True) + "\n")


def read_trials(path: Path) -> list[TrialRecord]:
    trials: list[TrialRecord] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            trials.append(TrialRecord.from_dict(json.loads(line)))
    return trials


def ephemeral_runs_root() -> Path:
    return Path(tempfile.mkdtemp(prefix="strongorc-"))


def checkout_root() -> Path:
    return Path(__file__).resolve().parents[2]


def is_inside_checkout(path: Path) -> bool:
    resolved = Path(path).resolve()
    root = checkout_root()
    return resolved == root or root in resolved.parents


def isolated_runs_root(runs_root: Path, adapter_name: str) -> Path:
    """Live command agents must not see the bench checkout (hidden tests, references)."""
    root = Path(runs_root).resolve()
    if adapter_name != "command" or not is_inside_checkout(root):
        return root
    return Path.home() / ".strongorc" / "runs" / root.name
