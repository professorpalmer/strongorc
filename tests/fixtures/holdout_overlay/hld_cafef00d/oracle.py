from __future__ import annotations

import json
from pathlib import Path

from strongorc.holdout import generated_root, opaque_case_name, read_harness_nonce
from strongorc.oracle_lib import file_exists, has_event
from strongorc.schema import CheckResult, TrialRecord


def check(run_dir: Path, trial: TrialRecord) -> list[CheckResult]:
    nonce = read_harness_nonce(run_dir)
    case_file = generated_root(run_dir) / "case.json"
    if not case_file.is_file():
        return [CheckResult("generator:ready", False, "missing generated case")]
    expected = json.loads(case_file.read_text(encoding="utf-8"))["expected"]
    answer = run_dir / "output" / "answer.txt"
    actual = answer.read_text(encoding="utf-8").strip() if answer.is_file() else ""
    name = opaque_case_name("answer", nonce)
    return [
        file_exists(run_dir, "output/answer.txt"),
        CheckResult(name, actual == expected, "" if actual == expected else "hidden case miss"),
        has_event(trial, "job_completed"),
    ]
