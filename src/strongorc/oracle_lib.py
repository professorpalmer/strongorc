from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

from strongorc.nodeutil import run_node_test
from strongorc.protocol import event_types
from strongorc.schema import CheckResult, TrialRecord


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


def event_count_at_least(trial: TrialRecord, name: str, minimum: int) -> CheckResult:
    count = event_types(trial.events).count(name)
    return CheckResult(
        f"event_count:{name}>={minimum}",
        count >= minimum,
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


def no_leftover_js(run_dir: Path, under: str = "src") -> CheckResult:
    root = run_dir / under
    if not root.is_dir():
        return CheckResult("no_leftover_js", False, f"missing {under}")
    leftovers = [path.relative_to(run_dir).as_posix() for path in sorted(root.rglob("*.js"))]
    return CheckResult("no_leftover_js", leftovers == [], f"left {leftovers}" if leftovers else "")


def no_any_in_ts(run_dir: Path, under: str = "src") -> CheckResult:
    root = run_dir / under
    if not root.is_dir():
        return CheckResult("no_any", False, f"missing {under}")
    hits = [
        path.relative_to(run_dir).as_posix()
        for path in sorted(root.rglob("*.ts"))
        if re.search(r"\bany\b", path.read_text(encoding="utf-8"))
    ]
    return CheckResult("no_any", hits == [], f"type escape in {hits}" if hits else "")


def hidden_node_test(run_dir: Path, hidden_test: Path) -> CheckResult:
    dest = run_dir / ".harness" / f"hidden_{hidden_test.name}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(hidden_test.read_text(encoding="utf-8"), encoding="utf-8")
    result = node_test_passes(run_dir, dest.relative_to(run_dir).as_posix())
    return CheckResult(f"hidden:{hidden_test.name}", result.passed, result.detail)


def node_test_passes(run_dir: Path, relative: str) -> CheckResult:
    try:
        completed = run_node_test(run_dir, relative)
    except FileNotFoundError:
        return CheckResult(f"node:{relative}", False, "node not installed")
    except subprocess.TimeoutExpired:
        return CheckResult(f"node:{relative}", False, "timeout")
    ok = completed.returncode == 0
    detail = "" if ok else (completed.stderr or completed.stdout)[:300]
    return CheckResult(f"node:{relative}", ok, detail)


def snapshot_hashes_match(run_dir: Path, relative: str, name: str = "") -> CheckResult:
    snap = run_dir / relative
    label = name or f"snapshot:{relative}"
    if not snap.is_file():
        return CheckResult(label, False, "missing snapshot")
    expected = json.loads(snap.read_text(encoding="utf-8"))
    if not expected:
        return CheckResult(label, False, "empty snapshot")
    mismatches: list[str] = []
    for path_name, digest in expected.items():
        path = run_dir / path_name
        if not path.is_file():
            mismatches.append(f"missing {path_name}")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != digest:
            mismatches.append(path_name)
    return CheckResult(label, not mismatches, ", ".join(mismatches) if mismatches else "")


def pre_kill_hashes_match(run_dir: Path) -> CheckResult:
    return snapshot_hashes_match(run_dir, ".harness/pre_kill_hashes.json", "pre_kill_hashes_match")


def event_order(trial: TrialRecord, earlier: str, later: str, name: str) -> CheckResult:
    types = event_types(trial.events)
    ok = earlier in types and later in types and types.index(earlier) < types.index(later)
    return CheckResult(name, ok, f"order={types}")
