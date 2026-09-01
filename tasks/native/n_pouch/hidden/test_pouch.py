from __future__ import annotations

import json
from pathlib import Path

import pytest

from pouch import Bin


def test_in_order_accepts(tmp_path: Path) -> None:
    bin = Bin(tmp_path)
    bin.accept(1, "a")
    bin.accept(2, "b")
    assert bin.get(1) == "a"
    assert bin.get(2) == "b"


def test_gap_is_rejected(tmp_path: Path) -> None:
    bin = Bin(tmp_path)
    bin.accept(1, "a")
    with pytest.raises(ValueError):
        bin.accept(3, "c")


def test_duplicate_seq_raises(tmp_path: Path) -> None:
    bin = Bin(tmp_path)
    bin.accept(1, "a")
    with pytest.raises(ValueError):
        bin.accept(1, "a")


def test_sealed_seq_cannot_overwrite(tmp_path: Path) -> None:
    bin = Bin(tmp_path)
    bin.accept(1, "first")
    with pytest.raises(ValueError):
        bin.accept(1, "second")
    assert bin.get(1) == "first"


def test_zero_seq_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        Bin(tmp_path).accept(0, "x")


def test_gaps_reports_missing(tmp_path: Path) -> None:
    bin = Bin(tmp_path)
    bin.accept(1, "a")
    store = tmp_path / "state" / "pouch.json"
    data = json.loads(store.read_text(encoding="utf-8"))
    data["3"] = "c"
    store.write_text(json.dumps(data), encoding="utf-8")
    assert 2 in Bin(tmp_path).gaps()


def test_first_payload_wins(tmp_path: Path) -> None:
    bin = Bin(tmp_path)
    bin.accept(1, "kept")
    with pytest.raises(ValueError):
        bin.accept(1, "nope")
    assert bin.get(1) == "kept"


def test_artifact_consumed_before_job_completed() -> None:
    events = []
    path = Path("protocol.jsonl")
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(json.loads(line)["type"])
    assert "artifact_consumed" in events
    assert "job_completed" in events
    assert events.index("artifact_consumed") < events.index("job_completed")
