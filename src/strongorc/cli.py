from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from strongorc.cards import build_card
from strongorc.catalog import list_tasks
from strongorc.grade import grade_trial
from strongorc.harness import read_trials, run_slice, write_trials


def _adapter_kwargs(args: argparse.Namespace) -> dict:
    kwargs: dict = {}
    if args.adapter == "scripted":
        kwargs["persona"] = args.persona
    if args.adapter == "command":
        kwargs["cmd"] = args.cmd
    return kwargs


def cmd_list(args: argparse.Namespace) -> int:
    tasks = list_tasks(args.slice)
    for task in tasks:
        print(f"{task.id}\t{task.track}\t{task.title}")
    return 0 if tasks else 1


def cmd_run(args: argparse.Namespace) -> int:
    runs_root = Path(args.runs_dir).resolve()
    results = run_slice(
        args.slice,
        adapter_name=args.adapter,
        model=args.model,
        runs_root=runs_root,
        adapter_kwargs=_adapter_kwargs(args),
    )
    trials = [trial for trial, _ in results]
    grades = [grade for _, grade in results]
    if args.out:
        write_trials(Path(args.out), trials)
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


def cmd_card(args: argparse.Namespace) -> int:
    trials = read_trials(Path(args.trials))
    grades = [grade_trial(trial) for trial in trials]
    card = build_card(trials, grades, model=args.model, slice_name=args.slice)
    text = json.dumps(card.to_dict(), indent=2) + "\n"
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="strongorc")
    sub = parser.add_subparsers(dest="command", required=True)

    list_p = sub.add_parser("list", help="list tasks in a slice")
    list_p.add_argument("--slice", default="core")
    list_p.set_defaults(func=cmd_list)

    run_p = sub.add_parser("run", help="run a slice through an adapter")
    run_p.add_argument("--slice", default="core")
    run_p.add_argument("--adapter", choices=["scripted", "command"], default="scripted")
    run_p.add_argument("--persona", choices=["pass", "fail"], default="pass")
    run_p.add_argument("--cmd", default=None, help="shell command for the command adapter")
    run_p.add_argument("--model", default="scripted")
    run_p.add_argument("--runs-dir", default="runs")
    run_p.add_argument("--out", default=None, help="write trials.jsonl")
    run_p.set_defaults(func=cmd_run)

    grade_p = sub.add_parser("grade", help="regrade frozen trials without calling a model")
    grade_p.add_argument("trials")
    grade_p.add_argument("--out", default=None)
    grade_p.set_defaults(func=cmd_grade)

    card_p = sub.add_parser("card", help="emit a dated score card")
    card_p.add_argument("trials")
    card_p.add_argument("--model", required=True)
    card_p.add_argument("--slice", default="core")
    card_p.add_argument("--out", default=None)
    card_p.set_defaults(func=cmd_card)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
