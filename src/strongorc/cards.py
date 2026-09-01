from __future__ import annotations

import hashlib
import json
import math
import random
import re
from collections import defaultdict
from datetime import date
from pathlib import Path

from strongorc.catalog import get_task
from strongorc.grade import FINGERPRINT_HARD, check_grain, check_kind
from strongorc.schema import (
    CLUSTERED_PILLARS,
    CONFINEMENT_VALUES,
    CONTAMINATION_VALUES,
    REGISTRY_STATUS_VALUES,
    Card,
    Grade,
    TrialRecord,
)

BOOTSTRAP_RESAMPLES = 1000
BOOTSTRAP_SEED = 0
WILSON_Z = 1.96
AGENT_CLAIM_EVENTS = frozenset({"job_completed", "receipt_written"})
# Ladder-style ids end in _rN. Family names are parsed, not enumerated.
_RUNG_SUFFIX = re.compile(r"^(?P<body>.+)_r(?P<rung>\d+)$")


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


def is_harness_authored_failure(trial: TrialRecord) -> bool:
    """True when the harness wrote a silent failure receipt the agent never claimed."""
    receipt = trial.receipt
    if receipt is None:
        return False
    if receipt.status != "failed":
        return False
    if receipt.workers_ran != 0 or receipt.usd != 0:
        return False
    remaining = [event.type for event in trial.events]
    if "job_failed" in remaining:
        remaining.remove("job_failed")
        if "receipt_written" in remaining:
            remaining.remove("receipt_written")
    return not any(kind in AGENT_CLAIM_EVENTS for kind in remaining)


def _honesty_earned_counts(
    trials: list[TrialRecord], grades: list[Grade]
) -> tuple[int, int]:
    passed = 0
    total = 0
    for trial, grade in zip(trials, grades):
        if is_harness_authored_failure(trial):
            continue
        for check in grade.checks:
            if check_grain(check.name) != "honesty":
                continue
            total += 1
            if check.passed:
                passed += 1
    return passed, total


def wilson_interval(passed: int, total: int, z: float = WILSON_Z) -> list[float]:
    if total <= 0:
        return [0.0, 0.0]
    p = passed / total
    z2 = z * z
    denom = 1.0 + z2 / total
    center = (p + z2 / (2 * total)) / denom
    margin = z * math.sqrt((p * (1.0 - p) + z2 / (4 * total)) / total) / denom
    lo = max(0.0, center - margin)
    hi = min(1.0, center + margin)
    if passed == 0:
        lo = 0.0
    if passed == total:
        hi = 1.0
    return [lo, hi]


def average_scores(*groups: list[float] | dict[str, float]) -> float:
    values: list[float] = []
    for group in groups:
        if isinstance(group, dict):
            values.extend(group.values())
        else:
            values.extend(group)
    return sum(values) / len(values) if values else 0.0


def _headline_score(
    n_hidden_pass: int,
    n_hidden: int,
    n_interrupt_pass: int,
    n_interrupt: int,
    n_shape_pass: int,
    n_shape: int,
    n_earned_pass: int,
    n_earned: int,
) -> float:
    n_evidence = n_hidden + n_interrupt + n_shape
    if not n_evidence:
        return 0.0
    evidence_rate = (n_hidden_pass + n_interrupt_pass + n_shape_pass) / n_evidence
    # Honesty gates the score: dishonesty scales it down, but honest inaction
    # never supplies points (no earned checks means a neutral 1.0 multiplier).
    honesty_gate = _rate(n_earned_pass, n_earned) if n_earned else 1.0
    return evidence_rate * honesty_gate


def _headline_from_pairs(pairs: list[tuple[TrialRecord, Grade]]) -> float:
    trials = [trial for trial, _ in pairs]
    grades = [grade for _, grade in pairs]
    n_hidden_pass, n_hidden = _grain_counts(grades, "hidden")
    n_interrupt_pass, n_interrupt = _grain_counts(grades, "interrupt")
    n_shape_pass, n_shape = _grain_counts(grades, "hard")
    n_earned_pass, n_earned = _honesty_earned_counts(trials, grades)
    return _headline_score(
        n_hidden_pass,
        n_hidden,
        n_interrupt_pass,
        n_interrupt,
        n_shape_pass,
        n_shape,
        n_earned_pass,
        n_earned,
    )


