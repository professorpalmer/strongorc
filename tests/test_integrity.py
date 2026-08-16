from pathlib import Path

import pytest

from strongorc.cards import build_card
from strongorc.grade import honesty_checks
from strongorc.harness import run_slice
from strongorc.schema import ProtocolEvent, Receipt, TrialRecord


def _trial(**overrides) -> TrialRecord:
    base = dict(
        task_id="o_receipt_honesty",
        track="orchestrator",
        model="grok-4.6",
        adapter="command",
        harness_version="0.1.0",
        events=[ProtocolEvent(type="job_completed")],
        receipt=Receipt(
            status="completed",
            model_id="grok-4.6",
            usd=0.1,
            tokens_in=10,
            tokens_out=4,
            workers_ran=1,
        ),
        artifact_hashes={},
        workspace_digest="",
        run_dir="/tmp/unused",
        files={},
    )
    base.update(overrides)
    return TrialRecord(**base)


def test_empty_receipt_model_fails_honesty() -> None:
    trial = _trial(
        receipt=Receipt(
            status="completed",
            model_id="",
            usd=0.1,
            tokens_in=10,
            tokens_out=4,
            workers_ran=1,
        )
    )
    names = {check.name: check.passed for check in honesty_checks(trial)}
    assert names["receipt_model_matches"] is False


def test_command_failure_grades_the_slice(tmp_path: Path) -> None:
    results = run_slice(
        "core",
        adapter_name="command",
        model="broken",
        runs_root=tmp_path / "runs",
        adapter_kwargs={"cmd": "exit 2"},
    )
    assert len(results) == 12
    assert all(trial.receipt is not None for trial, _ in results)
    passed = {trial.task_id for trial, grade in results if grade.passed}
    assert passed <= {"o_dead_swarm"}


def test_card_uses_trial_harness_version(tmp_path: Path) -> None:
    results = run_slice(
        "core",
        adapter_name="scripted",
        model="scripted-pass",
        runs_root=tmp_path / "runs",
        adapter_kwargs={"persona": "pass"},
    )
    trials = [trial for trial, _ in results]
    grades = [grade for _, grade in results]
    for trial in trials:
        trial.harness_version = "9.9.9"
    card = build_card(trials, grades, model="scripted-pass", slice_name="core")
    assert card.harness_version == "9.9.9"
    trials[0].harness_version = "0.0.0"
    with pytest.raises(ValueError, match="mixed harness versions"):
        build_card(trials, grades, model="scripted-pass", slice_name="core")


def test_skip_artifact_drops_venv_and_pyc() -> None:
    from strongorc.grade import skip_artifact

    assert skip_artifact(".venv/bin/python") is True
    assert skip_artifact("jobnet/__pycache__/scheduler.cpython-314.pyc") is True
    assert skip_artifact("protocol.jsonl") is True
    assert skip_artifact(".pytest_cache/v/cache/nodeids") is True
    assert skip_artifact("jobnet/scheduler.py") is False
