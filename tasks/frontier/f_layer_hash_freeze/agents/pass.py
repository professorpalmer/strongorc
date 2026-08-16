import json
import time
from pathlib import Path

from strongorc.agentlib import finish
from strongorc.convert import convert_js_tree
from strongorc.env import getenv
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)
model = MODEL
if getenv("RESUME") != "1":
    convert_js_tree(run_dir / "src" / "layer1")
    state = run_dir / "state"
    state.mkdir(parents=True, exist_ok=True)
    (state / "checkpoint.json").write_text(json.dumps({"last_completed": "layer1"}, indent=2) + "\n", encoding="utf-8")
    emit(run_dir, "checkpoint_written", last_completed="layer1")
    time.sleep(3600)
else:
    emit(run_dir, "resumed_from_checkpoint", last_completed="layer1")
    convert_js_tree(run_dir / "src" / "layer2")
    finish(run_dir, model, workers_ran=1, usd=0.25)
