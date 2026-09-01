from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from strongorc.instrument import default_live_channel

REPO = Path(__file__).resolve().parents[1]
MINT = REPO / "scripts" / "mint_holdout.py"
FIXTURE_OVERLAY = REPO / "tests" / "fixtures" / "holdout_overlay"


def test_default_live_channel_splits_practice_from_ranking() -> None:
    assert default_live_channel("reason") == "openrouter"
    assert default_live_channel("practice") == "openrouter"
    assert default_live_channel("ranking") == "openrouter"
    assert default_live_channel("holdout") == "openrouter"


def test_ranking_preregister_is_confined_and_attempt_aware() -> None:
    payload = json.loads(
        (REPO / "cards" / "preregister" / "holdout-0.6.0-openrouter.json").read_text(
            encoding="utf-8"
        )
    )
    assert payload["channel"] == "openrouter"
    assert payload["confinement"] == "confined"
    assert "--allow-shell" not in payload["cmd"]
    assert payload["jobs"] == 2
    assert payload["initial_repeats"] == 1
    assert len(payload["private_bank_commitment_sha256"]) == 64
    assert all(
        len(payload["systems"][band]) >= 2
        for band in ("weak", "middle", "frontier")
    )
    assert payload["publication_gates"]["attempts_per_task"] == 3


def _load_calibrate():
    spec = importlib.util.spec_from_file_location(
        "calibrate_script", REPO / "scripts" / "calibrate.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_private_bank_authoring_and_task_metadata_stay_out_of_git() -> None:
    assert not MINT.exists()
    public_files = [
        path.relative_to(REPO / "tasks" / "holdout").as_posix()
        for path in (REPO / "tasks" / "holdout").rglob("*")
        if path.is_file()
    ]
    assert public_files == ["README.md"]


def test_fixture_overlay_is_not_mistaken_for_ranking_bank(
    monkeypatch,
) -> None:
    monkeypatch.delenv("DURABLE_ORCH_HOLDOUT", raising=False)
    monkeypatch.setenv("STRONGORC_HOLDOUT", str(FIXTURE_OVERLAY))
    calibrate = _load_calibrate()
    validation = calibrate._validate_slice("holdout")
    assert validation["ready"] is False
    assert validation["scripted"] == {}
    assert any("at least 24 tasks" in error for error in validation["errors"])


def test_initial_cell_comes_from_private_manifest(
    tmp_path: Path, monkeypatch
) -> None:
    bank = tmp_path / "bank"
    bank.mkdir()
    (bank / "BANK.json").write_text(
        json.dumps(
            {
                "initial_cell": [
                    {"task_id": "hld_deadbeef"},
                    {"task_id": "hld_cafef00d"},
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("STRONGORC_HOLDOUT", str(bank))
    calibrate = _load_calibrate()
    assert calibrate._private_initial_cell_ids() == [
        "hld_deadbeef",
        "hld_cafef00d",
    ]
