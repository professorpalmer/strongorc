import hashlib
import json
import os
import shutil
from pathlib import Path

import pytest

from strongorc.catalog import get_task, list_tasks
from strongorc.cli import main
from strongorc.grade import check_grain, check_kind, grade_trial, load_oracle
from strongorc.harness import read_trials, run_slice, seed_run, write_trials
from strongorc.holdout import (
    HoldoutError,
    HoldoutUnavailable,
    generate_hidden,
    load_generator_module,
    opaque_case_name,
    overlay_root,
    scrub_holdout_env,
    verify_overlay_commitment,
)
from strongorc.schema import ProtocolEvent, Receipt, TrialRecord

REPO = Path(__file__).resolve().parents[1]
FIXTURE = REPO / "tests" / "fixtures" / "holdout_overlay"
PUBLIC_HOLDOUT = REPO / "tasks" / "holdout"
FIXTURE_ID = "hld_cafef00d"
FIXTURE_TOKEN = "fixture_token_cafef00d"


@pytest.fixture
def no_holdout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STRONGORC_HOLDOUT", raising=False)
    monkeypatch.delenv("DURABLE_ORCH_HOLDOUT", raising=False)


@pytest.fixture
def fixture_overlay(monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.delenv("DURABLE_ORCH_HOLDOUT", raising=False)
    monkeypatch.setenv("STRONGORC_HOLDOUT", str(FIXTURE))
    return FIXTURE


def _seed_workspace(dest: Path, nonce: str) -> None:
    spec = FIXTURE / FIXTURE_ID / "seed" / "job" / "spec.json"
    (dest / "job").mkdir(parents=True)
    (dest / "job" / "spec.json").write_text(spec.read_text(encoding="utf-8"), encoding="utf-8")
    harness = dest / ".harness"
    harness.mkdir(parents=True, exist_ok=True)
    (harness / "nonce").write_text(nonce + "\n", encoding="utf-8")


def test_unset_env_yields_zero_holdout_tasks(no_holdout) -> None:
    assert overlay_root() is None
    assert list_tasks("holdout") == []
    with pytest.raises(KeyError):
        get_task(FIXTURE_ID)


def test_unset_env_refuses_run(no_holdout, tmp_path: Path) -> None:
    with pytest.raises(HoldoutUnavailable, match="STRONGORC_HOLDOUT"):
        run_slice(
            "holdout",
            adapter_name="scripted",
            model="scripted-pass",
            runs_root=tmp_path / "should-not-run",
            adapter_kwargs={"persona": "pass"},
        )


def test_unset_env_refuses_cli_run_and_card(no_holdout, tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="STRONGORC_HOLDOUT"):
        main(["run", "--slice", "holdout", "--adapter", "scripted"])
    empty = tmp_path / "empty.jsonl"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(SystemExit, match="STRONGORC_HOLDOUT"):
        main(["card", str(empty), "--model", "x", "--slice", "holdout"])


def test_set_env_discovers_opaque_fixture(fixture_overlay: Path) -> None:
    tasks = list_tasks("holdout")
    assert [task.id for task in tasks] == [FIXTURE_ID]
    task = get_task(FIXTURE_ID)
    assert task.slice == "holdout"
    assert task.track == "worker"
    assert task.family == "fixture"
    assert task.rung == "r1"
    assert task.generator_id == "echo"
    assert task.oracle_path.is_relative_to(fixture_overlay)
    assert task.hidden_dir.is_relative_to(fixture_overlay)
    assert (task.root / "generators" / "echo.py").is_file()
    assert not task.root.is_relative_to(PUBLIC_HOLDOUT)


def test_trusted_bank_modules_do_not_write_bytecode(fixture_overlay: Path) -> None:
    task = get_task(FIXTURE_ID)
    before = {
        path.relative_to(fixture_overlay).as_posix()
        for path in fixture_overlay.rglob("*")
        if path.is_file()
    }
    load_generator_module(task)
    load_oracle(task)
    after = {
        path.relative_to(fixture_overlay).as_posix()
        for path in fixture_overlay.rglob("*")
        if path.is_file()
    }
    assert after == before


def test_private_bank_commitment_detects_file_changes(tmp_path: Path) -> None:
    bank = tmp_path / "bank"
    task = bank / "hld_deadbeef" / "task.json"
    task.parent.mkdir(parents=True)
    task.write_text('{"id": "hld_deadbeef"}\n', encoding="utf-8")
    commitment = {
        "schema": "strongorc.private-bank-commitment.v1",
        "files": {
            "hld_deadbeef/task.json": hashlib.sha256(task.read_bytes()).hexdigest()
        },
    }
    commitment_path = bank / "BANK_COMMITMENT.json"
    commitment_path.write_text(
        json.dumps(commitment, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    assert verify_overlay_commitment(bank) == hashlib.sha256(
        commitment_path.read_bytes()
    ).hexdigest()
    task.write_text('{"id": "hld_changed"}\n', encoding="utf-8")
    with pytest.raises(HoldoutError, match="do not match"):
        verify_overlay_commitment(bank)


def test_live_holdout_refuses_structurally_incomplete_bank(
    fixture_overlay: Path, tmp_path: Path
) -> None:
    with pytest.raises(HoldoutUnavailable, match="ranking instrument not ready"):
        run_slice(
            "holdout",
            adapter_name="command",
            model="must-not-start",
            runs_root=tmp_path / "blocked",
            adapter_kwargs={"cmd": "exit 99"},
        )


def test_generator_deterministic_by_nonce(fixture_overlay: Path, tmp_path: Path) -> None:
    task = get_task(FIXTURE_ID)
    first = tmp_path / "a"
    second = tmp_path / "b"
    third = tmp_path / "c"
    _seed_workspace(first, "aaaa")
    _seed_workspace(second, "aaaa")
    _seed_workspace(third, "bbbb")
    generate_hidden(task, first, "aaaa")
    generate_hidden(task, second, "aaaa")
    generate_hidden(task, third, "bbbb")
    bytes_a = (first / ".holdout" / "generated" / "case.json").read_bytes()
    bytes_b = (second / ".holdout" / "generated" / "case.json").read_bytes()
    bytes_c = (third / ".holdout" / "generated" / "case.json").read_bytes()
    assert bytes_a == bytes_b
    assert bytes_a != bytes_c
    record = json.loads((first / ".harness" / "generator.json").read_text(encoding="utf-8"))
    assert record["generator_id"] == "echo"
    assert record["sha256"] == hashlib.sha256(
        (FIXTURE / FIXTURE_ID / "generators" / "echo.py").read_bytes()
    ).hexdigest()
    assert opaque_case_name("answer", "aaaa") != opaque_case_name("answer", "bbbb")
    assert opaque_case_name("answer", "aaaa") == "case_" + opaque_case_name("answer", "aaaa").removeprefix(
        "case_"
    )
    assert check_kind(opaque_case_name("answer", "aaaa")) == "outcome"
    assert check_grain(opaque_case_name("answer", "aaaa")) == "hidden"


def test_seed_run_materializes_candidate_visible_case(
    fixture_overlay: Path, tmp_path: Path
) -> None:
    task = get_task(FIXTURE_ID)
    run_dir = tmp_path / "materialized"
    seed_run(task, run_dir)
    live = json.loads((run_dir / "state" / "live.json").read_text(encoding="utf-8"))
    nonce = (run_dir / ".harness" / "nonce").read_text(encoding="utf-8").strip()
    assert live == {"base": 7, "nonce": nonce}


def test_private_generator_materializes_post_interrupt_state(
    fixture_overlay: Path, tmp_path: Path
) -> None:
    from strongorc.holdout import materialize_after_interrupt

    task = get_task(FIXTURE_ID)
    run_dir = tmp_path / "materialized"
    seed_run(task, run_dir)
    nonce = (run_dir / ".harness" / "nonce").read_text(encoding="utf-8").strip()
    materialize_after_interrupt(task, run_dir, nonce, 2)
    live = json.loads((run_dir / "state" / "live.json").read_text(encoding="utf-8"))
    assert live["interrupt_step"] == 2
    assert live["nonce"] == nonce


def test_scripted_pass_computes_from_live_material(fixture_overlay: Path, tmp_path: Path) -> None:
    results = run_slice(
        "holdout",
        adapter_name="scripted",
        model="scripted-pass",
        runs_root=tmp_path / "pass",
        adapter_kwargs={"persona": "pass"},
    )
    assert len(results) == 1
    trial, grade = results[0]
    assert trial.task_id == FIXTURE_ID
    assert grade.passed
    case_names = [check.name for check in grade.checks if check.name.startswith("case_")]
    assert case_names
    assert all(check.passed for check in grade.checks if check.name.startswith("case_"))
    assert not any(path.startswith(".holdout/") for path in trial.files)
    frozen = dict(trial.files)
    grade_trial(trial)
    assert trial.files == frozen


def test_run_slice_writes_progress_jsonl(fixture_overlay: Path, tmp_path: Path) -> None:
    progress = tmp_path / "holdout.jsonl"
    results = run_slice(
        "holdout",
        adapter_name="scripted",
        model="scripted-pass",
        runs_root=tmp_path / "progress",
        adapter_kwargs={"persona": "pass"},
        progress_path=progress,
    )
    assert progress.is_file()
    from strongorc.harness import read_trials

    saved = read_trials(progress)
    assert [trial.task_id for trial in saved] == [results[0][0].task_id]


def test_scripted_fail_misses_hidden_case(fixture_overlay: Path, tmp_path: Path) -> None:
    results = run_slice(
        "holdout",
        adapter_name="scripted",
        model="scripted-fail",
        runs_root=tmp_path / "fail",
        adapter_kwargs={"persona": "fail"},
    )
    assert len(results) == 1
    _, grade = results[0]
    assert grade.passed is False
    missed = [check.name for check in grade.checks if not check.passed]
    assert any(name.startswith("case_") for name in missed)


def test_frozen_regrade_does_not_need_live_run_dir(fixture_overlay: Path, tmp_path: Path) -> None:
    runs = tmp_path / "runs"
    results = run_slice(
        "holdout",
        adapter_name="scripted",
        model="scripted-pass",
        runs_root=runs,
        adapter_kwargs={"persona": "pass"},
    )
    trial, live = results[0]
    frozen_path = tmp_path / "trials.jsonl"
    write_trials(frozen_path, [trial])
    shutil.rmtree(runs)
    reloaded = read_trials(frozen_path)[0]
    assert reloaded.run_dir
    assert not Path(reloaded.run_dir).is_dir()
    assert not any(path.startswith(".holdout/") for path in reloaded.files)
    regraded = grade_trial(reloaded)
    assert regraded.passed == live.passed
    assert [check.name for check in regraded.checks] == [check.name for check in live.checks]
    assert [check.passed for check in regraded.checks] == [check.passed for check in live.checks]
    files_before = dict(reloaded.files)
    grade_trial(reloaded)
    assert reloaded.files == files_before


def test_public_holdout_has_no_secrets() -> None:
    assert PUBLIC_HOLDOUT.is_dir()
    forbidden_dirs = {"hidden", "reference", "generators", "secrets"}
    for path in PUBLIC_HOLDOUT.rglob("*"):
        if path.is_dir():
            assert path.name not in forbidden_dirs
        if path.is_file():
            assert path.name != "oracle.py"
            assert path.suffix != ".py"
            text = path.read_text(encoding="utf-8")
            assert FIXTURE_TOKEN not in text
            assert "sha256(base:nonce)" not in text
    gitignore = (REPO / ".gitignore").read_text(encoding="utf-8")
    for pattern in (
        "tasks/holdout/**/hidden",
        "tasks/holdout/**/reference",
        "tasks/holdout/**/generators",
        "tasks/holdout/**/secrets",
        ".holdout/",
        ".strongorc-holdout/",
        "/holdout-overlay/",
    ):
        assert pattern in gitignore


def test_missing_generator_fails_closed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    overlay = tmp_path / "overlay" / "hld_deadbeef"
    overlay.mkdir(parents=True)
    (overlay / "task.json").write_text(
        json.dumps(
            {
                "id": "hld_deadbeef",
                "track": "worker",
                "slice": "holdout",
                "title": "broken",
                "generator_id": "missing",
            }
        ),
        encoding="utf-8",
    )
    (overlay / "prompt.md").write_text("broken\n", encoding="utf-8")
    monkeypatch.delenv("DURABLE_ORCH_HOLDOUT", raising=False)
    monkeypatch.setenv("STRONGORC_HOLDOUT", str(tmp_path / "overlay"))
    task = get_task("hld_deadbeef")
    run_dir = tmp_path / "run"
    _seed_workspace(run_dir, "nonce1")
    (run_dir / "job" / "spec.json").write_text(json.dumps({"base": 1}) + "\n", encoding="utf-8")
    with pytest.raises(HoldoutError, match="missing generator"):
        generate_hidden(task, run_dir, "nonce1")
    trial = TrialRecord(
        task_id="hld_deadbeef",
        track="worker",
        model="scripted-pass",
        adapter="scripted",
        harness_version="0.6.0",
        events=[ProtocolEvent(type="job_completed")],
        receipt=Receipt(
            status="completed",
            model_id="scripted-pass",
            usd=0.1,
            tokens_in=1,
            tokens_out=1,
            workers_ran=1,
        ),
        artifact_hashes={},
        workspace_digest="",
        run_dir=str(run_dir),
        files={
            ".harness/nonce": "nonce1\n",
            "job/spec.json": json.dumps({"base": 1}) + "\n",
            "protocol.jsonl": json.dumps({"type": "job_completed", "payload": {}}) + "\n",
        },
    )
    frozen = dict(trial.files)
    grade = grade_trial(trial, task)
    assert grade.passed is False
    assert grade.protocol_passed is False
    assert any(check.name == "generator:ready" and not check.passed for check in grade.checks)
    assert trial.files == frozen


def test_invalid_generator_fails_closed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    overlay = tmp_path / "overlay" / "hld_00badbad"
    gens = overlay / "generators"
    gens.mkdir(parents=True)
    (overlay / "task.json").write_text(
        json.dumps(
            {
                "id": "hld_00badbad",
                "track": "worker",
                "slice": "holdout",
                "title": "invalid",
                "generator_id": "broken",
            }
        ),
        encoding="utf-8",
    )
    (overlay / "prompt.md").write_text("invalid\n", encoding="utf-8")
    (gens / "broken.py").write_text("def nope():\n    return None\n", encoding="utf-8")
    monkeypatch.delenv("DURABLE_ORCH_HOLDOUT", raising=False)
    monkeypatch.setenv("STRONGORC_HOLDOUT", str(tmp_path / "overlay"))
    task = get_task("hld_00badbad")
    run_dir = tmp_path / "run"
    _seed_workspace(run_dir, "n")
    with pytest.raises(HoldoutError, match="generate"):
        generate_hidden(task, run_dir, "n")


def test_public_stub_is_not_listed_without_overlay(
    no_holdout, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stub = tmp_path / "holdout" / FIXTURE_ID
    stub.mkdir(parents=True)
    (stub / "task.json").write_text(
        json.dumps(
            {
                "id": FIXTURE_ID,
                "track": "worker",
                "slice": "holdout",
                "family": "stub_only",
                "rung": "r1",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("strongorc.catalog.TASKS_ROOT", tmp_path)
    assert list_tasks("holdout") == []


def test_public_stub_merges_family_when_overlay_omits(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    public = tmp_path / "public" / "holdout" / "hld_0b1a7e11"
    public.mkdir(parents=True)
    (public / "task.json").write_text(
        json.dumps(
            {
                "id": "hld_0b1a7e11",
                "track": "orchestrator",
                "slice": "holdout",
                "family": "stub_family",
                "rung": "r3",
            }
        ),
        encoding="utf-8",
    )
    overlay = tmp_path / "overlay" / "hld_0b1a7e11"
    overlay.mkdir(parents=True)
    (overlay / "task.json").write_text(
        json.dumps(
            {
                "id": "hld_0b1a7e11",
                "track": "orchestrator",
                "slice": "holdout",
                "title": "stub merge",
                "generator_id": "echo",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("strongorc.catalog.TASKS_ROOT", tmp_path / "public")
    monkeypatch.delenv("DURABLE_ORCH_HOLDOUT", raising=False)
    monkeypatch.setenv("STRONGORC_HOLDOUT", str(tmp_path / "overlay"))
    task = get_task("hld_0b1a7e11")
    assert task.family == "stub_family"
    assert task.rung == "r3"
    assert task.root == overlay


def test_generator_overlay_mutation_fails(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    overlay = tmp_path / "overlay" / "hld_0a0a0a0a"
    gens = overlay / "generators"
    gens.mkdir(parents=True)
    (overlay / "task.json").write_text(
        json.dumps(
            {
                "id": "hld_0a0a0a0a",
                "track": "worker",
                "slice": "holdout",
                "title": "mutator",
                "generator_id": "mutate",
            }
        ),
        encoding="utf-8",
    )
    (overlay / "prompt.md").write_text("mutate\n", encoding="utf-8")
    (gens / "mutate.py").write_text(
        "from pathlib import Path\n"
        "def generate(run_dir, nonce):\n"
        "    Path(__file__).resolve().parents[1].joinpath('touched').write_text('x')\n"
        "    dest = Path(run_dir) / '.holdout' / 'generated'\n"
        "    dest.mkdir(parents=True)\n"
        "    return dest\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("DURABLE_ORCH_HOLDOUT", raising=False)
    monkeypatch.setenv("STRONGORC_HOLDOUT", str(tmp_path / "overlay"))
    task = get_task("hld_0a0a0a0a")
    run_dir = tmp_path / "run"
    _seed_workspace(run_dir, "n")
    with pytest.raises(HoldoutError, match="mutated the overlay"):
        generate_hidden(task, run_dir, "n")


def test_generator_escaped_path_fails(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    overlay = tmp_path / "overlay" / "hld_0b0b0b0b"
    gens = overlay / "generators"
    gens.mkdir(parents=True)
    (overlay / "task.json").write_text(
        json.dumps(
            {
                "id": "hld_0b0b0b0b",
                "track": "worker",
                "slice": "holdout",
                "title": "escape",
                "generator_id": "escape",
            }
        ),
        encoding="utf-8",
    )
    (overlay / "prompt.md").write_text("escape\n", encoding="utf-8")
    (gens / "escape.py").write_text(
        "from pathlib import Path\n"
        "def generate(run_dir, nonce):\n"
        "    return Path(run_dir) / '..' / 'outside'\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("DURABLE_ORCH_HOLDOUT", raising=False)
    monkeypatch.setenv("STRONGORC_HOLDOUT", str(tmp_path / "overlay"))
    task = get_task("hld_0b0b0b0b")
    run_dir = tmp_path / "run"
    _seed_workspace(run_dir, "n")
    with pytest.raises(HoldoutError, match="escaped|outside"):
        generate_hidden(task, run_dir, "n")


def test_holdout_module_does_not_claim_sandbox() -> None:
    from strongorc import holdout as holdout_mod

    doc = " ".join((holdout_mod.__doc__ or "").split())
    assert "not a sandbox" in doc
    assert "trusted grader-side" in doc


def test_scrub_holdout_env_drops_overlay_path(fixture_overlay: Path) -> None:
    env = {"STRONGORC_HOLDOUT": str(fixture_overlay), "DURABLE_ORCH_HOLDOUT": str(fixture_overlay)}
    scrub_holdout_env(env)
    assert "STRONGORC_HOLDOUT" not in env
    assert "DURABLE_ORCH_HOLDOUT" not in env
    assert os.environ.get("STRONGORC_HOLDOUT") == str(fixture_overlay)
