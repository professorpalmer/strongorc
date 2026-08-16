from __future__ import annotations

from pathlib import Path

from strongorc.oracle_lib import (
    event_count_at_most,
    file_absent,
    file_exists,
    has_event,
)
from strongorc.schema import CheckResult, TrialRecord


def check(run_dir: Path, trial: TrialRecord) -> list[CheckResult]:
    return [
        file_exists(run_dir, "src/alpha/inc.ts"),
        file_exists(run_dir, "src/gamma/stay.js"),
        file_absent(run_dir, "src/gamma/stay.ts"),
        event_count_at_most(trial, "worker_started", 1),
        has_event(trial, "job_completed"),
    ]

