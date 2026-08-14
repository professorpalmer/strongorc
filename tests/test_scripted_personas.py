from pathlib import Path

from durable_orch_bench.harness import ephemeral_runs_root, run_slice

EXPECTED_FAIL_CHECK = {
    "o_kill_resume": "event:resumed_from_checkpoint",
    "o_dead_swarm": "honest_terminal_status",
    "o_planner_plays": "worker_wrote_solution",
    "o_wave_boundary": "verified_before_wave2",
    "o_lease_conflict": "absent:shared/cell.txt",
    "o_receipt_honesty": "usd_positive",
    "w_artifact_consume": "contains:src/adapter.py",
    "w_hollow_pass": "absent:src/widget.js",
    "w_worker_resume": "exists:progress/step1.done",
    "w_lease_respect": "absent:src/forbidden/secret.txt",
    "w_soft_refuse": "status_refused",
    "w_discovery_reuse": "event:discovery_reused",
}


def test_scripted_pass_clears_core(tmp_path: Path) -> None:
    results = run_slice(
        "core",
        adapter_name="scripted",
        model="scripted-pass",
        runs_root=tmp_path / "pass",
        adapter_kwargs={"persona": "pass"},
    )
    failed = [grade.task_id for _, grade in results if not grade.passed]
    assert failed == []
    assert len(results) == 12


def test_scripted_fail_misses_intended_check(tmp_path: Path) -> None:
    results = run_slice(
        "core",
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
        assert expected in names, f"{trial.task_id} failed {sorted(names)}, expected {expected}"


def test_ephemeral_helper_exists() -> None:
    root = ephemeral_runs_root()
    assert root.exists()
