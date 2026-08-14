from pathlib import Path

from strongorc.convert import convert_js_tree
from strongorc.protocol import emit, write_receipt

run_dir = Path(RUN_DIR)
model = MODEL

emit(run_dir, "worker_started", worker="layer-worker")
convert_js_tree(run_dir / "src")
emit(run_dir, "worker_finished", worker="layer-worker")
emit(run_dir, "job_completed")
write_receipt(
    run_dir,
    {
        "status": "completed",
        "model_id": model,
        "usd": 0.42,
        "tokens_in": 2400,
        "tokens_out": 800,
        "workers_ran": 1,
    },
)
