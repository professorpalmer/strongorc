import json
import shutil
from pathlib import Path

import pytest

from strongorc.catalog import get_task, list_tasks
from strongorc.harness import run_slice, run_task

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node required for hard slice")

EXPECTED_FAIL_CHECK = {
    "h_kill_resume": "event:harness_killed",
    "h_hollow_migration": "no_leftover_js",
    "h_wave_gate": "verified_before_wave2",
    "h_lease_tree": "absent:src/shared/CONFLICT",
}


def test_hard_slice_has_four_tasks() -> None:
    tasks = list_tasks("hard")
    ids = [task.id for task in tasks]
    assert ids == ["h_hollow_migration", "h_kill_resume", "h_lease_tree", "h_wave_gate"]
    assert get_task("h_kill_resume").interrupt is not None
    assert get_task("h_kill_resume").track == "orchestrator"
    assert get_task("h_hollow_migration").track == "worker"


def test_scripted_pass_clears_hard(tmp_path: Path) -> None:
    results = run_slice(
        "hard",
        adapter_name="scripted",
        model="scripted-pass",
        runs_root=tmp_path / "pass",
        adapter_kwargs={"persona": "pass"},
    )
    failed = [grade.task_id for _, grade in results if not grade.passed]
    assert failed == []
    assert len(results) == 4


def test_scripted_fail_misses_intended_check(tmp_path: Path) -> None:
    results = run_slice(
        "hard",
        adapter_name="scripted",
        model="scripted-fail",
        runs_root=tmp_path / "fail",
        adapter_kwargs={"persona": "fail"},
    )
    assert len(results) == 4
    for trial, grade in results:
        assert grade.passed is False, trial.task_id
        names = {check.name for check in grade.checks if not check.passed}
        expected = EXPECTED_FAIL_CHECK[trial.task_id]
        assert expected in names, f"{trial.task_id} failed {sorted(names)}, expected {expected}"


def test_kill_resume_pass_is_a_real_harness_kill(tmp_path: Path) -> None:
    task = get_task("h_kill_resume")
    trial, grade = run_task(
        task,
        adapter_name="scripted",
        model="scripted-pass",
        runs_root=tmp_path / "kill",
        adapter_kwargs={"persona": "pass"},
    )
    assert grade.passed
    assert any(event.type == "harness_killed" for event in trial.events)
    snapshot = json.loads(trial.files[".harness/pre_kill_hashes.json"])
    assert snapshot
    for relative, digest in snapshot.items():
        assert relative.startswith("src/layer1/")
        assert trial.artifact_hashes[relative] == digest


def test_kill_resume_fail_never_sees_a_kill(tmp_path: Path) -> None:
    task = get_task("h_kill_resume")
    trial, grade = run_task(
        task,
        adapter_name="scripted",
        model="scripted-fail",
        runs_root=tmp_path / "kill-fail",
        adapter_kwargs={"persona": "fail"},
    )
    assert grade.passed is False
    assert all(event.type != "harness_killed" for event in trial.events)
    assert ".harness/killed" not in trial.files
