from __future__ import annotations

from pathlib import Path

from strongorc.oracle_lib import (
    file_contains,
    file_exists,
    forbids_event,
    has_event,
    no_any_in_ts,
    no_leftover_js,
    node_test_passes,
    pre_kill_hashes_match,
)
from strongorc.schema import TrialRecord

_TS = [
    "src/layer1/alpha.ts",
    "src/layer1/beta.ts",
    "src/layer1/gamma.ts",
    "src/layer1/delta.ts",
    "src/layer2/echo.ts",
    "src/layer2/foxtrot.ts",
    "src/layer2/golf.ts",
    "src/layer2/hotel.ts",
    "src/layer3/india.ts",
    "src/layer3/juliet.ts",
    "src/layer3/kilo.ts",
    "src/layer3/lima.ts",
]


def check(run_dir: Path, trial: TrialRecord) -> list[CheckResult]:
    checks = [
        file_exists(run_dir, ".harness/killed"),
        file_exists(run_dir, ".harness/pre_kill_hashes.json"),
        file_exists(run_dir, "state/checkpoint.json"),
        file_contains(run_dir, "state/checkpoint.json", "layer1"),
        has_event(trial, "harness_killed"),
        has_event(trial, "checkpoint_written"),
        has_event(trial, "resumed_from_checkpoint"),
        has_event(trial, "worker_started"),
        has_event(trial, "job_completed"),
        forbids_event(trial, "orchestrator_wrote_solution"),
        pre_kill_hashes_match(run_dir),
        no_leftover_js(run_dir),
        no_any_in_ts(run_dir),
        node_test_passes(run_dir, "test/lima.mts"),
    ]
    checks.extend(file_exists(run_dir, relative) for relative in _TS)
    return checks
