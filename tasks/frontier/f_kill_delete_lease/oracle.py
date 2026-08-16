from __future__ import annotations

from pathlib import Path

from strongorc.oracle_lib import (
    file_absent,
    file_exists,
    forbids_event,
    has_event,
    no_leftover_js,
)
from strongorc.schema import CheckResult, TrialRecord


def check(run_dir: Path, trial: TrialRecord) -> list[CheckResult]:
    return [
        file_exists(run_dir, "src/alpha/inc.ts"),
        file_exists(run_dir, "src/beta/dec.js"),
        file_absent(run_dir, "src/beta/dec.ts"),
        no_leftover_js(run_dir, "src/alpha"),
        has_event(trial, "harness_killed"),
        has_event(trial, "job_completed"),
        forbids_event(trial, "lease_violated"),
    ]

