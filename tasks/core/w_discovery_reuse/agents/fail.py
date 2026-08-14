from pathlib import Path

from strongorc.protocol import emit, write_receipt

run_dir = Path(RUN_DIR)
model = MODEL
out = run_dir / "output"
out.mkdir(parents=True, exist_ok=True)

emit(run_dir, "llm_call", purpose="first")
(out / "first.txt").write_text("StrongOrc\n", encoding="utf-8")
emit(run_dir, "llm_call", purpose="second")
(out / "second.txt").write_text("StrongOrc\n", encoding="utf-8")
emit(run_dir, "job_completed")
write_receipt(
    run_dir,
    {
        "status": "completed",
        "model_id": model,
        "usd": 0.02,
        "tokens_in": 160,
        "tokens_out": 20,
        "workers_ran": 1,
    },
)
