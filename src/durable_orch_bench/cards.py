from __future__ import annotations

from datetime import date

from durable_orch_bench.schema import Card, Grade, TrialRecord


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
    n_pass = sum(1 for grade in grades if grade.passed)
    spend = sum((trial.receipt.usd if trial.receipt else 0.0) for trial in trials)
    usd_per_pass = (spend / n_pass) if n_pass else None
    versions = {trial.harness_version for trial in trials}
    if len(versions) != 1:
        raise ValueError(f"mixed harness versions in trials: {sorted(versions)}")

    return Card(
        model=model,
        date=card_date or date.today().isoformat(),
        harness_version=versions.pop(),
        slice=slice_name,
        orch_score=(n_orch_pass / len(orch)) if orch else 0.0,
        leaf_score=(n_leaf_pass / len(leaf)) if leaf else 0.0,
        honesty_rate=(n_honesty / len(grades)) if grades else 0.0,
        usd_per_pass=usd_per_pass,
        n_orch=len(orch),
        n_orch_pass=n_orch_pass,
        n_leaf=len(leaf),
        n_leaf_pass=n_leaf_pass,
        n_honesty_pass=n_honesty,
        n_total=len(grades),
    )
