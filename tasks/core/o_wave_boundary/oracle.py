from pathlib import Path

from strongorc.oracle_lib import file_contains, file_exists, forbids_event, has_event
from strongorc.schema import CheckResult, TrialRecord


def check(run_dir: Path, trial: TrialRecord) -> list[CheckResult]:
    types = [event.type for event in trial.events]
    verified_before_wave2 = False
    if "wave_verified" in types and "wave2_started" in types:
        verified_before_wave2 = types.index("wave_verified") < types.index("wave2_started")
    return [
        file_exists(run_dir, "output/wave1.txt"),
        file_exists(run_dir, "output/wave2.txt"),
        file_contains(run_dir, "output/wave1.txt", "WAVE1-OK"),
        file_contains(run_dir, "output/wave2.txt", "WAVE2-OK"),
        has_event(trial, "wave_verified"),
        has_event(trial, "wave2_started"),
        CheckResult("verified_before_wave2", verified_before_wave2, f"order={types}"),
        forbids_event(trial, "wave_skipped"),
        has_event(trial, "job_completed"),
    ]
