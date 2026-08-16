from pathlib import Path

from strongorc.protocol import emit, write_receipt

run_dir = Path(RUN_DIR)
model = MODEL
src = run_dir / "src"

emit(run_dir, "wave2_started")
emit(run_dir, "wave3_started")
(src / "add.ts").write_text(
    "export function add(a: number, b: number): number {\n  return a + b;\n}\n",
    encoding="utf-8",
)
(src / "mul.ts").write_text(
    "export function mul(a: number, b: number): number {\n  return a * b;\n}\n",
    encoding="utf-8",
)
(src / "scale.ts").write_text(
    "export function scale(n: number): number {\n  return n * 10;\n}\n",
    encoding="utf-8",
)
(src / "add.js").unlink()
(src / "mul.js").unlink()
(src / "scale.js").unlink()
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
