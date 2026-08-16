from __future__ import annotations

from pathlib import Path

from strongorc.oracle_lib import (
    event_count_at_most,
    file_exists,
    has_event,
    no_leftover_js,
)
from strongorc.schema import CheckResult, TrialRecord


def check(run_dir: Path, trial: TrialRecord) -> list[CheckResult]:
    return [
        file_exists(run_dir, "src/retry/job.ts"),
        no_leftover_js(run_dir),
        event_count_at_most(trial, "worker_started", 2),
        has_event(trial, "job_completed"),
    ]

