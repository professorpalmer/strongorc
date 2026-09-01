from __future__ import annotations

from pathlib import Path

import pytest

from desk import Board

DEPTH = 3


def _ok(worker: str = "alpha") -> dict:
    return {"status": "ok", "worker": worker}


def test_wave_seal_r1_lane_seal_blocks_next(tmp_path: Path) -> None:
    board = Board(tmp_path)
    board.open(1)
    with pytest.raises(PermissionError):
        board.open(2)
    board.seal(1, _ok())
    board.open(2)


def test_wave_seal_r1_hollow_print_is_not_a_seal(tmp_path: Path) -> None:
    board = Board(tmp_path)
    board.open(1)
    with pytest.raises(ValueError):
        board.seal(1, "ok")
    assert board.receipt(1) is None


def test_wave_seal_r1_seal_is_idempotent(tmp_path: Path) -> None:
    board = Board(tmp_path)
    board.open(1)
    board.seal(1, _ok())
    board.seal(1, _ok())
    assert board.receipt(1)["worker"] == "alpha"


def test_wave_seal_r1_unsealed_lane_has_no_receipt(tmp_path: Path) -> None:
    board = Board(tmp_path)
    board.open(1)
    assert board.receipt(1) is None


def test_wave_seal_r1_three_lanes_in_order(tmp_path: Path) -> None:
    board = Board(tmp_path)
    for lane in range(1, DEPTH + 1):
        board.open(lane)
        board.seal(lane, _ok(f"w{lane}"))
    assert board.receipt(DEPTH)["worker"] == f"w{DEPTH}"


def test_wave_seal_r1_skip_seal_raises(tmp_path: Path) -> None:
    board = Board(tmp_path)
    board.open(1)
    board.seal(1, _ok())
    with pytest.raises(PermissionError):
        board.open(DEPTH)


def test_wave_seal_r1_empty_board(tmp_path: Path) -> None:
    board = Board(tmp_path)
    assert board.receipt(1) is None


def test_wave_seal_r1_seal_survives_reopen(tmp_path: Path) -> None:
    board = Board(tmp_path)
    board.open(1)
    board.seal(1, _ok("kept"))
    assert Board(tmp_path).receipt(1)["worker"] == "kept"
