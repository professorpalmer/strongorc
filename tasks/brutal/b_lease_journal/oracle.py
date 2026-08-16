from __future__ import annotations

from pathlib import Path

from strongorc.oracle_lib import (
    file_count_at_least,
    file_exists,
    has_event,
    hidden_pytest_cases,
)
from strongorc.schema import CheckResult, TrialRecord


def check(run_dir: Path, trial: TrialRecord) -> list[CheckResult]:
    hidden = Path(__file__).with_name("hidden")
    return [
        file_exists(run_dir, "holdbook/__init__.py"),
        file_count_at_least(run_dir, "holdbook", ".py", 2),
        *hidden_pytest_cases(run_dir, hidden),
        has_event(trial, "harness_killed"),
        has_event(trial, "resumed_from_checkpoint"),
        has_event(trial, "job_completed"),
    ]
