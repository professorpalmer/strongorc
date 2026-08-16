from __future__ import annotations

from pathlib import Path

from strongorc.oracle_lib import (
    event_order,
    file_exists,
    has_event,
    hidden_node_test,
    json_field_equals,
    no_leftover_js,
)
from strongorc.schema import CheckResult, TrialRecord


def check(run_dir: Path, trial: TrialRecord) -> list[CheckResult]:
    hidden = Path(__file__).with_name("hidden") / "behavior.mts"
    return [
        file_exists(run_dir, "state/discoveries/scale.json"),
        json_field_equals(run_dir, "state/discoveries/scale.json", "scale", "n * 6"),
        file_exists(run_dir, "src/scale.ts"),
        no_leftover_js(run_dir),
        hidden_node_test(run_dir, hidden),
        has_event(trial, "discovery_materialized"),
        has_event(trial, "worker_started"),
        event_order(trial, "discovery_materialized", "worker_started", "discovery_before_workers"),
        has_event(trial, "job_completed"),
    ]

