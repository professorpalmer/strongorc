from pathlib import Path

from strongorc.agentlib import finish
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)
model = MODEL
(run_dir / "src" / "span.ts").write_text(
    "export function span(lo: number, hi: number): number {\n  return hi - lo + 1;\n}\n",
    encoding="utf-8",
)
(run_dir / "src" / "span.js").unlink()

finish(run_dir, model, workers_ran=1, usd=0.15)
