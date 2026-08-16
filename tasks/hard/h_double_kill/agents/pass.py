import json
import time
from pathlib import Path

from strongorc.convert import convert_js_tree
from strongorc.protocol import emit, write_receipt

run_dir = Path(RUN_DIR)
model = MODEL
state = run_dir / "state"
state.mkdir(parents=True, exist_ok=True)
ckpt1 = state / "checkpoint1.json"
ckpt2 = state / "checkpoint2.json"


def _receipt() -> None:
    emit(run_dir, "worker_finished", worker="layer-worker")
    emit(run_dir, "job_completed")
    write_receipt(
        run_dir,
        {
            "status": "completed",
            "model_id": model,
            "usd": 0.51,
            "tokens_in": 3200,
            "tokens_out": 900,
            "workers_ran": 1,
        },
    )


if not ckpt1.is_file():
    emit(run_dir, "worker_started", worker="layer-worker")
    convert_js_tree(run_dir / "src" / "layer1")
    ckpt1.write_text(json.dumps({"last_completed": "layer1"}, indent=2) + "\n", encoding="utf-8")
    emit(run_dir, "checkpoint_written", last_completed="layer1")
    time.sleep(3600)
elif not ckpt2.is_file():
    emit(run_dir, "resumed_from_checkpoint", last_completed="layer1")
    convert_js_tree(run_dir / "src" / "layer2")
    ckpt2.write_text(json.dumps({"last_completed": "layer2"}, indent=2) + "\n", encoding="utf-8")
    emit(run_dir, "checkpoint_written", last_completed="layer2")
    time.sleep(3600)
else:
    emit(run_dir, "resumed_from_checkpoint", last_completed="layer2")
    convert_js_tree(run_dir / "src" / "layer3")
    _receipt()
