from __future__ import annotations

from pathlib import Path

from strongorc.oracle_lib import (
    event_order,
    file_exists,
    has_event,
    hidden_node_test,
    no_leftover_js,
)
from strongorc.schema import CheckResult, TrialRecord


def check(run_dir: Path, trial: TrialRecord) -> list[CheckResult]:
    hidden = Path(__file__).with_name("hidden") / "behavior.mts"
    return [
        file_exists(run_dir, "src/add.ts"),
        file_exists(run_dir, "src/mul.ts"),
        no_leftover_js(run_dir),
        hidden_node_test(run_dir, hidden),
        has_event(trial, "wave_verified"),
        has_event(trial, "wave2_started"),
        event_order(trial, "wave_verified", "wave2_started", "verified_before_wave2"),
        has_event(trial, "job_completed"),
    ]

