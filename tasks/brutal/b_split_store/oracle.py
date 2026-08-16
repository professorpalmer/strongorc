from __future__ import annotations

from pathlib import Path

from strongorc.oracle_lib import (
    event_count_at_most,
    file_exists,
    has_event,
    hidden_pytest_cases,
    json_field_equals,
)
from strongorc.schema import CheckResult, TrialRecord


def check(run_dir: Path, trial: TrialRecord) -> list[CheckResult]:
    hidden = Path(__file__).with_name("hidden")
    return [
        file_exists(run_dir, "binbox/__init__.py"),
        file_exists(run_dir, "namemap/__init__.py"),
        *hidden_pytest_cases(run_dir, hidden),
        has_event(trial, "harness_killed"),
        has_event(trial, "resumed_from_checkpoint"),
        has_event(trial, "job_completed"),
        event_count_at_most(trial, "worker_started", 2),
        # Sealed grain: harness wrote these after kill. Still fail a trial
        # that overwrites them. Do not count as hard model skill.
        json_field_equals(run_dir, "job/budget.json", "max_workers", 1),
        json_field_equals(run_dir, "job/leases.json", "leased", ["namemap"]),
    ]
