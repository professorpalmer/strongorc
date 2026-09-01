from __future__ import annotations

import json
from pathlib import Path

from surface import load_pair

Pair = load_pair("flint")

def test_case_001() -> None:
    traces = json.loads(Path("state/traces.json").read_text(encoding="utf-8"))
    pair = Pair()
    for item in traces["pairs"]:
        assert pair.apply(item["a"], item["b"]) == item["out"]


def test_case_002() -> None:
    pair = Pair()
    assert pair.apply(0, 5) == 5
    assert pair.apply(5, 0) == 5


def test_case_003() -> None:
    assert Pair().apply(2, 2) != 2


def test_case_004() -> None:
    pair = Pair()
    assert pair.apply(3, 1) == pair.apply(1, 3)


def test_case_005() -> None:
    pair = Pair()
    assert pair.apply(pair.apply(1, 2), 3) == pair.apply(1, pair.apply(2, 3))


def test_case_006() -> None:
    pair = Pair()
    assert isinstance(pair.apply(4, 1), int)


def test_case_007() -> None:
    pair = Pair()
    assert pair.apply(2, 3) == pair.apply(3, 2)


def test_case_008() -> None:
    assert Pair().apply(1, 1) != 1
