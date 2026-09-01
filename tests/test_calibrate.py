from __future__ import annotations

import json
from pathlib import Path

import pytest

from strongorc.calibrate import (
    DISCRIMINATION_FLOOR,
    MIN_SYSTEMS_FOR_2PL,
    ResponseMatrix,
    SystemRow,
    assign_system_band,
    build_calibration_report,
    fit_irt,
    irf,
    item_verdict,
    matrix_from_expected,
    matrix_from_trial_paths,
    paired_task_bootstrap,
    pearson,
    simulate_2pl,
    system_from_pairs,
)
from strongorc.cards import hash_pre_register_config, receipt_spend, trial_usd
from strongorc.cli import build_parser
from strongorc.harness import merge_slice_trials, run_slice, write_trials
from strongorc.schema import CheckResult, Grade, ProtocolEvent, Receipt, TrialRecord

REPO = Path(__file__).resolve().parents[1]
PREREGISTER = REPO / "cards" / "preregister" / "reason-0.6.0.json"
OPENCODE_PREREGISTER = REPO / "cards" / "preregister" / "reason-0.6.0-opencode-go.json"


def _receipt() -> Receipt:
    return Receipt(
        status="completed",
        model_id="x",
        usd=0.1,
        tokens_in=4,
        tokens_out=2,
        workers_ran=1,
    )


def _trial(task_id: str, model: str, *, attempt: int = 0) -> TrialRecord:
    return TrialRecord(
        task_id=task_id,
        track="worker",
        model=model,
        adapter="scripted",
        harness_version="0.6.0",
        events=[ProtocolEvent(type="job_completed", payload={})],
        receipt=_receipt(),
        artifact_hashes={},
        workspace_digest="",
        run_dir="",
        attempt=attempt,
    )


def _grade(task_id: str, passed: bool) -> Grade:
    return Grade(
        task_id=task_id,
        passed=passed,
        honesty_passed=True,
        checks=(CheckResult("pytest:hidden:test_case_001", passed),),
        outcome_passed=passed,
        protocol_passed=True,
    )


def _scripted_matrix() -> ResponseMatrix:
    ids = [
        "r_trace_contract_r1",
        "r_trace_contract_r2",
        "r_trace_contract_r3",
        "r_retract_rule_r1",
        "r_diagnose_kill_r1",
    ]
    pass_row = SystemRow(
        system_id="scripted-pass",
        model="scripted-pass",
        adapter="scripted",
        confinement="scripted",
        contamination="unknown",
        task_equalized_score=1.0,
        tasks_passed=len(ids),
        tasks_total=len(ids),
        n_attempts=1,
        responses={task_id: 1.0 for task_id in ids},
        band="saturated",
        scripted=True,
    )
    fail_row = SystemRow(
        system_id="scripted-fail",
        model="scripted-fail",
        adapter="scripted",
        confinement="scripted",
        contamination="unknown",
        task_equalized_score=0.0,
        tasks_passed=0,
        tasks_total=len(ids),
        n_attempts=1,
        responses={task_id: 0.0 for task_id in ids},
        band="floor",
        scripted=True,
    )
    return ResponseMatrix(slice_name="reason", systems=[pass_row, fail_row], item_ids=ids)


def test_trial_usd_does_not_let_receipt_undercut_usage() -> None:
    billed = _trial("hld_relay_r2", "live-a")
    billed.receipt = Receipt(
        status="completed",
        model_id="live-a",
        usd=2.79,
        tokens_in=10,
        tokens_out=4,
        workers_ran=1,
    )
    billed.files = {".harness/openrouter_usage.json": json.dumps({"usd": 3.10})}
    assert trial_usd(billed) == pytest.approx(3.10)


def test_receipt_spend_uses_usage_when_receipt_missing() -> None:
    billed = _trial("r_trace_contract_r1", "live-a")
    billed.receipt = Receipt(
        status="completed",
        model_id="live-a",
        usd=0.4,
        tokens_in=10,
        tokens_out=4,
        workers_ran=1,
    )
    unfinished = _trial("r_trace_contract_r2", "live-a")
    unfinished.receipt = None
    unfinished.files = {".harness/openrouter_usage.json": json.dumps({"usd": 0.15})}
    total, per_task = receipt_spend([billed, unfinished])
    assert trial_usd(unfinished) == pytest.approx(0.15)
    assert total == pytest.approx(0.55)
    assert per_task["r_trace_contract_r1"] == pytest.approx(0.4)
    assert per_task["r_trace_contract_r2"] == pytest.approx(0.15)


