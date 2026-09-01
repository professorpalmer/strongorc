from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from strongorc.calibrate import build_calibration_report, matrix_from_trial_paths
from strongorc.cards import build_card, hash_pre_register_config, resolve_card_measurement
from strongorc.catalog import list_tasks
from strongorc.grade import grade_trial
from strongorc.harness import isolated_runs_root, read_trials, run_slice, write_trials
from strongorc.holdout import HoldoutUnavailable, ensure_holdout_slice
from strongorc.instrument import (
    DEFAULT_SLICE,
    expand_slice_alias,
    is_retired_ranking_slice,
    retired_ranking_warning,
)
from strongorc.schema import (
    CONFINEMENT_VALUES,
    CONTAMINATION_VALUES,
    REGISTRY_STATUS_VALUES,
    Card,
)


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be >= 1")
    return parsed


def _adapter_kwargs(args: argparse.Namespace) -> dict:
    kwargs: dict = {}
    if args.adapter == "scripted":
        kwargs["persona"] = args.persona
    if args.adapter == "command":
        kwargs["cmd"] = args.cmd
    return kwargs


def _load_model_config(raw: str | None) -> dict:
    if not raw:
        return {}
    path = Path(raw)
    payload = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("model-config must be a JSON object")
    return payload


def _measurement_claim(args: argparse.Namespace, adapter: str) -> tuple[str, str, str]:
    try:
        return resolve_card_measurement(
            adapter=adapter,
            confinement=args.confinement,
            contamination=args.contamination,
            registry_status=args.registry_status,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc


def _add_measurement_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--confinement",
        choices=sorted(CONFINEMENT_VALUES),
        default="unknown",
        help="how the agent was boxed (default unknown)",
    )
    parser.add_argument(
        "--contamination",
        choices=sorted(CONTAMINATION_VALUES),
        default="unknown",
        help="leak status (default unknown; never inferred as clean)",
    )
    parser.add_argument(
        "--pre-register",
        default=None,
        help="pre-registration config path; stored on the card as SHA-256",
    )
    parser.add_argument(
        "--comparable-series",
        default="",
        help="named series this card may be compared against",
    )
    parser.add_argument(
        "--registry-status",
        choices=sorted(REGISTRY_STATUS_VALUES),
        default="unknown",
        help="registry inventory class (default unknown)",
    )
    parser.add_argument(
        "--model-config",
        default=None,
        dest="model_config",
        help="JSON object or path to JSON object of model parameters",
    )


def _guard_holdout(slice_name: str) -> None:
    try:
        ensure_holdout_slice(slice_name)
    except HoldoutUnavailable as exc:
        raise SystemExit(str(exc)) from exc


def _resolved_slice(slice_name: str) -> str:
    names = expand_slice_alias(slice_name)
    if len(names) != 1:
        raise SystemExit(
            "run one practice slice at a time, or use scripts/calibrate.py --slice practice"
        )
    return names[0]


def _warn_retired_slice(slice_name: str) -> None:
    if is_retired_ranking_slice(slice_name):
        print(retired_ranking_warning(slice_name), file=sys.stderr)


def cmd_list(args: argparse.Namespace) -> int:
    names = expand_slice_alias(args.slice)
    found = 0
    for name in names:
        _warn_retired_slice(name)
        tasks = list_tasks(name)
        found += len(tasks)
        for task in tasks:
            label = f"{name}\t" if len(names) > 1 else ""
            print(f"{label}{task.id}\t{task.track}\t{task.title}")
    return 0 if found else 1


def cmd_run(args: argparse.Namespace) -> int:
    slice_name = _resolved_slice(args.slice)
    _measurement_claim(args, args.adapter)
    _warn_retired_slice(slice_name)
    _guard_holdout(slice_name)
    runs_root = isolated_runs_root(Path(args.runs_dir), args.adapter)
    if runs_root != Path(args.runs_dir).resolve():
        print(f"command adapter: runs-dir is inside the bench checkout; using {runs_root}", file=sys.stderr)
    confinement, contamination, _status = _measurement_claim(args, args.adapter)
    out_path = Path(args.out) if args.out else None
    task_ids = None
    if out_path is not None and out_path.is_file():
        done = {trial.task_id for trial in read_trials(out_path)}
        pending = [task.id for task in list_tasks(slice_name) if task.id not in done]
        if not pending:
            trials = read_trials(out_path)
            print(f"{sum(1 for _ in trials)}/{len(trials)} already on disk")
            return 0
        task_ids = pending
        print(f"resuming {len(pending)} pending of {len(done) + len(pending)}", file=sys.stderr)

    def _stamp(trial, grade) -> None:
        trial.confinement = confinement
        trial.contamination = contamination

    results = run_slice(
        slice_name,
        adapter_name=args.adapter,
        model=args.model,
        runs_root=runs_root,
        adapter_kwargs=_adapter_kwargs(args),
        repeats=args.repeats,
        task_ids=task_ids,
        progress_path=out_path,
        on_trial=_stamp,
    )
    trials = [trial for trial, _ in results]
    grades = [grade for _, grade in results]
    if out_path is not None and not trials:
        write_trials(out_path, [])
    passed = sum(1 for grade in grades if grade.passed)
    print(f"{passed}/{len(grades)} passed")
    for trial, grade in results:
        mark = "PASS" if grade.passed else "FAIL"
        failed = [check.name for check in grade.checks if not check.passed]
        extra = f" ({', '.join(failed)})" if failed else ""
        print(f"  {mark}  {trial.task_id}{extra}")
    return 0 if passed == len(grades) else 1


