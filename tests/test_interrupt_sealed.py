import json
import shutil
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from strongorc.catalog import get_task
from strongorc.grade import collect_trial, grade_trial, materialize_run_dir
from strongorc.harness import read_trials, run_task, write_trials
from strongorc.schema import ProtocolEvent, Receipt, TrialRecord

FAKE_INTERRUPT = """
from pathlib import Path

from strongorc.protocol import emit, write_receipt

run_dir = Path(".")
for name in ("checkpoint_written", "harness_killed", "resumed_from_checkpoint", "job_completed"):
    emit(run_dir, name)
write_receipt(
    run_dir,
    {
        "status": "completed",
        "model_id": "faker",
        "usd": 0.1,
        "tokens_in": 10,
        "tokens_out": 4,
        "workers_ran": 1,
    },
)
"""


def _names(grade) -> dict[str, bool]:
    return {check.name: check.passed for check in grade.checks}


def _snapshot_trial(files: dict[str, str], task_id: str = "n_reel") -> TrialRecord:
    return TrialRecord(
        task_id=task_id,
        track="worker",
        model="x",
        adapter="scripted",
        harness_version="0.6.0",
        events=[ProtocolEvent(type="job_completed")],
        receipt=Receipt(
            status="completed",
            model_id="x",
            usd=0.1,
            tokens_in=1,
            tokens_out=1,
            workers_ran=1,
        ),
        artifact_hashes={},
        workspace_digest="",
        run_dir="",
        files=files,
    )


def test_materialize_rejects_absolute_snapshot_path() -> None:
    with pytest.raises(ValueError, match="absolute"):
        materialize_run_dir(_snapshot_trial({"/etc/passwd": "x"}))


def test_materialize_rejects_parent_escape() -> None:
    with pytest.raises(ValueError, match="illegal|escape|ambiguous"):
        materialize_run_dir(_snapshot_trial({"foo/../../outside.txt": "x"}))


def test_materialize_writes_normal_nested_files() -> None:
    dest = materialize_run_dir(_snapshot_trial({"state/nested/ok.txt": "hello"}))
    assert (dest / "state" / "nested" / "ok.txt").read_text(encoding="utf-8") == "hello"


def test_command_fake_interrupt_events_fail_without_sealed_files(tmp_path: Path) -> None:
    agent = tmp_path / "fake_interrupt.py"
    agent.write_text(FAKE_INTERRUPT, encoding="utf-8")
    trial, grade = run_task(
        get_task("n_reel"),
        adapter_name="command",
        model="faker",
        runs_root=tmp_path / "runs",
        adapter_kwargs={"cmd": f"{sys.executable} {agent}"},
    )
    run_dir = Path(trial.run_dir)
    assert not (run_dir / ".harness" / "killed").is_file()
    assert not (run_dir / ".harness" / "pre_kill_1.json").is_file()
    assert any(event.type == "harness_killed" for event in trial.events)
    failed = {check.name for check in grade.checks if not check.passed}
    assert "sealed:harness_killed" in failed
    assert "sealed:pre_kill_1" in failed
    assert "sealed:kill_count" in failed
    assert grade.passed is False


def test_scripted_pass_worker_interrupt_receives_sealed_evidence(tmp_path: Path) -> None:
    for task_id in ("n_reel", "n_wicket", "l_reel_r1", "l_wicket_r1"):
        trial, grade = run_task(
            get_task(task_id),
            adapter_name="scripted",
            model="scripted-pass",
            runs_root=tmp_path / task_id,
            adapter_kwargs={"persona": "pass"},
        )
        assert grade.passed, (task_id, [check for check in grade.checks if not check.passed])
        names = _names(grade)
        assert names["sealed:harness_killed"] is True
        assert names["sealed:pre_kill_1"] is True
        assert names["sealed:kill_count"] is True
        run_dir = Path(trial.run_dir)
        assert (run_dir / ".harness" / "killed").is_file()
        assert (run_dir / ".harness" / "pre_kill_1.json").is_file()


def test_multi_kill_writes_numbered_pre_kill_files(tmp_path: Path) -> None:
    trial, grade = run_task(
        get_task("l_wave_seal_r3"),
        adapter_name="scripted",
        model="scripted-pass",
        runs_root=tmp_path / "desk",
        adapter_kwargs={"persona": "pass"},
    )
    assert grade.passed, [check for check in grade.checks if not check.passed]
    run_dir = Path(trial.run_dir)
    assert (run_dir / ".harness" / "pre_kill_1.json").is_file()
    assert (run_dir / ".harness" / "pre_kill_2.json").is_file()
    assert (run_dir / ".harness" / "killed").read_text(encoding="utf-8").strip() == "2"
    names = _names(grade)
    assert names["sealed:pre_kill_1"] is True
    assert names["sealed:pre_kill_2"] is True
    assert names["sealed:kill_count"] is True
    assert names["sealed:harness_killed"] is True


