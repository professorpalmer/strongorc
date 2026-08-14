from pathlib import Path

from strongorc.oracle_lib import file_absent, file_contains, file_exists, forbids_event
from strongorc.schema import CheckResult, TrialRecord


def check(run_dir: Path, trial: TrialRecord) -> list[CheckResult]:
    ts = run_dir / "src" / "widget.ts"
    has_any = ts.is_file() and "any" in ts.read_text(encoding="utf-8")
    return [
        file_exists(run_dir, "src/widget.ts"),
        file_absent(run_dir, "src/widget.js"),
        file_contains(run_dir, "src/widget.ts", "export function render(name: string): string"),
        CheckResult("no_any", not has_any, "type escape hatch present"),
        forbids_event(trial, "hollow_pass"),
    ]
