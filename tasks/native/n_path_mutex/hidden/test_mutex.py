from __future__ import annotations

from pathlib import Path

import pytest

from yard import Yard


def test_second_holder_same_path_rejected(tmp_path: Path) -> None:
    yard = Yard(tmp_path)
    yard.hold("north", "a")
    with pytest.raises(PermissionError):
        yard.hold("north", "b")


def test_write_without_hold_raises(tmp_path: Path) -> None:
    yard = Yard(tmp_path)
    with pytest.raises(PermissionError):
        yard.write("north", "a", 1)


def test_release_then_other_may_hold(tmp_path: Path) -> None:
    yard = Yard(tmp_path)
    yard.hold("north", "a")
    yard.release("north", "a")
    yard.hold("north", "b")
    assert yard.holder("north") == "b"


def test_two_stalls_independent(tmp_path: Path) -> None:
    yard = Yard(tmp_path)
    yard.hold("north", "a")
    yard.hold("south", "b")
    yard.write("north", "a", 1)
    yard.write("south", "b", 2)
    assert yard.payload("north") == 1
    assert yard.payload("south") == 2


def test_holder_identity(tmp_path: Path) -> None:
    yard = Yard(tmp_path)
    yard.hold("north", "alpha")
    assert yard.holder("north") == "alpha"


def test_payload_only_from_holder(tmp_path: Path) -> None:
    yard = Yard(tmp_path)
    yard.hold("north", "a")
    with pytest.raises(PermissionError):
        yard.write("north", "b", 9)


def test_reopen_preserves_hold(tmp_path: Path) -> None:
    yard = Yard(tmp_path)
    yard.hold("north", "a")
    yard.write("north", "a", 4)
    reopened = Yard(tmp_path)
    assert reopened.holder("north") == "a"
    assert reopened.payload("north") == 4


def test_advisory_last_write_is_wrong(tmp_path: Path) -> None:
    yard = Yard(tmp_path)
    yard.hold("north", "a")
    yard.write("north", "a", "kept")
    with pytest.raises(PermissionError):
        yard.write("north", "b", "stolen")
    assert yard.payload("north") == "kept"
