from pathlib import Path

from strongorc.nodeutil import run_node_test
from strongorc.protocol import emit, write_receipt

run_dir = Path(RUN_DIR)
model = MODEL
src = run_dir / "src"
harness = run_dir / ".harness"
harness.mkdir(parents=True, exist_ok=True)

emit(run_dir, "worker_started", worker="wave1")
(src / "add.ts").write_text(
    "export function add(a: number, b: number): number {\n  return a + b;\n}\n",
    encoding="utf-8",
)
(src / "add.js").unlink()
if run_node_test(run_dir, "test/wave1.mts").returncode != 0:
    raise SystemExit("wave1 failed")
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
if run_node_test(run_dir, "test/wave2.mts").returncode != 0:
    raise SystemExit("wave2 failed")
(harness / "wave2_verified").write_text("ok\n", encoding="utf-8")
emit(run_dir, "worker_finished", worker="wave2")
emit(run_dir, "wave2_verified", wave="wave2")
emit(run_dir, "wave3_started")
emit(run_dir, "worker_started", worker="wave3")
(src / "scale.ts").write_text(
    "export function scale(n: number): number {\n  return n * 10;\n}\n",
    encoding="utf-8",
)
(src / "scale.js").unlink()
emit(run_dir, "worker_finished", worker="wave3")
emit(run_dir, "job_completed")
write_receipt(
    run_dir,
    {
        "status": "completed",
        "model_id": model,
        "usd": 0.33,
        "tokens_in": 1800,
        "tokens_out": 420,
        "workers_ran": 3,
    },
)
