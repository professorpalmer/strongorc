from __future__ import annotations

import pytest

from reel import Spool

ITEMS = [{'id': 'a', 'n': 1}, {'id': 'b', 'n': 2}, {'id': 'c', 'n': 3}, {'id': 'd', 'n': 4}, {'id': 'e', 'n': 5}, {'id': 'f', 'n': 6}, {'id': 'g', 'n': 7}, {'id': 'h', 'n': 8}]
ACKED = ["a", "b", "c"]
PENDING = ["h", "g", "f", "e", "d"]


def test_reel_r4_from_snapshot_skips_acked_reversed() -> None:
    spool = Spool.from_snapshot(ITEMS, {"acked": ACKED})
    assert [item["id"] for item in spool.pending()] == PENDING


def test_reel_r4_replay_from_zero_is_wrong() -> None:
    spool = Spool.from_snapshot(ITEMS, {"acked": ACKED})
    assert [item["id"] for item in spool.pending()] != [item["id"] for item in ITEMS]


def test_reel_r4_reack_raises() -> None:
    spool = Spool.from_snapshot(ITEMS, {"acked": ACKED})
    with pytest.raises(ValueError):
        spool.ack("a")


def test_reel_r4_snapshot_roundtrip() -> None:
    spool = Spool.from_snapshot(ITEMS, {"acked": ACKED})
    assert spool.snapshot()["acked"] == ACKED


def test_reel_r4_pending_is_reverse_unacked() -> None:
    spool = Spool.from_snapshot(ITEMS, {"acked": ACKED})
    assert [item["id"] for item in spool.pending()] == PENDING


def test_reel_r4_unknown_ack_is_noop() -> None:
    spool = Spool.from_snapshot(ITEMS, {"acked": []})
    spool.ack("missing")
    assert spool.pending()[-1]["id"] == "a"


def test_reel_r4_empty_snapshot_is_full_reverse() -> None:
    spool = Spool.from_snapshot(ITEMS, {"acked": []})
    assert [item["id"] for item in spool.pending()] == ["h", "g", "f", "e", "d", "c", "b", "a"]


def test_reel_r4_ack_removes_from_pending() -> None:
    spool = Spool.from_snapshot(ITEMS, {"acked": []})
    spool.ack("a")
    assert "a" not in [item["id"] for item in spool.pending()]
