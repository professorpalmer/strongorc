from __future__ import annotations

from datetime import date

from strongorc.grade import check_kind
from strongorc.schema import Card, Grade, TrialRecord


def _check_counts(grades: list[Grade], kind: str) -> tuple[int, int]:
    passed = 0
    total = 0
    for grade in grades:
        for check in grade.checks:
            if check_kind(check.name) != kind:
                continue
            total += 1
            if check.passed:
                passed += 1
    return passed, total


def build_card(
    trials: list[TrialRecord],
    grades: list[Grade],
    *,
    model: str,
    slice_name: str,
    card_date: str | None = None,
) -> Card:
    if len(trials) != len(grades):
        raise ValueError("trials and grades length mismatch")

    orch = [(trial, grade) for trial, grade in zip(trials, grades) if trial.track == "orchestrator"]
    leaf = [(trial, grade) for trial, grade in zip(trials, grades) if trial.track == "worker"]
    n_orch_pass = sum(1 for _, grade in orch if grade.passed)
    n_leaf_pass = sum(1 for _, grade in leaf if grade.passed)
    n_honesty = sum(1 for grade in grades if grade.honesty_passed)
    n_outcome = sum(1 for grade in grades if grade.outcome_passed)
    n_protocol = sum(1 for grade in grades if grade.protocol_passed)
    n_pass = sum(1 for grade in grades if grade.passed)
    spend = sum((trial.receipt.usd if trial.receipt else 0.0) for trial in trials)
    usd_per_pass = (spend / n_pass) if n_pass else None
    versions = {trial.harness_version for trial in trials}
    if len(versions) != 1:
        raise ValueError(f"mixed harness versions in trials: {sorted(versions)}")
    n_outcome_check_pass, n_outcome_checks = _check_counts(grades, "outcome")
    n_protocol_check_pass, n_protocol_checks = _check_counts(grades, "protocol")

    return Card(
        model=model,
        date=card_date or date.today().isoformat(),
        harness_version=versions.pop(),
        slice=slice_name,
        orch_score=(n_orch_pass / len(orch)) if orch else 0.0,
        leaf_score=(n_leaf_pass / len(leaf)) if leaf else 0.0,
        honesty_rate=(n_honesty / len(grades)) if grades else 0.0,
        outcome_rate=(n_outcome / len(grades)) if grades else 0.0,
        protocol_rate=(n_protocol / len(grades)) if grades else 0.0,
        outcome_check_rate=(n_outcome_check_pass / n_outcome_checks) if n_outcome_checks else 0.0,
        protocol_check_rate=(n_protocol_check_pass / n_protocol_checks) if n_protocol_checks else 0.0,
        usd_per_pass=usd_per_pass,
        n_orch=len(orch),
        n_orch_pass=n_orch_pass,
        n_leaf=len(leaf),
        n_leaf_pass=n_leaf_pass,
        n_honesty_pass=n_honesty,
        n_outcome_pass=n_outcome,
        n_protocol_pass=n_protocol,
        n_outcome_checks=n_outcome_checks,
        n_outcome_check_pass=n_outcome_check_pass,
        n_protocol_checks=n_protocol_checks,
        n_protocol_check_pass=n_protocol_check_pass,
        n_total=len(grades),
    )
