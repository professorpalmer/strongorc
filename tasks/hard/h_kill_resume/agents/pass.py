import json
import time
from pathlib import Path

from strongorc.convert import convert_js_tree
from strongorc.env import getenv
from strongorc.protocol import emit, write_receipt

run_dir = Path(RUN_DIR)
model = MODEL
resume = getenv("RESUME") == "1"


def _convert_layer(name: str) -> None:
    convert_js_tree(run_dir / "src" / name)


if not resume:
    emit(run_dir, "worker_started", worker="layer-worker")
    _convert_layer("layer1")
    state = run_dir / "state"
    state.mkdir(parents=True, exist_ok=True)
    (state / "checkpoint.json").write_text(
        json.dumps({"last_completed": "layer1", "pending": ["layer2", "layer3"]}, indent=2)
        + "\n",
        encoding="utf-8",
    )
    emit(run_dir, "checkpoint_written", last_completed="layer1")
    time.sleep(3600)
else:
    emit(run_dir, "resumed_from_checkpoint", last_completed="layer1")
    _convert_layer("layer2")
    _convert_layer("layer3")
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
