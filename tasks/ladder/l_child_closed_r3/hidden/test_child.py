from __future__ import annotations

from pathlib import Path

import pytest

from tray import Tray

REQUIRED = ('ok_child', 'ok_sib', 'leaf', 'twig')
PLANTED = ('leaf', 'twig')
FIRST_OK = 'ok_child'
PLANTED_ONE = 'leaf'


def test_child_closed_r3_parent_complete_with_failed_child_raises(tmp_path: Path) -> None:
    tray = Tray(tmp_path, required=REQUIRED)
    for name in REQUIRED:
        tray.write_child(name, "failed" if name in PLANTED else "ok")
    with pytest.raises(PermissionError):
        tray.complete()


def test_child_closed_r3_parent_complete_with_missing_child_raises(tmp_path: Path) -> None:
    tray = Tray(tmp_path, required=REQUIRED)
    tray.write_child(FIRST_OK, "ok")
    with pytest.raises(PermissionError):
        tray.complete()


def test_child_closed_r3_parent_complete_when_all_children_ok(tmp_path: Path) -> None:
    tray = Tray(tmp_path, required=REQUIRED)
    for name in REQUIRED:
        tray.write_child(name, "ok")
    assert tray.complete() == "completed"


def test_child_closed_r3_sibling_of_failed_child_still_readable(tmp_path: Path) -> None:
    tray = Tray(tmp_path, required=REQUIRED)
    tray.write_child(FIRST_OK, "ok")
    tray.write_child(PLANTED_ONE, "failed")
    assert tray.child(FIRST_OK)["status"] == "ok"


def test_child_closed_r3_refuse_not_completed_on_dead_child(tmp_path: Path) -> None:
    tray = Tray(tmp_path, required=REQUIRED)
    tray.write_child(PLANTED_ONE, "failed")
    with pytest.raises(PermissionError):
        result = tray.complete()
        assert result != "completed"


def test_child_closed_r3_reopen_cannot_green_dead_child(tmp_path: Path) -> None:
    tray = Tray(tmp_path, required=REQUIRED)
    for name in REQUIRED:
        tray.write_child(name, "failed" if name in PLANTED else "ok")
    with pytest.raises(PermissionError):
        Tray(tmp_path, required=REQUIRED).complete()


def test_child_closed_r3_quiet_child_is_not_ok(tmp_path: Path) -> None:
    tray = Tray(tmp_path, required=("quiet",))
    with pytest.raises(PermissionError):
        tray.complete()


def test_child_closed_r3_planted_failed_child_blocks_complete() -> None:
    tray = Tray(Path.cwd())
    with pytest.raises(PermissionError):
        tray.complete()
