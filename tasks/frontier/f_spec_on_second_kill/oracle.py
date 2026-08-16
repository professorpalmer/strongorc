from __future__ import annotations

from pathlib import Path

from strongorc.oracle_lib import (
    event_count_at_least,
    file_exists,
    has_event,
    hidden_node_test,
    no_leftover_js,
)
from strongorc.schema import CheckResult, TrialRecord


def check(run_dir: Path, trial: TrialRecord) -> list[CheckResult]:
    hidden = Path(__file__).with_name("hidden") / "behavior.mts"
    return [
        file_exists(run_dir, "src/prep/prep.ts"),
        file_exists(run_dir, "src/scale.ts"),
        no_leftover_js(run_dir),
        hidden_node_test(run_dir, hidden),
        event_count_at_least(trial, "harness_killed", 2),
        has_event(trial, "job_completed"),
    ]

