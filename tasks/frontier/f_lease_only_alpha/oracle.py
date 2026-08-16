from __future__ import annotations

from pathlib import Path

from strongorc.oracle_lib import (
    file_absent,
    file_exists,
    forbids_event,
    has_event,
)
from strongorc.schema import CheckResult, TrialRecord


def check(run_dir: Path, trial: TrialRecord) -> list[CheckResult]:
    return [
        file_exists(run_dir, "src/alpha/inc.ts"),
        file_exists(run_dir, "src/beta/dec.js"),
        file_absent(run_dir, "src/beta/dec.ts"),
        has_event(trial, "lease_acquired"),
        forbids_event(trial, "lease_violated"),
        has_event(trial, "job_completed"),
    ]

