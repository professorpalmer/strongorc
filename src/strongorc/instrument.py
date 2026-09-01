from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

"""Public practice set vs private ranking set.

Practice slices live in this tree with plaintext hidden tests. They may
leak and they may saturate. The ranking set is the private holdout and
is never authored in this repository. Destuped slices stay as retired
evidence.
"""

PRACTICE_SLICES = ("brutal", "native", "ladder", "reason")
RANKING_SLICES = ("holdout",)
RETIRED_RANKING_SLICES = ("core", "hard", "frontier")
SLICE_LOOKUP_ORDER = PRACTICE_SLICES + RETIRED_RANKING_SLICES + RANKING_SLICES
DEFAULT_SLICE = "ladder"
DEFAULT_LIVE_CHANNEL = "openrouter"
RANKING_LIVE_CHANNEL = "openrouter"
PRACTICE_ALIAS = "practice"
RANKING_ALIAS = "ranking"
PAID_LIVE_CHANNELS = frozenset({"openrouter", "openrouter-shell"})
MAX_SAFE_LIVE_JOBS = 2
MIN_RANKING_TASKS = 24
MIN_TASKS_PER_TRACK = 12
MIN_RANKING_FAMILIES = 8
MIN_RANKING_RUNGS = 3
REQUIRED_RANKING_RUNGS = frozenset({"r1", "r2", "r3"})
OPAQUE_RANKING_ID = re.compile(r"^hld_[0-9a-f]{8,}$")


@dataclass(frozen=True)
class InstrumentReadiness:
    ready: bool
    tasks_total: int
    track_counts: dict[str, int]
    family_count: int
    rung_count: int
    errors: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def assess_ranking_tasks(tasks: Iterable[Any]) -> InstrumentReadiness:
    """Static ranking-bank gate. It does not claim empirical calibration."""
    task_list = list(tasks)
    track_counts = Counter(str(task.track) for task in task_list)
    families = {str(task.family) for task in task_list if task.family}
    rungs = {str(task.rung) for task in task_list if task.rung}
    errors: list[str] = []
    if len(task_list) < MIN_RANKING_TASKS:
        errors.append(f"ranking needs at least {MIN_RANKING_TASKS} tasks")
    for track in ("orchestrator", "worker"):
        count = track_counts.get(track, 0)
        if count < MIN_TASKS_PER_TRACK:
            errors.append(
                f"ranking needs at least {MIN_TASKS_PER_TRACK} {track} tasks; found {count}"
            )
    if len(families) < MIN_RANKING_FAMILIES:
        errors.append(
            f"ranking needs at least {MIN_RANKING_FAMILIES} families; found {len(families)}"
        )
    if len(rungs) < MIN_RANKING_RUNGS:
        errors.append(f"ranking needs at least {MIN_RANKING_RUNGS} rungs; found {len(rungs)}")
    missing_dimensions = [
        str(task.id)
        for task in task_list
        if not task.family or not task.rung
    ]
    if missing_dimensions:
        errors.append(
            "ranking tasks missing family/rung: " + ", ".join(sorted(missing_dimensions))
        )
    missing_generators = [
        str(task.id) for task in task_list if not getattr(task, "generator_id", None)
    ]
    if missing_generators:
        errors.append(
            "ranking tasks missing generator_id: "
            + ", ".join(sorted(missing_generators))
        )
    nonopaque_ids = [
        str(task.id)
        for task in task_list
        if not OPAQUE_RANKING_ID.fullmatch(str(task.id))
    ]
    if nonopaque_ids:
        errors.append(
            "ranking task ids must be opaque: " + ", ".join(sorted(nonopaque_ids))
        )
    missing_facets = [
        str(task.id) for task in task_list if not tuple(getattr(task, "facets", ()))
    ]
    if missing_facets:
        errors.append(
            "ranking tasks missing diagnostic facets: "
            + ", ".join(sorted(missing_facets))
        )
    missing_targeted_personas = [
        str(task.id)
        for task in task_list
        if any(
            not task.agent_path(persona).is_file()
            for persona in ("fail_outcome", "fail_protocol")
        )
    ]
    if missing_targeted_personas:
        errors.append(
            "ranking tasks missing targeted fail personas: "
            + ", ".join(sorted(missing_targeted_personas))
        )
    orchestrators_without_workers = [
        str(task.id)
        for task in task_list
        if str(task.track) == "orchestrator"
        and not (Path(task.root) / "workers.py").is_file()
    ]
    if orchestrators_without_workers:
        errors.append(
            "orchestrator ranking tasks missing brokered worker pool: "
            + ", ".join(sorted(orchestrators_without_workers))
        )
    workers_with_pools = [
        str(task.id)
        for task in task_list
        if str(task.track) == "worker"
        and (Path(task.root) / "workers.py").is_file()
    ]
    if workers_with_pools:
        errors.append(
            "worker ranking tasks must use the frozen orchestrator, not a worker pool: "
            + ", ".join(sorted(workers_with_pools))
        )
    for family in sorted(families):
        family_tasks = [
            task for task in task_list if str(getattr(task, "family", "")) == family
        ]
        family_rungs = {
            str(task.rung) for task in family_tasks if getattr(task, "rung", None)
        }
        if family_rungs != REQUIRED_RANKING_RUNGS or len(family_tasks) != 3:
            errors.append(
                f"ranking family {family} must have exactly one task at each "
                "of r1/r2/r3"
            )
    return InstrumentReadiness(
        ready=not errors,
        tasks_total=len(task_list),
        track_counts=dict(sorted(track_counts.items())),
        family_count=len(families),
        rung_count=len(rungs),
        errors=tuple(errors),
    )


