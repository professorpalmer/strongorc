import json
from pathlib import Path

from strongorc.cards import build_card
from strongorc.catalog import get_task, list_tasks
from strongorc.harness import _apply_after_kill, run_slice, run_task
from strongorc.oracle_lib import discover_hidden_test_names, hidden_pytest_cases

MANIFEST = json.loads((Path(__file__).resolve().parents[1] / "tasks" / "native" / "manifest.json").read_text())
NATIVE_IDS = [item["id"] for item in MANIFEST["tasks"]]
EXPECTED_FAIL_CHECK = {item["id"]: item["fail_check"] for item in MANIFEST["tasks"]}
ORCH_IDS = [item["id"] for item in MANIFEST["tasks"] if item["track"] == "orchestrator"]
WORKER_IDS = [item["id"] for item in MANIFEST["tasks"] if item["track"] == "worker"]


def test_native_slice_is_registered() -> None:
    tasks = list_tasks("native")
    ids = [task.id for task in tasks]
    assert ids == sorted(NATIVE_IDS)
    assert len(ids) == 12
    orch = [task for task in tasks if task.track == "orchestrator"]
    leaf = [task for task in tasks if task.track == "worker"]
    assert len(orch) == 6
    assert len(leaf) == 6
    assert get_task("n_wave_seal").slice == "native"
    assert "repo" in get_task("n_wave_seal").facets
    assert get_task("n_wave_seal").timeout_seconds >= 1800
    assert all(task.id.startswith("n_") for task in tasks)


def test_scripted_pass_clears_native(tmp_path: Path) -> None:
    results = run_slice(
        "native",
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
    assert len(results) == 12
    card = build_card(
        [trial for trial, _ in results],
        [grade for _, grade in results],
        model="scripted-pass",
        slice_name="native",
        card_date="2026-08-16",
    )
    assert card.hidden_rate == 1.0
    assert card.interrupt_rate == 1.0
    assert card.hard_rate == 1.0
    assert card.n_hidden == 96


def test_scripted_fail_misses_hidden_pytest(tmp_path: Path) -> None:
    results = run_slice(
        "native",
        adapter_name="scripted",
        model="scripted-fail",
        runs_root=tmp_path / "fail",
        adapter_kwargs={"persona": "fail"},
    )
    assert len(results) == 12
    for trial, grade in results:
        assert grade.passed is False, trial.task_id
        names = {check.name for check in grade.checks if not check.passed}
        expected = EXPECTED_FAIL_CHECK[trial.task_id]
        hit = any(name == expected or name.startswith(expected + ":") for name in names)
        assert hit, f"{trial.task_id} failed {sorted(names)}, expected {expected}"


def test_wave_seal_pass_is_a_real_kill(tmp_path: Path) -> None:
    trial, grade = run_task(
        get_task("n_wave_seal"),
        adapter_name="scripted",
        model="scripted-pass",
        runs_root=tmp_path / "desk",
        adapter_kwargs={"persona": "pass"},
    )
    assert grade.passed, [check for check in grade.checks if not check.passed]
    assert sum(1 for event in trial.events if event.type == "harness_killed") == 1


def test_worker_oracles_omit_kill_events() -> None:
    """Oracle templates omit kill events. Grade-level sealed checks still apply."""
    root = Path(__file__).resolve().parents[1] / "tasks" / "native"
    for task_id in WORKER_IDS:
        text = (root / task_id / "oracle.py").read_text(encoding="utf-8")
        assert "harness_killed" not in text
        assert "resumed_from_checkpoint" not in text


def test_plant_writes_json_objects(tmp_path: Path) -> None:
    _apply_after_kill(
        tmp_path,
        {"plant": {"state/children/leaf.json": {"status": "failed"}}},
    )
    data = json.loads((tmp_path / "state" / "children" / "leaf.json").read_text(encoding="utf-8"))
    assert data == {"status": "failed"}


def test_hidden_denominator_is_stable() -> None:
    root = Path(__file__).resolve().parents[1] / "tasks" / "native"
    names = []
    for task_id in NATIVE_IDS:
        names.extend(discover_hidden_test_names(root / task_id / "hidden"))
    assert len(names) == 96
    assert len(set(names)) == 96


def test_hidden_cases_keep_denominator_when_import_fails(tmp_path: Path) -> None:
    hidden = tmp_path / "hidden"
    hidden.mkdir()
    (hidden / "test_demo.py").write_text(
        "def test_one() -> None:\n    assert True\n\n"
        "def test_two() -> None:\n    assert True\n",
        encoding="utf-8",
    )
    assert discover_hidden_test_names(hidden) == ["test_one", "test_two"]
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (hidden / "test_demo.py").write_text(
        "import no_such_package_for_strongorc\n\n"
        "def test_one() -> None:\n    assert True\n\n"
        "def test_two() -> None:\n    assert True\n",
        encoding="utf-8",
    )
    cases = hidden_pytest_cases(run_dir, hidden)
    assert [check.name for check in cases] == ["pytest:hidden:test_one", "pytest:hidden:test_two"]
    assert all(check.passed is False for check in cases)