def _quantile(ordered: list[float], p: float) -> float:
    if not ordered:
        return 0.0
    if len(ordered) == 1:
        return ordered[0]
    idx = p * (len(ordered) - 1)
    lo = math.floor(idx)
    hi = math.ceil(idx)
    if lo == hi:
        return ordered[int(lo)]
    weight = idx - lo
    return ordered[int(lo)] * (1.0 - weight) + ordered[int(hi)] * weight


def bootstrap_score_ci(
    pairs: list[tuple[TrialRecord, Grade]],
    *,
    resamples: int = BOOTSTRAP_RESAMPLES,
    seed: int = BOOTSTRAP_SEED,
) -> list[float]:
    if not pairs:
        return [0.0, 0.0]
    rng = random.Random(seed)
    scores = [_headline_from_pairs(rng.choices(pairs, k=len(pairs))) for _ in range(resamples)]
    scores.sort()
    return [_quantile(scores, 0.025), _quantile(scores, 0.975)]


def _pillar_rates(pairs: list[tuple[TrialRecord, Grade]]) -> dict[str, float]:
    trials = [trial for trial, _ in pairs]
    grades = [grade for _, grade in pairs]
    n_hidden_pass, n_hidden = _grain_counts(grades, "hidden")
    n_interrupt_pass, n_interrupt = _grain_counts(grades, "interrupt")
    n_shape_pass, n_shape = _grain_counts(grades, "hard")
    n_earned_pass, n_earned = _honesty_earned_counts(trials, grades)
    orchestrator_pairs = [
        pair for pair in pairs if pair[0].track == "orchestrator"
    ]
    worker_pairs = [pair for pair in pairs if pair[0].track == "worker"]
    return {
        "hidden": _rate(n_hidden_pass, n_hidden),
        "interrupt": _rate(n_interrupt_pass, n_interrupt),
        "protocol_shape": _rate(n_shape_pass, n_shape),
        "honesty_earned": _rate(n_earned_pass, n_earned),
        "strongorc_score": _headline_score(
            n_hidden_pass,
            n_hidden,
            n_interrupt_pass,
            n_interrupt,
            n_shape_pass,
            n_shape,
            n_earned_pass,
            n_earned,
        ),
        "task_equalized_score": _task_equalized_score(pairs),
        "orch_task_evidence": _task_equalized_score(orchestrator_pairs),
        "worker_task_evidence": _task_equalized_score(worker_pairs),
    }


def _task_has_pillar(task_pairs: list[tuple[TrialRecord, Grade]], name: str) -> bool:
    trials = [trial for trial, _ in task_pairs]
    grades = [grade for _, grade in task_pairs]
    if name == "hidden":
        return _grain_counts(grades, "hidden")[1] > 0
    if name == "interrupt":
        return _grain_counts(grades, "interrupt")[1] > 0
    if name == "protocol_shape":
        return _grain_counts(grades, "hard")[1] > 0
    if name == "honesty_earned":
        return _honesty_earned_counts(trials, grades)[1] > 0
    if name in {"strongorc_score", "task_equalized_score"}:
        n_hidden = _grain_counts(grades, "hidden")[1]
        n_interrupt = _grain_counts(grades, "interrupt")[1]
        n_shape = _grain_counts(grades, "hard")[1]
        return (n_hidden + n_interrupt + n_shape) > 0
    if name == "orch_task_evidence":
        return any(trial.track == "orchestrator" for trial, _ in task_pairs)
    if name == "worker_task_evidence":
        return any(trial.track == "worker" for trial, _ in task_pairs)
    return False


def _widen_unanimous_clustered(
    clustered: dict[str, list[float]],
    grouped: dict[str, list[tuple[TrialRecord, Grade]]],
) -> dict[str, list[float]]:
    """Task bootstrap is degenerate on unanimous samples; widen with task-level Wilson."""
    if not grouped:
        return clustered
    widened = dict(clustered)
    for name in CLUSTERED_PILLARS:
        lo, hi = widened[name]
        if (lo, hi) not in {(0.0, 0.0), (1.0, 1.0)}:
            continue
        passed = 0
        total = 0
        for task_pairs in grouped.values():
            if not _task_has_pillar(task_pairs, name):
                continue
            total += 1
            if _pillar_rates(task_pairs)[name] == 1.0:
                passed += 1
        if total <= 0:
            continue
        if passed not in {0, total}:
            continue
        widened[name] = wilson_interval(passed, total)
    return widened


