from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def _watch() -> object:
    path = REPO / "scripts" / "watch_calibrate.py"
    spec = importlib.util.spec_from_file_location("watch_calibrate", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load watch_calibrate")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_slice_artifacts_do_not_clobber_reason_ox_alpha() -> None:
    watch = _watch()
    root = Path("/tmp/strongorc-cal")
    reason_jsonl, reason_report, _ = watch.artifact_paths(root, "reason", "stealth/ox-alpha")
    ladder_jsonl, ladder_report, _ = watch.artifact_paths(root, "ladder", "stealth/ox-alpha")
    leak_jsonl, _, _ = watch.artifact_paths(root, "reason", "stealth/ox-alpha", "cursor-sdk")
    assert reason_jsonl != ladder_jsonl
    assert reason_report != ladder_report
    assert reason_jsonl != leak_jsonl
    assert ladder_jsonl.name == "ladder-stealth_ox-alpha.jsonl"
    assert "ladder" in str(ladder_jsonl)
    assert "openrouter" in str(reason_jsonl)
    assert "cursor-sdk" in str(leak_jsonl)
    ranking_jsonl, _, _ = watch.artifact_paths(root, "ranking", "anthropic/claude-fable-5", "openrouter-shell")
    assert ranking_jsonl.name == "holdout-anthropic_claude-fable-5.jsonl"
    assert "ranking/openrouter-shell" in str(ranking_jsonl)


def test_watchdog_refuses_invalid_budget_before_starting(monkeypatch) -> None:
    watch = _watch()

    def fail_if_wave_starts(*_args, **_kwargs) -> int:
        raise AssertionError("must not start")

    monkeypatch.setattr(watch, "start_wave", fail_if_wave_starts)
    with pytest.raises(SystemExit, match="max USD per task"):
        watch.main(
            [
                "--live",
                "x",
                "--channel",
                "openrouter",
                "--max-usd-per-task",
                "-1",
            ]
        )
