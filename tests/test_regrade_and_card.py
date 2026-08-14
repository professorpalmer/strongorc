import shutil
from pathlib import Path

from durable_orch_bench.cards import build_card
from durable_orch_bench.grade import grade_trial
from durable_orch_bench.harness import read_trials, run_slice, write_trials


def test_regrade_matches_live_and_needs_no_adapter(tmp_path: Path) -> None:
    results = run_slice(
        "core",
        adapter_name="scripted",
        model="scripted-pass",
        runs_root=tmp_path / "runs",
        adapter_kwargs={"persona": "pass"},
    )
    trials = [trial for trial, _ in results]
    live = [grade.passed for _, grade in results]
    frozen = tmp_path / "trials.jsonl"
    write_trials(frozen, trials)
    shutil.rmtree(tmp_path / "runs")
    reloaded = read_trials(frozen)
    assert all(trial.files for trial in reloaded)
    regraded = [grade_trial(trial).passed for trial in reloaded]
    assert regraded == live
    assert all(regraded)


def test_scripted_pass_card_is_full_marks(tmp_path: Path) -> None:
    results = run_slice(
        "core",
        adapter_name="scripted",
        model="scripted-pass",
        runs_root=tmp_path / "runs",
        adapter_kwargs={"persona": "pass"},
    )
    trials = [trial for trial, _ in results]
    grades = [grade for _, grade in results]
    card = build_card(trials, grades, model="scripted-pass", slice_name="core", card_date="2026-08-14")
    assert card.orch_score == 1.0
    assert card.leaf_score == 1.0
    assert card.honesty_rate == 1.0
    assert card.n_total == 12
    assert card.usd_per_pass is not None
    assert card.usd_per_pass > 0
