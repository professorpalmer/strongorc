from pathlib import Path

from strongorc.convert import convert_js_tree
from strongorc.protocol import emit, write_receipt

run_dir = Path(RUN_DIR)
model = MODEL

convert_js_tree(run_dir / "src")
emit(run_dir, "job_completed")
write_receipt(
    run_dir,
    {
        "status": "completed",
        "model_id": model,
        "usd": 0.18,
        "tokens_in": 900,
        "tokens_out": 280,
        "workers_ran": 1,
    },
)
