from __future__ import annotations

import json
from pathlib import Path

import pytest

from kiln import Kiln


def _leases(root: Path, fence: str) -> None:
    job = root / "job"
    job.mkdir(parents=True, exist_ok=True)
    (job / "leases.json").write_text(
        json.dumps({"fence": fence, "leased": ["kiln"]}),
        encoding="utf-8",
    )


def test_stale_token_cannot_mutate(tmp_path: Path) -> None:
    _leases(tmp_path, "live")
    with pytest.raises(PermissionError):
        Kiln.open(tmp_path, "stale")


def test_live_token_can_mutate(tmp_path: Path) -> None:
    _leases(tmp_path, "live")
    kiln = Kiln.open(tmp_path, "live")
    kiln.mutate("k", 3)
    assert kiln.get("k") == 3


def test_open_with_old_token_raises(tmp_path: Path) -> None:
    _leases(tmp_path, "alpha-seed")
    Kiln.open(tmp_path, "alpha-seed")
    _leases(tmp_path, "rotated")
    with pytest.raises(PermissionError):
        Kiln.open(tmp_path, "alpha-seed")


def test_token_comes_from_leases_object(tmp_path: Path) -> None:
    _leases(tmp_path, "alpha-seed")
    Kiln.open(tmp_path, "alpha-seed").mutate("k", 1)
    _leases(tmp_path, "rotated")
    with pytest.raises(PermissionError):
        Kiln.open(tmp_path, "alpha-seed")
    Kiln.open(tmp_path, "rotated")
    import kiln as kiln_mod

    assert "beta-live" not in Path(kiln_mod.__file__).read_text(encoding="utf-8")


def test_payload_survives_token_rotate_if_reopened_live(tmp_path: Path) -> None:
    _leases(tmp_path, "first")
    Kiln.open(tmp_path, "first").mutate("city", "austin")
    _leases(tmp_path, "second")
    assert Kiln.open(tmp_path, "second").get("city") == "austin"


def test_cached_first_token_is_wrong(tmp_path: Path) -> None:
    _leases(tmp_path, "first")
    Kiln.open(tmp_path, "first")
    _leases(tmp_path, "second")
    with pytest.raises(PermissionError):
        Kiln.open(tmp_path, "first")


def test_empty_store_get_is_none(tmp_path: Path) -> None:
    _leases(tmp_path, "live")
    assert Kiln.open(tmp_path, "live").get("missing") is None


def test_exact_live_token_is_allowed(tmp_path: Path) -> None:
    _leases(tmp_path, "exact")
    kiln = Kiln.open(tmp_path, "exact")
    kiln.mutate("n", 1)
    assert kiln.get("n") == 1
