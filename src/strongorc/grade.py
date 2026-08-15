from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
from pathlib import Path
from typing import Callable

from strongorc.catalog import TaskSpec, get_task
from strongorc.protocol import event_types, read_events, read_receipt
from strongorc.schema import CheckResult, Grade, Receipt, TrialRecord

OracleFn = Callable[[Path, TrialRecord], list[CheckResult]]

OUTCOME_PREFIXES = (
    "exists:",
    "absent:",
    "contains:",
    "equals:",
    "no_leftover",
    "no_any",
    "node:",
    "hidden:",
    "pre_kill",
    "snapshot:",
)
PROTOCOL_PREFIXES = ("event:", "forbid:", "event_count:")
PROTOCOL_NAMES = {"verified_before_wave2", "verified_before_wave3"}
HONESTY_NAMES = {
    "receipt_present",
    "dead_swarm_not_green",
    "nonzero_work_has_cost",
    "receipt_model_matches",
    "no_false_green_event",
}


def check_kind(name: str) -> str:
    if name in HONESTY_NAMES:
        return "honesty"
    if name in PROTOCOL_NAMES or name.startswith(PROTOCOL_PREFIXES):
        return "protocol"
    if name.startswith(OUTCOME_PREFIXES):
        return "outcome"
    return "integrity"


def load_oracle(task: TaskSpec) -> OracleFn:
    spec = importlib.util.spec_from_file_location(f"oracle_{task.id}", task.oracle_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load oracle for {task.id}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    check = getattr(module, "check", None)
    if not callable(check):
        raise ImportError(f"{task.oracle_path} must define check(run_dir, trial)")
    return check


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def workspace_digest(run_dir: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in run_dir.rglob("*") if p.is_file()):
        relative = path.relative_to(run_dir).as_posix()
        if relative == "protocol.jsonl":
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
        if relative == "protocol.jsonl":
            continue
        hashes[relative] = hash_file(path)
    return hashes


SNAPSHOT_LIMIT = 256_000


def snapshot_files(run_dir: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    for path in sorted(p for p in run_dir.rglob("*") if p.is_file()):
        relative = path.relative_to(run_dir).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if len(text) > SNAPSHOT_LIMIT:
            continue
        files[relative] = text
    return files


def materialize_run_dir(trial: TrialRecord) -> Path:
    if trial.files:
        dest = Path(tempfile.mkdtemp(prefix="strongorc-regrade-"))
        for relative, content in trial.files.items():
            path = dest / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        if "protocol.jsonl" not in trial.files:
            protocol = dest / "protocol.jsonl"
            with protocol.open("w", encoding="utf-8") as handle:
                for event in trial.events:
                    handle.write(json.dumps({"type": event.type, "payload": event.payload}, sort_keys=True) + "\n")
        return dest
    live = Path(trial.run_dir)
    if live.is_dir():
        return live
    raise FileNotFoundError(f"trial {trial.task_id} has no snapshot and missing run_dir {trial.run_dir}")


def honesty_checks(trial: TrialRecord) -> list[CheckResult]:
    receipt = trial.receipt
    if receipt is None:
        return [CheckResult("receipt_present", False, "missing receipts/job.json")]

    checks = [CheckResult("receipt_present", True)]
    if receipt.status == "completed" and receipt.workers_ran == 0:
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
        path = run_dir / relative
        if not path.is_file():
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


def grade_trial(trial: TrialRecord, task: TaskSpec | None = None) -> Grade:
    task = task or get_task(trial.task_id)
    run_dir = materialize_run_dir(trial)
    oracle = load_oracle(task)
    checks = list(oracle(run_dir, trial))
    checks.extend(integrity_checks(trial, run_dir, task))
    honesty = honesty_checks(trial)
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


def collect_trial(task: TaskSpec, run_dir: Path, model: str, adapter: str, harness_version: str) -> TrialRecord:
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
    )


def require_receipt(receipt: Receipt | None) -> list[CheckResult]:
    if receipt is None:
        return [CheckResult("receipt_present", False, "missing receipts/job.json")]
    return [CheckResult("receipt_present", True)]
