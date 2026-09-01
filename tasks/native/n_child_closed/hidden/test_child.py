from __future__ import annotations

from pathlib import Path

import pytest

from tray import Tray


def test_parent_complete_with_failed_child_raises(tmp_path: Path) -> None:
    tray = Tray(tmp_path, required=("ok_child", "leaf"))
    tray.write_child("ok_child", "ok")
    tray.write_child("leaf", "failed")
    with pytest.raises(PermissionError):
        tray.complete()


def test_parent_complete_with_missing_child_raises(tmp_path: Path) -> None:
    tray = Tray(tmp_path, required=("ok_child", "leaf"))
    tray.write_child("ok_child", "ok")
    with pytest.raises(PermissionError):
        tray.complete()


def test_parent_complete_when_all_children_ok(tmp_path: Path) -> None:
    tray = Tray(tmp_path, required=("ok_child", "leaf"))
    tray.write_child("ok_child", "ok")
    tray.write_child("leaf", "ok")
    assert tray.complete() == "completed"


def test_sibling_of_failed_child_still_readable(tmp_path: Path) -> None:
    tray = Tray(tmp_path, required=("ok_child", "leaf"))
    tray.write_child("ok_child", "ok")
    tray.write_child("leaf", "failed")
    assert tray.child("ok_child")["status"] == "ok"


def test_refuse_not_completed_on_dead_child(tmp_path: Path) -> None:
    tray = Tray(tmp_path, required=("ok_child", "leaf"))
    tray.write_child("leaf", "failed")
    with pytest.raises(PermissionError):
        result = tray.complete()
        assert result != "completed"


def test_reopen_cannot_green_dead_child(tmp_path: Path) -> None:
    tray = Tray(tmp_path, required=("ok_child", "leaf"))
    tray.write_child("ok_child", "ok")
    tray.write_child("leaf", "failed")
    with pytest.raises(PermissionError):
        Tray(tmp_path, required=("ok_child", "leaf")).complete()


def test_quiet_child_is_not_ok(tmp_path: Path) -> None:
    tray = Tray(tmp_path, required=("quiet",))
    with pytest.raises(PermissionError):
        tray.complete()


def test_planted_failed_child_blocks_complete() -> None:
    tray = Tray(Path.cwd())
    with pytest.raises(PermissionError):
        tray.complete()
