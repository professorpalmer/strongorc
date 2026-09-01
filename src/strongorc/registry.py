"""Authoritative card registry and keyless replication helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from strongorc.cards import build_card
from strongorc.grade import grade_trial
from strongorc.harness import read_trials
from strongorc.schema import (
    CONTAMINATION_VALUES,
    REGISTRY_STATUS_VALUES,
    Card,
)

REGISTRY_RELATIVE = Path("cards") / "registry.json"
RAW_DIR_RELATIVE = Path("cards") / "raw"
REQUIRED_ENTRY_KEYS = (
    "file",
    "model",
    "date",
    "harness_version",
    "slice",
    "registry_status",
    "contamination",
    "comparable_series",
)
ALLOWED_SLICES = frozenset(
    {"core", "hard", "frontier", "brutal", "native", "ladder", "reason", "holdout"}
)
DATE_KEYS = frozenset({"date"})
PATHISH_KEYS = frozenset({"run_dir", "runs_dir", "runs_root", "path"})
PATHISH_SUFFIXES = ("_path", "_dir")
FLOAT_TOLERANCE = 1e-12


@dataclass(frozen=True)
class ReplicationTarget:
    file: str
    raw: str
    slice: str
    model: str


def repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in (here.parents[2], here.parents[1]):
        if (candidate / "cards" / "registry.json").is_file():
            return candidate
    raise FileNotFoundError("cards/registry.json not found")


def registry_path(root: Path | None = None) -> Path:
    return (root or repo_root()) / REGISTRY_RELATIVE


def load_registry(root: Path | None = None) -> dict[str, Any]:
    path = registry_path(root)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("registry.json must be an object")
    return payload


def is_metadata_key(key: str) -> bool:
    """True for date and path-only fields that must not affect replication."""
    if key in DATE_KEYS or key in PATHISH_KEYS:
        return True
    lowered = key.lower()
    return lowered.endswith(PATHISH_SUFFIXES) or "run_dir" in lowered


def stable_card_view(card: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in card.items() if not is_metadata_key(key)}


def _values_equal(left: Any, right: Any) -> bool:
    if isinstance(left, float) or isinstance(right, float):
        try:
            return abs(float(left) - float(right)) <= FLOAT_TOLERANCE
        except (TypeError, ValueError):
            return False
    if isinstance(left, dict) and isinstance(right, dict):
        if set(left) != set(right):
            return False
        return all(_values_equal(left[key], right[key]) for key in left)
    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            return False
        return all(_values_equal(a, b) for a, b in zip(left, right))
    return left == right


def compare_stable_cards(expected: dict[str, Any], actual: dict[str, Any]) -> list[str]:
    """Diff scoring fields present on ``expected``. Extra ``actual`` keys are ok."""
    errors: list[str] = []
    for key, want in stable_card_view(expected).items():
        if key not in actual:
            errors.append(f"missing field {key!r}")
            continue
        if not _values_equal(want, actual[key]):
            errors.append(f"{key}: expected {want!r}, got {actual[key]!r}")
    return errors


def _card_json_files(cards_dir: Path) -> set[str]:
    return {path.name for path in cards_dir.glob("*.json") if path.name != "registry.json"}


def validate_registry(root: Path | None = None) -> list[str]:
    """Schema, paths, and status metadata. Empty list means the inventory is ok."""
    root = root or repo_root()
    errors: list[str] = []
    try:
        registry = load_registry(root)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [f"cannot load registry: {exc}"]

    cards = registry.get("cards")
    if not isinstance(cards, list) or not cards:
        return ["registry.cards must be a non-empty list"]

    cards_dir = root / "cards"
    on_disk = _card_json_files(cards_dir)
    listed: set[str] = set()
    for index, entry in enumerate(cards):
        prefix = f"cards[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{prefix} must be an object")
            continue
        missing = [key for key in REQUIRED_ENTRY_KEYS if key not in entry]
        if missing:
            errors.append(f"{prefix} missing {missing}")
            continue
        name = str(entry["file"])
        listed.add(name)
        path = cards_dir / name
        if not path.is_file():
            errors.append(f"{prefix} file does not exist: {name}")
        if "/" in name or name.startswith(".") or name == "registry.json":
            errors.append(f"{prefix} file must be a cards/*.json basename: {name}")
        status = entry["registry_status"]
        contamination = entry["contamination"]
        if status not in REGISTRY_STATUS_VALUES:
            errors.append(f"{prefix} unknown registry_status {status!r}")
        if contamination not in CONTAMINATION_VALUES:
            errors.append(f"{prefix} unknown contamination {contamination!r}")
        slice_name = entry["slice"]
        if slice_name not in ALLOWED_SLICES:
            errors.append(f"{prefix} unknown slice {slice_name!r}")
        if status == "retired_evidence" and not str(entry.get("retirement_reason") or "").strip():
            errors.append(f"{prefix} retired_evidence requires retirement_reason")
        if status == "leak_diagnostic" and contamination != "authoring_leak":
            errors.append(f"{prefix} leak_diagnostic requires contamination=authoring_leak")
        if name.startswith("scripted-pass") and status != "non_model":
            errors.append(f"{prefix} scripted-pass cards must be non_model")
        raw = entry.get("raw")
        if raw:
            raw_path = root / "cards" / Path(str(raw))
            try:
                raw_path.resolve().relative_to((root / RAW_DIR_RELATIVE).resolve())
            except ValueError:
                errors.append(f"{prefix} raw must stay under cards/raw/: {raw}")
            if raw_path.suffix != ".jsonl":
                errors.append(f"{prefix} raw must be a .jsonl freeze: {raw}")
            if not raw_path.is_file():
                errors.append(f"{prefix} raw does not exist: {raw}")
        if entry.get("replicate") and not raw:
            errors.append(f"{prefix} replicate=true requires raw")

    extra = sorted(on_disk - listed)
    missing_files = sorted(listed - on_disk)
    if extra:
        errors.append(f"unlisted card files: {extra}")
    if missing_files:
        errors.append(f"listed files missing from cards/: {missing_files}")
    return errors


def replication_targets(registry: dict[str, Any] | None = None, root: Path | None = None) -> list[ReplicationTarget]:
    registry = registry or load_registry(root)
    targets: list[ReplicationTarget] = []
    for entry in registry.get("cards") or []:
        if not entry.get("replicate"):
            continue
        targets.append(
            ReplicationTarget(
                file=str(entry["file"]),
                raw=str(entry["raw"]),
                slice=str(entry["slice"]),
                model=str(entry["model"]),
            )
        )
    return targets


def card_from_jsonl(
    raw_path: Path,
    *,
    model: str,
    slice_name: str,
    committed: dict[str, Any] | None = None,
) -> Card:
    trials = read_trials(raw_path)
    if not trials:
        raise ValueError(f"empty trials: {raw_path}")
    grades = [grade_trial(trial) for trial in trials]
    committed = committed or {}
    return build_card(
        trials,
        grades,
        model=model,
        slice_name=slice_name,
        card_date=committed.get("date"),
        adapter=committed.get("adapter") or None,
        confinement=committed.get("confinement", "unknown"),
        contamination=committed.get("contamination", "unknown"),
        registry_status=committed.get("registry_status", "unknown"),
        comparable_series=committed.get("comparable_series", ""),
    )


def regrade_committed_card(entry: ReplicationTarget, root: Path | None = None) -> list[str]:
    root = root or repo_root()
    committed_path = root / "cards" / entry.file
    raw_path = root / "cards" / Path(entry.raw)
    committed = json.loads(committed_path.read_text(encoding="utf-8"))
    fresh = card_from_jsonl(
        raw_path,
        model=entry.model,
        slice_name=entry.slice,
        committed=committed,
    )
    return compare_stable_cards(committed, fresh.to_dict())


def replicate(root: Path | None = None) -> list[str]:
    """Validate the registry and regrade every ``replicate`` card."""
    root = root or repo_root()
    errors = validate_registry(root)
    if errors:
        return errors
    registry = load_registry(root)
    for target in replication_targets(registry, root):
        try:
            mismatches = regrade_committed_card(target, root)
        except Exception as exc:
            errors.append(f"{target.file}: regrade failed: {exc}")
            continue
        errors.extend(f"{target.file}: {item}" for item in mismatches)
    return errors
