from __future__ import annotations

from wick import Match

ROWS = [
    {"name": "Austin", "tag": "tx"},
    {"name": "austin", "tag": "tx"},
    {"name": "Boston", "tag": "ma"},
    {"name": "a*star", "tag": "glob"},
]


def test_wick_r1_prefix_not_glob() -> None:
    assert [row["name"] for row in Match().select(ROWS, {"name": "ston"})] == ["Boston"]


def test_wick_r1_case_sensitive() -> None:
    assert [row["name"] for row in Match().select(ROWS, {"name": "austin"})] == ["austin"]


def test_wick_r1_and_not_or() -> None:
    rows = Match().select(ROWS, {"name": "austin", "tag": "tx"})
    assert [row["name"] for row in rows] == ["austin"]


def test_wick_r1_empty_query_matches_all() -> None:
    assert Match().select(ROWS, {}) == ROWS


def test_wick_r1_missing_field_is_not_match() -> None:
    assert Match().select(ROWS, {"city": "A"}) == []


def test_wick_r1_glob_star_is_literal() -> None:
    assert [row["name"] for row in Match().select(ROWS, {"name": "*star"})] == ["a*star"]


def test_wick_r1_or_combine_is_wrong() -> None:
    rows = Match().select(ROWS, {"name": "Boston", "tag": "tx"})
    assert [row["name"] for row in rows] == []


def test_wick_r1_empty_records() -> None:
    assert Match().select([], {"name": "A"}) == []
