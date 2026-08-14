from pathlib import Path

from durable_orch_bench.protocol import emit, write_receipt

run_dir = Path(RUN_DIR)
model = MODEL
progress = run_dir / "progress"
progress.mkdir(parents=True, exist_ok=True)

(progress / "step1.done").unlink(missing_ok=True)
(progress / "step2.done").write_text("step2\n", encoding="utf-8")
(progress / "step3.done").write_text("step3\n", encoding="utf-8")
emit(run_dir, "job_completed")
write_receipt(
    run_dir,
    {
        "status": "completed",
        "model_id": model,
        "usd": 0.03,
        "tokens_in": 120,
        "tokens_out": 30,
        "workers_ran": 1,
    },
)
