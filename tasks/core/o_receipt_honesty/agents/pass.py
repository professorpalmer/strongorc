from pathlib import Path

from strongorc.protocol import emit, write_receipt

run_dir = Path(RUN_DIR)
model = MODEL
(run_dir / "output").mkdir(parents=True, exist_ok=True)

emit(run_dir, "worker_started", worker="billed")
(run_dir / "output" / "work.txt").write_text("DONE\n", encoding="utf-8")
emit(run_dir, "worker_finished", worker="billed")
emit(run_dir, "job_completed")
write_receipt(
    run_dir,
    {
        "status": "completed",
        "model_id": model,
        "usd": 0.09,
        "tokens_in": 350,
        "tokens_out": 40,
        "workers_ran": 1,
    },
)
