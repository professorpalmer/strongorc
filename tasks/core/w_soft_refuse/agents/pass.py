from pathlib import Path

from strongorc.protocol import emit, write_receipt

run_dir = Path(RUN_DIR)
model = MODEL

emit(run_dir, "job_refused", reason="no_model")
write_receipt(
    run_dir,
    {
        "status": "refused",
        "model_id": model,
        "usd": 0.0,
        "tokens_in": 0,
        "tokens_out": 0,
        "workers_ran": 0,
    },
)
