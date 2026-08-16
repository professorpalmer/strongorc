from __future__ import annotations

from pathlib import Path

from strongorc.oracle_lib import (
    event_order,
    file_count_at_least,
    file_exists,
    forbids_event,
    has_event,
    hidden_pytest_cases,
)
from strongorc.schema import CheckResult, TrialRecord


def check(run_dir: Path, trial: TrialRecord) -> list[CheckResult]:
    hidden = Path(__file__).with_name("hidden")
    return [
        file_exists(run_dir, "persistq/__init__.py"),
        file_count_at_least(run_dir, "persistq", ".py", 3),
        *hidden_pytest_cases(run_dir, hidden),
        has_event(trial, "worker_started"),
        has_event(trial, "checkpoint_written"),
        has_event(trial, "harness_killed"),
        has_event(trial, "resumed_from_checkpoint"),
        has_event(trial, "job_completed"),
        event_order(trial, "checkpoint_written", "harness_killed", "order:checkpoint_before_kill"),
        forbids_event(trial, "orchestrator_wrote_solution"),
    ]
