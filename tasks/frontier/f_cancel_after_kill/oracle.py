from __future__ import annotations

from pathlib import Path

from strongorc.oracle_lib import (
    file_absent,
    file_exists,
    forbids_event,
    has_event,
    receipt_status_is,
)
from strongorc.schema import CheckResult, TrialRecord


def check(run_dir: Path, trial: TrialRecord) -> list[CheckResult]:
    return [
        file_exists(run_dir, "src/early/early.ts"),
        file_exists(run_dir, "src/late/late.js"),
        file_absent(run_dir, "src/late/late.ts"),
        has_event(trial, "harness_killed"),
        has_event(trial, "job_refused"),
        forbids_event(trial, "job_completed"),
        receipt_status_is(trial, "refused"),
    ]

