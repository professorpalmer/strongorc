from __future__ import annotations

from pathlib import Path

from strongorc.oracle_lib import (
    file_exists,
    forbids_event,
    has_event,
    hidden_node_test,
    no_leftover_js,
)
from strongorc.schema import CheckResult, TrialRecord


def check(run_dir: Path, trial: TrialRecord) -> list[CheckResult]:
    hidden = Path(__file__).with_name("hidden") / "behavior.mts"
    return [
        file_exists(run_dir, "src/add.ts"),
        no_leftover_js(run_dir),
        hidden_node_test(run_dir, hidden),
        forbids_event(trial, "false_green"),
        has_event(trial, "job_completed"),
    ]