def test_system_from_pairs_records_usd_per_task() -> None:
    pairs = [
        (_trial("r_trace_contract_r1", "live-a"), _grade("r_trace_contract_r1", True)),
        (_trial("r_trace_contract_r2", "live-a"), _grade("r_trace_contract_r2", False)),
    ]
    row = system_from_pairs(pairs, slice_name="reason")
    assert row.usd_total == pytest.approx(0.2)
    assert row.usd_per_task == pytest.approx(0.1)
    assert row.usd_per_pass == pytest.approx(0.2)
    assert row.task_usd["r_trace_contract_r1"] == pytest.approx(0.1)


def test_assign_system_band_splits_protocol_ranges() -> None:
    assert assign_system_band(0.0) == "floor"
    assert assign_system_band(0.10) == "weak"
    assert assign_system_band(0.20) == "middle"
    assert assign_system_band(0.37) == "frontier"
    assert assign_system_band(0.75) == "high"
    assert assign_system_band(0.91) == "saturated"


def test_item_verdict_flags_inverted_and_flat_items() -> None:
    drop, _ = item_verdict(
        p=0.5, variance=0.25, point_biserial=-0.2, a=1.0, identified=True
    )
    rewrite, _ = item_verdict(
        p=0.5, variance=0.25, point_biserial=0.4, a=0.1, identified=True
    )
    keep, _ = item_verdict(
        p=0.5, variance=0.25, point_biserial=0.6, a=1.2, identified=True
    )
    unidentified, _ = item_verdict(
        p=0.5, variance=0.25, point_biserial=1.0, a=None, identified=False
    )
    assert drop == "drop"
    assert rewrite == "rewrite"
    assert keep == "keep"
    assert unidentified == "unidentified"
    assert DISCRIMINATION_FLOOR == 0.35


def test_scripted_matrix_is_oracle_nonvacuity() -> None:
    report = build_calibration_report(_scripted_matrix(), pre_register_path=PREREGISTER)
    assert report["status"] == "oracle_nonvacuity"
    assert report["irt_identified"] is False
    assert report["band_hits"]["protocol_ready"] is False
    assert report["pre_register_sha256"] == hash_pre_register_config(PREREGISTER)
    assert all(item["verdict"] == "unidentified" for item in report["items"])
    assert "Authored rungs are not calibrated" in " ".join(report["notes"])


def test_2pl_recovers_difficulty_order() -> None:
    thetas = [-1.6, -1.0, -0.4, 0.0, 0.4, 1.0, 1.4, 2.0]
    a = [1.2, 1.1, 1.3, 1.0, 1.4, 0.9, 1.2, 1.1]
    b = [-1.4, -0.8, -0.3, 0.2, 0.6, 1.0, 1.5, 2.0]
    ids = [f"r_synth_r{index + 1}" for index in range(len(b))]
    expected = simulate_2pl(thetas=thetas, a=a, b=b)
    matrix = matrix_from_expected(expected, slice_name="reason", item_ids=ids)
    assert len(matrix.systems) >= MIN_SYSTEMS_FOR_2PL
    fit = fit_irt(matrix)
    assert fit.identified
    assert fit.kind == "2pl"
    estimated = [fit.b[task_id] for task_id in ids]
    recovered = pearson(b, estimated)
    assert recovered is not None
    assert recovered > 0.85
    report = build_calibration_report(matrix)
    assert report["status"] == "fitted"
    assert report["rewrite"] == []


def test_near_zero_discrimination_is_rewrite() -> None:
    thetas = [-1.5, -0.8, -0.2, 0.3, 0.9, 1.6]
    a = [1.3, 1.2, 1.1, 1.0, 0.08, 1.2]
    b = [-1.0, -0.4, 0.0, 0.4, 0.1, 1.1]
    ids = [f"r_flat_r{index + 1}" for index in range(len(b))]
    expected = simulate_2pl(thetas=thetas, a=a, b=b)
    matrix = matrix_from_expected(expected, slice_name="reason", item_ids=ids)
    report = build_calibration_report(matrix)
    by_id = {item["task_id"]: item for item in report["items"]}
    assert by_id["r_flat_r5"]["verdict"] == "rewrite"
    assert "r_flat_r5" in report["rewrite"]


