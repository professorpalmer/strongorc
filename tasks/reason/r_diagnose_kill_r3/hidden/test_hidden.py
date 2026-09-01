from __future__ import annotations

import hashlib
import json
from pathlib import Path

from surface import load_clinic

Clinic = load_clinic("hearth")


def _write(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _healthy(root: Path) -> None:
    payload = {"body": "ok"}
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    _write(root / "job" / "leases.json", {"fence": "live-alpha", "leased": ["hearth"]})
    _write(root / "job" / "budget.json", {"max_workers": 2})
    _write(root / "state" / "children" / "leaf.json", {"status": "ok"})
    (root / "state").mkdir(parents=True, exist_ok=True)
    (root / "state" / "payload.json").write_text(text, encoding="utf-8")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    _write(root / "state" / "digest.json", {"sha256": digest})


def _unchanged_except(root: Path, before: dict[str, bytes], allowed: set[str]) -> None:
    for relative, original in before.items():
        if relative in allowed:
            continue
        assert (root / relative).read_bytes() == original

def test_case_001() -> None:
    path = Path("state/probe.json")
    assert path.is_file()
    probe = json.loads(path.read_text(encoding="utf-8"))
    inspect = probe.get("inspect")
    assert isinstance(inspect, str)
    assert inspect in {"dead_child", "stale_lease", "cap", "hash_drift", "leaf", "digest", "lease", "budget"}
    reply = Path("state/lab_reply.json")
    assert reply.is_file(), "missing planted lab reply"
    causal = json.loads(reply.read_text(encoding="utf-8")).get("causal")
    assert inspect == causal
    assert causal == "hash_drift"


def test_case_002(tmp_path: Path) -> None:
    _healthy(tmp_path)
    _write(tmp_path / "state" / "children" / "leaf.json", {"status": "failed"})
    before = {path.relative_to(tmp_path).as_posix(): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    Clinic(tmp_path).repair()
    assert json.loads((tmp_path / "state" / "children" / "leaf.json").read_text(encoding="utf-8"))["status"] == "ok"
    _unchanged_except(tmp_path, before, {"state/children/leaf.json"})


def test_case_003(tmp_path: Path) -> None:
    _healthy(tmp_path)
    _write(tmp_path / "state" / "digest.json", {"sha256": "0" * 64})
    before = {path.relative_to(tmp_path).as_posix(): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    Clinic(tmp_path).repair()
    payload = (tmp_path / "state" / "payload.json").read_bytes()
    digest = json.loads((tmp_path / "state" / "digest.json").read_text(encoding="utf-8"))
    assert digest["sha256"] == hashlib.sha256(payload).hexdigest()
    _unchanged_except(tmp_path, before, {"state/digest.json"})


def test_case_004(tmp_path: Path) -> None:
    _healthy(tmp_path)
    leases = json.loads((tmp_path / "job" / "leases.json").read_text(encoding="utf-8"))
    leases["fence"] = "stale"
    _write(tmp_path / "job" / "leases.json", leases)
    before = {path.relative_to(tmp_path).as_posix(): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    Clinic(tmp_path).repair()
    fence = json.loads((tmp_path / "job" / "leases.json").read_text(encoding="utf-8"))["fence"]
    assert fence not in {"", "stale", None}
    _unchanged_except(tmp_path, before, {"job/leases.json"})


def test_case_005(tmp_path: Path) -> None:
    _healthy(tmp_path)
    _write(tmp_path / "job" / "budget.json", {"max_workers": 0})
    before = {path.relative_to(tmp_path).as_posix(): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    Clinic(tmp_path).repair()
    assert int(json.loads((tmp_path / "job" / "budget.json").read_text(encoding="utf-8"))["max_workers"]) >= 1
    _unchanged_except(tmp_path, before, {"job/budget.json"})


def test_case_006() -> None:
    child = json.loads(Path("state/children/leaf.json").read_text(encoding="utf-8"))
    assert child.get("status") == "ok"
    payload = Path("state/payload.json").read_bytes()
    digest = json.loads(Path("state/digest.json").read_text(encoding="utf-8"))
    assert digest.get("sha256") == hashlib.sha256(payload).hexdigest()


def test_case_007() -> None:
    leases = json.loads(Path("job/leases.json").read_text(encoding="utf-8"))
    assert leases.get("fence") == "live-alpha"
    budget = json.loads(Path("job/budget.json").read_text(encoding="utf-8"))
    assert budget.get("max_workers") == 2


def test_case_008(tmp_path: Path) -> None:
    _healthy(tmp_path)
    Clinic(tmp_path).repair()
    payload = (tmp_path / "state" / "payload.json").read_bytes()
    digest = json.loads((tmp_path / "state" / "digest.json").read_text(encoding="utf-8"))
    assert digest["sha256"] == hashlib.sha256(payload).hexdigest()
