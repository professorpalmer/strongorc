from __future__ import annotations

from pathlib import Path

from durable_orch_bench.protocol import event_types
from durable_orch_bench.schema import CheckResult, TrialRecord


def has_event(trial: TrialRecord, name: str) -> CheckResult:
    present = name in event_types(trial.events)
    return CheckResult(f"event:{name}", present, "" if present else f"missing {name}")


def forbids_event(trial: TrialRecord, name: str) -> CheckResult:
    present = name in event_types(trial.events)
    return CheckResult(f"forbid:{name}", not present, f"emitted {name}" if present else "")


def event_count_at_most(trial: TrialRecord, name: str, maximum: int) -> CheckResult:
    count = event_types(trial.events).count(name)
    return CheckResult(
        f"event_count:{name}<={maximum}",
        count <= maximum,
        f"saw {count}",
    )


def file_exists(run_dir: Path, relative: str) -> CheckResult:
    path = run_dir / relative
    return CheckResult(f"exists:{relative}", path.is_file(), "" if path.is_file() else "missing")


def file_absent(run_dir: Path, relative: str) -> CheckResult:
    if not run_dir.is_dir():
        return CheckResult(f"absent:{relative}", False, "run_dir missing")
    path = run_dir / relative
    return CheckResult(f"absent:{relative}", not path.exists(), "present" if path.exists() else "")


def file_contains(run_dir: Path, relative: str, needle: str) -> CheckResult:
    path = run_dir / relative
    if not path.is_file():
        return CheckResult(f"contains:{relative}", False, "missing file")
    text = path.read_text(encoding="utf-8")
    ok = needle in text
    return CheckResult(f"contains:{relative}", ok, "" if ok else f"missing {needle!r}")


def file_text_equals(run_dir: Path, relative: str, expected: str) -> CheckResult:
    path = run_dir / relative
    if not path.is_file():
        return CheckResult(f"equals:{relative}", False, "missing file")
    actual = path.read_text(encoding="utf-8")
    return CheckResult(f"equals:{relative}", actual == expected, f"got {actual!r}")
