from pathlib import Path

from strongorc.protocol import emit, write_receipt

run_dir = Path(RUN_DIR)
model = MODEL

emit(run_dir, "artifact_consumed", path="job/spec.json")
(run_dir / "src" / "scale.ts").write_text(
    "export function scale(n: number): number {\n  return n * 3;\n}\n",
    encoding="utf-8",
)
(run_dir / "src" / "scale.js").unlink()
emit(run_dir, "job_completed")
write_receipt(
    run_dir,
    {
        "status": "completed",
        "model_id": model,
        "usd": 0.11,
        "tokens_in": 400,
        "tokens_out": 80,
        "workers_ran": 1,
    },
)