def test_system_from_pairs_averages_attempts() -> None:
    pairs = [
        (_trial("r_trace_contract_r1", "mid", attempt=0), _grade("r_trace_contract_r1", True)),
        (_trial("r_trace_contract_r1", "mid", attempt=1), _grade("r_trace_contract_r1", False)),
        (_trial("r_trace_contract_r2", "mid", attempt=0), _grade("r_trace_contract_r2", False)),
    ]
    row = system_from_pairs(pairs, slice_name="reason", confinement="scripted")
    assert row.responses["r_trace_contract_r1"] == pytest.approx(0.5)
    assert row.responses["r_trace_contract_r2"] == pytest.approx(0.0)
    assert row.n_attempts == 2
    assert row.scripted is False


def test_system_from_pairs_uses_strict_pass_as_primary_and_evidence_as_diagnostic() -> None:
    trial = _trial("r_trace_contract_r1", "mid")
    grade = Grade(
        task_id=trial.task_id,
        passed=False,
        honesty_passed=True,
        checks=(
            CheckResult("pytest:hidden:test_case_001", True),
            CheckResult("pytest:hidden:test_case_002", False),
        ),
        outcome_passed=False,
        protocol_passed=True,
    )
    row = system_from_pairs([(trial, grade)], slice_name="reason", confinement="confined")
    assert row.tasks_passed == 0
    assert row.responses[trial.task_id] == 0.0
    assert row.task_equalized_score == 0.0
    assert row.evidence_responses[trial.task_id] == pytest.approx(0.5)
    assert row.task_evidence_score == pytest.approx(0.5)


def test_task_evidence_requires_protocol_and_never_rewards_interrupt_only() -> None:
    trial = _trial("r_trace_contract_r1", "mid")
    grade = Grade(
        task_id=trial.task_id,
        passed=False,
        honesty_passed=True,
        checks=(
            CheckResult("pytest:hidden:test_case_001", True),
            CheckResult("sealed:pre_kill_1", True),
            CheckResult("event:worker_started", True),
        ),
        outcome_passed=True,
        protocol_passed=False,
    )
    row = system_from_pairs([(trial, grade)], slice_name="reason", confinement="confined")
    assert row.responses[trial.task_id] == 0.0
    assert row.task_equalized_score == 0.0


def test_provider_refusal_is_censored_from_capability_score() -> None:
    passed = _trial("r_trace_contract_r1", "model")
    refused = _trial("r_trace_contract_r2", "model")
    refused.receipt = Receipt(
        status="failed",
        model_id="model",
        usd=0.01,
        tokens_in=10,
        tokens_out=0,
        workers_ran=0,
    )
    refused.events = [
        ProtocolEvent(type="job_failed", payload={"reason": "provider_refusal"})
    ]

    row = system_from_pairs(
        [
            (passed, _grade(passed.task_id, True)),
            (refused, _grade(refused.task_id, False)),
        ],
        slice_name="reason",
        confinement="confined",
    )

    assert row.task_equalized_score == 1.0
    assert row.responses == {passed.task_id: 1.0}
    assert row.scored_attempts == 1
    assert row.censored_attempts == 1
    assert row.coverage_rate == 0.5
    assert row.censor_reasons == {"provider_refusal": 1}


def test_valid_and_censored_repeats_do_not_cherry_pick_capability() -> None:
    task_id = "r_trace_contract_r1"
    failed = _trial(task_id, "model", attempt=0)
    passed = _trial(task_id, "model", attempt=1)
    refused = _trial(task_id, "model", attempt=2)
    refused.receipt = Receipt(
        status="failed",
        model_id="model",
        usd=0.01,
        tokens_in=10,
        tokens_out=0,
        workers_ran=0,
    )
    refused.events = [
        ProtocolEvent(type="job_failed", payload={"reason": "provider_refusal"})
    ]

    row = system_from_pairs(
        [
            (failed, _grade(task_id, False)),
            (passed, _grade(task_id, True)),
            (refused, _grade(task_id, False)),
        ],
        slice_name="reason",
        confinement="confined",
    )

    assert row.responses[task_id] == pytest.approx(0.5)
    assert row.task_equalized_score == pytest.approx(0.5)
    assert row.scored_attempts == 2
    assert row.censored_attempts == 1
    assert row.coverage_rate == pytest.approx(2 / 3)


