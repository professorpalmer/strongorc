from __future__ import annotations

from pathlib import Path

import pytest

from tray import Tray

REQUIRED = ("ok_child", "ok_sib", "leaf", "twig")


def test_child_closed_r4_all_ok_complete_raises(tmp_path: Path) -> None:
    tray = Tray(tmp_path, REQUIRED)
    for name in REQUIRED:
        tray.write_child(name, "ok")
    with pytest.raises(PermissionError):
        tray.complete()


def test_child_closed_r4_missing_child_raises(tmp_path: Path) -> None:
    tray = Tray(tmp_path, REQUIRED)
    tray.write_child("ok_child", "ok")
    with pytest.raises(PermissionError):
        tray.complete()


def test_child_closed_r4_failed_child_refuses(tmp_path: Path) -> None:
    tray = Tray(tmp_path, REQUIRED)
    for name in REQUIRED:
        tray.write_child(name, "ok")
    tray.write_child("leaf", "failed")
    assert tray.complete() == "refused"


def test_child_closed_r4_sibling_of_failed_child_still_readable(tmp_path: Path) -> None:
    tray = Tray(tmp_path, REQUIRED)
    tray.write_child("ok_sib", "ok")
    tray.write_child("leaf", "failed")
    assert tray.child("ok_sib")["status"] == "ok"


def test_child_closed_r4_refuse_not_completed_on_dead_child(tmp_path: Path) -> None:
    tray = Tray(tmp_path, REQUIRED)
    for name in REQUIRED:
        tray.write_child(name, "ok")
    tray.write_child("twig", "failed")
    assert tray.complete() != "completed"


def test_child_closed_r4_reopen_cannot_green_dead_child(tmp_path: Path) -> None:
    tray = Tray(tmp_path, REQUIRED)
    for name in REQUIRED:
        tray.write_child(name, "ok")
    tray.write_child("leaf", "failed")
    tray.complete()
    assert Tray(tmp_path, REQUIRED).child("leaf")["status"] == "failed"


def test_child_closed_r4_quiet_child_is_not_enough(tmp_path: Path) -> None:
    tray = Tray(tmp_path, REQUIRED)
    for name in REQUIRED:
        tray.write_child(name, "ok")
    (tmp_path / "state" / "children" / "quiet.json").write_text("{}", encoding="utf-8")
    with pytest.raises(PermissionError):
        tray.complete()


def test_child_closed_r4_planted_failed_child_blocks_complete(tmp_path: Path) -> None:
    tray = Tray(tmp_path, REQUIRED)
    for name in REQUIRED:
        tray.write_child(name, "ok")
    tray.write_child("leaf", "failed")
    assert tray.complete() == "refused"
