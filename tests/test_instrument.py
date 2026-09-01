from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from strongorc.calibrate import SystemRow
from strongorc.catalog import TaskSpec, list_tasks
from strongorc.cli import build_parser
from strongorc.instrument import (
    DEFAULT_SLICE,
    PRACTICE_SLICES,
    RANKING_SLICES,
    SLICE_LOOKUP_ORDER,
    calibration_dest,
    default_live_channel,
    expand_slice_alias,
    assess_ranking_tasks,
    is_practice_slice,
    is_ranking_slice,
    is_retired_ranking_slice,
    refuse_mixed_live_channels,
    validate_paid_live_request,
)


def test_aliases_split_practice_from_ranking() -> None:
    assert expand_slice_alias("practice") == PRACTICE_SLICES
    assert expand_slice_alias("ranking") == RANKING_SLICES
    assert expand_slice_alias("ranking") == ("holdout",)
    assert expand_slice_alias("ladder") == ("ladder",)
    assert is_practice_slice("reason")
    assert not is_ranking_slice("reason")
    assert is_ranking_slice("holdout")
    assert not is_practice_slice("holdout")
    assert default_live_channel("practice") == "openrouter"
    assert default_live_channel("ranking") == "openrouter"


def test_cli_defaults_to_ladder() -> None:
    parser = build_parser()
    assert parser.parse_args(["list"]).slice == DEFAULT_SLICE
    assert parser.parse_args(["run"]).slice == DEFAULT_SLICE
    assert is_retired_ranking_slice("hard")
    assert not is_retired_ranking_slice("ladder")


def test_cli_run_refuses_practice_alias() -> None:
    parser = build_parser()
    args = parser.parse_args(["run", "--slice", "practice"])
    with pytest.raises(SystemExit, match="one practice slice"):
        args.func(args)


def test_cli_run_ranking_is_holdout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STRONGORC_HOLDOUT", raising=False)
    monkeypatch.delenv("DURABLE_ORCH_HOLDOUT", raising=False)
    parser = build_parser()
    args = parser.parse_args(["run", "--slice", "ranking"])
    with pytest.raises(SystemExit, match="STRONGORC_HOLDOUT"):
        args.func(args)


def test_refuse_mixed_live_channels() -> None:
    confined = SystemRow(
        system_id="jail",
        model="ox-alpha",
        adapter="command",
        confinement="confined",
        contamination="unknown",
        task_equalized_score=0.07,
        tasks_passed=0,
        tasks_total=12,
        n_attempts=1,
        responses={"r_trace_contract_r1": 0.0},
        band="floor",
    )
    leak = SystemRow(
        system_id="sdk",
        model="grok-4.6",
        adapter="command",
        confinement="authoring_sdk",
        contamination="authoring_leak",
        task_equalized_score=0.93,
        tasks_passed=11,
        tasks_total=12,
        n_attempts=1,
        responses={"r_trace_contract_r1": 1.0},
        band="saturated",
    )
    try:
        refuse_mixed_live_channels([confined, leak])
    except ValueError as exc:
        assert "mixed live channels" in str(exc)
    else:
        raise AssertionError("expected mixed-channel refusal")
    unknown = SystemRow(
        system_id="mystery",
        model="x",
        adapter="command",
        confinement="unknown",
        contamination="unknown",
        task_equalized_score=0.1,
        tasks_passed=0,
        tasks_total=12,
        n_attempts=1,
        responses={"r_trace_contract_r1": 0.0},
        band="weak",
    )
    try:
        refuse_mixed_live_channels([unknown, unknown])
    except ValueError as exc:
        assert "explicit confinement" in str(exc)
    else:
        raise AssertionError("expected unknown-channel refusal")
    refuse_mixed_live_channels([confined])
    shell = SystemRow(
        system_id="shell",
        model="fable",
        adapter="command",
        confinement="unconfined",
        contamination="unknown",
        task_equalized_score=0.2,
        tasks_passed=0,
        tasks_total=12,
        n_attempts=1,
        responses={"r_trace_contract_r1": 0.0},
        band="weak",
    )
    try:
        refuse_mixed_live_channels([confined, shell])
    except ValueError as exc:
        assert "mixed live channels" in str(exc)
    else:
        raise AssertionError("expected confined/unconfined refusal")


def test_calibration_dest_is_channel_scoped() -> None:
    jail = calibration_dest(Path("/tmp/cal"), "reason", "openrouter")
    leak = calibration_dest(Path("/tmp/cal"), "reason", "cursor-sdk")
    shell = calibration_dest(Path("/tmp/cal"), "reason", "openrouter-shell")
    assert jail != leak
    assert jail != shell
    assert jail.as_posix().endswith("reason/openrouter")
    assert shell.as_posix().endswith("reason/openrouter-shell")
    assert SLICE_LOOKUP_ORDER[0] == "brutal"
    assert SLICE_LOOKUP_ORDER[-1] == "holdout"


def _ranking_blueprint(tmp_path: Path) -> list[TaskSpec]:
    tasks = []
    for family_index in range(8):
        track = "orchestrator" if family_index < 4 else "worker"
        for rung_index, rung in enumerate(("r1", "r2", "r3"), start=1):
            root = tmp_path / f"family-{family_index}" / rung
            root.mkdir(parents=True)
            agents = root / "agents"
            agents.mkdir()
            for persona in ("fail_outcome", "fail_protocol"):
                (agents / f"{persona}.py").write_text("", encoding="utf-8")
            if track == "orchestrator":
                (root / "workers.py").write_text(
                    "def dispatch(worker_id, assignment, run_dir, nonce):\n"
                    "    return {'status': 'ok'}\n",
                    encoding="utf-8",
                )
            tasks.append(
                TaskSpec(
                    id=f"hld_{family_index:02x}{rung_index:06x}",
                    track=track,
                    slice="holdout",
                    title=f"family {family_index} {rung}",
                    timeout_seconds=30,
                    root=root,
                    facets=("hidden", f"family-{family_index}"),
                    family=f"family-{family_index}",
                    rung=rung,
                    generator_id="case",
                )
            )
    return tasks


def test_ranking_readiness_requires_full_balanced_blueprint(tmp_path: Path) -> None:
    reason_tasks = list_tasks("reason")
    public_reason = assess_ranking_tasks(reason_tasks)
    assert public_reason.ready is False
    assert public_reason.track_counts == {"orchestrator": 6, "worker": 6}

    tasks = _ranking_blueprint(tmp_path)
    balanced = assess_ranking_tasks(tasks)
    assert balanced.ready
    assert balanced.track_counts == {"orchestrator": 12, "worker": 12}

    one_track = assess_ranking_tasks([replace(task, track="orchestrator") for task in tasks])
    assert one_track.ready is False
    assert any("worker" in error for error in one_track.errors)


def test_paid_live_request_requires_budget_and_safe_concurrency() -> None:
    with pytest.raises(ValueError, match="max USD per task"):
        validate_paid_live_request(
            channel="openrouter-shell",
            jobs=1,
            max_usd_per_task=None,
            allow_high_concurrency=False,
        )
    with pytest.raises(ValueError, match="jobs <= 2"):
        validate_paid_live_request(
            channel="openrouter",
            jobs=3,
            max_usd_per_task=1.0,
            allow_high_concurrency=False,
        )
    validate_paid_live_request(
        channel="openrouter",
        jobs=3,
        max_usd_per_task=1.0,
        allow_high_concurrency=True,
    )
    validate_paid_live_request(
        channel="cursor-sdk",
        jobs=1,
        max_usd_per_task=None,
        allow_high_concurrency=False,
    )