def test_more_strict_successes_cannot_lose_to_partial_evidence() -> None:
    def partial_grade(task_id: str) -> Grade:
        return Grade(
            task_id=task_id,
            passed=False,
            honesty_passed=True,
            checks=(
                CheckResult("pytest:hidden:test_case_001", True),
                CheckResult("pytest:hidden:test_case_002", True),
                CheckResult("pytest:hidden:test_case_003", False),
            ),
            outcome_passed=False,
            protocol_passed=True,
        )

    stronger_pairs = []
    weaker_pairs = []
    for index in range(8):
        stronger_task = f"r_stronger_{index}_r1"
        weaker_task = f"r_weaker_{index}_r1"
        stronger_passed = index < 6
        weaker_passed = index < 5
        stronger_pairs.append(
            (
                _trial(stronger_task, "stronger"),
                _grade(stronger_task, True)
                if stronger_passed
                else _grade(stronger_task, False),
            )
        )
        weaker_pairs.append(
            (
                _trial(weaker_task, "weaker"),
                _grade(weaker_task, True)
                if weaker_passed
                else partial_grade(weaker_task),
            )
        )

    stronger = system_from_pairs(
        stronger_pairs, slice_name="reason", confinement="confined"
    )
    weaker = system_from_pairs(
        weaker_pairs, slice_name="reason", confinement="confined"
    )

    assert stronger.task_equalized_score == 0.75
    assert weaker.task_equalized_score == 0.625
    assert stronger.task_equalized_score > weaker.task_equalized_score
    assert weaker.task_evidence_score > weaker.task_equalized_score


def test_scripted_personas_do_not_identify_live_irt() -> None:
    task_ids = list(_scripted_matrix().item_ids)
    live = matrix_from_expected(
        [
            [0.1, 0.2, 0.3, 0.4, 0.5],
            [0.2, 0.3, 0.4, 0.5, 0.6],
        ],
        slice_name="reason",
        item_ids=task_ids,
        system_prefix="live",
    )
    scripted = _scripted_matrix()
    combined = ResponseMatrix(
        slice_name="reason",
        systems=[*scripted.systems, *live.systems],
        item_ids=task_ids,
    )
    fit = fit_irt(combined)
    assert fit.identified is False
    assert "live systems" in fit.note
    report = build_calibration_report(combined)
    assert report["n_systems"] == 4
    assert report["n_live_systems"] == 2
    by_id = {item["task_id"]: item for item in report["items"]}
    assert by_id[task_ids[0]]["p"] == pytest.approx(0.15)


def test_paired_task_bootstrap_reports_task_clustered_uncertainty() -> None:
    matrix = _scripted_matrix()
    comparison = paired_task_bootstrap(
        matrix.systems[0],
        matrix.systems[1],
        samples=1_000,
    )

    assert comparison["tasks"] == len(matrix.item_ids)
    assert comparison["mean_delta"] == 1.0
    assert comparison["ci95"] == [1.0, 1.0]
    assert comparison["probability_first_better"] == 1.0


def test_calibrate_cli_writes_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pass_path = tmp_path / "pass.jsonl"
    fail_path = tmp_path / "fail.jsonl"
    write_trials(pass_path, [_trial("r_trace_contract_r1", "scripted-pass")])
    write_trials(fail_path, [_trial("r_trace_contract_r1", "scripted-fail")])

    def fake_grade(trial: TrialRecord) -> Grade:
        return _grade(trial.task_id, trial.model == "scripted-pass")

    monkeypatch.setattr("strongorc.calibrate.grade_trial", fake_grade)
    out = tmp_path / "report.json"
    args = build_parser().parse_args(
        [
            "calibrate",
            str(pass_path),
            str(fail_path),
            "--slice",
            "reason",
            "--out",
            str(out),
            "--preregister",
            str(PREREGISTER),
        ]
    )
    assert args.func(args) == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["schema"] == "strongorc.calibration.v5"
    assert "family_check_curves" in report
    assert "rung_check_curves" in report
    assert "family_evidence_curves" in report
    assert "rung_evidence_curves" in report
    assert report["status"] == "oracle_nonvacuity"
    assert report["slice"] == "reason"
    assert report["pre_register_sha256"] == hash_pre_register_config(PREREGISTER)
    assert all("usd_total" in row and "task_usd" in row for row in report["systems"])


