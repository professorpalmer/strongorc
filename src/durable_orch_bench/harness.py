from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from durable_orch_bench import __version__
from durable_orch_bench.adapters import get_adapter
from durable_orch_bench.catalog import TaskSpec, list_tasks
from durable_orch_bench.grade import collect_trial, grade_trial
from durable_orch_bench.schema import Grade, TrialRecord


def seed_run(task: TaskSpec, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    if task.seed_dir.is_dir():
        shutil.copytree(task.seed_dir, dest, dirs_exist_ok=True)


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
    adapter.run(task, run_dir, model)
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
