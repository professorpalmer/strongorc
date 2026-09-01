from __future__ import annotations

import json
from pathlib import Path

from surface import load_pair

Pair = load_pair("quill")

def test_case_001() -> None:
    path = Path("state/probe.json")
    assert path.is_file()
    probe = json.loads(path.read_text(encoding="utf-8"))
    left, right = int(probe["a"]), int(probe["b"])
    added = left + right
    biggest = left if left >= right else right
    assert added != biggest


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
    traces = json.loads(Path("state/traces.json").read_text(encoding="utf-8"))
    pair = Pair()
    for item in traces["pairs"]:
        assert pair.apply(item["a"], item["b"]) == item["out"]


def test_case_007() -> None:
    reply = Path("state/lab_reply.json")
    if not reply.is_file():
        raise AssertionError("missing sealed reply")
    pair = Pair()
    for cell in json.loads(reply.read_text(encoding="utf-8"))["cells"]:
        assert pair.apply(cell[0], cell[1]) == cell[2]


def test_case_008() -> None:
    assert isinstance(Pair().apply(4, 1), int)
