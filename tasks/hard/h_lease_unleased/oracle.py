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
)
from strongorc.schema import TrialRecord


def check(run_dir: Path, trial: TrialRecord) -> list[CheckResult]:
    return [
        file_exists(run_dir, "src/alpha/one.ts"),
        file_exists(run_dir, "src/alpha/inc.ts"),
        file_exists(run_dir, "src/beta/two.ts"),
        file_exists(run_dir, "src/beta/dec.ts"),
        file_exists(run_dir, "src/index.ts"),
        file_exists(run_dir, "src/gamma/stay.js"),
        file_absent(run_dir, "src/gamma/stay.ts"),
        file_absent(run_dir, "src/shared/CONFLICT"),
        no_leftover_js(run_dir, "src/alpha"),
        no_leftover_js(run_dir, "src/beta"),
        no_any_in_ts(run_dir, "src/alpha"),
        no_any_in_ts(run_dir, "src/beta"),
        node_test_passes(run_dir, "test/test.mts"),
        has_event(trial, "lease_acquired"),
        has_event(trial, "job_completed"),
        forbids_event(trial, "lease_violated"),
    ]
