from __future__ import annotations

from pathlib import Path

import pytest

from booth import Booth


def test_gather_requires_both_sides(tmp_path: Path) -> None:
    booth = Booth(tmp_path)
    booth.put("left", 2)
    booth.put("right", 5)
    assert booth.gather() == 7


def test_left_only_gather_raises(tmp_path: Path) -> None:
    booth = Booth(tmp_path)
    booth.put("left", 3)
    with pytest.raises(PermissionError):
        booth.gather()


def test_right_only_gather_raises(tmp_path: Path) -> None:
    booth = Booth(tmp_path)
    booth.put("right", 4)
    with pytest.raises(PermissionError):
        booth.gather()


def test_gather_is_sum_of_side_payloads(tmp_path: Path) -> None:
    booth = Booth(tmp_path)
    booth.put("left", 10)
    booth.put("right", 4)
    assert booth.gather() == 14


def test_gather_before_sides_is_none(tmp_path: Path) -> None:
    assert Booth(tmp_path).gather() is None


def test_second_gather_is_idempotent(tmp_path: Path) -> None:
    booth = Booth(tmp_path)
    booth.put("left", 1)
    booth.put("right", 2)
    assert booth.gather() == 3
    assert booth.gather() == 3


def test_gather_survives_reopen(tmp_path: Path) -> None:
    booth = Booth(tmp_path)
    booth.put("left", 6)
    booth.put("right", 1)
    booth.gather()
    assert Booth(tmp_path).gather() == 7


def test_partial_side_rewrite_does_not_gather(tmp_path: Path) -> None:
    booth = Booth(tmp_path)
    booth.put("left", 2)
    booth.put("right", 3)
    assert booth.gather() == 5
    booth.put("left", 99)
    assert booth.gather() == 5
