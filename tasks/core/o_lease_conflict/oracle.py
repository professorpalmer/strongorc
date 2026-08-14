from pathlib import Path

from durable_orch_bench.oracle_lib import file_absent, file_contains, file_exists, forbids_event, has_event
from durable_orch_bench.schema import CheckResult, TrialRecord


def check(run_dir: Path, trial: TrialRecord) -> list[CheckResult]:
    lease_events = [event for event in trial.events if event.type == "lease_acquired"]
    return [
        file_exists(run_dir, "parts/a.txt"),
        file_exists(run_dir, "parts/b.txt"),
        file_contains(run_dir, "parts/a.txt", "ALPHA"),
        file_contains(run_dir, "parts/b.txt", "BETA"),
        file_absent(run_dir, "shared/cell.txt"),
        CheckResult("two_leases", len(lease_events) >= 2, f"leases={len(lease_events)}"),
        has_event(trial, "job_completed"),
        forbids_event(trial, "lease_violated"),
    ]
