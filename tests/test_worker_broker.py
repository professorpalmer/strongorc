from __future__ import annotations

import hashlib
import json
from pathlib import Path

from strongorc.catalog import TaskSpec
from strongorc.harness import run_task
from strongorc.worker_broker import WorkerBroker, WorkerClient


def _task_with_worker_pool(tmp_path: Path) -> TaskSpec:
    task_root = tmp_path / "task"
    task_root.mkdir()
    (task_root / "workers.py").write_text(
        """
from __future__ import annotations


def dispatch(worker_id, assignment, run_dir, nonce):
    return {
        "worker_id": worker_id,
        "answer": int(assignment["value"]) * 2,
        "nonce": nonce,
    }
""".lstrip(),
        encoding="utf-8",
    )
    return TaskSpec(
        id="hld_broker",
        track="orchestrator",
        slice="reason",
        title="broker fixture",
        timeout_seconds=30,
        root=task_root,
    )


def test_worker_broker_seals_dispatch_and_consumption(tmp_path: Path) -> None:
    task = _task_with_worker_pool(tmp_path)
    run_dir = tmp_path / "run"
    (run_dir / ".harness").mkdir(parents=True)
    (run_dir / ".harness" / "nonce").write_text("abc123\n", encoding="utf-8")

    with WorkerBroker(task, run_dir) as broker:
        client = WorkerClient.from_environment(broker.environment)
        dispatch = client.dispatch("analyst", {"value": 21})
        assert dispatch["report_path"] == "workers/dispatch_001.json"
        report = client.consume(dispatch["dispatch_id"])
        sealed = broker.snapshot()

    assert report == {"answer": 42, "nonce": "abc123", "worker_id": "analyst"}
    assert len(sealed["dispatches"]) == 1
    assert len(sealed["consumptions"]) == 1
    report_text = (run_dir / dispatch["report_path"]).read_text(encoding="utf-8")
    assert sealed["dispatches"][0]["report_sha256"] == hashlib.sha256(
        report_text.encode("utf-8")
    ).hexdigest()
    assert sealed["consumptions"][0]["dispatch_id"] == dispatch["dispatch_id"]


def test_worker_broker_refuses_unknown_dispatch_consumption(tmp_path: Path) -> None:
    task = _task_with_worker_pool(tmp_path)
    run_dir = tmp_path / "run"
    (run_dir / ".harness").mkdir(parents=True)
    (run_dir / ".harness" / "nonce").write_text("abc123\n", encoding="utf-8")

    with WorkerBroker(task, run_dir) as broker:
        client = WorkerClient.from_environment(broker.environment)
        response = client.request("consume", {"dispatch_id": "dispatch_999"})

    assert response["ok"] is False
    assert response["error"] == "unknown dispatch_id"
    assert broker.snapshot() == {"dispatches": [], "consumptions": []}


def test_worker_client_requires_broker_coordinates() -> None:
    try:
        WorkerClient.from_environment({})
    except ValueError as exc:
        assert str(exc) == "worker broker unavailable"
    else:
        raise AssertionError("missing worker broker coordinates were accepted")


def test_run_task_seals_broker_evidence_in_trial(tmp_path: Path) -> None:
    task = _task_with_worker_pool(tmp_path)
    (task.root / "prompt.md").write_text("Delegate the calculation.\n", encoding="utf-8")
    agents = task.root / "agents"
    agents.mkdir()
    (agents / "pass.py").write_text(
        """
import os
from pathlib import Path

from strongorc.agentlib import finish
from strongorc.protocol import emit
from strongorc.worker_broker import WorkerClient

run_dir = Path(RUN_DIR)
client = WorkerClient.from_environment(dict(os.environ))
dispatch = client.dispatch("analyst", {"value": 21})
report = client.consume(dispatch["dispatch_id"])
(run_dir / "answer.txt").write_text(str(report["answer"]) + "\\n", encoding="utf-8")
emit(run_dir, "job_completed")
finish(run_dir, MODEL, workers_ran=1, usd=0.01)
""".lstrip(),
        encoding="utf-8",
    )
    (task.root / "oracle.py").write_text(
        """
from pathlib import Path

from strongorc.schema import CheckResult


def check(run_dir, trial):
    answer = Path(run_dir) / "answer.txt"
    return [
        CheckResult("outcome:answer", answer.read_text(encoding="utf-8").strip() == "42"),
        CheckResult("protocol:dispatch", len(trial.worker_dispatches) == 1),
        CheckResult("protocol:consume", len(trial.worker_consumptions) == 1),
    ]
""".lstrip(),
        encoding="utf-8",
    )

    trial, grade = run_task(
        task,
        adapter_name="scripted",
        model="scripted-pass",
        runs_root=tmp_path / "runs",
        adapter_kwargs={"persona": "pass"},
    )

    assert grade.passed, [check for check in grade.checks if not check.passed]
    assert trial.worker_dispatches[0]["worker_id"] == "analyst"
    assert trial.worker_consumptions[0]["dispatch_id"] == "dispatch_001"
    provenance = json.loads(trial.files[".harness/provenance.json"])
    assert provenance["parent_worker_dispatches"] == trial.worker_dispatches
    assert provenance["parent_worker_consumptions"] == trial.worker_consumptions
