from __future__ import annotations

from pathlib import Path

from strongorc.oracle_lib import (
    event_order,
    file_exists,
    has_event,
    no_leftover_js,
    node_test_passes,
)
from strongorc.schema import CheckResult, TrialRecord


def check(run_dir: Path, trial: TrialRecord) -> list[CheckResult]:
    return [
        file_exists(run_dir, "src/a.ts"),
        file_exists(run_dir, "src/b.ts"),
        file_exists(run_dir, "src/c.ts"),
        file_exists(run_dir, "src/d.ts"),
        no_leftover_js(run_dir),
        node_test_passes(run_dir, "test/wave_a.mts"),
        node_test_passes(run_dir, "test/wave_b.mts"),
        node_test_passes(run_dir, "test/wave_c.mts"),
        has_event(trial, "wave_verified"),
        has_event(trial, "wave2_verified"),
        has_event(trial, "wave3_verified"),
        event_order(trial, "wave_verified", "wave2_started", "verified_before_wave2"),
        event_order(trial, "wave2_verified", "job_completed", "verified_before_join"),
        event_order(trial, "wave3_verified", "job_completed", "verified_before_join"),
        has_event(trial, "job_completed"),
    ]

