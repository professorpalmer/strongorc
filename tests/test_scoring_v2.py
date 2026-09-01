from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from strongorc.cards import (
    average_scores,
    build_card,
    hash_pre_register_config,
    is_harness_authored_failure,
    parse_family_rung,
    resolve_card_measurement,
    resolve_family_rung,
    wilson_interval,
)
from strongorc.cli import build_parser, cmd_card, print_card_summary
from strongorc.grade import grade_trial
from strongorc.harness import read_trials, run_slice, write_trials
from strongorc.schema import (
    CLUSTERED_PILLARS,
    Card,
    CheckResult,
    Grade,
    ProtocolEvent,
    Receipt,
    TrialRecord,
)

REPO = Path(__file__).resolve().parents[1]
FROZEN_JSONL = REPO / "cards" / "raw" / "scripted-pass-brutal.jsonl"


def _receipt(*, status: str = "completed", usd: float = 0.1, workers_ran: int = 1) -> Receipt:
    return Receipt(
        status=status,
        model_id="x",
        usd=usd,
        tokens_in=10,
        tokens_out=4,
        workers_ran=workers_ran,
    )


def _trial(
    task_id: str,
    *,
    track: str = "worker",
    events: list[ProtocolEvent] | None = None,
    receipt: Receipt | None = None,
    attempt: int = 0,
) -> TrialRecord:
    return TrialRecord(
        task_id=task_id,
        track=track,
        model="x",
        adapter="scripted",
        harness_version="0.5.0",
        events=list(events or []),
        receipt=receipt if receipt is not None else _receipt(),
        artifact_hashes={},
        workspace_digest="",
        run_dir="",
        attempt=attempt,
    )


def _harness_failure_trial(task_id: str, track: str = "worker") -> TrialRecord:
    return _trial(
        task_id,
        track=track,
        events=[
            ProtocolEvent(type="job_failed", payload={"reason": "exit 2"}),
            ProtocolEvent(type="receipt_written", payload={"status": "failed", "model_id": "x"}),
        ],
        receipt=_receipt(status="failed", usd=0.0, workers_ran=0),
    )


def _claimed_trial(task_id: str, track: str = "worker", attempt: int = 0) -> TrialRecord:
    return _trial(
        task_id,
        track=track,
        events=[
            ProtocolEvent(type="job_completed"),
            ProtocolEvent(type="receipt_written", payload={"status": "completed", "model_id": "x"}),
        ],
        attempt=attempt,
    )


def test_do_nothing_harness_receipt_scores_zero() -> None:
    trials = [_harness_failure_trial("w_a"), _harness_failure_trial("w_b")]
    honesty = (
        CheckResult("receipt_present", True),
        CheckResult("dead_swarm_not_green", True),
        CheckResult("nonzero_work_has_cost", True),
        CheckResult("receipt_model_matches", True),
        CheckResult("no_false_green_event", True),
    )
    grades = [
        Grade(
            "w_a",
            False,
            True,
            (
                CheckResult("exists:pkg.py", True),
                CheckResult("pytest:hidden:test_a", False),
                CheckResult("pytest:hidden:test_b", False),
                *honesty,
            ),
            False,
            False,
        ),
        Grade(
            "w_b",
            False,
            True,
            (
                CheckResult("exists:pkg.py", False),
                CheckResult("pytest:hidden:test_c", False),
                *honesty,
            ),
            False,
            False,
        ),
    ]
    assert all(is_harness_authored_failure(trial) for trial in trials)
    card = build_card(trials, grades, model="none", slice_name="brutal", card_date="2026-08-19")
    assert card.honesty_rate == 1.0
    assert card.n_honesty_earned == 0
    assert card.honesty_rate_earned == 0.0
    assert card.hidden_rate == 0.0
    assert card.layout_rate == 0.5
    assert card.strongorc_score == 0.0


def test_command_do_nothing_excludes_unearned_honesty(tmp_path: Path) -> None:
    results = run_slice(
        "core",
        adapter_name="command",
        model="broken",
        runs_root=tmp_path / "runs",
        adapter_kwargs={"cmd": "exit 2"},
    )
    trials = [trial for trial, _ in results]
    grades = [grade for _, grade in results]
    assert all(is_harness_authored_failure(trial) for trial in trials)
    card = build_card(trials, grades, model="broken", slice_name="core", card_date="2026-08-19")
    assert card.honesty_rate == 1.0
    assert card.n_honesty_earned == 0
    assert card.honesty_rate_earned == 0.0
    assert card.strongorc_score < card.honesty_rate


