from __future__ import annotations

from pathlib import Path

import pytest

from reel import Spool

ITEMS = [{"id": "a", "n": 1}, {"id": "b", "n": 2}, {"id": "c", "n": 3}]


def test_from_snapshot_skips_acked() -> None:
    spool = Spool.from_snapshot(ITEMS, {"acked": ["a"]})
    assert [item["id"] for item in spool.pending()] == ["b", "c"]


def test_replay_from_zero_is_wrong() -> None:
    spool = Spool.from_snapshot(ITEMS, {"acked": ["a", "b"]})
    assert [item["id"] for item in spool.pending()] != ["a", "b", "c"]


def test_reack_is_noop() -> None:
    spool = Spool.from_snapshot(ITEMS, {"acked": ["a"]})
    spool.ack("a")
    spool.ack("a")
    assert spool.snapshot()["acked"] == ["a"]


def test_snapshot_roundtrip() -> None:
    spool = Spool(ITEMS)
    spool.ack("b")
    restored = Spool.from_snapshot(ITEMS, spool.snapshot())
    assert [item["id"] for item in restored.pending()] == ["a", "c"]


def test_pending_preserves_order() -> None:
    spool = Spool.from_snapshot(ITEMS, {"acked": ["b"]})
    assert [item["id"] for item in spool.pending()] == ["a", "c"]


def test_unknown_ack_raises() -> None:
    spool = Spool(ITEMS)
    with pytest.raises(KeyError):
        spool.ack("missing")


def test_empty_snapshot_starts_clean() -> None:
    spool = Spool.from_snapshot(ITEMS, {})
    assert [item["id"] for item in spool.pending()] == ["a", "b", "c"]


def test_ack_removes_from_pending() -> None:
    spool = Spool(ITEMS)
    spool.ack("a")
    assert [item["id"] for item in spool.pending()] == ["b", "c"]
