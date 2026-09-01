#!/usr/bin/env python3
"""Run or fit the StrongOrc calibration protocol.

Scripted pass/fail is oracle non-vacuity, not a model result. Live rows
default to the OpenRouter confined jail (``examples/openrouter_agent.py``).

``--channel cursor-sdk`` is leak-diagnostic on this checkout.
``--channel openrouter`` is the official confined ranking path.
``openrouter-shell`` adds ``run_command`` and remains an unconfined jail
ablation. Do not ``--fit`` shell jsonl with confined jsonl.
``--channel agentic-opencode`` is a different adapter dialect (no
``emit_event``). Do not mix those jsonl files. IRT is fitted only from
the resulting jsonl, and refuses mixed confinement.

Examples::

    python scripts/calibrate.py --slice reason --scripted
    python scripts/calibrate.py --slice ranking --validate-only
    python scripts/calibrate.py --slice practice --live stealth/ox-alpha --max-usd-per-task 1
    python scripts/calibrate.py --slice ranking --live stealth/ox-alpha --jobs 2 --max-usd-per-task 1
    python scripts/calibrate.py --fit ~/.strongorc/calibration/reason/*.jsonl
    python scripts/calibrate.py --slice reason --channel cursor-sdk --live grok-4.6
    python scripts/calibrate.py --slice reason --channel agentic-opencode --live ox-alpha-free
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from strongorc.calibrate import (  # noqa: E402
    build_calibration_report,
    infrastructure_censor_reason,
    matrix_from_trial_paths,
)
from strongorc.cards import hash_pre_register_config  # noqa: E402
from strongorc.catalog import list_tasks  # noqa: E402
from strongorc.grade import grade_trial  # noqa: E402
from strongorc.harness import (  # noqa: E402
    isolated_runs_root,
    merge_slice_trials,
    read_trials,
    run_slice,
    write_trials,
)
from strongorc.holdout import (  # noqa: E402
    HoldoutError,
    overlay_root,
    verify_overlay_commitment,
)
from strongorc.instrument import (  # noqa: E402
    PRACTICE_ALIAS,
    RANKING_ALIAS,
    assess_ranking_tasks,
    calibration_dest,
    default_live_channel,
    expand_slice_alias,
    is_retired_ranking_slice,
    practice_sweep_warning,
    retired_ranking_warning,
    validate_paid_live_request,
)

DEFAULT_PREREGISTER = ROOT / "cards" / "preregister" / "reason-0.6.0.json"
OPENCODE_PREREGISTER = ROOT / "cards" / "preregister" / "reason-0.6.0-opencode-go.json"
OPENROUTER_PREREGISTER = ROOT / "cards" / "preregister" / "reason-0.6.0-openrouter.json"
OPENROUTER_SHELL_PREREGISTER = ROOT / "cards" / "preregister" / "reason-0.6.0-openrouter-shell.json"
RANKING_PREREGISTER = (
    ROOT / "cards" / "preregister" / "holdout-0.6.0-openrouter-ranking-v1.json"
)
DEFAULT_OUT_ROOT = Path.home() / ".strongorc" / "calibration"
LIVE_CHANNELS = ("cursor-sdk", "agentic-opencode", "openrouter", "openrouter-shell")


def _load_preregister(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("pre-register file must be a JSON object")
    return payload


def _run_scripted(slice_name: str, dest: Path) -> list[Path]:
    paths: list[Path] = []
    for persona, model in (("pass", "scripted-pass"), ("fail", "scripted-fail")):
        results = run_slice(
            slice_name,
            adapter_name="scripted",
            model=model,
            runs_root=dest / f"{slice_name}-{persona}",
            adapter_kwargs={"persona": persona},
        )
        trials = [trial for trial, _ in results]
        path = dest / f"{slice_name}-{model}.jsonl"
        write_trials(path, trials)
        passed = sum(1 for _, grade in results if grade.passed)
        print(f"scripted {model}: {passed}/{len(results)} passed -> {path}", file=sys.stderr)
        paths.append(path)
    return paths


def _validate_slice(slice_name: str) -> dict:
    tasks = list_tasks(slice_name)
    errors: list[str] = []
    structure = None
    if slice_name == "holdout":
        structure = assess_ranking_tasks(tasks)
        errors.extend(structure.errors)
        try:
            commitment_sha256 = verify_overlay_commitment()
        except HoldoutError as exc:
            commitment_sha256 = ""
            errors.append(str(exc))
    else:
        commitment_sha256 = ""
    scripted: dict[str, dict[str, int]] = {}
    if not errors:
        with tempfile.TemporaryDirectory(prefix=f"strongorc-{slice_name}-validate-") as raw:
            root = Path(raw)
            personas = [("pass", "scripted-pass"), ("fail", "scripted-fail")]
            if slice_name == "holdout":
                personas.extend(
                    [
                        ("fail_outcome", "scripted-fail-outcome"),
                        ("fail_protocol", "scripted-fail-protocol"),
                    ]
                )
                for persona in ("fail_assignment_blind", "fail_protocol_only"):
                    if all(task.agent_path(persona).is_file() for task in tasks):
                        personas.append((persona, f"scripted-{persona.replace('_', '-')}"))
            for persona, model in personas:
                results = run_slice(
                    slice_name,
                    adapter_name="scripted",
                    model=model,
                    runs_root=root / persona,
                    adapter_kwargs={"persona": persona},
                )
                passed = sum(1 for _, grade in results if grade.passed)
                scripted[persona] = {
                    "passed": passed,
                    "outcome_passed": sum(
                        1 for _, grade in results if grade.outcome_passed
                    ),
                    "protocol_passed": sum(
                        1 for _, grade in results if grade.protocol_passed
                    ),
                    "honesty_passed": sum(
                        1 for _, grade in results if grade.honesty_passed
                    ),
                    "total": len(results),
                }
        if scripted["pass"]["passed"] != len(tasks):
            errors.append(
                "scripted pass must pass every task; "
                f"passed {scripted['pass']['passed']}/{len(tasks)}"
            )
        for persona, result in scripted.items():
            if persona == "pass" or result["passed"] == 0:
                continue
            errors.append(
                f"scripted {persona} must pass no tasks; "
                f"passed {result['passed']}/{len(tasks)}"
            )
        if slice_name == "holdout":
            outcome_slip = scripted["fail_outcome"]
            if outcome_slip["outcome_passed"] != 0:
                errors.append("fail_outcome must fail outcome on every ranking task")
            if outcome_slip["protocol_passed"] != len(tasks):
                errors.append("fail_outcome must preserve protocol on every ranking task")
            protocol_slip = scripted["fail_protocol"]
            if protocol_slip["outcome_passed"] != len(tasks):
                errors.append("fail_protocol must preserve outcome on every ranking task")
            if protocol_slip["protocol_passed"] != 0:
                errors.append("fail_protocol must fail protocol on every ranking task")
    return {
        "slice": slice_name,
        "ready": not errors,
        "tasks_total": len(tasks),
        "structure": structure.to_dict() if structure is not None else None,
        "private_bank_commitment_sha256": commitment_sha256,
        "scripted": scripted,
        "errors": errors,
    }


def _live_command(cmd: str | None, channel: str) -> str:
    if cmd:
        return cmd
    if channel == "agentic-opencode":
        return f"{sys.executable} {ROOT / 'examples' / 'agentic_opencode_agent.py'}"
    if channel == "openrouter":
        return f"{sys.executable} {ROOT / 'examples' / 'openrouter_agent.py'}"
    if channel == "openrouter-shell":
        return f"{sys.executable} {ROOT / 'examples' / 'openrouter_agent.py'} --allow-shell"
    return f"{sys.executable} {ROOT / 'examples' / 'cursor_agent.py'}"


def _preregister_for_channel(path: Path, channel: str, slice_name: str = "reason") -> Path:
    if path != DEFAULT_PREREGISTER:
        return path
    if slice_name == "holdout" and channel == "openrouter":
        return RANKING_PREREGISTER
    if channel == "agentic-opencode":
        return OPENCODE_PREREGISTER
    if channel == "openrouter":
        slice_path = ROOT / "cards" / "preregister" / f"{slice_name}-0.6.0-openrouter.json"
        if slice_path.is_file():
            return slice_path
        return OPENROUTER_PREREGISTER
    if channel == "openrouter-shell":
        slice_path = ROOT / "cards" / "preregister" / f"{slice_name}-0.6.0-openrouter-shell.json"
        if slice_path.is_file():
            return slice_path
        return OPENROUTER_SHELL_PREREGISTER
    return path


def _parse_task_ids(raw: str | None) -> list[str] | None:
    if raw is None or not raw.strip():
        return None
    return [item.strip() for item in raw.split(",") if item.strip()]


def _private_initial_cell_ids() -> list[str]:
    root = overlay_root()
    if root is None:
        raise SystemExit("initial cell requires STRONGORC_HOLDOUT")
    path = root / "BANK.json"
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit("private BANK.json is unavailable or invalid") from exc
    entries = manifest.get("initial_cell") if isinstance(manifest, dict) else None
    if not isinstance(entries, list) or not entries:
        raise SystemExit("private BANK.json has no frozen initial_cell")
    task_ids = [
        str(entry.get("task_id") or "")
        for entry in entries
        if isinstance(entry, dict)
    ]
    if len(task_ids) != len(entries) or any(not task_id for task_id in task_ids):
        raise SystemExit("private BANK.json initial_cell is malformed")
    if len(set(task_ids)) != len(task_ids):
        raise SystemExit("private BANK.json initial_cell contains duplicate tasks")
    return task_ids


def _run_live(
    *,
    slice_name: str,
    model: str,
    cmd: str,
    dest: Path,
    repeats: int,
    jobs: int,
    confinement: str,
    contamination: str,
    max_usd_per_task: float | None,
    task_ids: list[str] | None = None,
    rerun_selected: bool = False,
) -> Path:
    runs_root = isolated_runs_root(dest / f"{slice_name}-{model.replace('/', '_')}", "command")
    path = dest / f"{slice_name}-{model.replace('/', '_')}.jsonl"
    existing = read_trials(path) if path.is_file() else []
    candidate_task_ids = task_ids or [task.id for task in list_tasks(slice_name)]
    completed_attempts = {
        (trial.task_id, trial.attempt)
        for trial in existing
        if infrastructure_censor_reason(trial) is None
        and not (rerun_selected and trial.task_id in candidate_task_ids)
    }
    pending = [
        task_id
        for task_id in candidate_task_ids
        if any(
            (task_id, attempt) not in completed_attempts
            for attempt in range(repeats)
        )
    ]
    if not pending:
        print(f"live {model}: already complete -> {path}", file=sys.stderr)
        return path
    pending_attempt_count = sum(
        (task_id, attempt) not in completed_attempts
        for task_id in pending
        for attempt in range(repeats)
    )
    if max_usd_per_task is not None:
        planned_ceiling = pending_attempt_count * max_usd_per_task
        print(
            f"paid budget threshold: {pending_attempt_count} pending attempts x "
            f"${max_usd_per_task:.2f} = ${planned_ceiling:.2f}; "
            "each task may overshoot by its final generation",
            file=sys.stderr,
        )

    def _stamp(trial, grade) -> None:
        trial.confinement = confinement
        trial.contamination = contamination

    extra_env = {}
    if max_usd_per_task is not None:
        extra_env["STRONGORC_MAX_USD"] = str(max_usd_per_task)
    results = run_slice(
        slice_name,
        adapter_name="command",
        model=model,
        runs_root=runs_root,
        adapter_kwargs={"cmd": cmd, "extra_env": extra_env},
        repeats=repeats,
        jobs=jobs,
        task_ids=pending,
        skip_attempts=completed_attempts,
        progress_path=path,
        on_trial=_stamp,
    )
    trials = [trial for trial, _ in results]
    if path.is_file():
        trials = merge_slice_trials(slice_name, read_trials(path), trials)
        write_trials(path, trials)
    elif not path.is_file():
        write_trials(path, trials)
    passed = sum(1 for trial, _grade in results if grade_trial(trial).passed)
    print(f"live {model}: {passed}/{len(results)} passed -> {path}", file=sys.stderr)
    return path


def _fit(
    paths: list[Path],
    slice_name: str,
    preregister: Path,
    out: Path,
    *,
    confinement: str = "unknown",
    contamination: str = "unknown",
) -> int:
    if all(trial_path.name.find("scripted") >= 0 for trial_path in paths):
        confinement = "scripted"
        contamination = "unknown"
    matrix = matrix_from_trial_paths(
        paths,
        slice_name=slice_name,
        confinement=confinement,
        contamination=contamination,
    )
    report = build_calibration_report(matrix, pre_register_path=preregister)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"calibration  {report['status']}  systems {report['n_systems']}  "
        f"items {report['n_items']}  irt {report['irt_kind']}  "
        f"rewrite {len(report['rewrite'])}  sha {hash_pre_register_config(preregister)[:12]}",
        file=sys.stderr,
    )
    print(out)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="scripts/calibrate.py")
    parser.add_argument(
        "--slice",
        default="reason",
        help="slice name, 'practice' for brutal+native+ladder+reason, or 'ranking' for holdout",
    )
    parser.add_argument("--scripted", action="store_true", help="run scripted pass and fail")
    parser.add_argument(
        "--live",
        action="append",
        default=[],
        metavar="MODEL",
        help="run one live model via the selected --channel (repeatable)",
    )
    parser.add_argument(
        "--channel",
        choices=LIVE_CHANNELS,
        default=None,
        help="omit to use confined openrouter",
    )
    parser.add_argument("--fit", nargs="*", default=None, help="existing trials.jsonl files")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument(
        "--jobs",
        type=int,
        default=1,
        help="run this many live tasks at once (isolated run dirs)",
    )
    parser.add_argument("--cmd", default=None, help="override command adapter argv")
    parser.add_argument(
        "--max-usd-per-task",
        type=float,
        default=None,
        help="required OpenRouter stop threshold; a task may overshoot by one generation",
    )
    parser.add_argument(
        "--allow-high-concurrency",
        action="store_true",
        help="explicitly allow more than two concurrent paid tasks",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="run structural and scripted preflight without a live model",
    )
    parser.add_argument(
        "--tasks",
        default=None,
        help="comma-separated task ids; merge into an existing slice jsonl",
    )
    parser.add_argument(
        "--rerun-selected",
        action="store_true",
        help="replace existing attempts for explicitly selected --tasks",
    )
    parser.add_argument(
        "--initial-cell",
        action="store_true",
        help="run the exact canary task ids frozen in the private bank manifest",
    )
    parser.add_argument("--preregister", default=str(DEFAULT_PREREGISTER))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_ROOT))
    parser.add_argument("--report", default=None, help="report JSON path")
    args = parser.parse_args(argv)

    if args.repeats < 1:
        raise SystemExit("repeats must be >= 1")
    if args.jobs < 1:
        raise SystemExit("jobs must be >= 1")
    if args.channel is None:
        args.channel = default_live_channel(args.slice)
    task_ids = _parse_task_ids(args.tasks)
    if args.rerun_selected and not task_ids:
        raise SystemExit("--rerun-selected requires --tasks")
    if args.initial_cell and task_ids:
        raise SystemExit("--initial-cell and --tasks are mutually exclusive")
    slices = expand_slice_alias(args.slice)
    if args.slice == PRACTICE_ALIAS:
        print(practice_sweep_warning(), file=sys.stderr)
    if len(slices) > 1 and args.report:
        raise SystemExit("practice sweeps write per-slice reports; omit --report")
    if len(slices) > 1:
        rc = 0
        for name in slices:
            child = list(argv if argv is not None else sys.argv[1:])
            replaced = False
            out: list[str] = []
            skip = False
            for item in child:
                if skip:
                    skip = False
                    continue
                if item == "--slice":
                    skip = True
                    out.extend(["--slice", name])
                    replaced = True
                    continue
                out.append(item)
            if not replaced:
                out.extend(["--slice", name])
            rc = max(rc, main(out))
        return rc
    if is_retired_ranking_slice(args.slice):
        print(retired_ranking_warning(args.slice), file=sys.stderr)
    if args.channel == "cursor-sdk":
        print(
            "cursor-sdk live rows are leak diagnostics on this checkout; "
            "do not mix them with openrouter jail jsonl",
            file=sys.stderr,
        )
    if args.channel == "openrouter-shell":
        print(
            "openrouter-shell is an unconfined jail-ablation series; "
            "do not fit it with confined openrouter jsonl",
            file=sys.stderr,
        )
    slice_name = slices[0]
    preregister = _preregister_for_channel(
        Path(args.preregister), args.channel, slice_name
    )
    spec = _load_preregister(preregister) if preregister.is_file() else {}
    validation = None
    if args.validate_only or args.live:
        validation = _validate_slice(slice_name)
        if slice_name == "holdout":
            expected_commitment = str(
                spec.get("private_bank_commitment_sha256") or ""
            ).strip()
            actual_commitment = str(
                validation.get("private_bank_commitment_sha256") or ""
            )
            if not expected_commitment:
                validation["errors"].append(
                    "ranking preregister is missing private bank commitment"
                )
            elif actual_commitment != expected_commitment:
                validation["errors"].append(
                    "private holdout bank does not match the preregistered commitment"
                )
            validation["ready"] = not validation["errors"]
    if args.initial_cell:
        if slice_name != "holdout":
            raise SystemExit("--initial-cell is only valid for the ranking holdout")
        task_ids = _private_initial_cell_ids()
        expected_size = int(spec.get("initial_cell_tasks") or 0)
        if expected_size and len(task_ids) != expected_size:
            raise SystemExit(
                "private initial cell size does not match the preregistration"
            )
    if args.validate_only:
        print(json.dumps(validation, indent=2, sort_keys=True))
        return 0 if validation and validation["ready"] else 2
    if args.live:
        if not validation or not validation["ready"]:
            reasons = "; ".join(validation["errors"] if validation else ["unknown"])
            raise SystemExit(f"instrument preflight failed: {reasons}")
        try:
            validate_paid_live_request(
                channel=args.channel,
                jobs=args.jobs,
                max_usd_per_task=args.max_usd_per_task,
                allow_high_concurrency=args.allow_high_concurrency,
            )
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
    dest = calibration_dest(Path(args.out_dir), args.slice, args.channel)
    dest.mkdir(parents=True, exist_ok=True)
    confinement = str(spec.get("confinement") or "unknown")
    contamination = str(spec.get("contamination") or "unknown")
    paths: list[Path] = []
    if args.scripted:
        paths.extend(_run_scripted(slice_name, dest))
    if args.live:
        cmd = _live_command(args.cmd, args.channel)
        for model in args.live:
            paths.append(
                _run_live(
                    slice_name=slice_name,
                    model=model,
                    cmd=cmd,
                    dest=dest,
                    repeats=args.repeats,
                    jobs=args.jobs,
                    confinement=confinement,
                    contamination=contamination,
                    max_usd_per_task=args.max_usd_per_task,
                    task_ids=task_ids,
                    rerun_selected=args.rerun_selected,
                )
            )
    if args.fit is not None:
        paths.extend(Path(item) for item in args.fit)
    if not paths:
        raise SystemExit("provide --scripted, --live MODEL, and/or --fit jsonl")
    report_path = Path(args.report) if args.report else dest / "report.json"
    return _fit(
        paths,
        args.slice,
        preregister,
        report_path,
        confinement=str(spec.get("confinement") or "unknown"),
        contamination=str(spec.get("contamination") or "unknown"),
    )


if __name__ == "__main__":
    raise SystemExit(main())
