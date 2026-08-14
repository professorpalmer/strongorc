from pathlib import Path

from strongorc.protocol import emit, write_receipt

run_dir = Path(RUN_DIR)
model = MODEL
src = run_dir / "src"

emit(run_dir, "wave2_started")
(src / "add.ts").write_text(
    "export function add(a: number, b: number): number {\n  return a + b;\n}\n",
    encoding="utf-8",
)
(src / "mul.ts").write_text(
    "export function mul(a: number, b: number): number {\n  return a * b;\n}\n",
    encoding="utf-8",
)
(src / "add.js").unlink()
(src / "mul.js").unlink()
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
