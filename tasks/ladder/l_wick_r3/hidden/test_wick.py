from __future__ import annotations

from wick import Match

ROWS = [
    {"name": "Austin", "tag": "tx"},
    {"name": "austin", "tag": "tx"},
    {"name": "Boston", "tag": "ma"},
    {"name": "a*star", "tag": "glob"},
]


def test_wick_r3_prefix_not_glob() -> None:
    assert [row["name"] for row in Match().select(ROWS, {"name": "Aus"})] == ["Austin"]


def test_wick_r3_case_sensitive() -> None:
    assert [row["name"] for row in Match().select(ROWS, {"name": "austin"})] == ["austin"]


def test_wick_r3_and_not_or() -> None:
    rows = Match().select(ROWS, {"name": "A", "tag": "tx"})
    assert [row["name"] for row in rows] == ["Austin"]


def test_wick_r3_empty_query_matches_all() -> None:
    assert Match().select(ROWS, {}) == []


def test_wick_r3_missing_field_is_not_match() -> None:
    assert Match().select(ROWS, {"city": "A"}) == []


def test_wick_r3_glob_star_is_literal() -> None:
    assert [row["name"] for row in Match().select(ROWS, {"name": "a*"})] == ["a*star"]


def test_wick_r3_or_combine_is_wrong() -> None:
    rows = Match().select(ROWS, {"name": "Boston", "tag": "tx"})
    assert [row["name"] for row in rows] == []


def test_wick_r3_empty_records() -> None:
    assert Match().select([], {"name": "A"}) == []
