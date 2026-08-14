from pathlib import Path

from durable_orch_bench.oracle_lib import file_contains, file_exists, has_event
from durable_orch_bench.schema import CheckResult, TrialRecord


def check(run_dir: Path, trial: TrialRecord) -> list[CheckResult]:
    receipt = trial.receipt
    return [
        file_exists(run_dir, "output/work.txt"),
        file_contains(run_dir, "output/work.txt", "DONE"),
        has_event(trial, "worker_started"),
        has_event(trial, "job_completed"),
        CheckResult("receipt_present", receipt is not None),
        CheckResult(
            "workers_ran_positive",
            receipt is not None and receipt.workers_ran >= 1,
            "" if receipt and receipt.workers_ran >= 1 else "workers_ran < 1",
        ),
        CheckResult(
            "usd_positive",
            receipt is not None and receipt.usd > 0,
            "" if receipt and receipt.usd > 0 else "usd must be > 0",
        ),
        CheckResult(
            "model_not_default",
            receipt is not None and receipt.model_id not in {"", "default"},
            f"model_id={getattr(receipt, 'model_id', None)!r}",
        ),
    ]
