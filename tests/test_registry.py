from pathlib import Path

from strongorc.registry import (
    compare_stable_cards,
    is_metadata_key,
    load_registry,
    registry_path,
    replicate,
    replication_targets,
    stable_card_view,
    validate_registry,
)
from strongorc.schema import CONTAMINATION_VALUES, REGISTRY_STATUS_VALUES

REPO = Path(__file__).resolve().parents[1]


def test_registry_schema_paths_and_metadata() -> None:
    errors = validate_registry(REPO)
    assert errors == []
    registry = load_registry(REPO)
    files = {entry["file"] for entry in registry["cards"]}
    on_disk = {path.name for path in (REPO / "cards").glob("*.json") if path.name != "registry.json"}
    assert files == on_disk
    assert "scripted-pass-reason.json" in files
    assert registry_path(REPO) == REPO / "cards" / "registry.json"
    for entry in registry["cards"]:
        assert entry["registry_status"] in REGISTRY_STATUS_VALUES
        assert entry["contamination"] in CONTAMINATION_VALUES
        assert entry["registry_status"] != "clean"
        assert entry["contamination"] != "clean"
        assert (REPO / "cards" / entry["file"]).is_file()
        if entry.get("raw"):
            raw = REPO / "cards" / Path(entry["raw"])
            assert raw.is_file()
            assert raw.resolve().is_relative_to((REPO / "cards" / "raw").resolve())
        if entry["registry_status"] == "retired_evidence":
            assert str(entry.get("retirement_reason") or "").strip()
        if entry["registry_status"] == "leak_diagnostic":
            assert entry["contamination"] == "authoring_leak"
        if entry["file"].startswith("scripted-pass"):
            assert entry["registry_status"] == "non_model"


def test_registry_status_is_not_inferred_from_filename() -> None:
    registry = load_registry(REPO)
    by_file = {entry["file"]: entry for entry in registry["cards"]}
    assert by_file["composer-2.5-brutal.json"]["registry_status"] == "leak_diagnostic"
    assert by_file["composer-2.5-frontier.json"]["registry_status"] == "retired_evidence"
    assert by_file["scripted-pass-reason.json"]["registry_status"] == "non_model"
    assert by_file["gemini-3.7-flash-brutal.json"]["registry_status"] == "unknown"


def test_stable_compare_ignores_date_and_paths() -> None:
    expected = {
        "date": "2026-01-01",
        "run_dir": "/old/runs/task",
        "strongorc_score": 1.0,
        "n_total": 12,
    }
    actual = {
        "date": "2026-08-20",
        "run_dir": "/tmp/other",
        "strongorc_score": 1.0,
        "n_total": 12,
        "protocol_shape_rate": 1.0,
    }
    assert is_metadata_key("date")
    assert is_metadata_key("run_dir")
    assert "date" not in stable_card_view(expected)
    assert compare_stable_cards(expected, actual) == []


def test_stable_compare_flags_scoring_drift() -> None:
    errors = compare_stable_cards({"hidden_rate": 1.0, "date": "x"}, {"hidden_rate": 0.5})
    assert errors
    assert any("hidden_rate" in item for item in errors)


def test_replicate_regrades_committed_scripted_cards() -> None:
    targets = replication_targets(root=REPO)
    names = {item.file for item in targets}
    assert names == {"scripted-pass-brutal.json", "scripted-pass-reason.json"}
    assert replicate(REPO) == []


def test_ci_does_not_require_real_holdout() -> None:
    workflow = (REPO / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "timeout-minutes: 45" in workflow
    assert "scripts/replicate.py" in workflow
    assert "pytest" in workflow
    assert "do not set" in workflow.lower()
    gitignore = (REPO / ".gitignore").read_text(encoding="utf-8")
    assert "*.jsonl" in gitignore
    assert "!cards/raw/*.jsonl" in gitignore
    assert "!.env" not in gitignore
    assert "!tasks/holdout/**/hidden" not in gitignore


def test_datasheet_and_spec_state_the_boundary() -> None:
    datasheet = (REPO / "docs" / "DATASHEET.md").read_text(encoding="utf-8")
    spec = (REPO / "SPEC.md").read_text(encoding="utf-8")
    for text in (datasheet, spec):
        assert "capability_score" in text
        assert "0.6.0" in text
        assert "task-clustered" in text.lower() or "task_clustered" in text
    assert "practice slices" in spec.lower()
    assert "holdout" in spec.lower()
    assert "retired evidence" in spec.lower()
    assert "general intelligence" in datasheet.lower() or "general intelligence" in spec.lower()
    assert "CITATION.cff" in datasheet

