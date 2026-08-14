from pathlib import Path

from strongorc.nodeutil import run_node_test
from strongorc.protocol import emit, write_receipt

run_dir = Path(RUN_DIR)
model = MODEL
src = run_dir / "src"

emit(run_dir, "worker_started", worker="wave1")
(src / "add.ts").write_text(
    "export function add(a: number, b: number): number {\n  return a + b;\n}\n",
    encoding="utf-8",
)
(src / "add.js").unlink()
wave1 = run_node_test(run_dir, "test/wave1.mts")
if wave1.returncode != 0:
    raise SystemExit(wave1.stderr or wave1.stdout)
harness = run_dir / ".harness"
harness.mkdir(parents=True, exist_ok=True)
(harness / "wave1_verified").write_text("ok\n", encoding="utf-8")
emit(run_dir, "worker_finished", worker="wave1")
emit(run_dir, "wave_verified", wave="wave1")
emit(run_dir, "wave2_started")
emit(run_dir, "worker_started", worker="wave2")
(src / "mul.ts").write_text(
    "export function mul(a: number, b: number): number {\n  return a * b;\n}\n",
    encoding="utf-8",
)
(src / "mul.js").unlink()
emit(run_dir, "worker_finished", worker="wave2")
emit(run_dir, "job_completed")
write_receipt(
    run_dir,
    {
        "status": "completed",
        "model_id": model,
        "usd": 0.27,
        "tokens_in": 1400,
        "tokens_out": 360,
        "workers_ran": 2,
    },
)
