from __future__ import annotations

from pathlib import Path

from strongorc.oracle_lib import (
    file_exists,
    file_text_equals,
    has_event,
    no_leftover_js,
)
from strongorc.schema import CheckResult, TrialRecord


def check(run_dir: Path, trial: TrialRecord) -> list[CheckResult]:
    return [
        file_text_equals(run_dir, "src/layer1/keep.ts", 'export function keep(n: number): number {\n  return n + 7;\n}\n'),
        file_exists(run_dir, "src/layer2/next.ts"),
        no_leftover_js(run_dir, "src/layer2"),
        has_event(trial, "resumed_from_checkpoint"),
        has_event(trial, "job_completed"),
    ]

