from pathlib import Path

from strongorc.agentlib import finish
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)
model = MODEL
(run_dir / "src" / "clamp.ts").write_text(
    "export function clamp(n: number): number {\n  return n < 0 ? 0 : n > 10 ? 10 : n;\n}\n",
    encoding="utf-8",
)
(run_dir / "src" / "clamp.js").unlink()

finish(run_dir, model, workers_ran=1, usd=0.15)
