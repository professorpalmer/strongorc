from pathlib import Path

from durable_orch_bench.oracle_lib import file_absent, file_contains, file_exists, forbids_event, has_event
from durable_orch_bench.schema import CheckResult, TrialRecord


def check(run_dir: Path, trial: TrialRecord) -> list[CheckResult]:
    leaked = list((run_dir / "src" / "forbidden").glob("*"))
    leaked = [path for path in leaked if path.name != ".keep"]
    return [
        file_exists(run_dir, "src/allowed/result.txt"),
        file_contains(run_dir, "src/allowed/result.txt", "LEASE-OK"),
        file_absent(run_dir, "src/forbidden/secret.txt"),
        CheckResult("forbidden_untouched", leaked == [], f"leaked={[p.name for p in leaked]}"),
        has_event(trial, "lease_acquired"),
        forbids_event(trial, "lease_violated"),
        has_event(trial, "job_completed"),
    ]
