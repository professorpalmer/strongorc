from __future__ import annotations

from pathlib import Path

from strongorc.oracle_lib import (
    event_count_at_least,
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
        file_exists(run_dir, "src/left/left.ts"),
        file_exists(run_dir, "src/right/right.ts"),
        file_exists(run_dir, "src/join.ts"),
        file_exists(run_dir, "state/left.done"),
        file_exists(run_dir, "state/right.done"),
        no_leftover_js(run_dir),
        hidden_node_test(run_dir, hidden),
        event_count_at_least(trial, "worker_finished", 2),
        event_order(trial, "worker_finished", "job_completed", "verified_before_join"),
        has_event(trial, "job_completed"),
    ]