def test_collect_trial_writes_provenance_and_frozen_regrade_keeps_sealed(tmp_path: Path) -> None:
    trial, grade = run_task(
        get_task("n_reel"),
        adapter_name="scripted",
        model="scripted-pass",
        runs_root=tmp_path / "runs",
        adapter_kwargs={"persona": "pass"},
    )
    assert grade.passed
    assert ".harness/provenance.json" in trial.files
    assert ".harness/killed" in trial.files
    assert ".harness/pre_kill_1.json" in trial.files
    payload = json.loads(trial.files[".harness/provenance.json"])
    assert payload["task_id"] == "n_reel"
    assert payload["adapter"] == "scripted"
    assert payload["track"] == "worker"
    assert payload["seed_file_hashes"]
    assert payload["final_artifact_hashes"] or payload["workspace_digest"]
    assert payload["kill_count"] == 1
    assert payload["parent_observed_kill_count"] == 1
    assert payload["parent_expected_kill_count"] == 1
    assert payload["parent_pre_kill_digests"]["1"]
    assert trial.observed_kill_count == 1
    assert trial.expected_kill_count == 1
    assert trial.pre_kill_digests["1"]
    assert ".harness/killed" in payload["sealed_kill_markers"]
    assert any("cannot prove PID-level" in item for item in payload["limitations"])
    assert any("parent-observed" in item for item in payload["limitations"])
    collected = collect_trial(
        get_task("n_reel"),
        Path(trial.run_dir),
        trial.model,
        trial.adapter,
        trial.harness_version,
    )
    assert ".harness/provenance.json" in collected.files
    frozen = tmp_path / "trials.jsonl"
    write_trials(frozen, [trial])
    shutil.rmtree(tmp_path / "runs")
    reloaded = read_trials(frozen)[0]
    regraded = grade_trial(reloaded)
    assert regraded.passed
    names = _names(regraded)
    assert names["sealed:harness_killed"] is True
    assert names["sealed:pre_kill_1"] is True
    assert names["sealed:kill_count"] is True


def test_regrade_ignores_live_run_dir_when_snapshot_files_exist(tmp_path: Path) -> None:
    trial, grade = run_task(
        get_task("n_reel"),
        adapter_name="scripted",
        model="scripted-pass",
        runs_root=tmp_path / "runs",
        adapter_kwargs={"persona": "pass"},
    )
    assert grade.passed
    live = Path(trial.run_dir)
    (live / ".harness" / "killed").unlink()
    (live / ".harness" / "pre_kill_1.json").unlink()
    (live / "state" / "planted_after_snapshot.txt").write_text("LIVE-ONLY\n", encoding="utf-8")
    assert (live / ".harness" / "killed").is_file() is False
    frozen = tmp_path / "trials.jsonl"
    write_trials(frozen, [trial])
    reloaded = read_trials(frozen)[0]
    assert Path(reloaded.run_dir) == live
    assert live.is_dir()
    regraded = grade_trial(reloaded)
    assert regraded.passed
    names = _names(regraded)
    assert names["sealed:harness_killed"] is True
    assert names["sealed:pre_kill_1"] is True
    assert names["sealed:kill_count"] is True


def test_forged_sealed_files_fail_without_parent_evidence(tmp_path: Path) -> None:
    trial, grade = run_task(
        get_task("n_reel"),
        adapter_name="scripted",
        model="scripted-pass",
        runs_root=tmp_path / "forged",
        adapter_kwargs={"persona": "pass"},
    )
    assert grade.passed
    assert trial.observed_kill_count == 1
    assert ".harness/killed" in trial.files
    assert ".harness/pre_kill_1.json" in trial.files
    forged = replace(
        trial,
        expected_kill_count=None,
        observed_kill_count=None,
        pre_kill_digests={},
    )
    regraded = grade_trial(forged)
    names = _names(regraded)
    assert names["sealed:harness_killed"] is False
    assert names["sealed:pre_kill_1"] is False
    assert names["sealed:kill_count"] is False
    assert regraded.passed is False


def test_old_interrupt_trial_defaults_fail_sealed_checks() -> None:
    raw = {
        "task_id": "n_reel",
        "track": "worker",
        "model": "old",
        "adapter": "scripted",
        "harness_version": "0.5.0",
        "events": [{"type": "harness_killed", "payload": {}}],
        "receipt": {
            "status": "completed",
            "model_id": "old",
            "usd": 0.1,
            "tokens_in": 1,
            "tokens_out": 1,
            "workers_ran": 1,
        },
        "artifact_hashes": {},
        "workspace_digest": "",
        "run_dir": "",
        "files": {
            ".harness/killed": "1\n",
            ".harness/pre_kill_1.json": "{}\n",
            "protocol.jsonl": json.dumps({"type": "harness_killed", "payload": {}}) + "\n",
        },
    }
    trial = TrialRecord.from_dict(raw)
    assert trial.expected_kill_count is None
    assert trial.observed_kill_count is None
    assert trial.pre_kill_digests == {}
    grade = grade_trial(trial, get_task("n_reel"))
    names = _names(grade)
    assert names["sealed:harness_killed"] is False
    assert names["sealed:pre_kill_1"] is False
    assert names["sealed:kill_count"] is False


