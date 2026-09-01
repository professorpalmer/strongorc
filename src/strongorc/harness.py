from __future__ import annotations

import hashlib
import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
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
    nonce = inject_run_nonce(task, dest)
    if task.generator_id:
        from strongorc.holdout import materialize_visible

        materialize_visible(task, dest, nonce)


def _adapter_env(task: TaskSpec, run_dir: Path, model: str, extra: dict[str, str] | None = None) -> dict[str, str]:
    env = os.environ.copy()
    from strongorc.holdout import scrub_holdout_env

    scrub_holdout_env(env)
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
        expect_interrupt="1" if task.interrupt_steps() else "0",
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
        env.update(adapter.extra_env)
        from strongorc.holdout import scrub_holdout_env

        scrub_holdout_env(env)
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
    task: TaskSpec,
    proc: subprocess.Popen,
    run_dir: Path,
    interrupt: dict,
    timeout: int,
    kill_index: int = 1,
) -> str | None:
    """Kill after the marker appears. Return the parent-observed snapshot digest."""
    marker = run_dir / interrupt["when_file"]
    deadline = time.time() + timeout
    while proc.poll() is None and time.time() < deadline:
        if marker.is_file():
            time.sleep(0.05)
            snapshot = _hash_globs(run_dir, interrupt.get("snapshot_globs") or [])
            harness_dir = run_dir / ".harness"
            harness_dir.mkdir(parents=True, exist_ok=True)
            payload = json.dumps(snapshot, indent=2, sort_keys=True) + "\n"
            digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
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
            if task.generator_id:
                from strongorc.holdout import (
                    materialize_after_interrupt,
                    read_harness_nonce,
                )

                materialize_after_interrupt(
                    task,
                    run_dir,
                    read_harness_nonce(run_dir),
                    kill_index,
                )
            return digest
        time.sleep(0.05)
    if proc.poll() is None:
        proc.kill()
        proc.wait(timeout=5)
    return None


def _apply_after_kill(run_dir: Path, step: dict) -> None:
    for relative, payload in (step.get("rewrite") or {}).items():
        path = run_dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(payload, (dict, list)):
            path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        else:
            path.write_text(str(payload), encoding="utf-8")
    for relative, payload in (step.get("plant") or {}).items():
        path = run_dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(payload, (dict, list)):
            path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        else:
            path.write_text(str(payload), encoding="utf-8")
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


def run_interruptible(
    task: TaskSpec,
    adapter,
    run_dir: Path,
    model: str,
    runtime_env: dict[str, str] | None = None,
) -> dict[str, str]:
    """Run interrupt steps. Return parent-observed pre-kill snapshot digests."""
    steps = task.interrupt_steps()
    digests: dict[str, str] = {}
    if not steps:
        return digests
    first_env = dict(runtime_env or {})
    first_env["RESUME"] = "0"
    proc = _spawn_adapter(adapter, task, run_dir, model, first_env)
    for index, step in enumerate(steps, start=1):
        digest = _wait_and_kill(
            task,
            proc,
            run_dir,
            step,
            task.timeout_seconds,
            kill_index=index,
        )
        if not digest:
            return digests
        digests[str(index)] = digest
        if not step.get("resume", True):
            return digests
        resume_env = dict(runtime_env or {})
        resume_env.update({"RESUME": "1", "RESUME_STEP": str(index)})
        proc = _spawn_adapter(
            adapter,
            task,
            run_dir,
            model,
            resume_env,
        )
    try:
        proc.wait(timeout=task.timeout_seconds)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)
        _record_failure(run_dir, model, "resume_timeout")
    return digests


