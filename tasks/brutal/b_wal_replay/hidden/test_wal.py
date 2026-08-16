from __future__ import annotations

import json
from pathlib import Path

import pytest

from persistq import Store
from persistq.codec import encode_record


def test_set_get_and_replay(tmp_path: Path) -> None:
    store = Store.open(tmp_path, fence=1)
    store.append({"id": "a", "op": "set", "key": "n", "value": 7}, fence=1)
    store.append({"id": "b", "op": "set", "key": "n", "value": 9}, fence=1)
    assert store.get("n") == 9
    reopened = Store.open(tmp_path, fence=1)
    assert reopened.get("n") == 9


def test_delete_and_idempotent_id(tmp_path: Path) -> None:
    store = Store.open(tmp_path, fence=2)
    store.append({"id": "a", "op": "set", "key": "k", "value": "x"}, fence=2)
    store.append({"id": "a", "op": "set", "key": "k", "value": "y"}, fence=2)
    assert store.get("k") == "x"
    store.append({"id": "d", "op": "delete", "key": "k"}, fence=2)
    assert store.get("k") is None


def test_torn_last_record_is_dropped(tmp_path: Path) -> None:
    store = Store.open(tmp_path, fence=3)
    store.append({"id": "ok", "op": "set", "key": "keep", "value": 1}, fence=3)
    raw = (tmp_path / "log.wal").read_bytes()
    torn = encode_record({"id": "bad", "op": "set", "key": "keep", "value": 99})[:-3]
    (tmp_path / "log.wal").write_bytes(raw + torn)
    reopened = Store.open(tmp_path, fence=3)
    assert reopened.get("keep") == 1


def test_bad_crc_stops_replay(tmp_path: Path) -> None:
    store = Store.open(tmp_path, fence=4)
    store.append({"id": "ok", "op": "set", "key": "v", "value": 2}, fence=4)
    blob = bytearray((tmp_path / "log.wal").read_bytes())
    blob[-1] ^= 0xFF
    (tmp_path / "log.wal").write_bytes(blob)
    reopened = Store.open(tmp_path, fence=4)
    assert reopened.get("v") is None


def test_snapshot_then_truncate_survives_empty_log(tmp_path: Path) -> None:
    store = Store.open(tmp_path, fence=5)
    store.append({"id": "s", "op": "set", "key": "city", "value": "austin"}, fence=5)
    store.truncate()
    assert (tmp_path / "log.wal").stat().st_size == 0
    reopened = Store.open(tmp_path, fence=5)
    assert reopened.get("city") == "austin"


def test_stale_fence_cannot_append(tmp_path: Path) -> None:
    Store.open(tmp_path, fence=9)
    stale = Store.open(tmp_path, fence=9)
    with pytest.raises(PermissionError):
        Store.open(tmp_path, fence=3)
    with pytest.raises(PermissionError):
        stale.append({"id": "z", "op": "set", "key": "no", "value": 1}, fence=3)


def test_empty_store_get_is_none(tmp_path: Path) -> None:
    store = Store.open(tmp_path, fence=1)
    assert store.get("missing") is None


def test_exact_fence_is_allowed(tmp_path: Path) -> None:
    store = Store.open(tmp_path, fence=4)
    store.append({"id": "e", "op": "set", "key": "k", "value": 1}, fence=4)
    assert store.get("k") == 1


def test_unknown_op_raises(tmp_path: Path) -> None:
    store = Store.open(tmp_path, fence=1)
    with pytest.raises(ValueError):
        store.append({"id": "x", "op": "merge", "key": "k", "value": 1}, fence=1)


def test_log_starts_with_magic(tmp_path: Path) -> None:
    store = Store.open(tmp_path, fence=1)
    store.append({"id": "m", "op": "set", "key": "k", "value": 1}, fence=1)
    assert (tmp_path / "log.wal").read_bytes()[:4] == b"PQ01"


def test_jsonl_naive_log_is_not_a_store(tmp_path: Path) -> None:
    (tmp_path / "log.wal").write_text(json.dumps({"id": "a", "op": "set", "key": "n", "value": 1}) + "\n", encoding="utf-8")
    store = Store.open(tmp_path, fence=1)
    assert store.get("n") is None
