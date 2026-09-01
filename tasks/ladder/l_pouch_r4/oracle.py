from __future__ import annotations

from pathlib import Path

from strongorc.oracle_lib import file_exists, has_event, hidden_pytest_cases, event_order
from strongorc.schema import CheckResult, TrialRecord


def check(run_dir: Path, trial: TrialRecord) -> list[CheckResult]:
    hidden = Path(__file__).with_name("hidden")
    return [
        file_exists(run_dir, "pouch/__init__.py"),
        *hidden_pytest_cases(run_dir, hidden),
        has_event(trial, "artifact_consumed"),
        has_event(trial, "job_completed"),
        event_order(trial, "artifact_consumed", "job_completed", "order:artifact_before_completed"),
    ]
