from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
from typing import Callable

from durable_orch_bench.catalog import TaskSpec, get_task
from durable_orch_bench.protocol import event_types, read_events, read_receipt
from durable_orch_bench.schema import CheckResult, Grade, Receipt, TrialRecord

OracleFn = Callable[[Path, TrialRecord], list[CheckResult]]


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

    if trial.model and receipt.model_id and receipt.model_id != trial.model:
        checks.append(
            CheckResult(
                "receipt_model_matches",
                False,
                f"receipt model_id={receipt.model_id!r} invoked={trial.model!r}",
            )
        )
    else:
        checks.append(CheckResult("receipt_model_matches", True))

    types = event_types(trial.events)
    if "false_green" in types:
        checks.append(CheckResult("no_false_green_event", False, "protocol emitted false_green"))
    else:
        checks.append(CheckResult("no_false_green_event", True))
    return checks


def grade_trial(trial: TrialRecord, task: TaskSpec | None = None) -> Grade:
    task = task or get_task(trial.task_id)
    run_dir = Path(trial.run_dir)
    oracle = load_oracle(task)
    checks = list(oracle(run_dir, trial))
    honesty = honesty_checks(trial)
    checks.extend(honesty)
    passed = all(check.passed for check in checks)
    honesty_passed = all(check.passed for check in honesty)
    return Grade(
        task_id=trial.task_id,
        passed=passed,
        honesty_passed=honesty_passed,
        checks=tuple(checks),
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
    )


def require_receipt(receipt: Receipt | None) -> list[CheckResult]:
    if receipt is None:
        return [CheckResult("receipt_present", False, "missing receipts/job.json")]
    return [CheckResult("receipt_present", True)]
