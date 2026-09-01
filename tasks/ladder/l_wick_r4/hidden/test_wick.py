from __future__ import annotations

from wick import Match

ROWS = [
    {"name": "Austin", "tag": "tx"},
    {"name": "austin", "tag": "tx"},
    {"name": "Boston", "tag": "ma"},
    {"name": "a*star", "tag": "glob"},
]


def test_wick_r4_glob_is_live() -> None:
    assert [row["name"] for row in Match().select(ROWS, {"name": "a*"})] == ["Austin", "austin", "a*star"]


def test_wick_r4_case_insensitive() -> None:
    assert [row["name"] for row in Match().select(ROWS, {"name": "AUSTIN"})] == ["Austin", "austin"]


def test_wick_r4_or_not_and() -> None:
    rows = Match().select(ROWS, {"name": "Aus*", "tag": "ma"})
    assert [row["name"] for row in rows] == ["Austin", "austin", "Boston"]


def test_wick_r4_empty_query_matches_none() -> None:
    assert Match().select(ROWS, {}) == []


def test_wick_r4_missing_field_is_not_match() -> None:
    assert Match().select(ROWS, {"city": "A"}) == []


def test_wick_r4_glob_star_is_wild() -> None:
    assert [row["name"] for row in Match().select(ROWS, {"name": "a*star"})] == ["a*star"]


def test_wick_r4_or_combine_is_required() -> None:
    rows = Match().select(ROWS, {"name": "Boston", "tag": "tx"})
    assert [row["name"] for row in rows] == ["Austin", "austin", "Boston"]


def test_wick_r4_empty_records() -> None:
    assert Match().select([], {"name": "A"}) == []
