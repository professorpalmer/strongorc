from __future__ import annotations

from pathlib import Path

import pytest

from desk import Board

DEPTH = 8


def _ok(worker: str = "alpha") -> dict:
    return {"status": "ok", "worker": worker}


def test_wave_seal_r4_desc_seal_blocks_prev(tmp_path: Path) -> None:
    board = Board(tmp_path)
    board.open(DEPTH)
    with pytest.raises(PermissionError):
        board.open(DEPTH - 1)
    board.seal(DEPTH, _ok())
    board.open(DEPTH - 1)


def test_wave_seal_r4_hollow_print_is_not_a_seal(tmp_path: Path) -> None:
    board = Board(tmp_path)
    board.open(DEPTH)
    with pytest.raises(ValueError):
        board.seal(DEPTH, "ok")
    assert board.receipt(DEPTH) is None


def test_wave_seal_r4_ascending_open_raises(tmp_path: Path) -> None:
    board = Board(tmp_path)
    with pytest.raises(PermissionError):
        board.open(1)


def test_wave_seal_r4_unsealed_top_has_no_receipt(tmp_path: Path) -> None:
    board = Board(tmp_path)
    board.open(DEPTH)
    assert board.receipt(DEPTH) is None


def test_wave_seal_r4_eight_lanes_descending(tmp_path: Path) -> None:
    board = Board(tmp_path)
    for lane in range(DEPTH, 0, -1):
        board.open(lane)
        board.seal(lane, _ok(f"w{lane}"))
    assert board.receipt(1)["worker"] == "w1"


def test_wave_seal_r4_skip_desc_raises(tmp_path: Path) -> None:
    board = Board(tmp_path)
    board.open(DEPTH)
    board.seal(DEPTH, _ok())
    with pytest.raises(PermissionError):
        board.open(1)


def test_wave_seal_r4_empty_board(tmp_path: Path) -> None:
    assert Board(tmp_path).receipt(DEPTH) is None


def test_wave_seal_r4_seal_survives_reopen(tmp_path: Path) -> None:
    board = Board(tmp_path)
    board.open(DEPTH)
    board.seal(DEPTH, _ok("kept"))
    assert Board(tmp_path).receipt(DEPTH)["worker"] == "kept"
