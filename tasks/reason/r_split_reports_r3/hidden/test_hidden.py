from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

import pytest

from surface import load_board

Board = load_board("ledger")


def _write(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _report(worker: str, value: int) -> dict:
    return {"claimed": "ok", "value": value, "worker": worker}


def _put(root: Path, values: dict[str, int]) -> dict[str, str]:
    hashes = {}
    for name, value in values.items():
        payload = _report(name, value)
        _write(root / "state" / "reports" / f"{name}.json", payload)
        hashes[name] = hashlib.sha256(json.dumps(payload, indent=2, sort_keys=True).encode("utf-8") + b"\n").hexdigest()
    return hashes

def test_case_001() -> None:
    path = Path("state/probe.json")
    assert path.is_file()
    probe = json.loads(path.read_text(encoding="utf-8"))
    reply = Path("state/lab_reply.json")
    assert reply.is_file(), "missing planted lab reply"
    cells = json.loads(reply.read_text(encoding="utf-8")).get("cells") or []
    want = {cell.get("sha256") for cell in cells if cell.get("eligible") and cell.get("sha256")}
    assert want
    reports = {}
    folder = Path("state/reports")
    if folder.is_dir():
        for report in sorted(folder.glob("*.json")):
            reports[report.stem] = hashlib.sha256(report.read_bytes()).hexdigest()
    wanted_workers = {name for name, digest in reports.items() if digest in want}
    sha = probe.get("sha256")
    worker = probe.get("worker")
    assert sha or worker
    if sha:
        assert sha in want
    if worker:
        assert worker in wanted_workers


def test_case_002(tmp_path: Path) -> None:
    hashes = _put(tmp_path, {"alpha": 7, "beta": 2, "gamma": 2})
    _write(tmp_path / "job" / "seals.json", {"eligible": ["alpha"], "sha256": hashes})
    assert Board(tmp_path).resolve() == 7


def test_case_003(tmp_path: Path) -> None:
    hashes = _put(tmp_path, {"alpha": 1, "beta": 4, "gamma": 1})
    _write(tmp_path / "job" / "seals.json", {"eligible": ["beta"], "sha256": hashes})
    assert Board(tmp_path).resolve() == 4


def test_case_004(tmp_path: Path) -> None:
    _put(tmp_path, {"alpha": 7, "beta": 2, "gamma": 2})
    _write(tmp_path / "job" / "seals.json", {"eligible": ["alpha"], "sha256": {"alpha": "deadbeef"}})
    with pytest.raises((PermissionError, ValueError, KeyError)):
        Board(tmp_path).resolve()


def test_case_005(tmp_path: Path) -> None:
    hashes = _put(tmp_path, {"alpha": 7, "beta": 2, "gamma": 2})
    _write(tmp_path / "job" / "seals.json", {"eligible": [], "sha256": hashes})
    with pytest.raises((PermissionError, ValueError, KeyError)):
        Board(tmp_path).resolve()


def test_case_006() -> None:
    value = Board(Path(".")).resolve()
    reports = []
    for path in sorted(Path("state/reports").glob("*.json")):
        reports.append(json.loads(path.read_text(encoding="utf-8"))["value"])
    majority = Counter(reports).most_common(1)[0][0]
    assert value != majority


def test_case_007(tmp_path: Path) -> None:
    hashes = _put(tmp_path, {"alpha": 9, "beta": 9, "gamma": 3})
    _write(tmp_path / "job" / "seals.json", {"eligible": ["gamma"], "sha256": hashes})
    assert Board(tmp_path).resolve() == 3


def test_case_008() -> None:
    assert Board(Path(".")).resolve() is not None
