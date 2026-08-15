from __future__ import annotations

from pathlib import Path

from strongorc.oracle_lib import (
    event_order,
    file_contains,
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
        file_exists(run_dir, "src/add.ts"),
        file_exists(run_dir, "src/mul.ts"),
        file_exists(run_dir, "src/scale.ts"),
        file_exists(run_dir, ".harness/wave1_verified"),
        file_exists(run_dir, ".harness/wave2_verified"),
        file_contains(run_dir, ".harness/wave1_verified", "ok"),
        file_contains(run_dir, ".harness/wave2_verified", "ok"),
        no_leftover_js(run_dir),
        no_any_in_ts(run_dir),
        node_test_passes(run_dir, "test/wave1.mts"),
        node_test_passes(run_dir, "test/wave2.mts"),
        node_test_passes(run_dir, "test/wave3.mts"),
        has_event(trial, "wave_verified"),
        has_event(trial, "wave2_started"),
        has_event(trial, "wave2_verified"),
        has_event(trial, "wave3_started"),
        event_order(trial, "wave_verified", "wave2_started", "verified_before_wave2"),
        event_order(trial, "wave2_verified", "wave3_started", "verified_before_wave3"),
        forbids_event(trial, "wave_skipped"),
        has_event(trial, "job_completed"),
    ]
