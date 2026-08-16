from __future__ import annotations

from pathlib import Path

from strongorc.oracle_lib import (
    file_absent,
    file_exists,
    forbids_event,
    has_event,
    no_any_in_ts,
    no_leftover_js,
    node_test_passes,
    pre_kill_hashes_match,
)
from strongorc.schema import TrialRecord


def check(run_dir: Path, trial: TrialRecord) -> list[CheckResult]:
    return [
        file_exists(run_dir, "src/east/one.ts"),
        file_exists(run_dir, "src/west/two.ts"),
        file_exists(run_dir, "src/index.ts"),
        file_absent(run_dir, "src/shared/CONFLICT"),
        no_leftover_js(run_dir, "src/east"),
        no_leftover_js(run_dir, "src/west"),
        no_any_in_ts(run_dir, "src/east"),
        no_any_in_ts(run_dir, "src/west"),
        node_test_passes(run_dir, "test/test.mts"),
        pre_kill_hashes_match(run_dir),
        has_event(trial, "harness_killed"),
        has_event(trial, "lease_acquired"),
        has_event(trial, "job_completed"),
        forbids_event(trial, "lease_violated"),
    ]
