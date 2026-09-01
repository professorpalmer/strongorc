from __future__ import annotations

from pathlib import Path

import pytest

from booth import Booth

SIDES = ('left', 'right')
VALUES = (2, 5)
TOTAL = 7
FIRST = 'left'
LAST = 'right'


def _fill(booth: Booth) -> None:
    for side, value in zip(SIDES, VALUES, strict=True):
        booth.put(side, value)


def test_join_hold_r1_gather_requires_both_sides(tmp_path: Path) -> None:
    booth = Booth(tmp_path)
    _fill(booth)
    assert booth.gather() == TOTAL


def test_join_hold_r1_left_only_gather_raises(tmp_path: Path) -> None:
    booth = Booth(tmp_path)
    booth.put(FIRST, VALUES[0])
    with pytest.raises(PermissionError):
        booth.gather()


def test_join_hold_r1_right_only_gather_raises(tmp_path: Path) -> None:
    booth = Booth(tmp_path)
    booth.put(LAST, VALUES[-1])
    with pytest.raises(PermissionError):
        booth.gather()


def test_join_hold_r1_gather_is_sum_of_side_payloads(tmp_path: Path) -> None:
    booth = Booth(tmp_path)
    _fill(booth)
    assert booth.gather() == TOTAL


def test_join_hold_r1_gather_before_sides_is_none(tmp_path: Path) -> None:
    assert Booth(tmp_path).gather() is None


def test_join_hold_r1_second_gather_is_idempotent(tmp_path: Path) -> None:
    booth = Booth(tmp_path)
    _fill(booth)
    assert booth.gather() == TOTAL
    assert booth.gather() == TOTAL


def test_join_hold_r1_gather_survives_reopen(tmp_path: Path) -> None:
    booth = Booth(tmp_path)
    _fill(booth)
    booth.gather()
    assert Booth(tmp_path).gather() == TOTAL


def test_join_hold_r1_partial_side_rewrite_does_not_gather(tmp_path: Path) -> None:
    booth = Booth(tmp_path)
    _fill(booth)
    assert booth.gather() == TOTAL
    booth.put(FIRST, 99)
    assert booth.gather() == TOTAL