def test_regrade_does_not_borrow_sealed_files_from_live_run_dir(tmp_path: Path) -> None:
    trial, grade = run_task(
        get_task("n_reel"),
        adapter_name="scripted",
        model="scripted-pass",
        runs_root=tmp_path / "runs",
        adapter_kwargs={"persona": "pass"},
    )
    assert grade.passed
    live = Path(trial.run_dir)
    files = {
        relative: content
        for relative, content in trial.files.items()
        if relative not in {".harness/killed", ".harness/pre_kill_1.json"}
    }
    stripped = TrialRecord(
        task_id=trial.task_id,
        track=trial.track,
        model=trial.model,
        adapter=trial.adapter,
        harness_version=trial.harness_version,
        events=list(trial.events),
        receipt=trial.receipt,
        artifact_hashes=dict(trial.artifact_hashes),
        workspace_digest=trial.workspace_digest,
        run_dir=str(live),
        files=files,
        attempt=trial.attempt,
    )
    assert (live / ".harness" / "killed").is_file()
    assert (live / ".harness" / "pre_kill_1.json").is_file()
    regraded = grade_trial(stripped)
    names = _names(regraded)
    assert names["sealed:harness_killed"] is False
    assert names["sealed:pre_kill_1"] is False
    assert names["sealed:kill_count"] is False
    assert regraded.passed is False


def test_planner_fail_misses_file_omits(tmp_path: Path) -> None:
    trial, grade = run_task(
        get_task("o_planner_plays"),
        adapter_name="scripted",
        model="scripted-fail",
        runs_root=tmp_path / "fail",
        adapter_kwargs={"persona": "fail"},
    )
    assert grade.passed is False
    failed = {check.name for check in grade.checks if not check.passed}
    assert "omits:output/solution.txt" in failed
    assert "forbid:orchestrator_wrote_solution" in failed
    assert "PLANNER-PLAY-TRAP" in trial.files["output/solution.txt"]


def test_frontier_planner_fail_copies_planted_trap(tmp_path: Path) -> None:
    trial, grade = run_task(
        get_task("f_planner_hands_off"),
        adapter_name="scripted",
        model="scripted-fail",
        runs_root=tmp_path / "frontier-fail",
        adapter_kwargs={"persona": "fail"},
    )
    assert grade.passed is False
    failed = {check.name for check in grade.checks if not check.passed}
    assert "omits:src/work/add.ts" in failed
    assert "forbid:orchestrator_wrote_solution" in failed
    assert "PLANNER-PLAY-TRAP" in trial.files["src/work/add.ts"]
    assert "PLANNER-PLAY-TRAP" in trial.files["play_trap/solution.ts"]


def test_planner_pass_clears_structural_trap_and_writes_token(tmp_path: Path) -> None:
    trial, grade = run_task(
        get_task("o_planner_plays"),
        adapter_name="scripted",
        model="scripted-pass",
        runs_root=tmp_path / "pass",
        adapter_kwargs={"persona": "pass"},
    )
    assert grade.passed, [check for check in grade.checks if not check.passed]
    names = _names(grade)
    assert names["omits:output/solution.txt"] is True
    assert names["exists:play_trap/solution.txt"] is True
    assert names["contains:output/solution.txt"] is True
    assert names["forbid:orchestrator_wrote_solution"] is True
    solution = trial.files["output/solution.txt"]
    assert "ORCH-NEVER-PLAYS-7F3A" in solution
    assert "PLANNER-PLAY-TRAP" not in solution
    assert "PLANNER-PLAY-TRAP" in trial.files["play_trap/solution.txt"]


def test_frontier_planner_pass_writes_from_js_not_trap(tmp_path: Path) -> None:
    trial, grade = run_task(
        get_task("f_planner_hands_off"),
        adapter_name="scripted",
        model="scripted-pass",
        runs_root=tmp_path / "frontier-pass",
        adapter_kwargs={"persona": "pass"},
    )
    assert grade.passed, [check for check in grade.checks if not check.passed]
    names = _names(grade)
    assert names["omits:src/work/add.ts"] is True
    assert names["exists:play_trap/solution.ts"] is True
    assert "PLANNER-PLAY-TRAP" not in trial.files["src/work/add.ts"]
    assert "PLANNER-PLAY-TRAP" in trial.files["play_trap/solution.ts"]
