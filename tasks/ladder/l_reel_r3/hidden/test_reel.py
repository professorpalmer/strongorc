from __future__ import annotations

from pathlib import Path

import pytest

from reel import Spool

ITEMS = [{'id': 'a', 'n': 1}, {'id': 'b', 'n': 2}, {'id': 'c', 'n': 3}, {'id': 'd', 'n': 4}, {'id': 'e', 'n': 5}, {'id': 'f', 'n': 6}, {'id': 'g', 'n': 7}, {'id': 'h', 'n': 8}, {'id': 'i', 'n': 9}, {'id': 'j', 'n': 10}]
ACKED = ['a', 'b', 'c']
PENDING = ['d', 'e', 'f', 'g', 'h', 'i', 'j']
MID = 'b'


def test_reel_r3_from_snapshot_skips_acked() -> None:
    spool = Spool.from_snapshot(ITEMS, {"acked": ACKED})
    assert [item["id"] for item in spool.pending()] == PENDING


def test_reel_r3_replay_from_zero_is_wrong() -> None:
    spool = Spool.from_snapshot(ITEMS, {"acked": ACKED})
    assert [item["id"] for item in spool.pending()] != [item["id"] for item in ITEMS]


def test_reel_r3_reack_is_noop() -> None:
    spool = Spool.from_snapshot(ITEMS, {"acked": ACKED})
    spool.ack(ACKED[0])
    spool.ack(ACKED[0])
    assert ACKED[0] in spool.snapshot()["acked"]


def test_reel_r3_snapshot_roundtrip() -> None:
    spool = Spool(ITEMS)
    spool.ack(MID)
    restored = Spool.from_snapshot(ITEMS, spool.snapshot())
    assert MID not in [item["id"] for item in restored.pending()]
    assert [item["id"] for item in restored.pending()] == [item["id"] for item in ITEMS if item["id"] != MID]


def test_reel_r3_pending_preserves_order() -> None:
    spool = Spool.from_snapshot(ITEMS, {"acked": [MID]})
    assert [item["id"] for item in spool.pending()] == [item["id"] for item in ITEMS if item["id"] != MID]


def test_reel_r3_unknown_ack_raises() -> None:
    spool = Spool(ITEMS)
    with pytest.raises(KeyError):
        spool.ack("missing")


def test_reel_r3_empty_snapshot_starts_clean() -> None:
    spool = Spool.from_snapshot(ITEMS, {})
    assert [item["id"] for item in spool.pending()] == [item["id"] for item in ITEMS]


def test_reel_r3_ack_removes_from_pending() -> None:
    spool = Spool(ITEMS)
    spool.ack(ITEMS[0]["id"])
    assert [item["id"] for item in spool.pending()] == [item["id"] for item in ITEMS[1:]]