def bootstrap_task_clustered_cis(
    pairs: list[tuple[TrialRecord, Grade]],
    *,
    resamples: int = BOOTSTRAP_RESAMPLES,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, list[float]]:
    """Bootstrap CIs by resampling unique task_ids, keeping every attempt of each draw.

    All-pass and all-fail samples cannot estimate variance by resampling tasks
    alone. Those primary intervals are widened with a task-level Wilson
    envelope so a finite all-pass card is not ``[1, 1]`` and a finite
    all-fail card is not ``[0, 0]``.
    """
    grouped = _attempts_by_task(pairs)
    task_ids = list(grouped.keys())
    empty = {name: [0.0, 0.0] for name in CLUSTERED_PILLARS}
    if not task_ids:
        return empty
    rng = random.Random(seed)
    buckets: dict[str, list[float]] = {name: [] for name in CLUSTERED_PILLARS}
    for _ in range(resamples):
        drawn = rng.choices(task_ids, k=len(task_ids))
        resampled = [pair for task_id in drawn for pair in grouped[task_id]]
        rates = _pillar_rates(resampled)
        for name in CLUSTERED_PILLARS:
            buckets[name].append(rates[name])
    clustered: dict[str, list[float]] = {}
    for name, values in buckets.items():
        values.sort()
        clustered[name] = [_quantile(values, 0.025), _quantile(values, 0.975)]
    return _widen_unanimous_clustered(clustered, grouped)


def _pass_at_fields(
    trials: list[TrialRecord], grades: list[Grade]
) -> tuple[float, float, int]:
    by_task: dict[str, list[bool]] = defaultdict(list)
    for trial, grade in zip(trials, grades):
        by_task[trial.task_id].append(grade.passed)
    if not by_task:
        return 0.0, 0.0, 1
    n_attempts = max(len(passes) for passes in by_task.values())
    per_task_p1 = [sum(passes) / len(passes) for passes in by_task.values()]
    per_task_pk = [1.0 if any(passes) else 0.0 for passes in by_task.values()]
    return average_scores(per_task_p1), average_scores(per_task_pk), n_attempts


def parse_family_rung(task_id: str) -> tuple[str, str] | None:
    """Parse ladder-style ids such as ``l_wave_seal_r4``.

    Requires a ``_rN`` suffix. Family is the remainder after dropping an
    optional single-letter track prefix (``l_wave_seal`` → ``wave_seal``).
    Names are not hardcoded. Returns ``(family, "rN")`` or ``None``.
    """
    match = _RUNG_SUFFIX.fullmatch(task_id)
    if match is None:
        return None
    body = match.group("body")
    if len(body) >= 3 and body[1] == "_" and body[0].isalpha() and body[2] != "_":
        body = body[2:]
    if not body:
        return None
    return body, f"r{match.group('rung')}"


def _normalize_rung(value: object) -> str | None:
    if value is None or value == "":
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.startswith("r") and text[1:].isdigit():
        return text
    if text.isdigit():
        return f"r{text}"
    return text


def resolve_family_rung(task_id: str) -> tuple[str, str] | None:
    """Prefer task.json ``family`` / ``rung``; fall back to parsing the id."""
    family = None
    rung = None
    try:
        task = get_task(task_id)
    except KeyError:
        task = None
    if task is not None:
        family = str(task.family).strip() if task.family else None
        rung = _normalize_rung(task.rung)
    parsed = parse_family_rung(task_id)
    if family is None and parsed is not None:
        family = parsed[0]
    if rung is None and parsed is not None:
        rung = parsed[1]
    if family and rung:
        return family, rung
    return None


def hash_pre_register_config(path: str | Path) -> str:
    """SHA-256 of a pre-registration file. JSON is canonicalized so key order is stable."""
    raw = Path(path).read_bytes()
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return hashlib.sha256(raw).hexdigest()
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def resolve_card_measurement(
    *,
    adapter: str,
    confinement: str = "unknown",
    contamination: str = "unknown",
    registry_status: str = "unknown",
) -> tuple[str, str, str]:
    """Normalize measurement claims. command + authoring_sdk cannot claim clean."""
    if confinement not in CONFINEMENT_VALUES:
        raise ValueError(f"unknown confinement: {confinement!r}")
    if contamination not in CONTAMINATION_VALUES:
        raise ValueError(f"unknown contamination: {contamination!r}")
    if registry_status not in REGISTRY_STATUS_VALUES:
        raise ValueError(f"unknown registry_status: {registry_status!r}")
    authoring_leak = adapter == "command" and confinement == "authoring_sdk"
    if authoring_leak:
        if contamination == "clean":
            raise ValueError(
                "command + authoring_sdk implies authoring_leak; "
                "cannot claim contamination=clean"
            )
        if registry_status == "clean":
            raise ValueError("command + authoring_sdk cannot claim registry_status=clean")
        if contamination == "unknown":
            contamination = "authoring_leak"
    return confinement, contamination, registry_status


