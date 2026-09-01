import json
from pathlib import Path

from strongorc import catalog
from strongorc.catalog import get_task, list_tasks


def test_core_slice_has_twelve_balanced_tasks() -> None:
    tasks = list_tasks("core")
    ids = [task.id for task in tasks]
    assert len(ids) == 12
    assert len(set(ids)) == 12
    orch = [task for task in tasks if task.track == "orchestrator"]
    leaf = [task for task in tasks if task.track == "worker"]
    assert len(orch) == 6
    assert len(leaf) == 6
    assert all(task.id.startswith("o_") for task in orch)
    assert all(task.id.startswith("w_") for task in leaf)


def test_hard_slice_is_registered() -> None:
    ids = [task.id for task in list_tasks("hard")]
    assert "h_kill_resume" in ids
    assert "h_hollow_migration" in ids
    assert "h_double_kill" in ids
    assert "h_stale_discovery" in ids
    assert "h_split_brain" in ids
    assert "h_lease_shift" in ids
    assert get_task("h_wave_gate").slice == "hard"
    assert len(get_task("h_double_kill").interrupt_steps()) == 2
    assert "resume" in get_task("h_kill_resume").facets


def test_frontier_slice_is_findable() -> None:
    assert get_task("f_triple_kill").slice == "frontier"
    assert get_task("f_hollow_sub").track == "worker"
    ids = [task.id for task in list_tasks("frontier")]
    assert len(ids) == 48
    assert len(set(ids)) == 48


def test_brutal_slice_is_findable() -> None:
    assert get_task("b_wal_replay").slice == "brutal"
    assert get_task("b_config_lang").track == "worker"
    ids = [task.id for task in list_tasks("brutal")]
    assert len(ids) == 8
    assert len(set(ids)) == 8


def test_native_slice_is_findable() -> None:
    assert get_task("n_wave_seal").slice == "native"
    assert get_task("n_pouch").track == "worker"
    ids = [task.id for task in list_tasks("native")]
    assert len(ids) == 12
    assert len(set(ids)) == 12


def test_ladder_slice_is_findable() -> None:
    assert get_task("l_wave_seal_r1").slice == "ladder"
    assert get_task("l_pouch_r1").track == "worker"
    ids = [task.id for task in list_tasks("ladder")]
    assert len(ids) == 48
    assert len(set(ids)) == 48
    assert "l_pouch_r4" in ids
    assert get_task("l_wave_seal_r1").family is None
    assert get_task("l_wave_seal_r1").rung is None


def test_reason_slice_is_findable() -> None:
    assert get_task("r_trace_contract_r1").slice == "reason"
    assert get_task("r_diagnose_kill_r1").track == "orchestrator"
    assert get_task("r_trace_contract_r1").track == "worker"
    ids = [task.id for task in list_tasks("reason")]
    assert len(ids) == 12
    assert len(set(ids)) == 12
    task = get_task("r_trace_contract_r2")
    assert task.family == "trace_contract"
    assert task.rung == "r2"


def test_holdout_slice_empty_without_overlay(monkeypatch) -> None:
    monkeypatch.delenv("STRONGORC_HOLDOUT", raising=False)
    monkeypatch.delenv("DURABLE_ORCH_HOLDOUT", raising=False)
    assert list_tasks("holdout") == []


def test_taskspec_reads_explicit_family_rung(tmp_path: Path, monkeypatch) -> None:
    task_dir = tmp_path / "ladder" / "l_demo_r1"
    task_dir.mkdir(parents=True)
    (task_dir / "task.json").write_text(
        json.dumps(
            {
                "id": "l_demo_r1",
                "track": "orchestrator",
                "slice": "ladder",
                "title": "demo",
                "family": "explicit_family",
                "rung": "r7",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(catalog, "TASKS_ROOT", tmp_path)
    task = catalog.list_tasks("ladder")[0]
    assert task.family == "explicit_family"
    assert task.rung == "r7"
