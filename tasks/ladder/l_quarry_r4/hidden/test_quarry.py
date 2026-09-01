from __future__ import annotations

import json
from pathlib import Path

import pytest

from quarry import Pit


def test_quarry_r4_leases_json_untouched() -> None:
    data = json.loads(Path("job/leases.json").read_text(encoding="utf-8"))
    assert data.get("leased") == ["quarry"]


def test_quarry_r4_extract_helper(tmp_path: Path) -> None:
    assert Pit(tmp_path).extract("helper") == {"mass": 0}


def test_quarry_r4_known_alpha_raises(tmp_path: Path) -> None:
    with pytest.raises(KeyError):
        Pit(tmp_path).extract("alpha")


def test_quarry_r4_names_frozen_to_helper(tmp_path: Path) -> None:
    assert Pit(tmp_path).names() == frozenset({"helper"})


def test_quarry_r4_sealed_true(tmp_path: Path) -> None:
    assert Pit(tmp_path).sealed() is True


def test_quarry_r4_duplicate_extract_same(tmp_path: Path) -> None:
    assert Pit(tmp_path).extract("helper") == Pit(tmp_path).extract("helper")


def test_quarry_r4_nonce_present_in_package() -> None:
    text = Path("quarry/__init__.py").read_text(encoding="utf-8")
    assert "NONCE =" in text


def test_quarry_r4_known_beta_raises(tmp_path: Path) -> None:
    with pytest.raises(KeyError):
        Pit(tmp_path).extract("beta")
