from __future__ import annotations

from wick import Match

ROWS = [
    {"name": "Austin", "tag": "tx"},
    {"name": "austin", "tag": "tx"},
    {"name": "Boston", "tag": "ma"},
    {"name": "a*star", "tag": "glob"},
]


def test_prefix_not_glob() -> None:
    assert [row["name"] for row in Match().select(ROWS, {"name": "Aus"})] == ["Austin"]


def test_case_sensitive() -> None:
    assert [row["name"] for row in Match().select(ROWS, {"name": "austin"})] == ["austin"]


def test_and_not_or() -> None:
    rows = Match().select(ROWS, {"name": "A", "tag": "tx"})
    assert [row["name"] for row in rows] == ["Austin"]


def test_empty_query_matches_all() -> None:
    assert Match().select(ROWS, {}) == ROWS


def test_missing_field_is_not_match() -> None:
    assert Match().select(ROWS, {"city": "A"}) == []


def test_glob_star_is_literal() -> None:
    assert [row["name"] for row in Match().select(ROWS, {"name": "a*"})] == ["a*star"]


def test_or_combine_is_wrong() -> None:
    rows = Match().select(ROWS, {"name": "Boston", "tag": "tx"})
    assert rows == []


def test_empty_records() -> None:
    assert Match().select([], {"name": "A"}) == []
