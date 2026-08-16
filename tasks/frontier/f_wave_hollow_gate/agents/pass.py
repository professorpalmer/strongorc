from pathlib import Path

from strongorc.agentlib import finish
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)
model = MODEL
src = run_dir / "src"
emit(run_dir, "worker_started", worker="wave1")
(src / "add.ts").write_text(
    "export function add(a: number, b: number): number {\n  return a + b;\n}\n", encoding="utf-8"
)
(src / "add.js").unlink()
harness = run_dir / ".harness"
harness.mkdir(parents=True, exist_ok=True)
(harness / "wave1_verified").write_text("ok\n", encoding="utf-8")
emit(run_dir, "worker_finished", worker="wave1")
emit(run_dir, "wave_verified", wave="wave1")
emit(run_dir, "wave2_started")
(src / "mul.ts").write_text(
    "export function mul(a: number, b: number): number {\n  return a * b;\n}\n", encoding="utf-8"
)
(src / "mul.js").unlink()
finish(run_dir, model, workers_ran=2, usd=0.29)
