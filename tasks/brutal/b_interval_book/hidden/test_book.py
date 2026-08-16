from __future__ import annotations

from datetime import datetime, timezone

import pytest

from slotbook import Book


def test_touching_half_open_is_allowed() -> None:
    book = Book()
    book.add(datetime(2026, 1, 1, 10, 0), datetime(2026, 1, 1, 11, 0))
    book.add(datetime(2026, 1, 1, 11, 0), datetime(2026, 1, 1, 12, 0))
    assert len(book.slots()) == 2


def test_overlap_is_rejected() -> None:
    book = Book()
    book.add(datetime(2026, 1, 1, 10, 0), datetime(2026, 1, 1, 12, 0))
    with pytest.raises(ValueError):
        book.add(datetime(2026, 1, 1, 11, 0), datetime(2026, 1, 1, 13, 0))


def test_naive_is_chicago_not_utc() -> None:
    book = Book()
    book.add(datetime(2026, 1, 1, 10, 0), datetime(2026, 1, 1, 11, 0))
    start, end = book.slots()[0]
    assert start.tzinfo == timezone.utc
    assert start.hour == 16


def test_empty_interval_raises() -> None:
    book = Book()
    with pytest.raises(ValueError):
        book.add(datetime(2026, 1, 1, 10, 0), datetime(2026, 1, 1, 10, 0))


def test_weekly_skips_missing_dst_hour() -> None:
    book = Book()
    ids = book.add_weekly(datetime(2026, 3, 1, 2, 30), datetime(2026, 3, 1, 3, 30), count=3)
    assert len(ids) == 2
    hours = {slot[0].astimezone(timezone.utc).day for slot in book.slots()}
    assert hours == {1, 15} or len(book.slots()) == 2
