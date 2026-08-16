from __future__ import annotations

from pathlib import Path

from strongorc.oracle_lib import (
    file_absent,
    file_contains,
    file_exists,
    has_event,
)
from strongorc.schema import CheckResult, TrialRecord


def check(run_dir: Path, trial: TrialRecord) -> list[CheckResult]:
    return [
        file_exists(run_dir, "src/work/job.ts"),
        file_exists(run_dir, "src/work/fence.ts"),
        file_contains(run_dir, "src/work/fence.ts", "beta-live"),
        file_absent(run_dir, "src/work/job.js"),
        has_event(trial, "harness_killed"),
        has_event(trial, "job_completed"),
    ]

