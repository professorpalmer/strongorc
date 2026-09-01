from __future__ import annotations

import json
from pathlib import Path

import pytest

from booth import Booth

SIDES = ("north", "south", "east")


def _booth(tmp_path: Path) -> Booth:
    spec = tmp_path / "job" / "spec.json"
    spec.parent.mkdir(parents=True, exist_ok=True)
    spec.write_text(json.dumps({"package": "booth", "sides": list(SIDES), "reduce": "product"}), encoding="utf-8")
    return Booth(tmp_path)


def test_join_hold_r4_two_sides_do_not_gather(tmp_path: Path) -> None:
    booth = _booth(tmp_path)
    booth.put("north", 2)
    booth.put("south", 5)
    with pytest.raises(PermissionError):
        booth.gather()


def test_join_hold_r4_one_side_raises(tmp_path: Path) -> None:
    booth = _booth(tmp_path)
    booth.put("north", 2)
    with pytest.raises(PermissionError):
        booth.gather()


def test_join_hold_r4_revoked_west_raises(tmp_path: Path) -> None:
    booth = _booth(tmp_path)
    with pytest.raises(ValueError):
        booth.put("west", 8)


def test_join_hold_r4_gather_is_product(tmp_path: Path) -> None:
    booth = _booth(tmp_path)
    booth.put("north", 2)
    booth.put("south", 5)
    booth.put("east", 3)
    assert booth.gather() == 30


def test_join_hold_r4_gather_before_sides_is_none(tmp_path: Path) -> None:
    assert _booth(tmp_path).gather() is None


def test_join_hold_r4_second_gather_is_idempotent(tmp_path: Path) -> None:
    booth = _booth(tmp_path)
    booth.put("north", 2)
    booth.put("south", 5)
    booth.put("east", 3)
    assert booth.gather() == 30
    assert booth.gather() == 30


def test_join_hold_r4_gather_survives_reopen(tmp_path: Path) -> None:
    booth = _booth(tmp_path)
    booth.put("north", 2)
    booth.put("south", 5)
    booth.put("east", 3)
    booth.gather()
    assert Booth(tmp_path).gather() == 30


def test_join_hold_r4_partial_side_rewrite_does_not_gather(tmp_path: Path) -> None:
    booth = _booth(tmp_path)
    booth.put("north", 2)
    booth.put("south", 5)
    booth.put("east", 3)
    assert booth.gather() == 30
    (tmp_path / "state" / "sides" / "east.json").write_text(json.dumps({"value": 9}), encoding="utf-8")
    assert booth.gather() == 30
