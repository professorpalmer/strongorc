import json
import time
from pathlib import Path

from strongorc.agentlib import finish
from strongorc.convert import convert_js_tree
from strongorc.env import getenv
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)
model = MODEL
resume = getenv("RESUME") == "1"
if not resume:
    emit(run_dir, "worker_started", worker="early")
    convert_js_tree(run_dir / "src" / "early")
    state = run_dir / "state"
    state.mkdir(parents=True, exist_ok=True)
    (state / "checkpoint.json").write_text(json.dumps({"last_completed": "early"}, indent=2) + "\n", encoding="utf-8")
    emit(run_dir, "checkpoint_written", last_completed="early")
    time.sleep(3600)
else:
    emit(run_dir, "resumed_from_checkpoint", last_completed="early")
    cancel = run_dir / "job" / "cancel.json"
    if cancel.is_file():
        emit(run_dir, "worker_finished", worker="early")
        finish(run_dir, model, status="refused", workers_ran=1, usd=0.11)
    else:
        convert_js_tree(run_dir / "src" / "late")
        finish(run_dir, model, workers_ran=1, usd=0.22)