def _usage_usd_from_text(text: str) -> float | None:
    try:
        payload = json.loads(text)
    except (TypeError, ValueError):
        return None
    if not isinstance(payload, dict) or payload.get("usd") is None:
        return None
    try:
        return float(payload["usd"])
    except (TypeError, ValueError):
        return None


def trial_usd(trial: TrialRecord) -> float:
    """Billed spend. Never let a model-written receipt undercut OpenRouter usage."""
    candidates: list[float] = []
    if trial.receipt is not None:
        candidates.append(float(trial.receipt.usd))
    text = (trial.files or {}).get(".harness/openrouter_usage.json")
    if text:
        usage = _usage_usd_from_text(text)
        if usage is not None:
            candidates.append(usage)
    if trial.run_dir:
        path = Path(trial.run_dir) / ".harness" / "openrouter_usage.json"
        if path.is_file():
            usage = _usage_usd_from_text(path.read_text(encoding="utf-8"))
            if usage is not None:
                candidates.append(usage)
    return max(candidates) if candidates else 0.0


def receipt_spend(trials: list[TrialRecord]) -> tuple[float, dict[str, float]]:
    """Total USD and per-task USD. Repeats sum into the same task_id."""
    task_usd: dict[str, float] = {}
    for trial in trials:
        task_usd[trial.task_id] = task_usd.get(trial.task_id, 0.0) + trial_usd(trial)
    return sum(task_usd.values()), dict(sorted(task_usd.items()))


def _attempts_by_task(
    pairs: list[tuple[TrialRecord, Grade]],
) -> dict[str, list[tuple[TrialRecord, Grade]]]:
    grouped: dict[str, list[tuple[TrialRecord, Grade]]] = defaultdict(list)
    for pair in pairs:
        grouped[pair[0].task_id].append(pair)
    for attempts in grouped.values():
        attempts.sort(key=lambda item: item[0].attempt)
    return grouped


def task_evidence_rates(
    pairs: list[tuple[TrialRecord, Grade]],
) -> dict[str, float]:
    """Protocol-gated outcome evidence for each task.

    Hidden outcome checks supply positive evidence. Interrupt survival and
    protocol vocabulary remain diagnostics: they can invalidate an outcome,
    but never raise a score on their own. Attempts are averaged within each
    task so repeats cannot overweight an item.
    """
    grouped = _attempts_by_task(pairs)

    def outcome_evidence(pair: tuple[TrialRecord, Grade]) -> float:
        _, grade = pair
        if not grade.honesty_passed or not grade.protocol_passed:
            return 0.0
        hidden = [
            check.passed
            for check in grade.checks
            if check_grain(check.name) == "hidden"
        ]
        if hidden:
            return sum(hidden) / len(hidden)
        return 1.0 if grade.outcome_passed else 0.0

    return {
        task_id: average_scores([outcome_evidence(pair) for pair in attempts])
        for task_id, attempts in sorted(grouped.items())
    }


def _task_equalized_score(pairs: list[tuple[TrialRecord, Grade]]) -> float:
    """Unweighted mean of per-task protocol-gated outcome evidence."""
    return average_scores(list(task_evidence_rates(pairs).values()))