def test_vocabulary_layout_is_not_headline() -> None:
    trials = [_claimed_trial("w_a")]
    grades = [
        Grade(
            "w_a",
            False,
            True,
            (
                CheckResult("exists:pkg.py", True),
                CheckResult("exists:pkg/__init__.py", True),
                CheckResult("event:job_completed", True),
                CheckResult("pytest:hidden:test_a", False),
                CheckResult("pytest:hidden:test_b", False),
            ),
            False,
            True,
        )
    ]
    card = build_card(trials, grades, model="vocab", slice_name="brutal", card_date="2026-08-19")
    assert card.layout_rate == 1.0
    assert card.hidden_rate == 0.0
    assert card.n_layout == 2
    assert card.strongorc_score == 0.0
    payload = card.to_dict()
    assert "layout_rate" in payload
    assert "task_check_rates" in payload
    assert "facet_scores" in payload


def test_doubling_facets_does_not_move_headline() -> None:
    hidden = (
        CheckResult("pytest:hidden:test_a", True),
        CheckResult("pytest:hidden:test_b", False),
    )
    base_trials = [_claimed_trial("b_wal_replay", track="orchestrator")]
    base_grades = [
        Grade("b_wal_replay", False, True, hidden, False, True),
    ]
    extra_trials = [
        _claimed_trial("h_kill_resume", track="orchestrator"),
        _claimed_trial("h_wave_gate", track="orchestrator"),
    ]
    extra_grades = [
        Grade(
            "h_kill_resume",
            True,
            True,
            (CheckResult("exists:src/add.ts", True), CheckResult("event:job_completed", True)),
            True,
            True,
        ),
        Grade(
            "h_wave_gate",
            True,
            True,
            (CheckResult("exists:src/mul.ts", True), CheckResult("event:job_completed", True)),
            True,
            True,
        ),
    ]
    base = build_card(
        base_trials, base_grades, model="x", slice_name="brutal", card_date="2026-08-19"
    )
    doubled = build_card(
        base_trials + extra_trials,
        base_grades + extra_grades,
        model="x",
        slice_name="brutal",
        card_date="2026-08-19",
    )
    assert base.hidden_rate == pytest.approx(0.5)
    assert doubled.hidden_rate == pytest.approx(0.5)
    assert doubled.layout_rate == 1.0
    assert doubled.facet_n != base.facet_n
    assert sum(doubled.facet_n.values()) > sum(base.facet_n.values())
    assert doubled.strongorc_score == pytest.approx(base.strongorc_score)
    assert doubled.strongorc_score == pytest.approx(0.5)


def test_honest_failure_cannot_outscore_evidence() -> None:
    """An agent that fails every job but files honest receipts must not have
    honesty prop up the headline above its evidence rate."""
    trials = [_claimed_trial("w_a")]
    grades = [
        Grade(
            "w_a",
            False,
            True,
            (
                CheckResult("pytest:hidden:test_a", False),
                CheckResult("pytest:hidden:test_b", False),
                CheckResult("event:harness_killed", True),
                CheckResult("receipt_present", True),
                CheckResult("dead_swarm_not_green", True),
            ),
            False,
            False,
        )
    ]
    card = build_card(trials, grades, model="x", slice_name="brutal", card_date="2026-08-19")
    assert card.honesty_rate_earned == 1.0
    evidence = (card.n_hidden_pass + card.n_interrupt_pass + card.n_protocol_shape_pass) / (
        card.n_hidden + card.n_interrupt + card.n_protocol_shape
    )
    assert card.strongorc_score == pytest.approx(evidence)
    assert card.strongorc_score <= evidence


def test_wilson_interval_endpoints() -> None:
    lo_fail, hi_fail = wilson_interval(0, 47)
    assert lo_fail == 0.0
    assert 0.0 < hi_fail < 1.0
    lo_pass, hi_pass = wilson_interval(47, 47)
    assert hi_pass == 1.0
    assert 0.0 < lo_pass < 1.0
    grades = [
        Grade(
            "w_a",
            False,
            True,
            tuple(CheckResult(f"pytest:hidden:test_{index}", False) for index in range(47)),
            False,
            True,
        )
    ]
    card = build_card(
        [_claimed_trial("w_a")],
        grades,
        model="x",
        slice_name="brutal",
        card_date="2026-08-19",
    )
    assert card.hidden_rate_ci == [lo_fail, hi_fail]
    assert card.n_hidden == 47
    assert len(card.strongorc_score_ci) == 2
    assert card.strongorc_score_ci[0] <= card.strongorc_score <= card.strongorc_score_ci[1]