def cmd_grade(args: argparse.Namespace) -> int:
    trials = read_trials(Path(args.trials))
    grades = [grade_trial(trial) for trial in trials]
    passed = sum(1 for grade in grades if grade.passed)
    print(f"{passed}/{len(grades)} passed")
    for grade in grades:
        mark = "PASS" if grade.passed else "FAIL"
        failed = [check.name for check in grade.checks if not check.passed]
        extra = f" ({', '.join(failed)})" if failed else ""
        print(f"  {mark}  {grade.task_id}{extra}")
    if args.out:
        Path(args.out).write_text(
            json.dumps([grade.to_dict() for grade in grades], indent=2) + "\n",
            encoding="utf-8",
        )
    return 0 if passed == len(grades) else 1


def _pct(rate: float) -> str:
    return f"{int(round(rate * 100))}%"


def _ci_text(bounds: list[float]) -> str:
    if len(bounds) != 2:
        return "n/a"
    return f"{_pct(bounds[0])}–{_pct(bounds[1])}"


def print_card_summary(card: Card) -> None:
    """Lead with unique-task counts, equalized score, family/rung, then fingerprint."""
    clustered = card.task_clustered_ci
    print(f"tasks  {card.tasks_passed}/{card.tasks_total}", file=sys.stderr)
    print(
        f"task_equalized  {_pct(card.task_equalized_score)}  "
        f"clustered {_ci_text(card.task_equalized_score_ci)}",
        file=sys.stderr,
    )
    if card.family_scores:
        bits = "  ".join(f"{name} {_pct(rate)}" for name, rate in card.family_scores.items())
        print(f"family  {bits}", file=sys.stderr)
    if card.rung_scores:
        bits = "  ".join(f"{name} {_pct(rate)}" for name, rate in card.rung_scores.items())
        print(f"rung  {bits}", file=sys.stderr)
    headline_ci = clustered.get("strongorc_score", card.strongorc_score_ci)
    print(
        f"strongorc  {_pct(card.strongorc_score)}  clustered {_ci_text(headline_ci)}",
        file=sys.stderr,
    )
    trial_rate = ((card.n_orch_pass + card.n_leaf_pass) / card.n_total) if card.n_total else 0.0
    hidden_ci = clustered.get("hidden", card.hidden_rate_ci)
    interrupt_ci = clustered.get("interrupt", card.interrupt_rate_ci)
    shape_ci = clustered.get("protocol_shape", card.protocol_shape_rate_ci)
    honesty_ci = clustered.get("honesty_earned", card.honesty_rate_earned_ci)
    print(
        f"{_pct(trial_rate)}  {_pct(card.hidden_rate)}  {_pct(card.interrupt_rate)}  "
        f"{_pct(card.protocol_shape_rate)}  {_pct(card.honesty_rate_earned)}  "
        f"clustered hidden {_ci_text(hidden_ci)} interrupt {_ci_text(interrupt_ci)} "
        f"protocol_shape {_ci_text(shape_ci)} honesty_earned {_ci_text(honesty_ci)}  "
        "# trials hidden interrupt protocol_shape honesty_earned",
        file=sys.stderr,
    )


def cmd_card(args: argparse.Namespace) -> int:
    slice_name = _resolved_slice(args.slice)
    _warn_retired_slice(slice_name)
    _guard_holdout(slice_name)
    trials = read_trials(Path(args.trials))
    if slice_name == "holdout" and not trials:
        raise SystemExit("holdout card refuses empty trials")
    adapters = {trial.adapter for trial in trials}
    if len(adapters) != 1:
        raise SystemExit(f"mixed adapters in trials: {sorted(adapters)}")
    adapter = adapters.pop()
    confinement, contamination, registry_status = _measurement_claim(args, adapter)
    pre_hash = hash_pre_register_config(args.pre_register) if args.pre_register else ""
    try:
        model_config = _load_model_config(args.model_config)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    grades = [grade_trial(trial) for trial in trials]
    card = build_card(
        trials,
        grades,
        model=args.model,
        slice_name=slice_name,
        adapter=adapter,
        model_config=model_config,
        confinement=confinement,
        contamination=contamination,
        pre_register_sha256=pre_hash,
        n_repeats_requested=args.repeats_requested,
        comparable_series=args.comparable_series,
        registry_status=registry_status,
    )
    print_card_summary(card)
    text = json.dumps(card.to_dict(), indent=2) + "\n"
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


