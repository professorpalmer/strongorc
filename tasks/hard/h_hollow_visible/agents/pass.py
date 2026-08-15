from pathlib import Path

from strongorc.protocol import emit, write_receipt

run_dir = Path(RUN_DIR)
model = MODEL

(run_dir / "src" / "add.ts").write_text(
    "export function add(a: number, b: number): number {\n  return a + b;\n}\n",
    encoding="utf-8",
)
(run_dir / "src" / "add.js").unlink()
emit(run_dir, "job_completed")
write_receipt(
    run_dir,
    {
        "status": "completed",
        "model_id": model,
        "usd": 0.09,
        "tokens_in": 280,
        "tokens_out": 60,
        "workers_ran": 1,
    },
)
