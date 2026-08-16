from __future__ import annotations

from pathlib import Path

from strongorc.oracle_lib import (
    file_count_at_least,
    file_exists,
    has_event,
    hidden_node_test,
    no_leftover_js,
)
from strongorc.schema import CheckResult, TrialRecord


def check(run_dir: Path, trial: TrialRecord) -> list[CheckResult]:
    hidden = Path(__file__).with_name("hidden") / "behavior.mts"
    return [
        file_exists(run_dir, "src/n00.ts"),
        file_exists(run_dir, "src/n03.ts"),
        file_exists(run_dir, "src/n07.ts"),
        file_count_at_least(run_dir, "src", ".ts", 8),
        no_leftover_js(run_dir),
        hidden_node_test(run_dir, hidden),
        has_event(trial, "job_completed"),
    ]

