from pathlib import Path

from strongorc.agentlib import finish
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)
model = MODEL
(run_dir / "src" / "gate.ts").write_text(
    "export function gate(n: number): number {\n  return n % 2 === 0 ? n : 0;\n}\n",
    encoding="utf-8",
)
(run_dir / "src" / "gate.js").unlink()

finish(run_dir, model, workers_ran=1, usd=0.15)
