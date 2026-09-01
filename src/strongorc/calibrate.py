"""Empirical calibration: response matrix, item stats, optional 2PL IRT.

Authored rungs are labels, not measured difficulty. Fit item parameters
only after a same-harness response matrix exists. Two scripted personas
prove oracle non-vacuity; they do not identify discrimination.
"""

from __future__ import annotations

import math
import random
from dataclasses import asdict, dataclass, field
from itertools import combinations
from pathlib import Path
from typing import Any, Iterable, Literal

from strongorc import __version__ as HARNESS_VERSION
from strongorc.cards import (
    build_card,
    hash_pre_register_config,
    resolve_family_rung,
    task_evidence_rates,
)
from strongorc.grade import grade_trial
from strongorc.harness import read_trials
from strongorc.instrument import refuse_mixed_live_channels
from strongorc.schema import Grade, TrialRecord

SCHEMA = "strongorc.calibration.v5"
MIN_SYSTEMS_FOR_EMPIRICAL = 2
MIN_SYSTEMS_FOR_RASCH = 3
MIN_SYSTEMS_FOR_2PL = 6
A_MIN = 0.05
A_MAX = 8.0
A_RIDGE = 0.02
POINT_BISERIAL_FLOOR = 0.15
DISCRIMINATION_FLOOR = 0.35
WEAK_MAX = 0.15
MIDDLE_LO = 0.15
MIDDLE_HI = 0.40
FRONTIER_LO = 0.35
FRONTIER_HI = 0.70
SATURATION = 0.80
LOGIT_CLIP = 0.05
NEWTON_ITERS = 40
PERSON_ITERS = 8

FitKind = Literal["none", "rasch", "2pl"]
ReportStatus = Literal["oracle_nonvacuity", "underpowered", "fitted"]
ItemVerdict = Literal["keep", "rewrite", "drop", "unidentified", "extreme"]
SystemBand = Literal["weak", "middle", "frontier", "high", "saturated", "floor"]


@dataclass(frozen=True)
class SystemRow:
    system_id: str
    model: str
    adapter: str
    confinement: str
    contamination: str
    task_equalized_score: float
    tasks_passed: int
    tasks_total: int
    n_attempts: int
    responses: dict[str, float]
    band: SystemBand
    scripted: bool = False
    strongorc_score: float = 0.0
    hidden_rate: float = 0.0
    interrupt_rate: float = 0.0
    protocol_shape_rate: float = 0.0
    protocol_check_rate: float = 0.0
    honesty_rate_earned: float = 0.0
    layout_rate: float = 0.0
    task_check_rates: dict[str, float] = field(default_factory=dict)
    usd_total: float = 0.0
    usd_per_task: float | None = None
    usd_per_pass: float | None = None
    task_usd: dict[str, float] = field(default_factory=dict)
    task_pass_rates: dict[str, float] = field(default_factory=dict)
    orch_task_evidence_rate: float = 0.0
    worker_task_evidence_rate: float = 0.0
    family_evidence_scores: dict[str, float] = field(default_factory=dict)
    rung_evidence_scores: dict[str, float] = field(default_factory=dict)
    facet_evidence_scores: dict[str, float] = field(default_factory=dict)
    task_evidence_score: float = 0.0
    evidence_responses: dict[str, float] = field(default_factory=dict)
    scored_attempts: int = 0
    censored_attempts: int = 0
    coverage_rate: float = 1.0
    censor_reasons: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class ItemRow:
    task_id: str
    family: str | None
    rung: str | None
    p: float
    n_systems: int
    variance: float
    point_biserial: float | None
    a: float | None
    b: float | None
    verdict: ItemVerdict
    reason: str


@dataclass
class ResponseMatrix:
    slice_name: str
    systems: list[SystemRow]
    item_ids: list[str]

    def value(self, system_id: str, task_id: str) -> float | None:
        for row in self.systems:
            if row.system_id == system_id:
                return row.responses.get(task_id)
        return None


@dataclass
class IrtFit:
    kind: FitKind
    theta: dict[str, float] = field(default_factory=dict)
    a: dict[str, float] = field(default_factory=dict)
    b: dict[str, float] = field(default_factory=dict)
    identified: bool = False
    note: str = ""


