from pathlib import Path

from durable_orch_bench.oracle_lib import file_exists, has_event
from durable_orch_bench.schema import CheckResult, TrialRecord


def check(run_dir: Path, trial: TrialRecord) -> list[CheckResult]:
    return [
        file_exists(run_dir, "progress/step1.done"),
        file_exists(run_dir, "progress/step2.done"),
        file_exists(run_dir, "progress/step3.done"),
        has_event(trial, "resumed_from_checkpoint"),
        has_event(trial, "job_completed"),
    ]
