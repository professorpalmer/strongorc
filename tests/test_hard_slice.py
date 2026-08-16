import json
import shutil
from pathlib import Path

import pytest

from strongorc.catalog import get_task, list_tasks
from strongorc.harness import run_slice, run_task

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node required for hard slice")

HARD_IDS = [
    "h_double_kill",
    "h_hollow_chain",
    "h_hollow_migration",
    "h_hollow_visible",
    "h_kill_resume",
    "h_lease_shift",
    "h_lease_tree",
    "h_lease_unleased",
    "h_lying_checkpoint",
    "h_nonce_bind",
    "h_resume_reread",
    "h_split_brain",
    "h_stale_discovery",
    "h_wave_gate",
    "h_wave_repair",
    "h_worker_cap",
]

EXPECTED_FAIL_CHECK = {
    "h_double_kill": "event_count:harness_killed>=2",
    "h_hollow_chain": "no_leftover_js",
    "h_hollow_migration": "no_leftover_js",
    "h_hollow_visible": "hidden:behavior.mts",
    "h_kill_resume": "event:harness_killed",
    "h_lease_shift": "event:harness_killed",
    "h_lease_tree": "absent:src/shared/CONFLICT",
    "h_lease_unleased": "absent:src/gamma/stay.ts",
    "h_lying_checkpoint": "no_leftover_js",
    "h_nonce_bind": "contains:src/index.ts",
    "h_resume_reread": "event:harness_killed",
    "h_split_brain": "hidden:behavior.mts",
    "h_stale_discovery": "hidden:behavior.mts",
    "h_wave_gate": "verified_before_wave2",
    "h_wave_repair": "verified_before_wave2",
    "h_worker_cap": "event_count:worker_started<=1",
}


def test_hard_slice_has_sixteen_tasks() -> None:
    tasks = list_tasks("hard")
    ids = [task.id for task in tasks]
    assert ids == HARD_IDS
    assert get_task("h_kill_resume").interrupt_steps()
    assert len(get_task("h_double_kill").interrupt_steps()) == 2
    assert get_task("h_lease_shift").interrupt_steps()[0]["rewrite"]
    assert get_task("h_hollow_migration").track == "worker"
    orch = [task for task in tasks if task.track == "orchestrator"]
    leaf = [task for task in tasks if task.track == "worker"]
    assert len(orch) == 9
    assert len(leaf) == 7
    assert "resume" in get_task("h_kill_resume").facets
    assert "mutation" in get_task("h_lease_shift").facets


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
    assert len(results) == 16
    assert all(grade.outcome_passed and grade.protocol_passed for _, grade in results)


def test_scripted_fail_misses_intended_check(tmp_path: Path) -> None:
    results = run_slice(
        "hard",
        adapter_name="scripted",
        model="scripted-fail",
        runs_root=tmp_path / "fail",
        adapter_kwargs={"persona": "fail"},
    )
    assert len(results) == 16
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


def test_double_kill_pass_is_two_real_harness_kills(tmp_path: Path) -> None:
    task = get_task("h_double_kill")
    trial, grade = run_task(
        task,
        adapter_name="scripted",
        model="scripted-pass",
        runs_root=tmp_path / "double",
        adapter_kwargs={"persona": "pass"},
    )
    assert grade.passed, [check for check in grade.checks if not check.passed]
    killed = [event for event in trial.events if event.type == "harness_killed"]
    assert len(killed) == 2
    first = json.loads(trial.files[".harness/pre_kill_1.json"])
    second = json.loads(trial.files[".harness/pre_kill_2.json"])
    assert first and all(path.startswith("src/layer1/") for path in first)
    assert second and all(path.startswith("src/layer2/") for path in second)


def test_kill_resume_pass_with_relative_runs_root(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    task = get_task("h_kill_resume")
    trial, grade = run_task(
        task,
        adapter_name="scripted",
        model="scripted-pass",
        runs_root=Path("runs"),
        adapter_kwargs={"persona": "pass"},
    )
    assert grade.passed
    assert any(event.type == "harness_killed" for event in trial.events)


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


def test_hollow_visible_fail_greens_the_seed_test(tmp_path: Path) -> None:
    task = get_task("h_hollow_visible")
    trial, grade = run_task(
        task,
        adapter_name="scripted",
        model="scripted-fail",
        runs_root=tmp_path / "hollow",
        adapter_kwargs={"persona": "fail"},
    )
    assert grade.passed is False
    names = {check.name: check.passed for check in grade.checks}
    assert names["node:test/test.mts"] is True
    assert names["hidden:behavior.mts"] is False
    assert "src/add.ts" in trial.files


def test_lease_shift_pass_sees_rewritten_leases(tmp_path: Path) -> None:
    task = get_task("h_lease_shift")
    trial, grade = run_task(
        task,
        adapter_name="scripted",
        model="scripted-pass",
        runs_root=tmp_path / "shift",
        adapter_kwargs={"persona": "pass"},
    )
    assert grade.passed, [check for check in grade.checks if not check.passed]
    leases = json.loads(trial.files["job/leases.json"])
    assert leases["leases"] == [{"worker": "west", "path": "src/west"}]
    assert "src/east/one.ts" in trial.files
    assert "src/west/two.ts" in trial.files
