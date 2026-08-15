from __future__ import annotations

from pathlib import Path

from strongorc.oracle_lib import (
    file_exists,
    forbids_event,
    has_event,
    no_any_in_ts,
    no_leftover_js,
    node_test_passes,
)
from strongorc.schema import TrialRecord

_TS = [f"src/n{i:02d}.ts" for i in range(16)] + ["src/index.ts"]


def check(run_dir: Path, trial: TrialRecord) -> list[CheckResult]:
    checks = [
        no_leftover_js(run_dir),
        no_any_in_ts(run_dir),
        node_test_passes(run_dir, "test/test.mts"),
        has_event(trial, "job_completed"),
        forbids_event(trial, "hollow_pass"),
    ]
    checks.extend(file_exists(run_dir, relative) for relative in _TS)
    return checks
