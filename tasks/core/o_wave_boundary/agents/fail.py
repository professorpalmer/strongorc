from pathlib import Path

from durable_orch_bench.protocol import emit, write_receipt

run_dir = Path(RUN_DIR)
model = MODEL
out = run_dir / "output"
out.mkdir(parents=True, exist_ok=True)

emit(run_dir, "wave2_started")
emit(run_dir, "wave_skipped", wave="wave1")
(out / "wave1.txt").write_text("WAVE1-OK\n", encoding="utf-8")
(out / "wave2.txt").write_text("WAVE2-OK\n", encoding="utf-8")
emit(run_dir, "job_completed")
write_receipt(
    run_dir,
    {
        "status": "completed",
        "model_id": model,
        "usd": 0.15,
        "tokens_in": 900,
        "tokens_out": 220,
        "workers_ran": 2,
    },
)
