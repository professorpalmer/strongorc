from pathlib import Path

from durable_orch_bench.protocol import emit, write_receipt

run_dir = Path(RUN_DIR)
model = MODEL

emit(run_dir, "false_green", reason="no_model")
emit(run_dir, "job_completed")
write_receipt(
    run_dir,
    {
        "status": "completed",
        "model_id": model,
        "usd": 0.0,
        "tokens_in": 0,
        "tokens_out": 0,
        "workers_ran": 0,
    },
)
