from pathlib import Path

from strongorc.agentlib import finish

run_dir = Path(RUN_DIR)
model = MODEL
(run_dir / "src" / "add.ts").write_text(
    "export function add(a: number, b: number): number {\n  return a + b;\n}\n", encoding="utf-8"
)
(run_dir / "src" / "add.js").unlink()
finish(run_dir, model, workers_ran=1, usd=0.1)
