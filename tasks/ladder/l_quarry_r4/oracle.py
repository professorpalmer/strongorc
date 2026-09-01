from __future__ import annotations

from pathlib import Path

from strongorc.oracle_lib import file_exists, has_event, hidden_pytest_cases
from strongorc.schema import CheckResult, TrialRecord


def check(run_dir: Path, trial: TrialRecord) -> list[CheckResult]:
    hidden = Path(__file__).with_name("hidden")
    return [
        file_exists(run_dir, "quarry/__init__.py"),
        *hidden_pytest_cases(run_dir, hidden),
        has_event(trial, "artifact_consumed"),
        has_event(trial, "job_completed"),
    ]
