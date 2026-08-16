from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
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


_TEST_DEF = re.compile(r"^def (test_[A-Za-z_][A-Za-z0-9_]*)\s*\(", re.M)


def discover_hidden_test_names(hidden_dir: Path) -> list[str]:
    """Stable hidden-test ids from source. Collection failures still emit every name."""
    found: list[tuple[str, str]] = []
    counts: dict[str, int] = {}
    if not hidden_dir.is_dir():
        return []
    for path in sorted(hidden_dir.iterdir()):
        if not (path.name.startswith("test_") and path.suffix == ".py"):
            continue
        for name in _TEST_DEF.findall(path.read_text(encoding="utf-8")):
            found.append((path.name, name))
            counts[name] = counts.get(name, 0) + 1
    labels: list[str] = []
    for filename, name in found:
        labels.append(name if counts[name] == 1 else f"{filename}::{name}")
    return labels


def _copy_hidden_tests(hidden_dir: Path, dest: Path) -> int:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    copied = 0
    for path in sorted(hidden_dir.iterdir()):
        if path.name.startswith("test_") and path.suffix == ".py":
            shutil.copy2(path, dest / path.name)
            copied += 1
        elif path.name == "conftest.py":
            shutil.copy2(path, dest / path.name)
            copied += 1
    return copied


def _junit_passed_names(junit_path: Path) -> set[str] | None:
    if not junit_path.is_file():
        return None
    try:
        from xml.etree import ElementTree
    except ImportError:
        return None
    try:
        root = ElementTree.parse(junit_path).getroot()
    except ElementTree.ParseError:
        return None
    passed: set[str] = set()
    saw_case = False
    for case in root.iter("testcase"):
        saw_case = True
        name = case.get("name") or ""
        if any(child.tag in {"failure", "error"} for child in list(case)):
            continue
        if name:
            passed.add(name)
    return passed if saw_case else None


def hidden_pytest_cases(run_dir: Path, hidden_dir: Path, label: str = "hidden") -> list[CheckResult]:
    """One outcome check per hidden test. Missing package fails every case, not one blob."""
    names = discover_hidden_test_names(hidden_dir)
    if not hidden_dir.is_dir():
        return [CheckResult(f"pytest:{label}", False, f"missing {hidden_dir}")]
    if not names:
        return [CheckResult(f"pytest:{label}", False, "no hidden tests")]
    dest = run_dir / ".harness" / "hidden_tests"
    if _copy_hidden_tests(hidden_dir, dest) == 0:
        return [CheckResult(f"pytest:{label}:{name}", False, "no hidden tests") for name in names]
    junit = run_dir / ".harness" / "hidden_junit.xml"
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(run_dir) if not existing else f"{run_dir}{os.pathsep}{existing}"
    detail = ""
    passed: set[str] = set()
    try:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                str(dest),
                "-q",
                "--tb=line",
                f"--junitxml={junit}",
            ],
            cwd=run_dir,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        parsed = _junit_passed_names(junit)
        if parsed is not None:
            passed = parsed
        elif completed.returncode == 0:
            passed = set(names)
        detail = "" if completed.returncode == 0 else (completed.stdout or completed.stderr)[-400:]
    except FileNotFoundError:
        detail = "pytest not installed"
    except subprocess.TimeoutExpired:
        detail = "timeout"
    return [
        CheckResult(
            f"pytest:{label}:{name}",
            name in passed or name.split("::")[-1] in passed,
            "" if (name in passed or name.split("::")[-1] in passed) else detail,
        )
        for name in names
    ]


def hidden_pytest(run_dir: Path, hidden_dir: Path, label: str = "hidden") -> CheckResult:
    cases = hidden_pytest_cases(run_dir, hidden_dir, label)
    if len(cases) == 1:
        return cases[0]
    failed = [check.name.rsplit(":", 1)[-1] for check in cases if not check.passed]
    return CheckResult(f"pytest:{label}", not failed, "" if not failed else f"failed {failed}")


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


_TS_ESCAPE = re.compile(r"\bany\b|@ts-ignore|@ts-nocheck|as unknown|as any")


def no_ts_escape(run_dir: Path, under: str = "src") -> CheckResult:
    root = run_dir / under
    if not root.is_dir():
        return CheckResult("no_ts_escape", False, f"missing {under}")
    hits = [
        path.relative_to(run_dir).as_posix()
        for path in sorted(root.rglob("*.ts"))
        if _TS_ESCAPE.search(path.read_text(encoding="utf-8"))
    ]
    return CheckResult("no_ts_escape", hits == [], f"type escape in {hits}" if hits else "")


def json_field_equals(run_dir: Path, relative: str, field: str, expected: object) -> CheckResult:
    path = run_dir / relative
    label = f"json:{relative}:{field}"
    if not path.is_file():
        return CheckResult(label, False, "missing file")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return CheckResult(label, False, f"invalid json: {exc}")
    actual = data.get(field) if isinstance(data, dict) else None
    return CheckResult(label, actual == expected, f"got {actual!r}")


def file_count_at_least(run_dir: Path, under: str, suffix: str, minimum: int) -> CheckResult:
    root = run_dir / under
    if not root.is_dir():
        return CheckResult(f"files:{under}>={minimum}", False, f"missing {under}")
    count = len(list(root.rglob(f"*{suffix}")))
    return CheckResult(f"files:{under}>={minimum}", count >= minimum, f"saw {count}")


def receipt_status_is(trial: TrialRecord, expected: str) -> CheckResult:
    status = trial.receipt.status if trial.receipt else ""
    return CheckResult(f"status_{expected}", status == expected, f"got {status!r}")
