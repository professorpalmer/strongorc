from pathlib import Path

from durable_orch_bench.oracle_lib import event_count_at_most, file_contains, file_exists, has_event
from durable_orch_bench.schema import CheckResult, TrialRecord


def check(run_dir: Path, trial: TrialRecord) -> list[CheckResult]:
    return [
        file_exists(run_dir, "output/first.txt"),
        file_exists(run_dir, "output/second.txt"),
        file_contains(run_dir, "output/first.txt", "DurableOrch"),
        file_contains(run_dir, "output/second.txt", "DurableOrch"),
        has_event(trial, "discovery_reused"),
        event_count_at_most(trial, "llm_call", 1),
        has_event(trial, "job_completed"),
    ]
