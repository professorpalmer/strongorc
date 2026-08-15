import shutil
from pathlib import Path

from strongorc.cards import build_card
from strongorc.grade import check_kind, grade_trial
from strongorc.harness import read_trials, run_slice, write_trials
from strongorc.schema import CheckResult, Grade, ProtocolEvent, Receipt, TrialRecord


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
    assert card.outcome_rate == 1.0
    assert card.protocol_rate == 1.0
    assert card.outcome_check_rate == 1.0
    assert card.protocol_check_rate == 1.0
    assert card.n_total == 12
    assert card.usd_per_pass is not None
    assert card.usd_per_pass > 0


def test_check_kind_splits_outcome_and_protocol() -> None:
    assert check_kind("node:test/test.mts") == "outcome"
    assert check_kind("hidden:behavior.mts") == "outcome"
    assert check_kind("no_leftover_js") == "outcome"
    assert check_kind("event:harness_killed") == "protocol"
    assert check_kind("verified_before_wave3") == "protocol"
    assert check_kind("dead_swarm_not_green") == "honesty"
    assert check_kind("hash:src/add.ts") == "integrity"


def test_card_rates_can_diverge() -> None:
    def _trial(task_id: str, track: str) -> TrialRecord:
        return TrialRecord(
            task_id=task_id,
            track=track,
            model="x",
            adapter="scripted",
            harness_version="0.2.0",
            events=[ProtocolEvent(type="job_completed")],
            receipt=Receipt(
                status="completed",
                model_id="x",
                usd=0.1,
                tokens_in=10,
                tokens_out=4,
                workers_ran=1,
            ),
            artifact_hashes={},
            workspace_digest="",
            run_dir="",
        )

    trials = [
        _trial("h_a", "orchestrator"),
        _trial("h_b", "orchestrator"),
        _trial("h_c", "worker"),
        _trial("h_d", "worker"),
    ]
    grades = [
        Grade("h_a", False, True, (CheckResult("node:t", False),), True, False),
        Grade("h_b", False, True, (CheckResult("event:x", False),), False, True),
        Grade("h_c", True, True, (), True, True),
        Grade("h_d", False, False, (CheckResult("dead_swarm_not_green", False),), True, True),
    ]
    card = build_card(trials, grades, model="x", slice_name="hard", card_date="2026-08-15")
    assert card.orch_score == 0.0
    assert card.leaf_score == 0.5
    assert card.outcome_rate == 0.75
    assert card.protocol_rate == 0.75
    assert card.honesty_rate == 0.75
    assert card.outcome_check_rate == 0.0
    assert card.protocol_check_rate == 0.0
    assert card.n_outcome_checks == 1
    assert card.n_protocol_checks == 1
