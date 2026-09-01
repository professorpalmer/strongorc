import json
from pathlib import Path

from strongorc.cards import build_card
from strongorc.catalog import get_task, list_tasks
from strongorc.harness import run_slice, run_task
from strongorc.oracle_lib import discover_hidden_test_names

MANIFEST = json.loads((Path(__file__).resolve().parents[1] / "tasks" / "ladder" / "manifest.json").read_text())
LADDER_IDS = [item["id"] for item in MANIFEST["tasks"]]
EXPECTED_FAIL_CHECK = {item["id"]: item["fail_check"] for item in MANIFEST["tasks"]}
ORCH_IDS = [item["id"] for item in MANIFEST["tasks"] if item["track"] == "orchestrator"]
WORKER_IDS = [item["id"] for item in MANIFEST["tasks"] if item["track"] == "worker"]

MULTI_KILL = {
    "l_wave_seal_r3": 2,
    "l_path_mutex_r3": 2,
    "l_child_closed_r3": 2,
    "l_live_token_r2": 2,
    "l_live_token_r3": 3,
}


def test_ladder_slice_is_registered() -> None:
    tasks = list_tasks("ladder")
    ids = [task.id for task in tasks]
    assert ids == sorted(LADDER_IDS)
    assert len(ids) == 48
    orch = [task for task in tasks if task.track == "orchestrator"]
    leaf = [task for task in tasks if task.track == "worker"]
    assert len(orch) == 24
    assert len(leaf) == 24
    assert get_task("l_wave_seal_r1").slice == "ladder"
    assert get_task("l_wave_seal_r4").slice == "ladder"
    assert "repo" in get_task("l_wave_seal_r1").facets
    assert get_task("l_wave_seal_r1").timeout_seconds >= 1800
    assert all(task.id.startswith("l_") for task in tasks)
    assert all(task.id.endswith(("_r1", "_r2", "_r3", "_r4")) for task in tasks)


def test_scripted_pass_clears_ladder(tmp_path: Path) -> None:
    results = run_slice(
        "ladder",
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
    card = build_card(
        [trial for trial, _ in results],
        [grade for _, grade in results],
        model="scripted-pass",
        slice_name="ladder",
        card_date="2026-08-19",
    )
    assert card.hidden_rate == 1.0
    assert card.interrupt_rate == 1.0
    assert card.hard_rate == 1.0
    assert card.n_hidden == 384


def test_scripted_fail_misses_hidden_pytest(tmp_path: Path) -> None:
    results = run_slice(
        "ladder",
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
        hit = any(name == expected or name.startswith(expected + ":") for name in names)
        assert hit, f"{trial.task_id} failed {sorted(names)}, expected {expected}"


def test_worker_oracles_omit_kill_events() -> None:
    """Oracle templates omit kill events. Grade-level sealed checks still apply."""
    root = Path(__file__).resolve().parents[1] / "tasks" / "ladder"
    for task_id in WORKER_IDS:
        text = (root / task_id / "oracle.py").read_text(encoding="utf-8")
        assert "harness_killed" not in text
        assert "resumed_from_checkpoint" not in text


def test_multi_kill_interrupt_is_a_list() -> None:
    for task_id, kills in MULTI_KILL.items():
        task = get_task(task_id)
        assert isinstance(task.interrupt, list), task_id
        assert len(task.interrupt) == kills
        assert len(task.interrupt_steps()) == kills
    for task in list_tasks("ladder"):
        if task.id in MULTI_KILL:
            continue
        if task.interrupt is None:
            continue
        if isinstance(task.interrupt, list):
            raise AssertionError(f"{task.id} used a list interrupt without a multi-kill")


def test_hidden_denominator_is_stable() -> None:
    root = Path(__file__).resolve().parents[1] / "tasks" / "ladder"
    names = []
    for task_id in LADDER_IDS:
        found = discover_hidden_test_names(root / task_id / "hidden")
        assert len(found) == 8, task_id
        names.extend(found)
    assert len(names) == 384
    assert len(set(names)) == 384
    for name in names:
        assert name.startswith("test_")
        assert any(f"_{rung}_" in name for rung in ("r1", "r2", "r3", "r4"))


def test_wave_seal_r3_is_a_real_double_kill(tmp_path: Path) -> None:
    trial, grade = run_task(
        get_task("l_wave_seal_r3"),
        adapter_name="scripted",
        model="scripted-pass",
        runs_root=tmp_path / "desk",
        adapter_kwargs={"persona": "pass"},
    )
    assert grade.passed, [check for check in grade.checks if not check.passed]
    assert sum(1 for event in trial.events if event.type == "harness_killed") == 2


def test_wave_seal_r4_inverts_order_after_kill(tmp_path: Path) -> None:
    trial, grade = run_task(
        get_task("l_wave_seal_r4"),
        adapter_name="scripted",
        model="scripted-pass",
        runs_root=tmp_path / "desk",
        adapter_kwargs={"persona": "pass"},
    )
    assert grade.passed, [check for check in grade.checks if not check.passed]
    assert sum(1 for event in trial.events if event.type == "harness_killed") == 1
    spec = json.loads((Path(trial.run_dir) / "job" / "spec.json").read_text(encoding="utf-8"))
    assert spec.get("order") == "desc"
