from __future__ import annotations

from pathlib import Path

from strongorc.oracle_lib import (
    event_count_at_least,
    file_exists,
    has_event,
    no_any_in_ts,
    no_leftover_js,
    pre_kill_hashes_match,
)
from strongorc.schema import CheckResult, TrialRecord


def check(run_dir: Path, trial: TrialRecord) -> list[CheckResult]:
    return [
        file_exists(run_dir, "src/layer1/n1.ts"),
        file_exists(run_dir, "src/layer2/n2.ts"),
        file_exists(run_dir, "src/layer3/n3.ts"),
        file_exists(run_dir, "src/layer4/n4.ts"),
        no_leftover_js(run_dir),
        no_any_in_ts(run_dir),
        event_count_at_least(trial, "harness_killed", 3),
        has_event(trial, "checkpoint_written"),
        has_event(trial, "resumed_from_checkpoint"),
        has_event(trial, "job_completed"),
        pre_kill_hashes_match(run_dir),
    ]

