from __future__ import annotations

from pathlib import Path

from strongorc.oracle_lib import (
    file_exists,
    has_event,
    no_leftover_js,
    pre_kill_hashes_match,
)
from strongorc.schema import CheckResult, TrialRecord


def check(run_dir: Path, trial: TrialRecord) -> list[CheckResult]:
    return [
        file_exists(run_dir, "src/layer1/a.ts"),
        file_exists(run_dir, "src/layer2/c.ts"),
        no_leftover_js(run_dir),
        has_event(trial, "harness_killed"),
        has_event(trial, "job_completed"),
        pre_kill_hashes_match(run_dir),
    ]

