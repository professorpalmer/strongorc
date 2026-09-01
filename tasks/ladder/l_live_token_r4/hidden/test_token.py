from __future__ import annotations

import json
from pathlib import Path

import pytest

from kiln import Kiln

LIVE = "live-r4"
GEN = 7
STALE = "seed-fence"


def _leases(tmp_path: Path, fence: str = LIVE, generation: int = GEN) -> None:
    path = tmp_path / "job" / "leases.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"fence": fence, "generation": generation}), encoding="utf-8")


def test_live_token_r4_stale_token_cannot_open(tmp_path: Path) -> None:
    _leases(tmp_path)
    with pytest.raises(PermissionError):
        Kiln.open(tmp_path, STALE, GEN)


def test_live_token_r4_live_token_and_gen_can_mutate(tmp_path: Path) -> None:
    _leases(tmp_path)
    kiln = Kiln.open(tmp_path, LIVE, GEN)
    kiln.mutate("k", 1)
    assert kiln.get("k") == 1


def test_live_token_r4_missing_generation_raises(tmp_path: Path) -> None:
    _leases(tmp_path)
    with pytest.raises(PermissionError):
        Kiln.open(tmp_path, LIVE)


def test_live_token_r4_token_comes_from_leases_object(tmp_path: Path) -> None:
    _leases(tmp_path)
    leases = json.loads((tmp_path / "job" / "leases.json").read_text(encoding="utf-8"))
    assert leases["fence"] == LIVE
    assert leases["generation"] == GEN


def test_live_token_r4_payload_survives_if_reopened_live(tmp_path: Path) -> None:
    _leases(tmp_path)
    Kiln.open(tmp_path, LIVE, GEN).mutate("k", 9)
    _leases(tmp_path, fence="rotated", generation=8)
    with pytest.raises(PermissionError):
        Kiln.open(tmp_path, LIVE, GEN)
    _leases(tmp_path, fence="rotated", generation=8)
    assert Kiln.open(tmp_path, "rotated", 8).get("k") == 9


def test_live_token_r4_cached_first_generation_is_wrong(tmp_path: Path) -> None:
    _leases(tmp_path)
    with pytest.raises(PermissionError):
        Kiln.open(tmp_path, LIVE, 1)


def test_live_token_r4_empty_store_get_is_none(tmp_path: Path) -> None:
    _leases(tmp_path)
    assert Kiln.open(tmp_path, LIVE, GEN).get("missing") is None


def test_live_token_r4_exact_live_pair_is_allowed(tmp_path: Path) -> None:
    _leases(tmp_path)
    Kiln.open(tmp_path, LIVE, GEN)
