#!/usr/bin/env python3
"""Keep a live calibration wave alive after the chat session dies.

If the wave pid vanishes before its jsonl and report exist, restart
that wave only. Stdlib only.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = ROOT / ".venv" / "bin" / "python"
OUT_ROOT = Path.home() / ".strongorc" / "calibration"
LOG = OUT_ROOT / "watchdog.log"
POLL_SECONDS = 60


def artifact_paths(
    out_root: Path,
    slice_name: str,
    live: str,
    channel: str = "openrouter",
) -> tuple[Path, Path, Path]:
    """jsonl, report, and live log. Dest is slice/channel so jail and leak cannot clobber."""
    from strongorc.instrument import expand_slice_alias

    slug = live.replace("/", "_")
    dest = out_root / slice_name / channel
    resolved = expand_slice_alias(slice_name)[0]
    return (
        dest / f"{resolved}-{slug}.jsonl",
        dest / f"report-{slug}.json",
        dest / f"live-{slug}.log",
    )


def stamp(message: str) -> None:
    line = f"{datetime.now(timezone.utc).strftime('%H:%M:%SZ')} {message}"
    print(line, flush=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def wave_running(needle: str) -> bool:
    completed = subprocess.run(
        ["pgrep", "-f", needle],
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.returncode == 0 and bool(completed.stdout.strip())


def start_wave(cmd: list[str], log_path: Path) -> int:
    keep = {"STRONGORC_HOLDOUT", "DURABLE_ORCH_HOLDOUT"}
    env = {
        key: value
        for key, value in os.environ.items()
        if (not key.startswith("STRONGORC_")) or key in keep
    }
    env["PATH"] = os.environ.get("PATH", "")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handle = log_path.open("a")
    proc = subprocess.Popen(
        cmd,
        cwd=str(ROOT),
        env=env,
        stdout=handle,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    return proc.pid


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="scripts/watch_calibrate.py")
    parser.add_argument("--channel", default="openrouter")
    parser.add_argument("--live", required=True)
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--slice", default="reason")
    parser.add_argument("--out-dir", default=str(OUT_ROOT))
    parser.add_argument("--max-usd-per-task", type=float, required=True)
    parser.add_argument("--allow-high-concurrency", action="store_true")
    args = parser.parse_args(argv)
    if args.jobs < 1:
        raise SystemExit("jobs must be >= 1")
    from strongorc.instrument import validate_paid_live_request

    try:
        validate_paid_live_request(
            channel=args.channel,
            jobs=args.jobs,
            max_usd_per_task=args.max_usd_per_task,
            allow_high_concurrency=args.allow_high_concurrency,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    out_root = Path(args.out_dir)
    jsonl, report, log_path = artifact_paths(out_root, args.slice, args.live, args.channel)
    python = str(PY if PY.is_file() else sys.executable)
    cmd = [
        python,
        str(ROOT / "scripts" / "calibrate.py"),
        "--slice",
        args.slice,
        "--channel",
        args.channel,
        "--live",
        args.live,
        "--jobs",
        str(args.jobs),
        "--out-dir",
        str(out_root),
        "--max-usd-per-task",
        str(args.max_usd_per_task),
        "--report",
        str(report),
    ]
    if args.allow_high_concurrency:
        cmd.append("--allow-high-concurrency")
    needle = f"calibrate.py --slice {args.slice} --channel {args.channel} --live {args.live}"
    stamp(f"watchdog start slice={args.slice} {args.channel} {args.live} jobs={args.jobs}")
    if not wave_running(needle) and not (jsonl.is_file() and report.is_file()):
        pid = start_wave(cmd, log_path)
        stamp(f"start {args.live} pid={pid}")
    while True:
        if jsonl.is_file() and report.is_file():
            stamp(f"wave finished {jsonl}")
            return 0
        if not wave_running(needle):
            pid = start_wave(cmd, log_path)
            stamp(f"restart {args.live} pid={pid}")
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