def test_matrix_from_trial_paths_rejects_empty(tmp_path: Path) -> None:
    empty = tmp_path / "empty.jsonl"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="empty trials"):
        matrix_from_trial_paths([empty], slice_name="reason")


def test_preregister_states_the_protocol() -> None:
    payload = json.loads(PREREGISTER.read_text(encoding="utf-8"))
    assert payload["slice"] == "reason"
    assert payload["harness_version"] == "0.6.0"
    assert payload["repeats"] == 3
    assert payload["adapter"] == "command"
    assert payload["channel"] == "cursor-sdk"
    assert payload["confinement"] == "authoring_sdk"
    assert payload["contamination"] == "authoring_leak"
    assert payload["cmd"].endswith("cursor_agent.py")
    assert len(payload["systems"]["weak"]) >= 2
    assert len(payload["systems"]["middle"]) >= 2
    assert len(payload["systems"]["frontier"]) >= 2
    assert payload["targets"]["saturation"] == 0.80


def test_openrouter_preregister_is_a_separate_series() -> None:
    path = REPO / "cards" / "preregister" / "reason-0.6.0-openrouter.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["channel"] == "openrouter"
    assert payload["confinement"] == "confined"
    assert payload["cmd"].endswith("openrouter_agent.py")
    assert "stealth/ox-alpha" in payload["systems"]["frontier"]


def test_openrouter_shell_preregister_is_a_separate_series() -> None:
    path = REPO / "cards" / "preregister" / "reason-0.6.0-openrouter-shell.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    confined = json.loads(
        (REPO / "cards" / "preregister" / "reason-0.6.0-openrouter.json").read_text(
            encoding="utf-8"
        )
    )
    assert payload["channel"] == "openrouter-shell"
    assert payload["confinement"] == "unconfined"
    assert "--allow-shell" in payload["cmd"]
    assert payload["comparable_series"] != confined["comparable_series"]
    assert payload["comparable_series"] not in {
        json.loads(
            (REPO / "cards" / "preregister" / f"{name}-0.6.0-openrouter.json").read_text(
                encoding="utf-8"
            )
        )["comparable_series"]
        for name in ("reason", "ladder", "brutal", "native")
    }


def test_openrouter_slice_preregisters_do_not_share_a_series() -> None:
    series = set()
    for slice_name in ("reason", "ladder", "brutal", "native", "core", "hard", "frontier"):
        path = REPO / "cards" / "preregister" / f"{slice_name}-0.6.0-openrouter.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["slice"] == slice_name
        assert payload["channel"] == "openrouter"
        assert payload["confinement"] == "confined"
        assert payload["comparable_series"] not in series
        series.add(payload["comparable_series"])


def test_opencode_preregister_is_a_separate_series() -> None:
    payload = json.loads(OPENCODE_PREREGISTER.read_text(encoding="utf-8"))
    assert payload["channel"] == "agentic-opencode"
    assert payload["provider"] == "opencode-go"
    assert payload["confinement"] == "confined"
    assert payload["contamination"] == "unknown"
    assert payload["comparable_series"] != json.loads(PREREGISTER.read_text(encoding="utf-8"))[
        "comparable_series"
    ]
    assert payload["cmd"].endswith("agentic_opencode_agent.py")
    assert "ox-alpha-free" in payload["systems"]["frontier"]
    assert "minimax-m2.5" in payload["systems"]["middle"]


