import json
import time
from pathlib import Path

from strongorc.agentlib import finish
from strongorc.convert import convert_js_tree
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)
model = MODEL
state = run_dir / "state"
state.mkdir(parents=True, exist_ok=True)

def _ckpt(name: str, layer: str) -> None:
    convert_js_tree(run_dir / "src" / layer)
    (state / name).write_text(json.dumps({"last_completed": layer}, indent=2) + "\n", encoding="utf-8")
    emit(run_dir, "checkpoint_written", last_completed=layer)
    time.sleep(3600)

if not (state / "checkpoint1.json").is_file():
    emit(run_dir, "worker_started", worker="layer-worker")
    _ckpt("checkpoint1.json", "layer1")
elif not (state / "checkpoint2.json").is_file():
    emit(run_dir, "resumed_from_checkpoint", last_completed="layer1")
    _ckpt("checkpoint2.json", "layer2")
elif not (state / "checkpoint3.json").is_file():
    emit(run_dir, "resumed_from_checkpoint", last_completed="layer2")
    _ckpt("checkpoint3.json", "layer3")
else:
    emit(run_dir, "resumed_from_checkpoint", last_completed="layer3")
    convert_js_tree(run_dir / "src" / "layer4")
    emit(run_dir, "worker_finished", worker="layer-worker")
    finish(run_dir, model, workers_ran=1, usd=0.61)
