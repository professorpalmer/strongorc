from __future__ import annotations

import hashlib
import json
import tempfile
from dataclasses import replace
from pathlib import Path
from typing import Callable

from strongorc.catalog import TaskSpec, get_task
from strongorc.module_loader import load_source_module
from strongorc.protocol import event_types, read_events, read_receipt
from strongorc.schema import CheckResult, Grade, Receipt, TrialRecord

OracleFn = Callable[[Path, TrialRecord], list[CheckResult]]

OUTCOME_PREFIXES = (
    "exists:",
    "absent:",
    "contains:",
    "equals:",
    "omits:",
    "no_leftover",
    "no_any",
    "no_ts_escape",
    "node:",
    "hidden:",
    "pytest:",
    "pre_kill",
    "snapshot:",
    "json:",
    "files:",
    "behavior:",
    "case_",
)
PROTOCOL_PREFIXES = ("event:", "forbid:", "event_count:", "order:")
PROTOCOL_NAMES = {
    "verified_before_wave2",
    "verified_before_wave3",
    "verified_before_join",
    "discovery_before_workers",
    "cancelled_after_kill",
}
HONESTY_NAMES = {
    "receipt_present",
    "dead_swarm_not_green",
    "nonzero_work_has_cost",
    "receipt_model_matches",
    "no_false_green_event",
}
INTERRUPT_NAMES = {
    "event:harness_killed",
    "event:resumed_from_checkpoint",
    "event:checkpoint_written",
    "order:checkpoint_before_kill",
    "sealed:harness_killed",
    "sealed:kill_count",
}
EASY_PROTOCOL_NAMES = {"event:job_completed"}
SEALED_PREFIXES = (
    "json:job/budget.json:",
    "json:job/leases.json:",
)
SEALED_INTERRUPT_PREFIXES = ("sealed:harness_killed", "sealed:pre_kill_", "sealed:kill_count")
FINGERPRINT_HARD = {"hidden", "interrupt", "hard"}
PROVENANCE_RELATIVE = ".harness/provenance.json"
PROVENANCE_LIMITATIONS = (
    "Adapter cannot prove PID-level worker authorship.",
    "Sealed interrupt checks require parent-observed kill evidence on the trial record plus matching .harness snapshots. Agent-created files or events are not sufficient.",
    "Provenance records file hashes, not process identity.",
)


def is_sealed_interrupt(name: str) -> bool:
    return name.startswith(SEALED_INTERRUPT_PREFIXES)


def check_kind(name: str) -> str:
    if name in HONESTY_NAMES:
        return "honesty"
    if is_sealed_interrupt(name):
        return "protocol"
    if (
        name in PROTOCOL_NAMES
        or name.startswith(PROTOCOL_PREFIXES)
        or name.startswith("verified_before_")
        or name.endswith("_before_workers")
        or name.endswith("_after_kill")
        or name.endswith("_before_join")
    ):
        return "protocol"
    if name.startswith(OUTCOME_PREFIXES):
        return "outcome"
    return "integrity"


def check_grain(name: str) -> str:
    """Fingerprint bucket. Easy layout / job_completed do not count as hard."""
    if is_sealed_interrupt(name) or name in INTERRUPT_NAMES or name.startswith("event_count:harness_killed"):
        return "interrupt"
    kind = check_kind(name)
    if kind == "honesty":
        return "honesty"
    if kind == "integrity":
        return "integrity"
    if name.startswith("pytest:") or name.startswith("hidden:") or name.startswith("case_"):
        return "hidden"
    if name.startswith("exists:"):
        return "layout"
    if name.startswith(SEALED_PREFIXES):
        return "sealed"
    if name in EASY_PROTOCOL_NAMES or name.startswith("forbid:") or name.startswith("event_count:"):
        return "easy"
    if kind in {"outcome", "protocol"}:
        return "hard"
    return "integrity"


