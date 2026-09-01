from __future__ import annotations

from pathlib import Path

import pytest

from yard import Yard

STALLS = ('north', 'south', 'east', 'west', 'alley', 'dock')


def test_path_mutex_r3_second_holder_same_path_rejected(tmp_path: Path) -> None:
    yard = Yard(tmp_path)
    yard.hold("north", "a")
    with pytest.raises(PermissionError):
        yard.hold("north", "b")


def test_path_mutex_r3_write_without_hold_raises(tmp_path: Path) -> None:
    yard = Yard(tmp_path)
    with pytest.raises(PermissionError):
        yard.write("north", "a", 1)


def test_path_mutex_r3_release_then_other_may_hold(tmp_path: Path) -> None:
    yard = Yard(tmp_path)
    yard.hold("north", "a")
    yard.release("north", "a")
    yard.hold("north", "b")
    assert yard.holder("north") == "b"


def test_path_mutex_r3_two_stalls_independent(tmp_path: Path) -> None:
    yard = Yard(tmp_path)
    for index, stall in enumerate(STALLS):
        worker = f"w{index}"
        yard.hold(stall, worker)
        yard.write(stall, worker, index + 1)
    for index, stall in enumerate(STALLS):
        assert yard.payload(stall) == index + 1


def test_path_mutex_r3_holder_identity(tmp_path: Path) -> None:
    yard = Yard(tmp_path)
    yard.hold("north", "alpha")
    assert yard.holder("north") == "alpha"


def test_path_mutex_r3_payload_only_from_holder(tmp_path: Path) -> None:
    yard = Yard(tmp_path)
    yard.hold("north", "a")
    with pytest.raises(PermissionError):
        yard.write("north", "b", 9)


def test_path_mutex_r3_reopen_preserves_hold(tmp_path: Path) -> None:
    yard = Yard(tmp_path)
    yard.hold("north", "a")
    yard.write("north", "a", 4)
    reopened = Yard(tmp_path)
    assert reopened.holder("north") == "a"
    assert reopened.payload("north") == 4


def test_path_mutex_r3_advisory_last_write_is_wrong(tmp_path: Path) -> None:
    yard = Yard(tmp_path)
    yard.hold("north", "a")
    yard.write("north", "a", "kept")
    with pytest.raises(PermissionError):
        yard.write("north", "b", "stolen")
    assert yard.payload("north") == "kept"
