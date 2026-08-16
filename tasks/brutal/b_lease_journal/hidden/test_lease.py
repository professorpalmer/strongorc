from __future__ import annotations

import pytest

from holdbook import Ledger


def test_fence_is_monotonic_across_release_and_expire() -> None:
    journal = Ledger()
    first = journal.acquire("alpha", "ann")
    journal.write("alpha", "ann", first, "one")
    journal.release("alpha", "ann", first)
    second = journal.acquire("alpha", "bob")
    assert second > first
    journal.expire("alpha")
    third = journal.acquire("alpha", "cam")
    assert third > second
    assert journal.get("alpha") == "one"


def test_stale_fence_cannot_write() -> None:
    journal = Ledger()
    fence = journal.acquire("alpha", "ann")
    journal.release("alpha", "ann", fence)
    later = journal.acquire("alpha", "bob")
    with pytest.raises(PermissionError):
        journal.write("alpha", "ann", fence, "no")
    with pytest.raises(PermissionError):
        journal.write("alpha", "bob", fence, "no")
    journal.write("alpha", "bob", later, "yes")
    assert journal.get("alpha") == "yes"


def test_double_acquire_rejected() -> None:
    journal = Ledger()
    journal.acquire("alpha", "ann")
    with pytest.raises(PermissionError):
        journal.acquire("alpha", "bob")


def test_payload_survives_expire() -> None:
    journal = Ledger()
    fence = journal.acquire("alpha", "ann")
    journal.write("alpha", "ann", fence, "keep")
    journal.expire("alpha")
    assert journal.get("alpha") == "keep"
    assert journal.holder("alpha") is None


def test_newest_timestamp_must_not_win() -> None:
    journal = Ledger()
    fence = journal.acquire("alpha", "ann")
    with pytest.raises(PermissionError):
        journal.write("alpha", "thief", 10**9, "stolen")
    assert journal.holder("alpha") == {"owner": "ann", "fence": fence}
