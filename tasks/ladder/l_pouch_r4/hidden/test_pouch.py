from __future__ import annotations

import json
from pathlib import Path

import pytest

from pouch import Bin

LENGTH = 10


def test_pouch_r4_descending_accepts(tmp_path: Path) -> None:
    bin = Bin(tmp_path)
    for seq in range(LENGTH, 0, -1):
        bin.accept(seq, f"s{seq}")
    assert bin.get(LENGTH) == f"s{LENGTH}"
    assert bin.get(1) == "s1"


def test_pouch_r4_ascending_first_raises(tmp_path: Path) -> None:
    bin = Bin(tmp_path)
    with pytest.raises(ValueError):
        bin.accept(1, "a")


def test_pouch_r4_duplicate_seq_raises(tmp_path: Path) -> None:
    bin = Bin(tmp_path)
    bin.accept(LENGTH, "a")
    with pytest.raises(ValueError):
        bin.accept(LENGTH, "a")


def test_pouch_r4_sealed_seq_cannot_overwrite(tmp_path: Path) -> None:
    bin = Bin(tmp_path)
    bin.accept(LENGTH, "first")
    with pytest.raises(ValueError):
        bin.accept(LENGTH, "second")
    assert bin.get(LENGTH) == "first"


def test_pouch_r4_zero_seq_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        Bin(tmp_path).accept(0, "x")


def test_pouch_r4_gaps_reports_missing(tmp_path: Path) -> None:
    bin = Bin(tmp_path)
    bin.accept(LENGTH, "a")
    store = tmp_path / "state" / "pouch.json"
    data = json.loads(store.read_text(encoding="utf-8"))
    data["1"] = "tail"
    store.write_text(json.dumps(data), encoding="utf-8")
    assert 9 in Bin(tmp_path).gaps()


def test_pouch_r4_first_payload_wins(tmp_path: Path) -> None:
    bin = Bin(tmp_path)
    bin.accept(LENGTH, "kept")
    with pytest.raises(ValueError):
        bin.accept(LENGTH, "nope")
    assert bin.get(LENGTH) == "kept"


def test_pouch_r4_artifact_consumed_before_job_completed() -> None:
    events = []
    path = Path("protocol.jsonl")
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(json.loads(line)["type"])
    assert "artifact_consumed" in events
    assert "job_completed" in events
    assert events.index("artifact_consumed") < events.index("job_completed")