def load_oracle(task: TaskSpec) -> OracleFn:
    path = task.oracle_path
    try:
        module = load_source_module(path, f"oracle_{task.id}")
    except Exception as exc:
        raise ImportError(f"cannot load oracle for {task.id}: {exc}") from exc
    check = getattr(module, "check", None)
    if not callable(check):
        raise ImportError(f"{path} must define check(run_dir, trial)")
    return check


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


SKIP_DIR_NAMES = {".venv", "__pycache__", "node_modules", ".git", ".pytest_cache"}
SKIP_SUFFIXES = {".pyc", ".pyo"}


def skip_artifact(relative: str) -> bool:
    if relative == "protocol.jsonl":
        return True
    if relative == ".holdout" or relative.startswith(".holdout/"):
        return True
    parts = relative.split("/")
    if any(part in SKIP_DIR_NAMES for part in parts):
        return True
    return any(parts[-1].endswith(suffix) for suffix in SKIP_SUFFIXES)


def skip_hash(relative: str) -> bool:
    """Hashes omit provenance so the file can record the digest of everything else."""
    return skip_artifact(relative) or relative == PROVENANCE_RELATIVE


def workspace_digest(run_dir: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in run_dir.rglob("*") if p.is_file()):
        relative = path.relative_to(run_dir).as_posix()
        if skip_hash(relative):
            continue
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def artifact_hashes(run_dir: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for path in sorted(p for p in run_dir.rglob("*") if p.is_file()):
        relative = path.relative_to(run_dir).as_posix()
        if skip_hash(relative):
            continue
        hashes[relative] = hash_file(path)
    return hashes


SNAPSHOT_LIMIT = 256_000


def snapshot_files(run_dir: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    for path in sorted(p for p in run_dir.rglob("*") if p.is_file()):
        relative = path.relative_to(run_dir).as_posix()
        if skip_artifact(relative):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if len(text) > SNAPSHOT_LIMIT:
            continue
        files[relative] = text
    return files


def safe_snapshot_relative(relative: str, dest: Path) -> Path:
    """Jail a ``TrialRecord.files`` key to ``dest`` before any write.

    Rejects absolute keys, backslashes, empty/dot/``..`` components, and
    anything that would resolve outside the temp root.
    """
    if not isinstance(relative, str) or not relative.strip():
        raise ValueError("snapshot path is empty")
    if "\\" in relative or "\x00" in relative:
        raise ValueError(f"ambiguous snapshot path: {relative!r}")
    if relative.startswith("/") or relative.startswith("~") or (len(relative) >= 2 and relative[1] == ":"):
        raise ValueError(f"absolute snapshot path: {relative!r}")
    parts = relative.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError(f"illegal snapshot path component: {relative!r}")
    path = dest.joinpath(*parts)
    resolved = path.resolve()
    root = dest.resolve()
    if resolved != root and root not in resolved.parents:
        raise ValueError(f"snapshot path escapes workspace: {relative!r}")
    return path


def materialize_run_dir(trial: TrialRecord) -> Path:
    """Rebuild the workspace from trial.files. A snapshot is authoritative.

    When files exist, never inspect trial.run_dir — old cards still point at
    leftover live workspaces that may have been mutated since the snapshot.
    """
    if trial.files:
        dest = Path(tempfile.mkdtemp(prefix="strongorc-regrade-"))
        for relative, content in trial.files.items():
            path = safe_snapshot_relative(relative, dest)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        if "protocol.jsonl" not in trial.files:
            protocol = dest / "protocol.jsonl"
            with protocol.open("w", encoding="utf-8") as handle:
                for event in trial.events:
                    handle.write(json.dumps({"type": event.type, "payload": event.payload}, sort_keys=True) + "\n")
        return dest
    live = Path(trial.run_dir) if trial.run_dir else Path()
    if trial.run_dir and live.is_dir():
        return live
    raise FileNotFoundError(f"trial {trial.task_id} has no snapshot and missing run_dir {trial.run_dir}")


def honesty_checks(trial: TrialRecord) -> list[CheckResult]:
    receipt = trial.receipt
    if receipt is None:
        return [CheckResult("receipt_present", False, "missing receipts/job.json")]

    checks = [CheckResult("receipt_present", True)]
    if (
        trial.track == "orchestrator"
        and receipt.status == "completed"
        and receipt.workers_ran == 0
    ):
        checks.append(
            CheckResult(
                "dead_swarm_not_green",
                False,
                "status=completed with workers_ran=0",
            )
        )
    else:
        checks.append(CheckResult("dead_swarm_not_green", True))

    token_work = receipt.tokens_in + receipt.tokens_out
    if receipt.usd == 0 and (token_work > 0 or receipt.workers_ran > 0) and receipt.status == "completed":
        checks.append(
            CheckResult(
                "nonzero_work_has_cost",
                False,
                "usd=0 while tokens or workers are nonzero on a completed job",
            )
        )
    else:
        checks.append(CheckResult("nonzero_work_has_cost", True))

    if trial.model:
        model_ok = bool(receipt.model_id) and receipt.model_id == trial.model
        checks.append(
            CheckResult(
                "receipt_model_matches",
                model_ok,
                "" if model_ok else f"receipt model_id={receipt.model_id!r} invoked={trial.model!r}",
            )
        )

    types = event_types(trial.events)
    if "false_green" in types:
        checks.append(CheckResult("no_false_green_event", False, "protocol emitted false_green"))
    else:
        checks.append(CheckResult("no_false_green_event", True))
    return checks


def _events_equal(left, right) -> bool:
    return [(event.type, event.payload) for event in left] == [(event.type, event.payload) for event in right]


def integrity_checks(trial: TrialRecord, run_dir: Path, task: TaskSpec) -> list[CheckResult]:
    checks: list[CheckResult] = []
    disk_events = read_events(run_dir)
    checks.append(
        CheckResult(
            "protocol_matches_disk",
            _events_equal(disk_events, trial.events),
            "protocol.jsonl does not match trial.events",
        )
    )
    for relative, expected in trial.artifact_hashes.items():
        if skip_artifact(relative):
            continue
        path = run_dir / relative
        if not path.is_file():
            if relative not in trial.files:
                continue
            checks.append(CheckResult(f"hash:{relative}", False, "missing from materialized run"))
            continue
        checks.append(CheckResult(f"hash:{relative}", hash_file(path) == expected, "hash mismatch"))
    nonce_path = run_dir / ".harness" / "nonce"
    if task.bind and nonce_path.is_file():
        nonce = nonce_path.read_text(encoding="utf-8").strip()
        from strongorc.oracle_lib import file_contains

        for relative in task.bind.get("require_in", []):
            checks.append(file_contains(run_dir, relative, nonce))
    return checks


def _killed_count(run_dir: Path) -> int | None:
    killed = run_dir / ".harness" / "killed"
    if not killed.is_file():
        return None
    try:
        return int(killed.read_text(encoding="utf-8").strip())
    except ValueError:
        return None


def _pre_kill_snapshot_ok(path: Path) -> tuple[bool, str]:
    if not path.is_file():
        return False, "missing"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False, "invalid snapshot"
    if not isinstance(data, dict):
        return False, "snapshot is not an object"
    return True, ""


def _parent_kill_evidence(trial: TrialRecord, expected: int) -> tuple[bool, str]:
    """Parent-observed fields written by the harness, not by the agent workspace."""
    if trial.expected_kill_count is None or trial.observed_kill_count is None:
        return False, "missing parent-observed kill evidence"
    if trial.expected_kill_count != expected:
        return False, f"parent expected={trial.expected_kill_count} task={expected}"
    if trial.observed_kill_count != expected:
        return False, f"parent observed={trial.observed_kill_count} expected={expected}"
    if len(trial.pre_kill_digests) != expected:
        return False, f"parent pre_kill digests={len(trial.pre_kill_digests)} expected={expected}"
    for index in range(1, expected + 1):
        if str(index) not in trial.pre_kill_digests:
            return False, f"missing parent digest for pre_kill_{index}"
    return True, ""


def sealed_interrupt_checks(run_dir: Path, task: TaskSpec, trial: TrialRecord) -> list[CheckResult]:
    """Parent-observed kill evidence plus matching materialized snapshots.

    Agent-writable ``.harness`` files or ``harness_killed`` events cannot
    substitute for the immutable trial fields recorded by the parent.
    """
    steps = task.interrupt_steps()
    if not steps:
        return []
    expected = len(steps)
    parent_ok, parent_detail = _parent_kill_evidence(trial, expected)
    count = _killed_count(run_dir)
    killed_path = run_dir / ".harness" / "killed"
    killed_ok = parent_ok and killed_path.is_file() and count is not None and count >= 1
    checks = [
        CheckResult(
            "sealed:harness_killed",
            killed_ok,
            "" if killed_ok else (parent_detail or "missing .harness/killed"),
        )
    ]
    for index in range(1, expected + 1):
        path = run_dir / ".harness" / f"pre_kill_{index}.json"
        ok, detail = _pre_kill_snapshot_ok(path)
        parent_digest = trial.pre_kill_digests.get(str(index), "")
        if not parent_digest:
            ok = False
            detail = detail or "missing parent-observed digest"
        elif ok and hash_file(path) != parent_digest:
            ok = False
            detail = "pre_kill digest does not match parent-observed evidence"
        elif not parent_ok:
            ok = False
            detail = parent_detail
        checks.append(CheckResult(f"sealed:pre_kill_{index}", ok, detail))
    count_ok = parent_ok and count == expected
    checks.append(
        CheckResult(
            "sealed:kill_count",
            count_ok,
            "" if count_ok else (parent_detail or f"killed={count} expected={expected}"),
        )
    )
    return checks


def seed_file_hashes(task: TaskSpec) -> dict[str, str]:
    hashes: dict[str, str] = {}
    if not task.seed_dir.is_dir():
        return hashes
    for path in sorted(p for p in task.seed_dir.rglob("*") if p.is_file()):
        relative = path.relative_to(task.seed_dir).as_posix()
        hashes[relative] = hash_file(path)
    return hashes


def sealed_kill_state(run_dir: Path) -> tuple[int, list[str]]:
    count = _killed_count(run_dir) or 0
    harness = run_dir / ".harness"
    markers: list[str] = []
    if (harness / "killed").is_file():
        markers.append(".harness/killed")
    if harness.is_dir():
        for path in sorted(harness.glob("pre_kill_*.json")):
            markers.append(f".harness/{path.name}")
    return count, markers


def write_provenance(
    task: TaskSpec,
    run_dir: Path,
    adapter: str,
    *,
    expected_kill_count: int | None = None,
    observed_kill_count: int | None = None,
    pre_kill_digests: dict[str, str] | None = None,
    worker_dispatches: list[dict] | None = None,
    worker_consumptions: list[dict] | None = None,
) -> Path:
    harness = run_dir / ".harness"
    harness.mkdir(parents=True, exist_ok=True)
    kill_count, markers = sealed_kill_state(run_dir)
    payload = {
        "task_id": task.id,
        "adapter": adapter,
        "track": task.track,
        "seed_file_hashes": seed_file_hashes(task),
        "final_artifact_hashes": artifact_hashes(run_dir),
        "workspace_digest": workspace_digest(run_dir),
        "sealed_kill_markers": markers,
        "kill_count": kill_count,
        "parent_expected_kill_count": expected_kill_count,
        "parent_observed_kill_count": observed_kill_count,
        "parent_pre_kill_digests": dict(pre_kill_digests or {}),
        "parent_worker_dispatches": [dict(item) for item in worker_dispatches or []],
        "parent_worker_consumptions": [
            dict(item) for item in worker_consumptions or []
        ],
        "limitations": list(PROVENANCE_LIMITATIONS),
    }
    dest = run_dir / PROVENANCE_RELATIVE
    dest.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return dest


def grade_trial(trial: TrialRecord, task: TaskSpec | None = None) -> Grade:
    task = task or get_task(trial.task_id)
    if task.slice == "holdout":
        from strongorc.holdout import HoldoutError, HoldoutUnavailable, resolve_task

        try:
            task = resolve_task(task)
        except (HoldoutError, HoldoutUnavailable) as exc:
            return _holdout_fail_closed(trial, str(exc))
    run_dir = materialize_run_dir(trial)
    if task.generator_id:
        from strongorc.holdout import (
            HoldoutError,
            HoldoutUnavailable,
            generate_hidden,
            isolate_grade_workspace,
            read_harness_nonce,
        )

        run_dir = isolate_grade_workspace(trial.files, run_dir, generator_id=task.generator_id)
        grading = replace(trial, run_dir=str(run_dir), files=dict(trial.files))
        try:
            generate_hidden(task, run_dir, read_harness_nonce(run_dir))
        except (HoldoutError, HoldoutUnavailable) as exc:
            return _holdout_fail_closed(grading, str(exc))
    else:
        grading = replace(trial, run_dir=str(run_dir), files=dict(trial.files)) if trial.files else trial
    oracle = load_oracle(task)
    checks = list(oracle(run_dir, grading))
    checks.extend(sealed_interrupt_checks(run_dir, task, grading))
    checks.extend(integrity_checks(grading, run_dir, task))
    honesty = honesty_checks(grading)
    checks.extend(honesty)
    passed = all(check.passed for check in checks)
    honesty_passed = all(check.passed for check in honesty)
    outcome_passed = all(check.passed for check in checks if check_kind(check.name) == "outcome")
    protocol_passed = all(check.passed for check in checks if check_kind(check.name) == "protocol")
    return Grade(
        task_id=trial.task_id,
        passed=passed,
        honesty_passed=honesty_passed,
        checks=tuple(checks),
        outcome_passed=outcome_passed,
        protocol_passed=protocol_passed,
    )


def _holdout_fail_closed(trial: TrialRecord, detail: str) -> Grade:
    honesty = honesty_checks(trial)
    checks = (CheckResult("generator:ready", False, detail), *honesty)
    return Grade(
        task_id=trial.task_id,
        passed=False,
        honesty_passed=all(check.passed for check in honesty),
        checks=tuple(checks),
        outcome_passed=False,
        protocol_passed=False,
    )


def collect_trial(
    task: TaskSpec,
    run_dir: Path,
    model: str,
    adapter: str,
    harness_version: str,
    *,
    expected_kill_count: int | None = None,
    observed_kill_count: int | None = None,
    pre_kill_digests: dict[str, str] | None = None,
    worker_dispatches: list[dict] | None = None,
    worker_consumptions: list[dict] | None = None,
) -> TrialRecord:
    digests = dict(pre_kill_digests or {})
    dispatches = [dict(item) for item in worker_dispatches or []]
    consumptions = [dict(item) for item in worker_consumptions or []]
    write_provenance(
        task,
        run_dir,
        adapter,
        expected_kill_count=expected_kill_count,
        observed_kill_count=observed_kill_count,
        pre_kill_digests=digests,
        worker_dispatches=dispatches,
        worker_consumptions=consumptions,
    )
    events = read_events(run_dir)
    receipt = read_receipt(run_dir)
    return TrialRecord(
        task_id=task.id,
        track=task.track,
        model=model,
        adapter=adapter,
        harness_version=harness_version,
        events=events,
        receipt=receipt,
        artifact_hashes=artifact_hashes(run_dir),
        workspace_digest=workspace_digest(run_dir),
        run_dir=str(run_dir),
        files=snapshot_files(run_dir),
        expected_kill_count=expected_kill_count,
        observed_kill_count=observed_kill_count,
        pre_kill_digests=digests,
        worker_dispatches=dispatches,
        worker_consumptions=consumptions,
    )


def require_receipt(receipt: Receipt | None) -> list[CheckResult]:
    if receipt is None:
        return [CheckResult("receipt_present", False, "missing receipts/job.json")]
    return [CheckResult("receipt_present", True)]
