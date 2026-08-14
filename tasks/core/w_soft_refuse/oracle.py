from pathlib import Path

from durable_orch_bench.oracle_lib import file_absent, forbids_event, has_event
from durable_orch_bench.schema import CheckResult, TrialRecord


def check(run_dir: Path, trial: TrialRecord) -> list[CheckResult]:
    receipt = trial.receipt
    return [
        file_absent(run_dir, "output/success.txt"),
        has_event(trial, "job_refused"),
        forbids_event(trial, "job_completed"),
        forbids_event(trial, "false_green"),
        CheckResult(
            "status_refused",
            receipt is not None and receipt.status == "refused",
            f"status={getattr(receipt, 'status', None)!r}",
        ),
    ]
