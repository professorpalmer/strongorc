from __future__ import annotations

import json
import secrets
import shutil
import tempfile
from pathlib import Path

from durable_orch_bench import __version__
from durable_orch_bench.adapters import get_adapter
from durable_orch_bench.catalog import TaskSpec, list_tasks
from durable_orch_bench.grade import collect_trial, grade_trial
from durable_orch_bench.protocol import emit, receipt_path, write_receipt
from durable_orch_bench.schema import Grade, TrialRecord


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


def run_task(
    task: TaskSpec,
    *,
    adapter_name: str,
    model: str,
    runs_root: Path,
    adapter_kwargs: dict | None = None,
) -> tuple[TrialRecord, Grade]:
    run_dir = runs_root / task.id
    if run_dir.exists():
        shutil.rmtree(run_dir)
    seed_run(task, run_dir)
    adapter = get_adapter(adapter_name, **(adapter_kwargs or {}))
    try:
        adapter.run(task, run_dir, model)
    except Exception as exc:
        emit(run_dir, "job_failed", reason=type(exc).__name__)
        if not receipt_path(run_dir).is_file():
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
    return Path(tempfile.mkdtemp(prefix="durable-orch-"))
