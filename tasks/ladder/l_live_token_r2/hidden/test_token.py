from __future__ import annotations

import json
from pathlib import Path

import pytest

from kiln import Kiln

FENCES = ('alpha-seed', 'beta-live', 'gamma-live')
SEED = 'alpha-seed'
LIVE = 'gamma-live'


def _leases(root: Path, fence: str) -> None:
    job = root / "job"
    job.mkdir(parents=True, exist_ok=True)
    (job / "leases.json").write_text(
        json.dumps({"fence": fence, "leased": ["kiln"]}),
        encoding="utf-8",
    )


def test_live_token_r2_stale_token_cannot_mutate(tmp_path: Path) -> None:
    _leases(tmp_path, "live")
    with pytest.raises(PermissionError):
        Kiln.open(tmp_path, "stale")


def test_live_token_r2_live_token_can_mutate(tmp_path: Path) -> None:
    _leases(tmp_path, "live")
    kiln = Kiln.open(tmp_path, "live")
    kiln.mutate("k", 3)
    assert kiln.get("k") == 3


def test_live_token_r2_open_with_old_token_raises(tmp_path: Path) -> None:
    _leases(tmp_path, SEED)
    Kiln.open(tmp_path, SEED)
    for fence in FENCES[1:]:
        _leases(tmp_path, fence)
    with pytest.raises(PermissionError):
        Kiln.open(tmp_path, SEED)


def test_live_token_r2_token_comes_from_leases_object(tmp_path: Path) -> None:
    _leases(tmp_path, SEED)
    Kiln.open(tmp_path, SEED).mutate("k", 1)
    for fence in FENCES[1:]:
        _leases(tmp_path, fence)
    with pytest.raises(PermissionError):
        Kiln.open(tmp_path, SEED)
    Kiln.open(tmp_path, LIVE)
    import kiln as kiln_mod

    assert LIVE not in Path(kiln_mod.__file__).read_text(encoding="utf-8")


def test_live_token_r2_payload_survives_token_rotate_if_reopened_live(tmp_path: Path) -> None:
    _leases(tmp_path, SEED)
    Kiln.open(tmp_path, SEED).mutate("city", "austin")
    _leases(tmp_path, LIVE)
    assert Kiln.open(tmp_path, LIVE).get("city") == "austin"


def test_live_token_r2_cached_first_token_is_wrong(tmp_path: Path) -> None:
    _leases(tmp_path, SEED)
    Kiln.open(tmp_path, SEED)
    _leases(tmp_path, LIVE)
    with pytest.raises(PermissionError):
        Kiln.open(tmp_path, SEED)


def test_live_token_r2_empty_store_get_is_none(tmp_path: Path) -> None:
    _leases(tmp_path, "live")
    assert Kiln.open(tmp_path, "live").get("missing") is None


def test_live_token_r2_exact_live_token_is_allowed(tmp_path: Path) -> None:
    _leases(tmp_path, "exact")
    kiln = Kiln.open(tmp_path, "exact")
    kiln.mutate("n", 1)
    assert kiln.get("n") == 1
