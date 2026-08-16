from __future__ import annotations

from pathlib import Path

from strongorc.oracle_lib import (
    file_absent,
    file_exists,
    has_event,
    hidden_node_test,
    no_leftover_js,
)
from strongorc.schema import CheckResult, TrialRecord


def check(run_dir: Path, trial: TrialRecord) -> list[CheckResult]:
    hidden = Path(__file__).with_name("hidden") / "behavior.mts"
    return [
        file_exists(run_dir, "src/payload.ts"),
        file_absent(run_dir, "src/legacy.ts"),
        no_leftover_js(run_dir),
        hidden_node_test(run_dir, hidden),
        has_event(trial, "job_completed"),
    ]

