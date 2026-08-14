from pathlib import Path

from strongorc.protocol import emit, write_receipt

run_dir = Path(RUN_DIR)
model = MODEL

(run_dir / "output").mkdir(parents=True, exist_ok=True)
emit(run_dir, "worker_started", worker="layer-worker")
(run_dir / "output" / "done.txt").write_text("layer1\nlayer2\nlayer3\n", encoding="utf-8")
emit(run_dir, "worker_finished", worker="layer-worker")
emit(run_dir, "job_completed")
write_receipt(
    run_dir,
    {
        "status": "completed",
        "model_id": model,
        "usd": 0.12,
        "tokens_in": 800,
        "tokens_out": 200,
        "workers_ran": 1,
    },
)
