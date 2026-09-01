from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from strongorc.instrument import default_live_channel

REPO = Path(__file__).resolve().parents[1]
MINT = REPO / "scripts" / "mint_holdout.py"
FIXTURE_OVERLAY = REPO / "tests" / "fixtures" / "holdout_overlay"
RANKING_PREREGISTER = (
    REPO / "cards" / "preregister" / "holdout-0.6.0-openrouter-ranking-v1.json"
)
RANKING_COMMITMENT = "b4dee106cd5d442e23899c38adf122b54ad82f71163ff36770b7b71f9ee00110"


def test_default_live_channel_splits_practice_from_ranking() -> None:
    assert default_live_channel("reason") == "openrouter"
    assert default_live_channel("practice") == "openrouter"
    assert default_live_channel("ranking") == "openrouter"
    assert default_live_channel("holdout") == "openrouter"


def test_ranking_preregister_is_confined_and_attempt_aware() -> None:
    payload = json.loads(RANKING_PREREGISTER.read_text(encoding="utf-8"))
    assert payload["name"] == "holdout-0.6.0-openrouter-ranking-v1"
    assert payload["channel"] == "openrouter"
    assert payload["confinement"] == "confined"
    assert "--allow-shell" not in payload["cmd"]
    assert payload["jobs"] == 2
    assert payload["repeats"] == 3
    assert payload["initial_repeats"] == 1
    assert payload["private_bank_commitment_sha256"] == RANKING_COMMITMENT
    assert payload["publication_gates"]["attempts_per_task"] == 3
    assert payload["publication_gates"]["same_channel_only"] is True
    assert payload["publication_gates"]["minimum_coverage"] == 0.95
    assert "systems" not in payload


def test_default_holdout_openrouter_preregister_is_ranking_v1() -> None:
    calibrate = _load_calibrate()
    path = calibrate._preregister_for_channel(
        calibrate.DEFAULT_PREREGISTER, "openrouter", "holdout"
    )
    assert path == calibrate.RANKING_PREREGISTER
    assert path == RANKING_PREREGISTER


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
    assert not (REPO / "scripts" / "mint_frontier_bank.py").exists()
    assert not (REPO / "scripts" / "mint_ranking_bank.py").exists()
    public_files = [
        path.relative_to(REPO / "tasks" / "holdout").as_posix()
        for path in (REPO / "tasks" / "holdout").rglob("*")
        if path.is_file()
    ]
    assert public_files == ["README.md"]
    ranking_docs = (REPO / "docs" / "RANKING.md").read_text(encoding="utf-8")
    assert RANKING_COMMITMENT in ranking_docs


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