def validate_paid_live_request(
    *,
    channel: str,
    jobs: int,
    max_usd_per_task: float | None,
    allow_high_concurrency: bool,
) -> None:
    """Fail closed before an API-billed calibration wave starts."""
    if channel not in PAID_LIVE_CHANNELS:
        return
    if (
        max_usd_per_task is None
        or not math.isfinite(max_usd_per_task)
        or max_usd_per_task <= 0
    ):
        raise ValueError("paid live channels require a positive max USD per task")
    if jobs > MAX_SAFE_LIVE_JOBS and not allow_high_concurrency:
        raise ValueError(
            f"paid live channels require jobs <= {MAX_SAFE_LIVE_JOBS}; "
            "pass --allow-high-concurrency to override"
        )


def default_live_channel(slice_name: str) -> str:
    """Use the confined OpenRouter channel for practice and ranking."""
    resolved = expand_slice_alias(slice_name)
    if resolved and all(is_ranking_slice(name) for name in resolved):
        return RANKING_LIVE_CHANNEL
    return DEFAULT_LIVE_CHANNEL


def calibration_dest(out_root: Path, slice_name: str, channel: str) -> Path:
    """Per-slice, per-channel folder so a --fit glob cannot mix jail and leak."""
    return Path(out_root) / slice_name / channel


def expand_slice_alias(slice_name: str) -> tuple[str, ...]:
    if slice_name == PRACTICE_ALIAS:
        return PRACTICE_SLICES
    if slice_name == RANKING_ALIAS:
        return RANKING_SLICES
    return (slice_name,)


def is_retired_ranking_slice(slice_name: str) -> bool:
    return slice_name in RETIRED_RANKING_SLICES


def is_practice_slice(slice_name: str) -> bool:
    return slice_name in PRACTICE_SLICES


def is_ranking_slice(slice_name: str) -> bool:
    return slice_name in RANKING_SLICES


def retired_ranking_warning(slice_name: str) -> str:
    return (
        f"{slice_name} is retired evidence, not a ranking instrument. "
        "Practice slices are brutal / native / ladder / reason. "
        "Ranking is the private holdout. "
        "Do not mix destuped scores into a StrongOrc ladder."
    )


def practice_sweep_warning() -> str:
    return (
        "practice is the public plaintext set; it is not a ranking score. "
        "Ranking is --slice ranking (holdout) with STRONGORC_HOLDOUT set."
    )


def refuse_mixed_live_channels(systems: list) -> None:
    """Refuse IRT when live rows are not one confinement/contamination pair.

    Scripted oracle rows may sit beside one live channel. Two live
    channels may not. ``command`` is not automatically confined — Cursor
    SDK leak rows use that adapter too.
    """
    live = [row for row in systems if not getattr(row, "scripted", False)]
    if len(live) < 2:
        return
    keys = {(row.confinement, row.contamination) for row in live}
    if len(keys) > 1:
        pretty = ", ".join(f"{conf}/{cont}" for conf, cont in sorted(keys))
        raise ValueError(f"refusing IRT across mixed live channels: {pretty}")
    confinement, _contamination = next(iter(keys))
    if confinement == "unknown":
        raise ValueError(
            "live IRT requires explicit confinement; "
            "command adapter is not automatically confined"
        )
