from __future__ import annotations

import json
from pathlib import Path

import pytest

from loom import Table
from spool import Store


def _root(tmp_path: Path, cap: int = 0, leased: list[str] | None = None) -> Path:
    (tmp_path / "job").mkdir(parents=True, exist_ok=True)
    (tmp_path / "job" / "budget.json").write_text(json.dumps({"max_workers": cap}), encoding="utf-8")
    (tmp_path / "job" / "leases.json").write_text(
        json.dumps({"leased": leased or ["spool"]}),
        encoding="utf-8",
    )
    return tmp_path


def test_cap_shift_r4_admit_raises_when_cap_zero(tmp_path: Path) -> None:
    table = Table(_root(tmp_path, 0))
    with pytest.raises(PermissionError):
        table.admit()


def test_cap_shift_r4_second_admit_still_raises(tmp_path: Path) -> None:
    table = Table(_root(tmp_path, 0))
    with pytest.raises(PermissionError):
        table.admit()
    with pytest.raises(PermissionError):
        table.admit()


def test_cap_shift_r4_unleased_package_write_raises(tmp_path: Path) -> None:
    table = Table(_root(tmp_path, 0, ["spool"]))
    with pytest.raises(PermissionError):
        table.write("loom", "k", 1)


def test_cap_shift_r4_leased_package_write_ok(tmp_path: Path) -> None:
    table = Table(_root(tmp_path, 0, ["spool"]))
    table.write("spool", "k", 4)
    assert table.get("spool", "k") == 4


def test_cap_shift_r4_table_rereads_leases_from_disk(tmp_path: Path) -> None:
    root = _root(tmp_path, 0, ["spool"])
    Table(root).write("spool", "k", 1)
    (root / "job" / "leases.json").write_text(json.dumps({"leased": []}), encoding="utf-8")
    with pytest.raises(PermissionError):
        Table(root).write("spool", "k", 2)


def test_cap_shift_r4_two_keys_independent_payload(tmp_path: Path) -> None:
    store = Store(_root(tmp_path))
    store.put("a", 1)
    store.put("b", 2)
    assert store.get("a") == 1
    assert store.get("b") == 2


def test_cap_shift_r4_empty_get_is_none(tmp_path: Path) -> None:
    table = Table(_root(tmp_path, 0))
    assert table.get("spool", "missing") is None


def test_cap_shift_r4_live_files_reread_budget(tmp_path: Path) -> None:
    root = _root(tmp_path, 2, ["spool"])
    Table(root).admit()
    (root / "job" / "budget.json").write_text(json.dumps({"max_workers": 0}), encoding="utf-8")
    with pytest.raises(PermissionError):
        Table(root).admit()