def run_task(
    task: TaskSpec,
    *,
    adapter_name: str,
    model: str,
    runs_root: Path,
    adapter_kwargs: dict | None = None,
    attempt: int = 0,
) -> tuple[TrialRecord, Grade]:
    runs_root = isolated_runs_root(runs_root, adapter_name)
    run_name = task.id if attempt == 0 else f"{task.id}--attempt-{attempt + 1}"
    run_dir = (Path(runs_root) / run_name).resolve()
    if run_dir.exists():
        shutil.rmtree(run_dir)
    seed_run(task, run_dir)
    adapter = get_adapter(adapter_name, **(adapter_kwargs or {}))
    expected_kill_count: int | None = None
    observed_kill_count: int | None = None
    pre_kill_digests: dict[str, str] = {}
    worker_dispatches: list[dict] = []
    worker_consumptions: list[dict] = []
    broker = None
    try:
        from strongorc.holdout import holdout_env_hidden
        from strongorc.worker_broker import WorkerBroker

        worker_pool = task.root / "workers.py"
        broker = WorkerBroker(task, run_dir) if worker_pool.is_file() else None
        if broker is not None and task.track != "orchestrator":
            raise ValueError("worker pools are only valid for orchestrator tasks")
        broker_context = broker if broker is not None else nullcontext(None)
        with broker_context as active_broker:
            broker_extra = None
            if broker is not None:
                broker_extra = {
                    key.removeprefix("STRONGORC_"): value
                    for key, value in broker.environment.items()
                }
            with holdout_env_hidden():
                if task.interrupt_steps():
                    expected_kill_count = len(task.interrupt_steps())
                    pre_kill_digests = run_interruptible(
                        task,
                        adapter,
                        run_dir,
                        model,
                        broker_extra,
                    )
                    observed_kill_count = len(pre_kill_digests)
                elif broker is not None:
                    proc = _spawn_adapter(
                        adapter,
                        task,
                        run_dir,
                        model,
                        broker_extra,
                    )
                    try:
                        proc.wait(timeout=task.timeout_seconds)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait(timeout=5)
                        _record_failure(run_dir, model, "worker_broker_timeout")
                    if proc.returncode:
                        _record_failure(
                            run_dir,
                            model,
                            f"worker_broker_exit_{proc.returncode}",
                        )
                else:
                    adapter.run(task, run_dir, model)
            if active_broker is not None:
                sealed_workers = active_broker.snapshot()
                worker_dispatches = sealed_workers["dispatches"]
                worker_consumptions = sealed_workers["consumptions"]
    except Exception as exc:
        if broker is not None:
            sealed_workers = broker.snapshot()
            worker_dispatches = sealed_workers["dispatches"]
            worker_consumptions = sealed_workers["consumptions"]
        _record_failure(run_dir, model, type(exc).__name__)
    trial = collect_trial(
        task,
        run_dir,
        model,
        adapter_name,
        __version__,
        expected_kill_count=expected_kill_count,
        observed_kill_count=observed_kill_count,
        pre_kill_digests=pre_kill_digests,
        worker_dispatches=worker_dispatches,
        worker_consumptions=worker_consumptions,
    )
    trial.attempt = attempt
    return trial, grade_trial(trial, task)


def run_slice(
    slice_name: str,
    *,
    adapter_name: str,
    model: str,
    runs_root: Path,
    adapter_kwargs: dict | None = None,
    repeats: int = 1,
    jobs: int = 1,
    task_ids: list[str] | None = None,
    skip_attempts: set[tuple[str, int]] | None = None,
    progress_path: Path | None = None,
    on_trial: Callable[[TrialRecord, Grade], None] | None = None,
) -> list[tuple[TrialRecord, Grade]]:
    if repeats < 1:
        raise ValueError("repeats must be >= 1")
    if jobs < 1:
        raise ValueError("jobs must be >= 1")
    from strongorc.holdout import HoldoutUnavailable, ensure_holdout_slice
    from strongorc.instrument import assess_ranking_tasks

    ensure_holdout_slice(slice_name)
    tasks = list_tasks(slice_name)
    if slice_name == "holdout" and adapter_name != "scripted":
        readiness = assess_ranking_tasks(tasks)
        if not readiness.ready:
            raise HoldoutUnavailable(
                "ranking instrument not ready: " + "; ".join(readiness.errors)
            )
    if task_ids:
        known = {task.id: task for task in tasks}
        missing = [task_id for task_id in task_ids if task_id not in known]
        if missing:
            raise ValueError(f"unknown task_ids for {slice_name}: {missing}")
        tasks = [known[task_id] for task_id in task_ids]
    skipped = skip_attempts or set()
    work = [
        (task, attempt)
        for task in tasks
        for attempt in range(repeats)
        if (task.id, attempt) not in skipped
    ]
    lock = threading.Lock()

    def _persist(trial: TrialRecord, grade: Grade) -> None:
        if on_trial is not None:
            on_trial(trial, grade)
        if progress_path is None:
            return
        dest = Path(progress_path)
        with lock:
            incoming = [trial]
            if dest.is_file():
                incoming = merge_slice_trials(slice_name, read_trials(dest), incoming)
            write_trials(dest, incoming)

    def _one(item: tuple) -> tuple[TrialRecord, Grade]:
        task, attempt = item
        trial, grade = run_task(
            task,
            adapter_name=adapter_name,
            model=model,
            runs_root=runs_root,
            adapter_kwargs=adapter_kwargs,
            attempt=attempt,
        )
        _persist(trial, grade)
        return trial, grade

    if jobs == 1:
        return [_one(item) for item in work]
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        return list(pool.map(_one, work))


def merge_slice_trials(
    slice_name: str,
    existing: list[TrialRecord],
    incoming: list[TrialRecord],
) -> list[TrialRecord]:
    """Replace matching attempts, keep the rest, order by task then attempt."""
    by_key = {(trial.task_id, trial.attempt): trial for trial in existing}
    for trial in incoming:
        by_key[(trial.task_id, trial.attempt)] = trial
    catalog_ids = [task.id for task in list_tasks(slice_name)]
    ordered = [
        trial
        for task_id in catalog_ids
        for (_key, trial) in sorted(
            (
                (key, value)
                for key, value in by_key.items()
                if key[0] == task_id
            ),
            key=lambda item: item[0][1],
        )
    ]
    extras = [
        trial
        for (task_id, _attempt), trial in sorted(by_key.items())
        if task_id not in catalog_ids
    ]
    return ordered + extras


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
