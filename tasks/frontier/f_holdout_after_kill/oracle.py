from __future__ import annotations

from pathlib import Path

from strongorc.oracle_lib import (
    file_absent,
    file_exists,
    has_event,
)
from strongorc.schema import CheckResult, TrialRecord


def check(run_dir: Path, trial: TrialRecord) -> list[CheckResult]:
    return [
        file_exists(run_dir, "src/main/main.ts"),
        file_exists(run_dir, "src/holdout/secret.js"),
        file_absent(run_dir, "src/holdout/secret.ts"),
        has_event(trial, "harness_killed"),
        has_event(trial, "job_completed"),
    ]