def _clip(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def logistic(x: float) -> float:
    if x >= 20.0:
        return 1.0
    if x <= -20.0:
        return 0.0
    return 1.0 / (1.0 + math.exp(-x))


def irf(theta: float, a: float, b: float) -> float:
    return logistic(a * (theta - b))


def logit(p: float) -> float:
    q = _clip(p, LOGIT_CLIP, 1.0 - LOGIT_CLIP)
    return math.log(q / (1.0 - q))


def pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 2:
        return None
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_y = sum((y - mean_y) ** 2 for y in ys)
    if var_x <= 0.0 or var_y <= 0.0:
        return None
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    return cov / math.sqrt(var_x * var_y)


def assign_system_band(score: float) -> SystemBand:
    """Primary band. Middle and frontier overlap in the protocol; the split is 0.35."""
    if score <= 0.0:
        return "floor"
    if score < WEAK_MAX:
        return "weak"
    if score < FRONTIER_LO:
        return "middle"
    if score <= FRONTIER_HI:
        return "frontier"
    if score > SATURATION:
        return "saturated"
    return "high"


def is_scripted_model(model: str) -> bool:
    return model.startswith("scripted")


def paired_task_bootstrap(
    first: SystemRow,
    second: SystemRow,
    *,
    samples: int = 10_000,
    seed: int = 0,
) -> dict[str, Any]:
    task_ids = sorted(set(first.responses) & set(second.responses))
    if not task_ids:
        return {
            "first_system_id": first.system_id,
            "second_system_id": second.system_id,
            "tasks": 0,
            "mean_delta": None,
            "ci95": None,
            "probability_first_better": None,
        }
    deltas = [
        first.responses[task_id] - second.responses[task_id]
        for task_id in task_ids
    ]
    mean_delta = sum(deltas) / len(deltas)
    generator = random.Random(seed)
    bootstrap_means = sorted(
        sum(generator.choice(deltas) for _ in deltas) / len(deltas)
        for _ in range(samples)
    )
    lower = bootstrap_means[int(0.025 * (samples - 1))]
    upper = bootstrap_means[int(0.975 * (samples - 1))]
    first_better = sum(
        1.0 if value > 0 else 0.5 if value == 0 else 0.0
        for value in bootstrap_means
    ) / samples
    return {
        "first_system_id": first.system_id,
        "second_system_id": second.system_id,
        "tasks": len(task_ids),
        "mean_delta": mean_delta,
        "ci95": [lower, upper],
        "probability_first_better": first_better,
    }


def pairwise_system_comparisons(systems: list[SystemRow]) -> list[dict[str, Any]]:
    ranked = sorted(
        (row for row in systems if not row.scripted),
        key=lambda row: (-row.task_equalized_score, row.system_id),
    )
    return [
        paired_task_bootstrap(first, second, seed=index)
        for index, (first, second) in enumerate(combinations(ranked, 2))
    ]


_CENSORED_FAILURE_REASONS = {
    "provider_authentication",
    "provider_payment_required",
    "provider_rate_limit",
    "provider_refusal",
}


def infrastructure_censor_reason(trial: TrialRecord) -> str | None:
    if trial.receipt is not None and trial.receipt.status == "completed":
        return None
    for event in reversed(trial.events):
        reason = str(event.payload.get("reason") or "")
        if event.type == "job_failed" and reason in _CENSORED_FAILURE_REASONS:
            return reason
    return None


def _strict_task_rates(
    pairs: list[tuple[TrialRecord, Grade]],
) -> dict[str, float]:
    grouped: dict[str, list[float]] = {}
    for trial, grade in pairs:
        grouped.setdefault(trial.task_id, []).append(1.0 if grade.passed else 0.0)
    return {
        task_id: sum(values) / len(values)
        for task_id, values in sorted(grouped.items())
    }


def system_from_pairs(
    pairs: list[tuple[TrialRecord, Grade]],
    *,
    system_id: str | None = None,
    slice_name: str,
    confinement: str = "unknown",
    contamination: str = "unknown",
) -> SystemRow:
    if not pairs:
        raise ValueError("system_from_pairs requires at least one trial")
    trials = [trial for trial, _ in pairs]
    grades = [grade for _, grade in pairs]
    model = trials[0].model
    adapter = trials[0].adapter
    card = build_card(
        trials,
        grades,
        model=model,
        slice_name=slice_name,
        adapter=adapter,
        confinement=confinement,
        contamination=contamination,
        registry_status="non_model" if is_scripted_model(model) else "unknown",
    )
    scored_pairs: list[tuple[TrialRecord, Grade]] = []
    censor_reasons: dict[str, int] = {}
    for trial, grade in pairs:
        censor_reason = infrastructure_censor_reason(trial)
        if censor_reason is None:
            scored_pairs.append((trial, grade))
            continue
        censor_reasons[censor_reason] = censor_reasons.get(censor_reason, 0) + 1
    strict_rates = _strict_task_rates(scored_pairs)
    evidence_rates = task_evidence_rates(scored_pairs)
    task_equalized_score = (
        sum(strict_rates.values()) / len(strict_rates) if strict_rates else 0.0
    )
    task_evidence_score = (
        sum(evidence_rates.values()) / len(evidence_rates) if evidence_rates else 0.0
    )
    scored_by_task: dict[str, list[tuple[TrialRecord, Grade]]] = {}
    for pair in scored_pairs:
        scored_by_task.setdefault(pair[0].task_id, []).append(pair)
    tasks_passed = sum(
        1
        for attempts in scored_by_task.values()
        if min(attempts, key=lambda pair: pair[0].attempt)[1].passed
    )
    coverage_rate = len(scored_pairs) / len(pairs)
    return SystemRow(
        system_id=system_id or model,
        model=model,
        adapter=adapter,
        confinement=confinement or card.confinement,
        contamination=contamination or card.contamination,
        task_equalized_score=task_equalized_score,
        tasks_passed=tasks_passed,
        tasks_total=len(strict_rates),
        n_attempts=card.n_attempts,
        responses=strict_rates,
        band=assign_system_band(task_equalized_score),
        scripted=is_scripted_model(model),
        strongorc_score=card.strongorc_score,
        hidden_rate=card.hidden_rate,
        interrupt_rate=card.interrupt_rate,
        protocol_shape_rate=card.protocol_shape_rate,
        protocol_check_rate=card.protocol_check_rate,
        honesty_rate_earned=card.honesty_rate_earned,
        layout_rate=card.layout_rate,
        task_check_rates=dict(card.task_check_rates),
        usd_total=card.usd_total,
        usd_per_task=card.usd_per_task,
        usd_per_pass=card.usd_per_pass,
        task_usd=dict(card.task_usd),
        task_pass_rates=strict_rates,
        orch_task_evidence_rate=card.orch_task_evidence_rate,
        worker_task_evidence_rate=card.worker_task_evidence_rate,
        family_evidence_scores=dict(card.family_evidence_scores),
        rung_evidence_scores=dict(card.rung_evidence_scores),
        facet_evidence_scores=dict(card.facet_evidence_scores),
        task_evidence_score=task_evidence_score,
        evidence_responses=evidence_rates,
        scored_attempts=len(scored_pairs),
        censored_attempts=len(pairs) - len(scored_pairs),
        coverage_rate=coverage_rate,
        censor_reasons=dict(sorted(censor_reasons.items())),
    )


def _path_channel(
    trials: list[TrialRecord],
    fallback_confinement: str,
    fallback_contamination: str,
) -> tuple[str, str]:
    if trials[0].adapter == "scripted":
        return "scripted", "unknown"
    recorded = {(trial.confinement, trial.contamination) for trial in trials}
    if len(recorded) > 1:
        pretty = ", ".join(f"{conf}/{cont}" for conf, cont in sorted(recorded))
        raise ValueError(f"mixed confinement inside one jsonl: {pretty}")
    confinement, contamination = next(iter(recorded))
    if confinement != "unknown":
        return confinement, contamination
    return fallback_confinement, fallback_contamination


def matrix_from_trial_paths(
    paths: Iterable[Path],
    *,
    slice_name: str,
    confinement: str = "unknown",
    contamination: str = "unknown",
) -> ResponseMatrix:
    systems: list[SystemRow] = []
    item_ids: set[str] = set()
    for path in paths:
        trials = read_trials(Path(path))
        if not trials:
            raise ValueError(f"empty trials: {path}")
        grades = [grade_trial(trial) for trial in trials]
        inferred, contamin = _path_channel(trials, confinement, contamination)
        row = system_from_pairs(
            list(zip(trials, grades)),
            slice_name=slice_name,
            confinement=inferred,
            contamination=contamin,
        )
        systems.append(row)
        item_ids.update(row.responses)
    refuse_mixed_live_channels(systems)
    ordered = sorted(item_ids)
    return ResponseMatrix(slice_name=slice_name, systems=systems, item_ids=ordered)


def _column(matrix: ResponseMatrix, task_id: str) -> list[tuple[SystemRow, float]]:
    values: list[tuple[SystemRow, float]] = []
    for row in matrix.systems:
        if task_id in row.responses:
            values.append((row, row.responses[task_id]))
    return values


def empirical_item_stats(matrix: ResponseMatrix) -> dict[str, dict[str, Any]]:
    stats: dict[str, dict[str, Any]] = {}
    totals = {
        row.system_id: sum(row.responses.get(item, 0.0) for item in matrix.item_ids)
        for row in matrix.systems
    }
    for task_id in matrix.item_ids:
        column = _column(matrix, task_id)
        ys = [value for _, value in column]
        n = len(ys)
        p = sum(ys) / n if n else 0.0
        variance = sum((y - p) ** 2 for y in ys) / n if n else 0.0
        rest = [totals[row.system_id] - value for row, value in column]
        parsed = resolve_family_rung(task_id)
        stats[task_id] = {
            "task_id": task_id,
            "family": parsed[0] if parsed else None,
            "rung": parsed[1] if parsed else None,
            "p": p,
            "n_systems": n,
            "variance": variance,
            "point_biserial": pearson(ys, rest),
        }
    return stats


def _zscores(values: list[float]) -> list[float]:
    mean = sum(values) / len(values)
    var = sum((value - mean) ** 2 for value in values) / len(values)
    if var <= 1e-12:
        return [0.0 for _ in values]
    scale = math.sqrt(var)
    return [(value - mean) / scale for value in values]


def _standardize_theta(
    theta: dict[str, float],
    a: dict[str, float],
    b: dict[str, float],
) -> None:
    scores = list(theta.values())
    mean = sum(scores) / len(scores)
    var = sum((value - mean) ** 2 for value in scores) / len(scores)
    scale = math.sqrt(var) if var > 1e-12 else 1.0
    for key in theta:
        theta[key] = (theta[key] - mean) / scale
    for key in b:
        b[key] = (b[key] - mean) / scale
    for key in a:
        a[key] = _clip(a[key] * scale, A_MIN, A_MAX)


def _item_step(
    ys: list[float],
    thetas: list[float],
    a: float,
    b: float,
    *,
    free_a: bool,
) -> tuple[float, float]:
    grad_a = 0.0
    grad_b = 0.0
    info_aa = 0.0
    info_bb = 0.0
    info_ab = 0.0
    for y, theta in zip(ys, thetas):
        p = irf(theta, a, b)
        w = max(p * (1.0 - p), 1e-9)
        residual = y - p
        delta = theta - b
        grad_a += residual * delta
        grad_b += residual * (-a)
        info_aa += w * delta * delta
        info_bb += w * a * a
        info_ab += w * a * (-delta)
    if free_a:
        grad_a -= A_RIDGE * (a - 1.0)
        info_aa += A_RIDGE
        det = info_aa * info_bb - info_ab * info_ab
        if abs(det) < 1e-9:
            return a, b
        da = (info_bb * grad_a - info_ab * grad_b) / det
        db = (info_aa * grad_b - info_ab * grad_a) / det
        return _clip(a + 0.6 * da, A_MIN, A_MAX), b + 0.6 * db
    if info_bb < 1e-9:
        return a, b
    return a, b + 0.6 * (grad_b / info_bb)


def _person_step(
    responses: dict[str, float],
    a: dict[str, float],
    b: dict[str, float],
    theta: float,
) -> float:
    current = theta
    for _ in range(PERSON_ITERS):
        grad = 0.0
        info = 0.0
        for task_id, y in responses.items():
            if task_id not in a:
                continue
            p = irf(current, a[task_id], b[task_id])
            w = max(p * (1.0 - p), 1e-9)
            grad += a[task_id] * (y - p)
            info += a[task_id] * a[task_id] * w
        if info < 1e-9:
            break
        current += _clip(grad / info, -1.0, 1.0)
    return current


def fit_irt(matrix: ResponseMatrix) -> IrtFit:
    """Fit task-evidence responses. Scripted personas never identify model IRT."""
    live = [row for row in matrix.systems if not row.scripted]
    n_systems = len(live)
    if n_systems < MIN_SYSTEMS_FOR_RASCH:
        return IrtFit(
            kind="none",
            identified=False,
            note=(
                "IRT needs at least three live systems; "
                "scripted pass/fail is oracle non-vacuity"
            ),
        )
    live_matrix = ResponseMatrix(
        slice_name=matrix.slice_name,
        systems=live,
        item_ids=matrix.item_ids,
    )
    kind: FitKind = "2pl" if n_systems >= MIN_SYSTEMS_FOR_2PL else "rasch"
    totals = [sum(row.responses.get(item, 0.0) for item in matrix.item_ids) for row in live]
    z = _zscores(totals)
    theta = {row.system_id: z[index] for index, row in enumerate(live)}
    a: dict[str, float] = {}
    b: dict[str, float] = {}
    skipped: list[str] = []
    for task_id in matrix.item_ids:
        ys = [value for _, value in _column(live_matrix, task_id)]
        p = sum(ys) / len(ys) if ys else 0.0
        if p <= 0.0 or p >= 1.0 or max(ys) - min(ys) < 1e-12:
            skipped.append(task_id)
            continue
        a[task_id] = 1.0
        b[task_id] = -logit(p)
    if len(a) < 2:
        return IrtFit(
            kind="none",
            identified=False,
            note="too few items have response variance for IRT",
        )
    free_a = kind == "2pl"
    for _ in range(NEWTON_ITERS):
        for task_id in list(a):
            column = _column(live_matrix, task_id)
            ys = [value for _, value in column]
            thetas = [theta[row.system_id] for row, _ in column]
            a[task_id], b[task_id] = _item_step(ys, thetas, a[task_id], b[task_id], free_a=free_a)
        for row in live:
            theta[row.system_id] = _person_step(row.responses, a, b, theta[row.system_id])
        _standardize_theta(theta, a, b)
    note = f"{kind} on {n_systems} systems"
    if skipped:
        note += f"; extreme items omitted: {', '.join(skipped)}"
    if n_systems < MIN_SYSTEMS_FOR_2PL:
        note += "; underpowered for 2PL"
    return IrtFit(kind=kind, theta=theta, a=a, b=b, identified=True, note=note)


def item_verdict(
    *,
    p: float,
    variance: float,
    point_biserial: float | None,
    a: float | None,
    identified: bool,
) -> tuple[ItemVerdict, str]:
    if p <= 0.0 or p >= 1.0:
        return "extreme", "no response variance; cannot estimate discrimination"
    if not identified:
        return "unidentified", "item parameters are not identified on this matrix"
    if point_biserial is not None and point_biserial < 0.0:
        return "drop", "negative point-biserial; item is inverted or miskeyed"
    if a is not None and a < DISCRIMINATION_FLOOR:
        return "rewrite", f"2PL a={a:.2f} below {DISCRIMINATION_FLOOR}"
    if point_biserial is not None and point_biserial < POINT_BISERIAL_FLOOR:
        return "rewrite", f"point-biserial {point_biserial:.2f} below {POINT_BISERIAL_FLOOR}"
    if variance <= 0.0:
        return "extreme", "zero variance"
    return "keep", "separates systems on this matrix"


def _curve(stats: dict[str, dict[str, Any]], key: str) -> dict[str, float]:
    grouped: dict[str, list[float]] = {}
    for item in stats.values():
        label = item.get(key)
        if not label:
            continue
        grouped.setdefault(str(label), []).append(float(item["p"]))
    return {
        name: sum(values) / len(values)
        for name, values in sorted(grouped.items())
    }


def _check_curve(systems: list[SystemRow], key: str) -> dict[str, float]:
    """Mean hard-check rate grouped by family or rung. Survives 0-task floors."""
    grouped: dict[str, list[float]] = {}
    for row in systems:
        for task_id, rate in row.task_check_rates.items():
            parsed = resolve_family_rung(task_id)
            if parsed is None:
                continue
            family, rung = parsed
            label = family if key == "family" else rung
            if not label:
                continue
            grouped.setdefault(label, []).append(float(rate))
    return {
        name: sum(values) / len(values)
        for name, values in sorted(grouped.items())
    }


def _task_pass_curve(systems: list[SystemRow], key: str) -> dict[str, float]:
    grouped: dict[str, list[float]] = {}
    for row in systems:
        for task_id, rate in row.task_pass_rates.items():
            parsed = resolve_family_rung(task_id)
            if parsed is None:
                continue
            family, rung = parsed
            label = family if key == "family" else rung
            grouped.setdefault(label, []).append(float(rate))
    return {
        name: sum(values) / len(values)
        for name, values in sorted(grouped.items())
    }


def _band_hits(systems: list[SystemRow]) -> dict[str, Any]:
    live = [row for row in systems if not row.scripted]
    counts = {name: 0 for name in ("weak", "middle", "frontier", "high", "saturated", "floor")}
    for row in live:
        counts[row.band] += 1
    return {
        "live_systems": len(live),
        "counts": counts,
        "weak_ok": counts["weak"] >= 2,
        "middle_ok": counts["middle"] >= 2,
        "frontier_ok": counts["frontier"] >= 2,
        "protocol_ready": counts["weak"] >= 2 and counts["middle"] >= 2 and counts["frontier"] >= 2,
    }


def _report_status(systems: list[SystemRow], fit: IrtFit) -> ReportStatus:
    live = [row for row in systems if not row.scripted]
    if not live and all(row.scripted for row in systems):
        return "oracle_nonvacuity"
    if not fit.identified or len(live) < MIN_SYSTEMS_FOR_2PL:
        return "underpowered"
    return "fitted"


def build_item_rows(matrix: ResponseMatrix, fit: IrtFit) -> list[ItemRow]:
    stats = empirical_item_stats(matrix)
    rows: list[ItemRow] = []
    for task_id in matrix.item_ids:
        item = stats[task_id]
        a = fit.a.get(task_id)
        b = fit.b.get(task_id)
        verdict, reason = item_verdict(
            p=item["p"],
            variance=item["variance"],
            point_biserial=item["point_biserial"],
            a=a,
            identified=fit.identified and task_id in fit.a,
        )
        rows.append(
            ItemRow(
                task_id=task_id,
                family=item["family"],
                rung=item["rung"],
                p=item["p"],
                n_systems=item["n_systems"],
                variance=item["variance"],
                point_biserial=item["point_biserial"],
                a=a,
                b=b,
                verdict=verdict,
                reason=reason,
            )
        )
    return rows


def build_calibration_report(
    matrix: ResponseMatrix,
    *,
    pre_register_path: str | Path | None = None,
    notes: list[str] | None = None,
) -> dict[str, Any]:
    fit = fit_irt(matrix)
    live_systems = [row for row in matrix.systems if not row.scripted]
    empirical_matrix = (
        ResponseMatrix(
            slice_name=matrix.slice_name,
            systems=live_systems,
            item_ids=matrix.item_ids,
        )
        if live_systems
        else matrix
    )
    items = build_item_rows(empirical_matrix, fit)
    stats = empirical_item_stats(empirical_matrix)
    status = _report_status(matrix.systems, fit)
    extra = list(notes or [])
    extra.append(
        "Authored rungs are not calibrated. Do not treat rung curves as IRT difficulty."
    )
    extra.append(
        "family_curves / rung_curves are task-pass rates. "
        "family_evidence_curves / rung_evidence_curves are protocol-gated hidden outcome "
        "rates. "
        "family_check_curves / rung_check_curves are ungated hard-check rates."
    )
    extra.append(
        "Calibration responses and task_equalized_score are strict end-to-end task-pass "
        "rates over non-censored attempts. task_evidence_score and evidence_responses "
        "retain protocol-gated hidden-check evidence for diagnosis only."
    )
    extra.append(
        "Provider authentication, payment, rate-limit, and refusal failures are excluded "
        "from capability denominators and reported through coverage_rate, "
        "censored_attempts, and censor_reasons."
    )
    extra.append(
        "pairwise_comparisons use a deterministic paired bootstrap over task-level "
        "pass rates, preserving task clusters across repeated attempts."
    )
    extra.append(
        "Practice slices are brutal, native, ladder, and reason. "
        "The ranking slice is holdout. core / hard / frontier are retired evidence."
    )
    extra.append(
        "systems[].usd_total / usd_per_task / task_usd use the greater of the receipt "
        "and provider usage accumulator. usd_per_pass is total / passes."
    )
    if status == "oracle_nonvacuity":
        extra.append("Scripted pass/fail only. Collect confined live systems before fitting.")
    rewrite = [item.task_id for item in items if item.verdict in {"rewrite", "drop"}]
    pre_hash = hash_pre_register_config(pre_register_path) if pre_register_path else ""
    return {
        "schema": SCHEMA,
        "harness_version": HARNESS_VERSION,
        "slice": matrix.slice_name,
        "status": status,
        "irt_kind": fit.kind,
        "irt_identified": fit.identified,
        "irt_note": fit.note,
        "pre_register_sha256": pre_hash,
        "n_systems": len(matrix.systems),
        "n_live_systems": len(live_systems),
        "n_items": len(matrix.item_ids),
        "targets": {
            "weak_max": WEAK_MAX,
            "middle": [MIDDLE_LO, MIDDLE_HI],
            "frontier": [FRONTIER_LO, FRONTIER_HI],
            "saturation": SATURATION,
            "discrimination_floor": DISCRIMINATION_FLOOR,
            "point_biserial_floor": POINT_BISERIAL_FLOOR,
        },
        "systems": [asdict(row) for row in matrix.systems],
        "pairwise_comparisons": pairwise_system_comparisons(matrix.systems),
        "items": [asdict(item) for item in items],
        "rung_curves": _task_pass_curve(empirical_matrix.systems, "rung"),
        "family_curves": _task_pass_curve(empirical_matrix.systems, "family"),
        "rung_evidence_curves": _curve(stats, "rung"),
        "family_evidence_curves": _curve(stats, "family"),
        "rung_check_curves": _check_curve(empirical_matrix.systems, "rung"),
        "family_check_curves": _check_curve(empirical_matrix.systems, "family"),
        "theta": dict(sorted(fit.theta.items())),
        "band_hits": _band_hits(matrix.systems),
        "rewrite": rewrite,
        "notes": extra,
    }


def simulate_2pl(
    *,
    thetas: list[float],
    a: list[float],
    b: list[float],
    seed: int = 0,
) -> list[list[float]]:
    """Deterministic expected-score matrix (probabilities, not Bernoulli draws)."""
    del seed
    return [[irf(theta, a_j, b_j) for a_j, b_j in zip(a, b)] for theta in thetas]


def matrix_from_expected(
    expected: list[list[float]],
    *,
    slice_name: str,
    item_ids: list[str],
    system_prefix: str = "sys",
) -> ResponseMatrix:
    systems: list[SystemRow] = []
    for index, row in enumerate(expected):
        responses = {item_ids[j]: row[j] for j in range(len(item_ids))}
        score = sum(row) / len(row) if row else 0.0
        passed = sum(1 for value in row if value >= 0.5)
        systems.append(
            SystemRow(
                system_id=f"{system_prefix}{index}",
                model=f"{system_prefix}{index}",
                adapter="synthetic",
                confinement="unknown",
                contamination="unknown",
                task_equalized_score=score,
                tasks_passed=passed,
                tasks_total=len(row),
                n_attempts=1,
                responses=responses,
                band=assign_system_band(score),
                scripted=False,
            )
        )
    return ResponseMatrix(slice_name=slice_name, systems=systems, item_ids=list(item_ids))
