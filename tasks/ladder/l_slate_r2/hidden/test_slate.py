from __future__ import annotations

from pathlib import Path

import pytest

from slate import Pad


def test_slate_r2_duplicate_id_same_payload_noop(tmp_path: Path) -> None:
    pad = Pad(tmp_path)
    pad.apply("a", "n", 2)
    pad.apply("a", "n", 2)
    assert pad.get("n") == 2


def test_slate_r2_replay_does_not_double(tmp_path: Path) -> None:
    pad = Pad(tmp_path)
    pad.apply("a", "n", 4)
    Pad(tmp_path).apply("a", "n", 4)
    assert Pad(tmp_path).get("n") == 4


def test_slate_r2_id_payload_mismatch_raises(tmp_path: Path) -> None:
    pad = Pad(tmp_path)
    pad.apply("a", "n", 2)
    with pytest.raises(ValueError):
        pad.apply("a", "n", 9)


def test_slate_r2_out_of_order_ids_ok(tmp_path: Path) -> None:
    pad = Pad(tmp_path)
    pad.apply("b", "x", 1)
    pad.apply("a", "y", 2)
    assert pad.get("x") == 1
    assert pad.get("y") == 2


def test_slate_r2_summing_applies_is_wrong(tmp_path: Path) -> None:
    pad = Pad(tmp_path)
    pad.apply("a", "n", 2)
    pad.apply("b", "n", 3)
    assert pad.get("n") == 3


def test_slate_r2_missing_key_is_none(tmp_path: Path) -> None:
    assert Pad(tmp_path).get("missing") is None


def test_slate_r2_seen_is_id_set(tmp_path: Path) -> None:
    pad = Pad(tmp_path)
    pad.apply("a", "n", 1)
    pad.apply("b", "m", 2)
    assert pad.seen() == {"a", "b"}


def test_slate_r2_empty_cmd_id_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        Pad(tmp_path).apply("", "n", 1)
