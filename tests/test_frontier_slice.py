import json
import shutil
from pathlib import Path

import pytest

from strongorc.catalog import get_task, list_tasks
from strongorc.harness import run_slice, run_task

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node required for frontier slice")

MANIFEST = json.loads((Path(__file__).resolve().parents[1] / "tasks" / "frontier" / "manifest.json").read_text())
FRONTIER_IDS = [item["id"] for item in MANIFEST["tasks"]]
EXPECTED_FAIL_CHECK = {item["id"]: item["fail_check"] for item in MANIFEST["tasks"]}


def test_frontier_slice_is_registered() -> None:
    tasks = list_tasks("frontier")
    ids = [task.id for task in tasks]
    assert ids == sorted(FRONTIER_IDS)
    assert len(ids) == 48
    orch = [task for task in tasks if task.track == "orchestrator"]
    leaf = [task for task in tasks if task.track == "worker"]
    assert len(orch) == 28
    assert len(leaf) == 20
    assert get_task("f_triple_kill").slice == "frontier"
    assert "resume" in get_task("f_triple_kill").facets
    assert len(get_task("f_triple_kill").interrupt_steps()) == 3
    assert get_task("f_scale_flip").interrupt_steps()[0]["rewrite"]


def test_scripted_pass_clears_frontier(tmp_path: Path) -> None:
    results = run_slice(
        "frontier",
        adapter_name="scripted",
        model="scripted-pass",
        runs_root=tmp_path / "pass",
        adapter_kwargs={"persona": "pass"},
    )
    failed = [
        (grade.task_id, [check.name for check in grade.checks if not check.passed])
        for _, grade in results
        if not grade.passed
    ]
    assert failed == []
    assert len(results) == 48


def test_scripted_fail_misses_intended_check(tmp_path: Path) -> None:
    results = run_slice(
        "frontier",
        adapter_name="scripted",
        model="scripted-fail",
        runs_root=tmp_path / "fail",
        adapter_kwargs={"persona": "fail"},
    )
    assert len(results) == 48
    for trial, grade in results:
        assert grade.passed is False, trial.task_id
        names = {check.name for check in grade.checks if not check.passed}
        expected = EXPECTED_FAIL_CHECK[trial.task_id]
        assert expected in names, f"{trial.task_id} failed {sorted(names)}, expected {expected}"


def test_triple_kill_pass_is_three_real_kills(tmp_path: Path) -> None:
    task = get_task("f_triple_kill")
    trial, grade = run_task(
        task,
        adapter_name="scripted",
        model="scripted-pass",
        runs_root=tmp_path / "triple",
        adapter_kwargs={"persona": "pass"},
    )
    assert grade.passed, [check for check in grade.checks if not check.passed]
    killed = [event for event in trial.events if event.type == "harness_killed"]
    assert len(killed) == 3
