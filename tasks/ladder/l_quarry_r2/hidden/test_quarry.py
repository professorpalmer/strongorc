from __future__ import annotations

import json
from pathlib import Path

import pytest

from quarry import Pit

NAMES = frozenset(['alpha', 'beta', 'delta', 'gamma'])
BETA = {'mass': 2}


def test_quarry_r2_leases_json_untouched() -> None:
    data = json.loads(Path("job/leases.json").read_text(encoding="utf-8"))
    assert data.get("leased") == ["quarry"]


def test_quarry_r2_extract_known(tmp_path: Path) -> None:
    assert Pit(tmp_path).extract("alpha") == {"mass": 1}


def test_quarry_r2_unknown_name_raises(tmp_path: Path) -> None:
    with pytest.raises(KeyError):
        Pit(tmp_path).extract("helper")


def test_quarry_r2_names_frozen(tmp_path: Path) -> None:
    names = Pit(tmp_path).names()
    assert names == NAMES
    with pytest.raises(AttributeError):
        names.add("helper")  # type: ignore[attr-defined]


def test_quarry_r2_sealed_true(tmp_path: Path) -> None:
    assert Pit(tmp_path).sealed() is True


def test_quarry_r2_duplicate_extract_same(tmp_path: Path) -> None:
    pit = Pit(tmp_path)
    first = pit.extract("beta")
    second = pit.extract("beta")
    assert first == second == BETA


def test_quarry_r2_nonce_present_in_package() -> None:
    nonce = json.loads(Path("job/leases.json").read_text(encoding="utf-8"))["nonce"]
    text = Path("quarry/__init__.py").read_text(encoding="utf-8")
    assert nonce in text


def test_quarry_r2_helper_name_not_extractable(tmp_path: Path) -> None:
    with pytest.raises(KeyError):
        Pit(tmp_path).extract("omega")
