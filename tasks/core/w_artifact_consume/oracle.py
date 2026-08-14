from pathlib import Path

from strongorc.oracle_lib import file_contains, file_exists, has_event
from strongorc.schema import CheckResult, TrialRecord


def check(run_dir: Path, trial: TrialRecord) -> list[CheckResult]:
    return [
        file_exists(run_dir, "src/adapter.py"),
        file_contains(run_dir, "src/adapter.py", "def add(x, y)"),
        file_contains(run_dir, "src/adapter.py", "-> int"),
        has_event(trial, "artifact_consumed"),
        has_event(trial, "job_completed"),
    ]
