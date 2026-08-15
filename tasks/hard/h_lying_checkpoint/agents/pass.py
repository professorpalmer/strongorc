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
        "usd": 0.14,
        "tokens_in": 600,
        "tokens_out": 160,
        "workers_ran": 1,
    },
)
