from __future__ import annotations

from pathlib import Path

from strongorc.oracle_lib import (
    event_order,
    file_contains,
    file_exists,
    has_event,
    hidden_node_test,
    no_leftover_js,
    node_test_passes,
)
from strongorc.schema import CheckResult, TrialRecord


def check(run_dir: Path, trial: TrialRecord) -> list[CheckResult]:
    hidden = Path(__file__).with_name("hidden") / "behavior.mts"
    return [
        file_exists(run_dir, "src/add.ts"),
        file_exists(run_dir, "src/mul.ts"),
        file_contains(run_dir, ".harness/wave1_verified", "ok"),
        no_leftover_js(run_dir),
        node_test_passes(run_dir, "test/wave1.mts"),
        hidden_node_test(run_dir, hidden),
        has_event(trial, "wave_verified"),
        has_event(trial, "wave2_started"),
        event_order(trial, "wave_verified", "wave2_started", "verified_before_wave2"),
        has_event(trial, "harness_killed"),
        has_event(trial, "job_completed"),
    ]

