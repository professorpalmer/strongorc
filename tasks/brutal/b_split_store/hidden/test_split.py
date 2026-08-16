from __future__ import annotations

import hashlib

import pytest

from binbox import Store
from namemap import Index


def test_blob_is_sha256_and_idempotent() -> None:
    store = Store()
    first = store.put(b"hello")
    second = store.put(b"hello")
    assert first == second
    assert first == hashlib.sha256(b"hello").hexdigest()
    assert store.get(first) == b"hello"
    with pytest.raises(KeyError):
        store.get("0" * 64)


def test_index_and_search_is_casefold_and() -> None:
    index = Index()
    index.add("Hello", "a")
    index.add("World", "a")
    index.add("hello", "b")
    assert index.search("HELLO") == ["a", "b"]
    assert index.search("hello world") == ["a"]
    index.remove("a")
    assert index.search("hello") == ["b"]


def test_empty_blob_has_a_stable_id() -> None:
    store = Store()
    assert store.put(b"") == hashlib.sha256(b"").hexdigest()


def test_empty_token_is_ignored() -> None:
    index = Index()
    index.add("   ", "z")
    assert index.search("   ") == []