def cmd_calibrate(args: argparse.Namespace) -> int:
    """Fit a response matrix from one jsonl per system. Does not call a model."""
    slice_name = _resolved_slice(args.slice)
    _warn_retired_slice(slice_name)
    _guard_holdout(slice_name)
    paths = [Path(item) for item in args.trials]
    try:
        matrix = matrix_from_trial_paths(
            paths,
            slice_name=slice_name,
            confinement=args.confinement,
            contamination=args.contamination,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    report = build_calibration_report(matrix, pre_register_path=args.preregister)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    print(text, end="")
    print(
        f"calibration  {report['status']}  systems {report['n_systems']}  "
        f"items {report['n_items']}  irt {report['irt_kind']}  "
        f"rewrite {len(report['rewrite'])}",
        file=sys.stderr,
    )
    for row in report.get("systems") or []:
        if row.get("scripted"):
            continue
        per_task = row.get("usd_per_task")
        per_task_s = f"{float(per_task):.2f}" if per_task is not None else "n/a"
        print(
            f"grain  {row.get('model')}  score {_pct(float(row.get('strongorc_score') or 0))}  "
            f"hidden {_pct(float(row.get('hidden_rate') or 0))}  "
            f"interrupt {_pct(float(row.get('interrupt_rate') or 0))}  "
            f"protocol {_pct(float(row.get('protocol_shape_rate') or row.get('protocol_check_rate') or 0))}  "
            f"honesty {_pct(float(row.get('honesty_rate_earned') or 0))}  "
            f"usd {float(row.get('usd_total') or 0):.2f}  "
            f"usd/task {per_task_s}",
            file=sys.stderr,
        )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="strongorc")
    sub = parser.add_subparsers(dest="command", required=True)

    list_p = sub.add_parser("list", help="list tasks in a slice")
    list_p.add_argument("--slice", default=DEFAULT_SLICE)
    list_p.set_defaults(func=cmd_list)

    run_p = sub.add_parser("run", help="run a slice through an adapter")
    run_p.add_argument("--slice", default=DEFAULT_SLICE)
    run_p.add_argument("--adapter", choices=["scripted", "command"], default="scripted")
    run_p.add_argument("--persona", choices=["pass", "fail"], default="pass")
    run_p.add_argument("--cmd", default=None, help="shell command for the command adapter")
    run_p.add_argument("--model", default="scripted")
    run_p.add_argument("--runs-dir", default="runs")
    run_p.add_argument("--out", default=None, help="write trials.jsonl")
    run_p.add_argument(
        "--repeats",
        type=_positive_int,
        default=1,
        metavar="N",
        help="run each task N times (default 1)",
    )
    _add_measurement_args(run_p)
    run_p.set_defaults(func=cmd_run)

    grade_p = sub.add_parser("grade", help="regrade frozen trials without calling a model")
    grade_p.add_argument("trials")
    grade_p.add_argument("--out", default=None)
    grade_p.set_defaults(func=cmd_grade)

    card_p = sub.add_parser("card", help="emit a dated score card")
    card_p.add_argument("trials")
    card_p.add_argument("--model", required=True)
    card_p.add_argument("--slice", default=DEFAULT_SLICE)
    card_p.add_argument("--out", default=None)
    card_p.add_argument(
        "--repeats-requested",
        type=_positive_int,
        default=None,
        dest="repeats_requested",
        metavar="N",
        help="attempt count that was requested (defaults to observed n_attempts)",
    )
    _add_measurement_args(card_p)
    card_p.set_defaults(func=cmd_card)

    cal_p = sub.add_parser(
        "calibrate",
        help="fit a same-harness response matrix; does not call a model",
    )
    cal_p.add_argument("trials", nargs="+", help="one trials.jsonl per system")
    cal_p.add_argument("--slice", default=DEFAULT_SLICE)
    cal_p.add_argument("--out", default=None, help="write calibration report JSON")
    cal_p.add_argument(
        "--preregister",
        default=None,
        help="pre-registration JSON; stored on the report as SHA-256",
    )
    cal_p.add_argument(
        "--confinement",
        choices=sorted(CONFINEMENT_VALUES),
        default="unknown",
    )
    cal_p.add_argument(
        "--contamination",
        choices=sorted(CONTAMINATION_VALUES),
        default="unknown",
    )
    cal_p.set_defaults(func=cmd_calibrate)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
