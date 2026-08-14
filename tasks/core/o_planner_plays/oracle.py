from pathlib import Path

from durable_orch_bench.oracle_lib import file_contains, file_exists, forbids_event, has_event
from durable_orch_bench.schema import CheckResult, TrialRecord


def check(run_dir: Path, trial: TrialRecord) -> list[CheckResult]:
    writer = (run_dir / "output" / "writer.txt").read_text(encoding="utf-8").strip() if (
        run_dir / "output" / "writer.txt"
    ).is_file() else ""
    return [
        file_exists(run_dir, "output/solution.txt"),
        file_contains(run_dir, "output/solution.txt", "ORCH-NEVER-PLAYS-7F3A"),
        has_event(trial, "worker_started"),
        has_event(trial, "worker_finished"),
        has_event(trial, "job_completed"),
        forbids_event(trial, "orchestrator_wrote_solution"),
        CheckResult("worker_wrote_solution", writer == "worker", f"writer={writer!r}"),
    ]
