from __future__ import annotations

from pathlib import Path

from strongorc.oracle_lib import (
    file_exists,
    has_event,
    no_leftover_js,
)
from strongorc.schema import CheckResult, TrialRecord


def check(run_dir: Path, trial: TrialRecord) -> list[CheckResult]:
    return [
        file_exists(run_dir, "src/work/job.ts"),
        no_leftover_js(run_dir),
        has_event(trial, "worker_started"),
        has_event(trial, "job_completed"),
    ]

