from __future__ import annotations

from pathlib import Path

from strongorc import __version__
from strongorc.catalog import get_task
from strongorc.grade import collect_trial, grade_trial
from strongorc.oracle_lib import consumed_disk_evidence, dispatched_worker
from strongorc.schema import ProtocolEvent, Receipt, TrialRecord

LIVE = (
    Path.home()
    / ".strongorc"
    / "calibration"
    / "reason"
    / "openrouter-shell"
    / "reason-anthropic_claude-fable-5"
)


def _hidden_pass_count(task_id: str, run_dir: Path) -> tuple[int, int]:
    task = get_task(task_id)
    trial = collect_trial(task, run_dir, "anthropic/claude-fable-5", "command", __version__)
    trial.confinement = "unconfined"
    grade = grade_trial(trial, task)
    hidden = [check for check in grade.checks if check.name.startswith("pytest:hidden:")]
    return sum(1 for check in hidden if check.passed), len(hidden)


def test_surface_accepts_function_apply_without_pair_class(tmp_path: Path) -> None:
    pkg = tmp_path / "quill"
    pkg.mkdir()
    (pkg / "__init__.py").write_text(
        "def apply(a, b):\n    return a + b\n",
        encoding="utf-8",
    )
    traces = tmp_path / "state"
    traces.mkdir()
    (traces / "traces.json").write_text(
        '{"pairs": [{"a": 2, "b": 3, "out": 5}, {"a": 4, "b": 1, "out": 5},'
        ' {"a": 0, "b": 7, "out": 7}, {"a": 3, "b": 3, "out": 6}]}\n',
        encoding="utf-8",
    )
    passed, total = _hidden_pass_count("r_retract_rule_r1", tmp_path)
    assert total == 8
    assert passed == 8


def test_surface_still_rejects_wrong_operation(tmp_path: Path) -> None:
    pkg = tmp_path / "quill"
    pkg.mkdir()
    (pkg / "__init__.py").write_text(
        "def apply(a, b):\n    return a * b\n",
        encoding="utf-8",
    )
    traces = tmp_path / "state"
    traces.mkdir()
    (traces / "traces.json").write_text(
        '{"pairs": [{"a": 2, "b": 3, "out": 5}, {"a": 4, "b": 1, "out": 5},'
        ' {"a": 0, "b": 7, "out": 7}, {"a": 3, "b": 3, "out": 6}]}\n',
        encoding="utf-8",
    )
    passed, total = _hidden_pass_count("r_retract_rule_r1", tmp_path)
    assert total == 8
    assert passed < 8


def test_probe_events_count_as_disk_evidence() -> None:
    def trial(*types: str) -> TrialRecord:
        return TrialRecord(
            task_id="t",
            track="worker",
            model="m",
            adapter="command",
            harness_version="0.6.0",
            events=[ProtocolEvent(type=name) for name in types],
            receipt=None,
            artifact_hashes={},
            workspace_digest="",
            run_dir="",
        )

    assert consumed_disk_evidence(trial("probe_written")).passed
    assert consumed_disk_evidence(trial("artifact_consumed")).passed
    assert consumed_disk_evidence(trial("worker_started")).passed
    assert consumed_disk_evidence(trial("job_completed")).passed is False

    empty = trial("job_completed")
    assert dispatched_worker(empty).passed is False
    assert dispatched_worker(trial("worker_dispatched")).passed
    billed = TrialRecord(
        task_id="t",
        track="orchestrator",
        model="m",
        adapter="command",
        harness_version="0.6.0",
        events=[],
        receipt=Receipt(
            status="completed",
            model_id="m",
            usd=1.0,
            tokens_in=10,
            tokens_out=4,
            workers_ran=1,
        ),
        artifact_hashes={},
        workspace_digest="",
        run_dir="",
    )
    assert dispatched_worker(billed).passed


def test_surface_does_not_invent_a_clinic_repairer(tmp_path: Path) -> None:
    pkg = tmp_path / "hearth"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("BODY = 'ok'\n", encoding="utf-8")
    passed, total = _hidden_pass_count("r_diagnose_kill_r1", tmp_path)
    assert total == 8
    assert passed < 6
