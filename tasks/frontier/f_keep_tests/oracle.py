from __future__ import annotations

from pathlib import Path

from strongorc.oracle_lib import (
    file_exists,
    file_text_equals,
    has_event,
    hidden_node_test,
    no_leftover_js,
    node_test_passes,
)
from strongorc.schema import CheckResult, TrialRecord


def check(run_dir: Path, trial: TrialRecord) -> list[CheckResult]:
    hidden = Path(__file__).with_name("hidden") / "behavior.mts"
    return [
        file_exists(run_dir, "src/add.ts"),
        file_text_equals(run_dir, "test/test.mts", 'import { add } from "../src/add.ts";\nif (add(2, 3) !== 5) { console.error(add(2, 3)); process.exit(1); }\nconsole.log("ok");\n'),
        no_leftover_js(run_dir),
        node_test_passes(run_dir, "test/test.mts"),
        hidden_node_test(run_dir, hidden),
        has_event(trial, "job_completed"),
    ]

