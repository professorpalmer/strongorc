from __future__ import annotations

import json
from pathlib import Path

import pytest

from loom import Table
from spool import Store


def _job(root: Path, cap: int, leased: list[str]) -> None:
    job = root / "job"
    job.mkdir(parents=True, exist_ok=True)
    (job / "budget.json").write_text(json.dumps({"max_workers": cap}), encoding="utf-8")
    (job / "leases.json").write_text(json.dumps({"leased": leased}), encoding="utf-8")


def test_admit_respects_live_cap(tmp_path: Path) -> None:
    _job(tmp_path, 1, ["loom"])
    table = Table(tmp_path)
    table.admit()
    with pytest.raises(PermissionError):
        table.admit()


def test_second_admit_raises_when_cap_is_one(tmp_path: Path) -> None:
    _job(tmp_path, 1, ["loom"])
    table = Table(tmp_path)
    table.admit()
    with pytest.raises(PermissionError):
        Table(tmp_path).admit()


def test_unleased_package_write_raises(tmp_path: Path) -> None:
    _job(tmp_path, 2, ["spool"])
    with pytest.raises(PermissionError):
        Table(tmp_path).write("loom", "k", 1)


def test_leased_package_write_ok(tmp_path: Path) -> None:
    _job(tmp_path, 2, ["loom"])
    table = Table(tmp_path)
    table.write("loom", "k", 4)
    assert table.get("loom", "k") == 4


def test_table_rereads_leases_from_disk(tmp_path: Path) -> None:
    _job(tmp_path, 2, ["loom"])
    table = Table(tmp_path)
    table.write("loom", "k", 1)
    _job(tmp_path, 1, ["spool"])
    with pytest.raises(PermissionError):
        table.write("loom", "k", 2)
    table.write("spool", "k", 3)
    assert table.get("spool", "k") == 3


def test_two_packages_independent_payload(tmp_path: Path) -> None:
    _job(tmp_path, 2, ["loom", "spool"])
    Table(tmp_path).write("loom", "a", 1)
    Store(tmp_path).put("a", 2)
    assert Table(tmp_path).get("loom", "a") == 1
    assert Store(tmp_path).get("a") == 2


def test_empty_admit_ok(tmp_path: Path) -> None:
    _job(tmp_path, 1, ["loom"])
    Table(tmp_path).admit()


def test_live_files_reread_budget(tmp_path: Path) -> None:
    _job(tmp_path, 2, ["loom"])
    table = Table(tmp_path)
    table.admit()
    table.admit()
    _job(tmp_path, 1, ["loom"])
    with pytest.raises(PermissionError):
        Table(tmp_path).admit()