def test_command_jsonl_is_not_automatically_confined(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "live.jsonl"
    trial = _trial("r_trace_contract_r1", "ox-alpha")
    trial.adapter = "command"
    write_trials(path, [trial])

    def fake_grade(item: TrialRecord) -> Grade:
        return _grade(item.task_id, False)

    monkeypatch.setattr("strongorc.calibrate.grade_trial", fake_grade)
    matrix = matrix_from_trial_paths([path], slice_name="reason")
    assert matrix.systems[0].confinement == "unknown"
    assert matrix.systems[0].hidden_rate == 0.0


def test_live_irt_refuses_unknown_confinement(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    paths = []
    for name in ("a", "b"):
        path = tmp_path / f"{name}.jsonl"
        trial = _trial("r_trace_contract_r1", name)
        trial.adapter = "command"
        write_trials(path, [trial])
        paths.append(path)

    def fake_grade(item: TrialRecord) -> Grade:
        return _grade(item.task_id, False)

    monkeypatch.setattr("strongorc.calibrate.grade_trial", fake_grade)
    with pytest.raises(ValueError, match="explicit confinement"):
        matrix_from_trial_paths(paths, slice_name="reason")


def test_one_jsonl_refuses_mixed_recorded_confinement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "mixed.jsonl"
    jail = _trial("r_trace_contract_r1", "ox-alpha")
    jail.adapter = "command"
    jail.confinement = "confined"
    leak = _trial("r_trace_contract_r2", "ox-alpha")
    leak.adapter = "command"
    leak.confinement = "authoring_sdk"
    leak.contamination = "authoring_leak"
    write_trials(path, [jail, leak])

    def fake_grade(item: TrialRecord) -> Grade:
        return _grade(item.task_id, False)

    monkeypatch.setattr("strongorc.calibrate.grade_trial", fake_grade)
    with pytest.raises(ValueError, match="mixed confinement inside one jsonl"):
        matrix_from_trial_paths([path], slice_name="reason")


def test_check_curves_skip_ids_without_rungs() -> None:
    from strongorc.calibrate import _check_curve

    row = SystemRow(
        system_id="ox",
        model="ox",
        adapter="command",
        confinement="confined",
        contamination="unknown",
        task_equalized_score=0.0,
        tasks_passed=0,
        tasks_total=1,
        n_attempts=1,
        responses={"b_wal_replay": 0.0},
        band="floor",
        task_check_rates={"b_wal_replay": 0.12, "l_wave_seal_r1": 0.25},
    )
    assert _check_curve([row], "family") == {"wave_seal": 0.25}
    assert _check_curve([row], "rung") == {"r1": 0.25}


def test_merge_slice_trials_replaces_ids_and_keeps_neighbors() -> None:
    old = _trial("r_diagnose_kill_r1", "kimi")
    keep = _trial("r_diagnose_kill_r2", "kimi")
    incoming = _trial("r_diagnose_kill_r1", "kimi-rerun")
    merged = merge_slice_trials("reason", [old, keep], [incoming])
    by_id = {trial.task_id: trial for trial in merged}
    assert by_id["r_diagnose_kill_r1"].model == "kimi-rerun"
    assert by_id["r_diagnose_kill_r2"].model == "kimi"
    assert [trial.task_id for trial in merged[:2]] == [
        "r_diagnose_kill_r1",
        "r_diagnose_kill_r2",
    ]


def test_merge_slice_trials_preserves_distinct_attempts() -> None:
    first = _trial("r_diagnose_kill_r1", "first", attempt=0)
    second = _trial("r_diagnose_kill_r1", "second", attempt=1)
    replacement = _trial("r_diagnose_kill_r1", "replacement", attempt=1)
    merged = merge_slice_trials("reason", [first, second], [replacement])
    attempts = [trial for trial in merged if trial.task_id == first.task_id]
    assert [(trial.attempt, trial.model) for trial in attempts] == [
        (0, "first"),
        (1, "replacement"),
    ]


def test_run_slice_task_ids_filters_and_rejects_unknown(tmp_path: Path) -> None:
    results = run_slice(
        "core",
        adapter_name="scripted",
        model="scripted-pass",
        runs_root=tmp_path / "subset",
        adapter_kwargs={"persona": "pass"},
        task_ids=["o_kill_resume", "w_hollow_pass"],
    )
    assert [trial.task_id for trial, _ in results] == ["o_kill_resume", "w_hollow_pass"]
    with pytest.raises(ValueError, match="unknown task_ids"):
        run_slice(
            "core",
            adapter_name="scripted",
            model="scripted-pass",
            runs_root=tmp_path / "bad",
            adapter_kwargs={"persona": "pass"},
            task_ids=["not_a_task"],
        )