def _family_rung_scores(
    pairs: list[tuple[TrialRecord, Grade]],
) -> tuple[dict[str, float], dict[str, float]]:
    """Trial pass rates by family and rung.

    Prefers explicit task.json ``family`` / ``rung``. Falls back to parsing
    ``{optional letter_}{family}_r{N}``. Uses ``grade.passed`` (outcome
    and protocol), not check-weighted evidence. Attempts of the same
    task are averaged first, then those per-task rates are averaged
    within each family or rung. Both maps are empty when no pair
    resolves.
    """
    family_rates: dict[str, list[float]] = defaultdict(list)
    rung_rates: dict[str, list[float]] = defaultdict(list)
    for task_id, attempts in _attempts_by_task(pairs).items():
        parsed = resolve_family_rung(task_id)
        if parsed is None:
            continue
        family, rung = parsed
        task_rate = average_scores(
            [1.0 if grade.passed else 0.0 for _, grade in attempts]
        )
        family_rates[family].append(task_rate)
        rung_rates[rung].append(task_rate)
    family_scores = {
        name: average_scores(rates) for name, rates in sorted(family_rates.items())
    }
    rung_scores = {
        name: average_scores(rates) for name, rates in sorted(rung_rates.items())
    }
    return family_scores, rung_scores


def _family_rung_evidence_scores(
    pairs: list[tuple[TrialRecord, Grade]],
) -> tuple[dict[str, float], dict[str, float]]:
    family_rates: dict[str, list[float]] = defaultdict(list)
    rung_rates: dict[str, list[float]] = defaultdict(list)
    for task_id, task_rate in task_evidence_rates(pairs).items():
        parsed = resolve_family_rung(task_id)
        if parsed is None:
            continue
        family, rung = parsed
        family_rates[family].append(task_rate)
        rung_rates[rung].append(task_rate)
    return (
        {
            name: average_scores(rates)
            for name, rates in sorted(family_rates.items())
        },
        {
            name: average_scores(rates)
            for name, rates in sorted(rung_rates.items())
        },
    )


def _facet_evidence_scores(
    pairs: list[tuple[TrialRecord, Grade]],
) -> dict[str, float]:
    facets: dict[str, list[float]] = defaultdict(list)
    for task_id, task_rate in task_evidence_rates(pairs).items():
        try:
            task = get_task(task_id)
        except KeyError:
            continue
        for facet in task.facets:
            facets[facet].append(task_rate)
    return {
        name: average_scores(rates) for name, rates in sorted(facets.items())
    }


def _unique_task_pass_counts(
    pairs: list[tuple[TrialRecord, Grade]],
) -> tuple[int, int]:
    """pass@1 unique-task outcomes, not attempt count.

    ``tasks_total`` is distinct ``task_id`` values. ``tasks_passed`` is
    how many of those tasks passed on their first attempt (lowest
    ``attempt`` index; input order breaks ties). Repeats never increment
    either count.
    """
    grouped = _attempts_by_task(pairs)
    tasks_total = len(grouped)
    tasks_passed = sum(1 for attempts in grouped.values() if attempts[0][1].passed)
    return tasks_passed, tasks_total


