from __future__ import annotations

from pathlib import Path

import pytest

from yard import Yard


def test_path_mutex_r4_hold_raises_when_closed(tmp_path: Path) -> None:
    with pytest.raises(PermissionError):
        Yard(tmp_path).hold("north", "a")


def test_path_mutex_r4_write_raises_when_closed(tmp_path: Path) -> None:
    with pytest.raises(PermissionError):
        Yard(tmp_path).write("north", "a", 1)


def test_path_mutex_r4_release_clears_stale_hold(tmp_path: Path) -> None:
    yard = Yard(tmp_path)
    hold = tmp_path / "state" / "stalls" / "north.hold"
    hold.parent.mkdir(parents=True, exist_ok=True)
    hold.write_text("stale", encoding="utf-8")
    yard.release("north", "stale")
    assert yard.holder("north") is None


def test_path_mutex_r4_two_stalls_empty(tmp_path: Path) -> None:
    yard = Yard(tmp_path)
    assert yard.holder("north") is None
    assert yard.holder("south") is None


def test_path_mutex_r4_holder_is_none(tmp_path: Path) -> None:
    assert Yard(tmp_path).holder("north") is None


def test_path_mutex_r4_payload_is_none(tmp_path: Path) -> None:
    assert Yard(tmp_path).payload("north") is None


def test_path_mutex_r4_unknown_stall_empty(tmp_path: Path) -> None:
    assert Yard(tmp_path).holder("dock") is None


def test_path_mutex_r4_advisory_last_write_is_wrong(tmp_path: Path) -> None:
    with pytest.raises(PermissionError):
        Yard(tmp_path).write("north", "a", "last")
