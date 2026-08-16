from pathlib import Path

from strongorc.agentlib import finish
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)
model = MODEL
emit(run_dir, "worker_started", worker="work")
(run_dir / "src" / "work" / "add.ts").write_text(
    "export function add(a: number, b: number): number {\n  return a + b;\n}\n", encoding="utf-8"
)
(run_dir / "src" / "work" / "add.js").unlink()
emit(run_dir, "worker_finished", worker="work")
finish(run_dir, model, workers_ran=1, usd=0.14)
