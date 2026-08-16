from __future__ import annotations

from pathlib import Path

from strongorc.oracle_lib import (
    event_count_at_most,
    file_exists,
    has_event,
    no_any_in_ts,
    no_leftover_js,
    node_test_passes,
)
from strongorc.schema import TrialRecord


def check(run_dir: Path, trial: TrialRecord) -> list[CheckResult]:
    return [
        file_exists(run_dir, "src/left/add.ts"),
        file_exists(run_dir, "src/right/mul.ts"),
        file_exists(run_dir, "src/index.ts"),
        no_leftover_js(run_dir),
        no_any_in_ts(run_dir),
        node_test_passes(run_dir, "test/test.mts"),
        has_event(trial, "worker_started"),
        event_count_at_most(trial, "worker_started", 1),
        has_event(trial, "job_completed"),
    ]
