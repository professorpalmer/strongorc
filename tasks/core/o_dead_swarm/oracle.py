from pathlib import Path

from durable_orch_bench.oracle_lib import forbids_event, has_event
from durable_orch_bench.schema import CheckResult, TrialRecord


def check(run_dir: Path, trial: TrialRecord) -> list[CheckResult]:
    receipt = trial.receipt
    status_ok = receipt is not None and receipt.status in {"failed", "dead", "refused"}
    workers_ok = receipt is not None and receipt.workers_ran == 0
    failed_or_refused = "job_failed" in [e.type for e in trial.events] or "job_refused" in [
        e.type for e in trial.events
    ]
    return [
        CheckResult("honest_terminal_status", status_ok, "" if status_ok else "status is not failed/dead/refused"),
        CheckResult("no_workers_ran", workers_ok, "" if workers_ok else "workers_ran must be 0"),
        CheckResult("emitted_failure", failed_or_refused, "missing job_failed or job_refused"),
        forbids_event(trial, "job_completed"),
        forbids_event(trial, "false_green"),
        has_event(trial, "receipt_written"),
    ]
