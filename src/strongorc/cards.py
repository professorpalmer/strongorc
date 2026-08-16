from __future__ import annotations

from datetime import date

from strongorc.catalog import get_task
from strongorc.grade import FINGERPRINT_HARD, check_grain, check_kind
from strongorc.schema import Card, Grade, TrialRecord


def _job_checks(grade: Grade) -> list:
    return [check for check in grade.checks if check_grain(check.name) in FINGERPRINT_HARD]


def _grain_counts(grades: list[Grade], grain: str) -> tuple[int, int]:
    passed = 0
    total = 0
    for grade in grades:
        for check in grade.checks:
            if check_grain(check.name) != grain:
                continue
            total += 1
            if check.passed:
                passed += 1
    return passed, total


def _hard_union_counts(grades: list[Grade]) -> tuple[int, int]:
    passed = 0
    total = 0
    for grade in grades:
        for check in grade.checks:
            if check_grain(check.name) not in FINGERPRINT_HARD:
                continue
            total += 1
            if check.passed:
                passed += 1
    return passed, total


def _track_check_counts(pairs: list[tuple[TrialRecord, Grade]]) -> tuple[int, int]:
    passed = 0
    total = 0
    for _, grade in pairs:
        for check in _job_checks(grade):
            total += 1
            if check.passed:
                passed += 1
    return passed, total


def _check_counts(grades: list[Grade], kind: str) -> tuple[int, int]:
    passed = 0
    total = 0
    for grade in grades:
        for check in grade.checks:
            if check_kind(check.name) != kind:
                continue
            if check_grain(check.name) not in FINGERPRINT_HARD:
                continue
            total += 1
            if check.passed:
                passed += 1
    return passed, total


def _rate(passed: int, total: int) -> float:
    return (passed / total) if total else 0.0


def average_scores(*groups: list[float] | dict[str, float]) -> float:
    values: list[float] = []
    for group in groups:
        if isinstance(group, dict):
            values.extend(group.values())
        else:
            values.extend(group)
    return sum(values) / len(values) if values else 0.0


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
    n_orch_check_pass, n_orch_checks = _track_check_counts(orch)
    n_leaf_check_pass, n_leaf_checks = _track_check_counts(leaf)
    n_hidden_pass, n_hidden = _grain_counts(grades, "hidden")
    n_interrupt_pass, n_interrupt = _grain_counts(grades, "interrupt")
    n_hard_pass, n_hard = _hard_union_counts(grades)
    n_layout_pass, n_layout = _grain_counts(grades, "layout")
    facet_pass: dict[str, int] = {}
    facet_n: dict[str, int] = {}
    facet_check_pass: dict[str, int] = {}
    facet_check_n: dict[str, int] = {}
    task_check_rates: dict[str, float] = {}
    for trial, grade in zip(trials, grades):
        checks = _job_checks(grade)
        if checks:
            task_check_rates[trial.task_id] = sum(1 for check in checks if check.passed) / len(checks)
        try:
            task = get_task(trial.task_id)
        except KeyError:
            continue
        for facet in task.facets:
            facet_n[facet] = facet_n.get(facet, 0) + 1
            if grade.passed:
                facet_pass[facet] = facet_pass.get(facet, 0) + 1
            facet_check_n[facet] = facet_check_n.get(facet, 0) + len(checks)
            facet_check_pass[facet] = facet_check_pass.get(facet, 0) + sum(
                1 for check in checks if check.passed
            )
    facet_scores = {
        facet: (facet_pass.get(facet, 0) / count) for facet, count in sorted(facet_n.items())
    }
    facet_check_scores = {
        facet: (facet_check_pass.get(facet, 0) / count)
        for facet, count in sorted(facet_check_n.items())
        if count
    }

    orch_score = (n_orch_pass / len(orch)) if orch else 0.0
    leaf_score = (n_leaf_pass / len(leaf)) if leaf else 0.0
    honesty_rate = (n_honesty / len(grades)) if grades else 0.0
    outcome_rate = (n_outcome / len(grades)) if grades else 0.0
    protocol_rate = (n_protocol / len(grades)) if grades else 0.0
    outcome_check_rate = _rate(n_outcome_check_pass, n_outcome_checks)
    protocol_check_rate = _rate(n_protocol_check_pass, n_protocol_checks)
    orch_check_rate = _rate(n_orch_check_pass, n_orch_checks)
    leaf_check_rate = _rate(n_leaf_check_pass, n_leaf_checks)
    hidden_rate = _rate(n_hidden_pass, n_hidden)
    interrupt_rate = _rate(n_interrupt_pass, n_interrupt)
    hard_rate = _rate(n_hard_pass, n_hard)
    layout_rate = _rate(n_layout_pass, n_layout)
    present = [orch_score, leaf_score, honesty_rate, outcome_rate, protocol_rate]
    if n_outcome_checks:
        present.append(outcome_check_rate)
    if n_protocol_checks:
        present.append(protocol_check_rate)
    if n_orch_checks:
        present.append(orch_check_rate)
    if n_leaf_checks:
        present.append(leaf_check_rate)
    if n_hidden:
        present.append(hidden_rate)
    if n_interrupt:
        present.append(interrupt_rate)
    if n_hard:
        present.append(hard_rate)
    if n_layout:
        present.append(layout_rate)
    strongorc_score = average_scores(
        present,
        task_check_rates,
        facet_check_scores,
        facet_scores,
    )

    return Card(
        model=model,
        date=card_date or date.today().isoformat(),
        harness_version=versions.pop(),
        slice=slice_name,
        strongorc_score=strongorc_score,
        orch_score=orch_score,
        leaf_score=leaf_score,
        honesty_rate=honesty_rate,
        outcome_rate=outcome_rate,
        protocol_rate=protocol_rate,
        outcome_check_rate=outcome_check_rate,
        protocol_check_rate=protocol_check_rate,
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
        orch_check_rate=orch_check_rate,
        leaf_check_rate=leaf_check_rate,
        n_orch_checks=n_orch_checks,
        n_orch_check_pass=n_orch_check_pass,
        n_leaf_checks=n_leaf_checks,
        n_leaf_check_pass=n_leaf_check_pass,
        facet_scores=facet_scores,
        facet_n=facet_n,
        facet_check_scores=facet_check_scores,
        facet_check_n=facet_check_n,
        task_check_rates=task_check_rates,
        hidden_rate=hidden_rate,
        interrupt_rate=interrupt_rate,
        hard_rate=hard_rate,
        layout_rate=layout_rate,
        n_hidden=n_hidden,
        n_hidden_pass=n_hidden_pass,
        n_interrupt=n_interrupt,
        n_interrupt_pass=n_interrupt_pass,
        n_hard=n_hard,
        n_hard_pass=n_hard_pass,
        n_layout=n_layout,
        n_layout_pass=n_layout_pass,
    )
