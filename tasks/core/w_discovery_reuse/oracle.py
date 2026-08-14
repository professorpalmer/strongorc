from pathlib import Path

from strongorc.oracle_lib import event_count_at_most, file_contains, file_exists, has_event
from strongorc.schema import CheckResult, TrialRecord


def check(run_dir: Path, trial: TrialRecord) -> list[CheckResult]:
    return [
        file_exists(run_dir, "output/first.txt"),
        file_exists(run_dir, "output/second.txt"),
        file_contains(run_dir, "output/first.txt", "StrongOrc"),
        file_contains(run_dir, "output/second.txt", "StrongOrc"),
        has_event(trial, "discovery_reused"),
        event_count_at_most(trial, "llm_call", 1),
        has_event(trial, "job_completed"),
    ]
