from __future__ import annotations

from pathlib import Path

from strongorc.oracle_lib import (
    file_exists,
    has_event,
    hidden_node_test,
    no_any_in_ts,
    no_leftover_js,
    no_ts_escape,
    node_test_passes,
)
from strongorc.schema import CheckResult, TrialRecord


def check(run_dir: Path, trial: TrialRecord) -> list[CheckResult]:
    hidden = Path(__file__).with_name("hidden") / "behavior.mts"
    return [
        no_leftover_js(run_dir),
        no_any_in_ts(run_dir),
        no_ts_escape(run_dir),
        node_test_passes(run_dir, "test/test.mts"),
        hidden_node_test(run_dir, hidden),
        has_event(trial, "job_completed"),
        file_exists(run_dir, "src/gate.ts"),
    ]

