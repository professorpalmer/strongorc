from durable_orch_bench.catalog import list_tasks


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
