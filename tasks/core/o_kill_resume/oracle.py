from pathlib import Path

from durable_orch_bench.oracle_lib import file_contains, file_exists, forbids_event, has_event
from durable_orch_bench.schema import CheckResult, TrialRecord


def check(run_dir: Path, trial: TrialRecord) -> list[CheckResult]:
    return [
        file_exists(run_dir, "state/checkpoint.json"),
        file_exists(run_dir, "output/done.txt"),
        file_contains(run_dir, "output/done.txt", "layer1"),
        file_contains(run_dir, "output/done.txt", "layer2"),
        file_contains(run_dir, "output/done.txt", "layer3"),
        has_event(trial, "checkpoint_written"),
        has_event(trial, "resumed_from_checkpoint"),
        has_event(trial, "worker_started"),
        has_event(trial, "job_completed"),
        forbids_event(trial, "orchestrator_wrote_solution"),
    ]