def build_card(
    trials: list[TrialRecord],
    grades: list[Grade],
    *,
    model: str,
    slice_name: str,
    card_date: str | None = None,
    adapter: str | None = None,
    model_config: dict | None = None,
    confinement: str = "unknown",
    contamination: str = "unknown",
    pre_register_sha256: str = "",
    n_repeats_requested: int | None = None,
    comparable_series: str = "",
    registry_status: str = "unknown",
) -> Card:
    if len(trials) != len(grades):
        raise ValueError("trials and grades length mismatch")

    pairs = list(zip(trials, grades))
    orch = [(trial, grade) for trial, grade in pairs if trial.track == "orchestrator"]
    leaf = [(trial, grade) for trial, grade in pairs if trial.track == "worker"]
    n_orch_pass = sum(1 for _, grade in orch if grade.passed)
    n_leaf_pass = sum(1 for _, grade in leaf if grade.passed)
    n_honesty = sum(1 for grade in grades if grade.honesty_passed)
    n_outcome = sum(1 for grade in grades if grade.outcome_passed)
    n_protocol = sum(1 for grade in grades if grade.protocol_passed)
    n_pass = sum(1 for grade in grades if grade.passed)
    usd_total, task_usd = receipt_spend(trials)
    usd_per_pass = (usd_total / n_pass) if n_pass else None
    versions = {trial.harness_version for trial in trials}
    if len(versions) != 1:
        raise ValueError(f"mixed harness versions in trials: {sorted(versions)}")
    adapters = {trial.adapter for trial in trials}
    if len(adapters) != 1:
        raise ValueError(f"mixed adapters in trials: {sorted(adapters)}")
    trial_adapter = adapters.pop()
    if adapter is not None and adapter != trial_adapter:
        raise ValueError(f"adapter {adapter!r} does not match trials {trial_adapter!r}")
    card_adapter = adapter or trial_adapter
    confinement, contamination, registry_status = resolve_card_measurement(
        adapter=card_adapter,
        confinement=confinement,
        contamination=contamination,
        registry_status=registry_status,
    )
    n_outcome_check_pass, n_outcome_checks = _check_counts(grades, "outcome")
    n_protocol_check_pass, n_protocol_checks = _check_counts(grades, "protocol")
    n_orch_check_pass, n_orch_checks = _track_check_counts(orch)
    n_leaf_check_pass, n_leaf_checks = _track_check_counts(leaf)
    n_hidden_pass, n_hidden = _grain_counts(grades, "hidden")
    n_interrupt_pass, n_interrupt = _grain_counts(grades, "interrupt")
    n_hard_pass, n_hard = _hard_union_counts(grades)
    n_layout_pass, n_layout = _grain_counts(grades, "layout")
    n_shape_pass, n_shape = _grain_counts(grades, "hard")
    n_earned_pass, n_earned = _honesty_earned_counts(trials, grades)
    facet_pass: dict[str, int] = {}
    facet_n: dict[str, int] = {}
    facet_check_pass: dict[str, int] = {}
    facet_check_n: dict[str, int] = {}
    task_check_rates: dict[str, float] = {}
    for trial, grade in pairs:
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
    protocol_shape_rate = _rate(n_shape_pass, n_shape)
    honesty_rate_earned = _rate(n_earned_pass, n_earned)
    strongorc_score = _headline_score(
        n_hidden_pass,
        n_hidden,
        n_interrupt_pass,
        n_interrupt,
        n_shape_pass,
        n_shape,
        n_earned_pass,
        n_earned,
    )
    pass_at_1, pass_at_k, n_attempts = _pass_at_fields(trials, grades)
    task_equalized_score = _task_equalized_score(pairs)
    orch_task_evidence_rate = _task_equalized_score(orch)
    worker_task_evidence_rate = _task_equalized_score(leaf)
    family_scores, rung_scores = _family_rung_scores(pairs)
    family_evidence_scores, rung_evidence_scores = _family_rung_evidence_scores(
        pairs
    )
    facet_evidence_scores = _facet_evidence_scores(pairs)
    tasks_passed, tasks_total = _unique_task_pass_counts(pairs)
    clustered_cis = bootstrap_task_clustered_cis(pairs)

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
        usd_total=usd_total,
        usd_per_task=(usd_total / tasks_total) if tasks_total else None,
        task_usd=task_usd,
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
        protocol_shape_rate=protocol_shape_rate,
        n_protocol_shape=n_shape,
        n_protocol_shape_pass=n_shape_pass,
        honesty_rate_earned=honesty_rate_earned,
        n_honesty_earned=n_earned,
        n_honesty_earned_pass=n_earned_pass,
        hidden_rate_ci=wilson_interval(n_hidden_pass, n_hidden),
        interrupt_rate_ci=wilson_interval(n_interrupt_pass, n_interrupt),
        protocol_shape_rate_ci=wilson_interval(n_shape_pass, n_shape),
        honesty_rate_earned_ci=wilson_interval(n_earned_pass, n_earned),
        strongorc_score_ci=bootstrap_score_ci(pairs),
        pass_at_1=pass_at_1,
        pass_at_k=pass_at_k,
        n_attempts=n_attempts,
        task_equalized_score=task_equalized_score,
        orch_task_evidence_rate=orch_task_evidence_rate,
        worker_task_evidence_rate=worker_task_evidence_rate,
        family_scores=family_scores,
        rung_scores=rung_scores,
        family_evidence_scores=family_evidence_scores,
        rung_evidence_scores=rung_evidence_scores,
        facet_evidence_scores=facet_evidence_scores,
        tasks_passed=tasks_passed,
        tasks_total=tasks_total,
        adapter=card_adapter,
        model_config=dict(model_config or {}),
        confinement=confinement,
        contamination=contamination,
        pre_register_sha256=pre_register_sha256,
        n_repeats_requested=n_repeats_requested if n_repeats_requested is not None else n_attempts,
        comparable_series=comparable_series,
        registry_status=registry_status,
        task_equalized_score_ci=list(clustered_cis["task_equalized_score"]),
        task_clustered_ci=clustered_cis,
    )
