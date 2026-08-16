from __future__ import annotations

from pathlib import Path

from strongorc.oracle_lib import (
    file_absent,
    file_exists,
    forbids_event,
    has_event,
    hidden_node_test,
    no_any_in_ts,
)
from strongorc.schema import CheckResult, TrialRecord


def check(run_dir: Path, trial: TrialRecord) -> list[CheckResult]:
    hidden = Path(__file__).with_name("hidden") / "behavior.mts"
    return [
        file_exists(run_dir, "src/east/one.ts"),
        file_exists(run_dir, "src/west/two.ts"),
        file_absent(run_dir, "src/west/two.js"),
        no_any_in_ts(run_dir),
        hidden_node_test(run_dir, hidden),
        has_event(trial, "harness_killed"),
        has_event(trial, "resumed_from_checkpoint"),
        has_event(trial, "job_completed"),
        forbids_event(trial, "lease_violated"),
    ]