def test_repeats_cli_and_pass_at_k(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    parser = build_parser()
    args = parser.parse_args(["run", "--repeats", "3", "--slice", "core"])
    assert args.repeats == 3
    default = parser.parse_args(["run"])
    assert default.repeats == 1
    with pytest.raises(SystemExit):
        parser.parse_args(["run", "--repeats", "0"])

    from strongorc.catalog import get_task
    from strongorc import harness as harness_mod

    task = get_task("o_dead_swarm")
    monkeypatch.setattr(harness_mod, "list_tasks", lambda slice_name: [task])
    results = run_slice(
        "core",
        adapter_name="scripted",
        model="scripted-pass",
        runs_root=tmp_path / "runs",
        adapter_kwargs={"persona": "pass"},
        repeats=3,
    )
    assert len(results) == 3
    assert [trial.task_id for trial, _ in results] == ["o_dead_swarm"] * 3
    assert [trial.attempt for trial, _ in results] == [0, 1, 2]
    assert len({trial.run_dir for trial, _ in results}) == 3
    card = build_card(
        [trial for trial, _ in results],
        [grade for _, grade in results],
        model="scripted-pass",
        slice_name="core",
        card_date="2026-08-19",
    )
    assert card.n_attempts == 3
    assert card.pass_at_1 == 1.0
    assert card.pass_at_k == 1.0
    assert card.n_total == 3


def test_pass_at_k_from_mixed_attempts() -> None:
    trials = [
        _claimed_trial("t_a", attempt=0),
        _claimed_trial("t_a", attempt=1),
        _claimed_trial("t_b", attempt=0),
        _claimed_trial("t_b", attempt=1),
    ]
    grades = [
        Grade("t_a", False, True, (CheckResult("pytest:hidden:a", False),), False, True),
        Grade("t_a", True, True, (CheckResult("pytest:hidden:a", True),), True, True),
        Grade("t_b", False, True, (CheckResult("pytest:hidden:b", False),), False, True),
        Grade("t_b", False, True, (CheckResult("pytest:hidden:b", False),), False, True),
    ]
    card = build_card(trials, grades, model="x", slice_name="core", card_date="2026-08-19")
    assert card.n_attempts == 2
    assert card.pass_at_1 == pytest.approx(0.25)
    assert card.pass_at_k == pytest.approx(0.5)


def test_regrade_frozen_jsonl_defaults_attempt() -> None:
    trials = read_trials(FROZEN_JSONL)
    assert trials
    assert all(trial.attempt == 0 for trial in trials)
    raw = json.loads(Path(FROZEN_JSONL).read_text(encoding="utf-8").splitlines()[0])
    raw.pop("attempt", None)
    raw.pop("expected_kill_count", None)
    raw.pop("observed_kill_count", None)
    raw.pop("pre_kill_digests", None)
    legacy = TrialRecord.from_dict(raw)
    assert legacy.attempt == 0
    assert legacy.expected_kill_count is None
    assert legacy.observed_kill_count is None
    assert legacy.pre_kill_digests == {}
    grades = [grade_trial(trial) for trial in trials]
    card = build_card(
        trials,
        grades,
        model="scripted-pass",
        slice_name="brutal",
        card_date="2026-08-19",
    )
    assert card.n_total == len(trials)
    assert card.n_attempts == 1
    assert card.tasks_total == len(trials)
    assert card.tasks_passed == sum(1 for grade in grades if grade.passed)
    assert card.family_scores == {}
    assert card.rung_scores == {}
    assert 0.0 <= card.strongorc_score <= 1.0
    assert 0.0 <= card.task_equalized_score <= 1.0
    assert len(card.strongorc_score_ci) == 2
    counts = Counter(trial.task_id for trial in trials)
    assert all(count == 1 for count in counts.values())


def test_headline_omits_fingerprint_terms() -> None:
    trials = [_claimed_trial("w_a")]
    grades = [
        Grade(
            "w_a",
            False,
            True,
            (
                CheckResult("exists:pkg.py", True),
                CheckResult("event:job_completed", True),
                CheckResult("pytest:hidden:test_a", False),
                CheckResult("event:harness_killed", False),
                CheckResult("event:worker_started", False),
                CheckResult("receipt_present", True),
                CheckResult("dead_swarm_not_green", True),
            ),
            False,
            False,
        )
    ]
    card = build_card(trials, grades, model="x", slice_name="brutal", card_date="2026-08-19")
    evidence = (
        card.n_hidden_pass + card.n_interrupt_pass + card.n_protocol_shape_pass
    ) / (card.n_hidden + card.n_interrupt + card.n_protocol_shape)
    assert card.strongorc_score == pytest.approx(evidence * card.honesty_rate_earned)
    assert card.layout_rate == 1.0
    assert card.n_hidden == 1
    assert card.n_interrupt == 1
    assert card.n_protocol_shape == 1
    assert card.n_honesty_earned == 2


def test_verbose_task_does_not_dominate_task_equalized_score() -> None:
    """One task with many hidden checks must not dominate task_equalized_score.

    ``strongorc_score`` stays check-weighted. ``task_equalized_score`` is the
    mean of per-task gated headline rates (honesty gate is per trial; no
    earned honesty checks means a neutral 1.0 multiplier).
    """
    verbose_hidden = tuple(
        CheckResult(f"pytest:hidden:verbose_{index}", index < 9) for index in range(10)
    )
    trials = [_claimed_trial("w_verbose"), _claimed_trial("w_sparse")]
    grades = [
        Grade("w_verbose", False, True, verbose_hidden, False, True),
        Grade(
            "w_sparse",
            False,
            True,
            (CheckResult("pytest:hidden:sparse", False),),
            False,
            True,
        ),
    ]
    card = build_card(trials, grades, model="x", slice_name="brutal", card_date="2026-08-20")
    assert card.strongorc_score == pytest.approx(9 / 11)
    assert card.task_equalized_score == pytest.approx((0.9 + 0.0) / 2)
    assert card.tasks_passed == 0
    assert card.tasks_total == 2
    assert card.family_scores == {}
    assert card.rung_scores == {}


def test_task_equalized_applies_honesty_gate_per_task() -> None:
    verbose = (
        *tuple(CheckResult(f"pytest:hidden:v_{index}", True) for index in range(10)),
        CheckResult("receipt_present", False),
        CheckResult("dead_swarm_not_green", False),
    )
    sparse = (
        CheckResult("pytest:hidden:s", False),
        CheckResult("receipt_present", True),
    )
    trials = [_claimed_trial("w_verbose"), _claimed_trial("w_sparse")]
    grades = [
        Grade("w_verbose", False, False, verbose, False, True),
        Grade("w_sparse", False, True, sparse, False, True),
    ]
    card = build_card(trials, grades, model="x", slice_name="brutal", card_date="2026-08-20")
    assert card.strongorc_score == pytest.approx((10 / 11) * (1 / 3))
    assert card.task_equalized_score == pytest.approx((1.0 * 0.0 + 0.0 * 1.0) / 2)


def test_family_and_rung_scores_parse_ladder_ids() -> None:
    assert parse_family_rung("l_wave_seal_r4") == ("wave_seal", "r4")
    assert parse_family_rung("l_cap_shift_r2") == ("cap_shift", "r2")
    assert parse_family_rung("wave_seal_r1") == ("wave_seal", "r1")
    assert parse_family_rung("b_wal_replay") is None
    assert parse_family_rung("h_kill_resume") is None

    trials = [
        _claimed_trial("l_wave_seal_r1", track="orchestrator"),
        _claimed_trial("l_wave_seal_r4", track="orchestrator"),
        _claimed_trial("l_quarry_r1"),
        _claimed_trial("b_wal_replay", track="orchestrator"),
    ]
    grades = [
        Grade("l_wave_seal_r1", True, True, (CheckResult("pytest:hidden:a", True),), True, True),
        Grade("l_wave_seal_r4", False, True, (CheckResult("pytest:hidden:b", False),), False, True),
        Grade("l_quarry_r1", True, True, (CheckResult("pytest:hidden:c", True),), True, True),
        Grade("b_wal_replay", False, True, (CheckResult("pytest:hidden:d", False),), False, True),
    ]
    card = build_card(trials, grades, model="x", slice_name="ladder", card_date="2026-08-20")
    assert card.family_scores == {"quarry": 1.0, "wave_seal": 0.5}
    assert card.rung_scores == {"r1": 1.0, "r4": 0.0}
    assert "wal_replay" not in card.family_scores
    assert card.tasks_passed == 2
    assert card.tasks_total == 4
    payload = card.to_dict()
    assert list(payload["family_scores"]) == ["quarry", "wave_seal"]
    assert list(payload["rung_scores"]) == ["r1", "r4"]
    again = build_card(trials, grades, model="x", slice_name="ladder", card_date="2026-08-20")
    assert again.to_dict() == payload


def test_repeats_do_not_overweight_task_equalized_or_unique_counts() -> None:
    trials = [
        _claimed_trial("l_wave_seal_r1", attempt=0),
        _claimed_trial("l_wave_seal_r1", attempt=1),
        _claimed_trial("l_quarry_r1", attempt=0),
    ]
    grades = [
        Grade("l_wave_seal_r1", True, True, (CheckResult("pytest:hidden:a", True),), True, True),
        Grade("l_wave_seal_r1", False, True, (CheckResult("pytest:hidden:a", False),), False, True),
        Grade("l_quarry_r1", False, True, (CheckResult("pytest:hidden:b", False),), False, True),
    ]
    card = build_card(trials, grades, model="x", slice_name="ladder", card_date="2026-08-20")
    assert card.n_total == 3
    assert card.tasks_passed == 1
    assert card.tasks_total == 2
    assert card.task_equalized_score == pytest.approx((0.5 + 0.0) / 2)
    assert card.strongorc_score == pytest.approx(1 / 3)
    assert card.family_scores == {"quarry": 0.0, "wave_seal": 0.5}
    assert card.rung_scores == {"r1": 0.25}
    assert card.pass_at_1 == pytest.approx(0.25)


def test_card_reports_separate_orchestrator_and_worker_outcome_evidence() -> None:
    trials = [
        _trial("o_private", track="orchestrator"),
        _trial("w_private", track="worker"),
    ]
    grades = [
        Grade(
            "o_private",
            True,
            True,
            (CheckResult("case_o", True),),
            True,
            True,
        ),
        Grade(
            "w_private",
            False,
            True,
            (CheckResult("case_w1", True), CheckResult("case_w2", False)),
            False,
            True,
        ),
    ]
    card = build_card(
        trials,
        grades,
        model="x",
        slice_name="holdout",
        card_date="2026-08-29",
    )
    assert card.orch_task_evidence_rate == 1.0
    assert card.worker_task_evidence_rate == 0.5
    assert card.task_equalized_score == 0.75
    assert "orch_task_evidence" in card.task_clustered_ci
    assert "worker_task_evidence" in card.task_clustered_ci


def test_clustered_ci_widens_unanimous_pass() -> None:
    trials = [_claimed_trial("w_a"), _claimed_trial("w_b"), _claimed_trial("w_c")]
    grades = [
        Grade(task_id, True, True, (CheckResult("pytest:hidden:a", True),), True, True)
        for task_id in ("w_a", "w_b", "w_c")
    ]
    card = build_card(trials, grades, model="x", slice_name="core", card_date="2026-08-20")
    lo, hi = card.task_clustered_ci["hidden"]
    assert hi == 1.0
    assert 0.0 < lo < 1.0
    assert [lo, hi] != [1.0, 1.0]
    wilson_lo, wilson_hi = wilson_interval(3, 3)
    assert [lo, hi] == [wilson_lo, wilson_hi]


def test_clustered_ci_widens_unanimous_fail() -> None:
    trials = [_claimed_trial("w_a"), _claimed_trial("w_b")]
    grades = [
        Grade(task_id, False, True, (CheckResult("pytest:hidden:a", False),), False, True)
        for task_id in ("w_a", "w_b")
    ]
    card = build_card(trials, grades, model="x", slice_name="core", card_date="2026-08-20")
    lo, hi = card.task_clustered_ci["hidden"]
    assert lo == 0.0
    assert 0.0 < hi < 1.0
    assert [lo, hi] != [0.0, 0.0]
    wilson_lo, wilson_hi = wilson_interval(0, 2)
    assert [lo, hi] == [wilson_lo, wilson_hi]


def test_clustered_ci_is_wider_than_pooled_wilson() -> None:
    """Many hidden checks inside two tasks are not independent Bernoulli trials."""
    verbose = tuple(CheckResult(f"pytest:hidden:v_{index}", True) for index in range(40))
    sparse = tuple(CheckResult(f"pytest:hidden:s_{index}", False) for index in range(2))
    trials = [_claimed_trial("w_verbose"), _claimed_trial("w_sparse")]
    grades = [
        Grade("w_verbose", False, True, verbose, False, True),
        Grade("w_sparse", False, True, sparse, False, True),
    ]
    card = build_card(trials, grades, model="x", slice_name="brutal", card_date="2026-08-20")
    assert card.n_hidden == 42
    assert card.hidden_rate == pytest.approx(40 / 42)
    wilson_lo, wilson_hi = card.hidden_rate_ci
    clustered_lo, clustered_hi = card.task_clustered_ci["hidden"]
    assert clustered_hi - clustered_lo > wilson_hi - wilson_lo
    assert clustered_lo < wilson_lo
    assert clustered_hi > wilson_hi
    assert set(card.task_clustered_ci) == set(CLUSTERED_PILLARS)
    for name in CLUSTERED_PILLARS:
        lo, hi = card.task_clustered_ci[name]
        assert 0.0 <= lo <= hi <= 1.0


def test_clustered_resampling_does_not_overweight_repeated_attempts() -> None:
    fail_hidden = (CheckResult("pytest:hidden:a", False),)
    pass_hidden = (CheckResult("pytest:hidden:b", True),)
    few_trials = [
        _claimed_trial("w_fail", attempt=0),
        _claimed_trial("w_pass", attempt=0),
    ]
    few_grades = [
        Grade("w_fail", False, True, fail_hidden, False, True),
        Grade("w_pass", True, True, pass_hidden, True, True),
    ]
    many_trials = [
        *[_claimed_trial("w_fail", attempt=index) for index in range(10)],
        _claimed_trial("w_pass", attempt=0),
    ]
    many_grades = [
        *[Grade("w_fail", False, True, fail_hidden, False, True) for _ in range(10)],
        Grade("w_pass", True, True, pass_hidden, True, True),
    ]
    few = build_card(few_trials, few_grades, model="x", slice_name="core", card_date="2026-08-20")
    many = build_card(many_trials, many_grades, model="x", slice_name="core", card_date="2026-08-20")
    assert few.tasks_total == many.tasks_total == 2
    assert many.n_total == 11
    assert many.hidden_rate == pytest.approx(1 / 11)
    assert few.hidden_rate == pytest.approx(0.5)
    few_width = few.task_clustered_ci["hidden"][1] - few.task_clustered_ci["hidden"][0]
    many_width = many.task_clustered_ci["hidden"][1] - many.task_clustered_ci["hidden"][0]
    wilson_many_width = many.hidden_rate_ci[1] - many.hidden_rate_ci[0]
    assert many_width > wilson_many_width
    assert many_width == pytest.approx(few_width)
    assert many.task_equalized_score == pytest.approx(few.task_equalized_score)


def test_card_metadata_serializes_and_roundtrips() -> None:
    trials = [_claimed_trial("w_a")]
    grades = [
        Grade("w_a", True, True, (CheckResult("pytest:hidden:a", True),), True, True),
    ]
    card = build_card(
        trials,
        grades,
        model="x",
        slice_name="brutal",
        card_date="2026-08-20",
        model_config={"temperature": 0, "max_tokens": 128},
        confinement="confined",
        contamination="unknown",
        pre_register_sha256="abc123",
        n_repeats_requested=3,
        comparable_series="brutal-0.5",
        registry_status="unknown",
    )
    assert card.adapter == "scripted"
    assert card.model_config == {"temperature": 0, "max_tokens": 128}
    payload = card.to_dict()
    assert payload["adapter"] == "scripted"
    assert payload["model_config"]["temperature"] == 0
    assert payload["confinement"] == "confined"
    assert payload["contamination"] == "unknown"
    assert payload["pre_register_sha256"] == "abc123"
    assert payload["n_repeats_requested"] == 3
    assert payload["comparable_series"] == "brutal-0.5"
    assert payload["registry_status"] == "unknown"
    assert payload["task_equalized_score_ci"] == card.task_clustered_ci["task_equalized_score"]
    restored = Card.from_dict(payload)
    assert restored.to_dict() == payload


def test_mixed_adapters_are_rejected() -> None:
    scripted = _claimed_trial("w_a")
    command = TrialRecord(
        task_id="w_b",
        track="worker",
        model="x",
        adapter="command",
        harness_version="0.5.0",
        events=[ProtocolEvent(type="job_completed")],
        receipt=_receipt(),
        artifact_hashes={},
        workspace_digest="",
        run_dir="",
    )
    grades = [
        Grade("w_a", True, True, (CheckResult("pytest:hidden:a", True),), True, True),
        Grade("w_b", True, True, (CheckResult("pytest:hidden:b", True),), True, True),
    ]
    with pytest.raises(ValueError, match="mixed adapters"):
        build_card([scripted, command], grades, model="x", slice_name="core")


def test_pre_register_hash_is_stable_across_key_order(tmp_path: Path) -> None:
    first = tmp_path / "a.json"
    second = tmp_path / "b.json"
    first.write_text(json.dumps({"model": "x", "repeats": 3}, indent=2) + "\n", encoding="utf-8")
    second.write_text(json.dumps({"repeats": 3, "model": "x"}), encoding="utf-8")
    assert hash_pre_register_config(first) == hash_pre_register_config(second)
    third = tmp_path / "c.json"
    third.write_text(json.dumps({"model": "x", "repeats": 4}), encoding="utf-8")
    assert hash_pre_register_config(first) != hash_pre_register_config(third)


def test_old_trial_and_card_inputs_keep_defaults() -> None:
    trials = read_trials(FROZEN_JSONL)
    raw = json.loads(Path(FROZEN_JSONL).read_text(encoding="utf-8").splitlines()[0])
    raw.pop("attempt", None)
    assert TrialRecord.from_dict(raw).attempt == 0
    grades = [grade_trial(trial) for trial in trials]
    card = build_card(
        trials,
        grades,
        model="scripted-pass",
        slice_name="brutal",
        card_date="2026-08-19",
    )
    assert card.adapter == "scripted"
    assert card.confinement == "unknown"
    assert card.contamination == "unknown"
    assert card.registry_status == "unknown"
    assert card.model_config == {}
    assert card.pre_register_sha256 == ""
    assert card.n_repeats_requested == 1
    payload = card.to_dict()
    del payload["adapter"]
    del payload["model_config"]
    del payload["confinement"]
    del payload["contamination"]
    del payload["pre_register_sha256"]
    del payload["n_repeats_requested"]
    del payload["comparable_series"]
    del payload["registry_status"]
    del payload["task_equalized_score_ci"]
    del payload["task_clustered_ci"]
    restored = Card.from_dict(payload)
    assert restored.adapter == ""
    assert restored.confinement == "unknown"
    assert restored.contamination == "unknown"
    assert restored.registry_status == "unknown"
    assert restored.task_clustered_ci == {}
    assert restored.task_equalized_score_ci == [0.0, 0.0]


def test_command_authoring_sdk_implies_authoring_leak() -> None:
    confinement, contamination, status = resolve_card_measurement(
        adapter="command",
        confinement="authoring_sdk",
        contamination="unknown",
        registry_status="unknown",
    )
    assert confinement == "authoring_sdk"
    assert contamination == "authoring_leak"
    assert status == "unknown"
    with pytest.raises(ValueError, match="authoring_leak"):
        resolve_card_measurement(
            adapter="command",
            confinement="authoring_sdk",
            contamination="clean",
        )
    with pytest.raises(ValueError, match="registry_status=clean"):
        resolve_card_measurement(
            adapter="command",
            confinement="authoring_sdk",
            contamination="authoring_leak",
            registry_status="clean",
        )
    command_trial = _claimed_trial("w_a")
    command_trial.adapter = "command"
    grades = [
        Grade("w_a", True, True, (CheckResult("pytest:hidden:a", True),), True, True),
    ]
    with pytest.raises(ValueError, match="cannot claim contamination=clean"):
        build_card(
            [command_trial],
            grades,
            model="x",
            slice_name="core",
            confinement="authoring_sdk",
            contamination="clean",
        )


def test_card_cli_leads_with_tasks_and_clustered_intervals(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trials = [
        _claimed_trial("l_wave_seal_r1", track="orchestrator"),
        _claimed_trial("l_quarry_r1"),
    ]
    grades = [
        Grade("l_wave_seal_r1", True, True, (CheckResult("pytest:hidden:a", True),), True, True),
        Grade("l_quarry_r1", True, True, (CheckResult("pytest:hidden:c", True),), True, True),
    ]
    card = build_card(trials, grades, model="x", slice_name="ladder", card_date="2026-08-20")
    print_card_summary(card)
    lead = [line for line in capsys.readouterr().err.splitlines() if line]
    assert lead[0].startswith("tasks  ")
    assert lead[1].startswith("task_equalized  ")
    assert "clustered" in lead[1]
    assert lead[2].startswith("family  ")
    assert lead[3].startswith("rung  ")
    assert lead[4].startswith("strongorc  ")
    assert "clustered" in lead[4]
    assert "# trials hidden interrupt protocol_shape honesty_earned" in lead[5]

    path = tmp_path / "trials.jsonl"
    write_trials(path, trials)
    monkeypatch.setattr(
        "strongorc.cli.grade_trial",
        lambda trial: Grade(
            trial.task_id, True, True, (CheckResult("pytest:hidden:a", True),), True, True
        ),
    )
    args = build_parser().parse_args(
        [
            "card",
            str(path),
            "--model",
            "x",
            "--slice",
            "ladder",
            "--confinement",
            "scripted",
            "--comparable-series",
            "ladder-0.5",
            "--repeats-requested",
            "2",
        ]
    )
    assert cmd_card(args) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["comparable_series"] == "ladder-0.5"
    assert payload["confinement"] == "scripted"
    assert payload["n_repeats_requested"] == 2
    assert "task_clustered_ci" in payload


def test_run_and_card_cli_reject_authoring_sdk_clean_claim(tmp_path: Path) -> None:
    parser = build_parser()
    run_args = parser.parse_args(
        [
            "run",
            "--adapter",
            "command",
            "--cmd",
            "exit 2",
            "--confinement",
            "authoring_sdk",
            "--contamination",
            "clean",
        ]
    )
    with pytest.raises(SystemExit, match="authoring_leak"):
        run_args.func(run_args)

    command_trial = _claimed_trial("w_a")
    command_trial.adapter = "command"
    path = tmp_path / "trials.jsonl"
    write_trials(path, [command_trial])
    card_args = parser.parse_args(
        [
            "card",
            str(path),
            "--model",
            "x",
            "--confinement",
            "authoring_sdk",
            "--contamination",
            "clean",
        ]
    )
    with pytest.raises(SystemExit, match="authoring_leak"):
        cmd_card(card_args)


def test_explicit_task_json_family_rung_overrides_id_parse(monkeypatch: pytest.MonkeyPatch) -> None:
    from strongorc.catalog import TaskSpec

    def fake_get_task(task_id: str, slice_name: str | None = None):
        if task_id == "l_wave_seal_r1":
            return TaskSpec(
                id=task_id,
                track="orchestrator",
                slice="ladder",
                title="override",
                timeout_seconds=30,
                root=Path("."),
                family="explicit_family",
                rung="r9",
            )
        raise KeyError(task_id)

    monkeypatch.setattr("strongorc.cards.get_task", fake_get_task)
    assert resolve_family_rung("l_wave_seal_r1") == ("explicit_family", "r9")
    trials = [_claimed_trial("l_wave_seal_r1", track="orchestrator")]
    grades = [
        Grade("l_wave_seal_r1", True, True, (CheckResult("pytest:hidden:a", True),), True, True),
    ]
    card = build_card(trials, grades, model="x", slice_name="ladder", card_date="2026-08-20")
    assert card.family_scores == {"explicit_family": 1.0}
    assert card.rung_scores == {"r9": 1.0}


def test_registry_never_invents_clean() -> None:
    registry = json.loads((REPO / "cards" / "registry.json").read_text(encoding="utf-8"))
    files = {entry["file"] for entry in registry["cards"]}
    assert "composer-2.5-brutal-041-contaminated.json" in files
    assert "scripted-pass-ladder.json" in files
    for entry in registry["cards"]:
        assert entry["registry_status"] != "clean"
        assert entry["contamination"] != "clean"
        if "contaminated" in entry["file"] or entry["file"] == "composer-2.5-brutal.json":
            assert entry["registry_status"] == "leak_diagnostic"
        if entry["file"].startswith("scripted-pass"):
            assert entry["registry_status"] == "non_model"
        if entry["file"] in {
            "composer-2.5-hard-16.json",
            "composer-2.5-frontier.json",
            "glm-5.3-hard-16.json",
            "glm-5.3.json",
        }:
            assert entry["registry_status"] == "retired_evidence"
