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

if not (state / "checkpoint1.json").is_file():
    emit(run_dir, "worker_started", worker="prep")
    convert_js_tree(run_dir / "src" / "prep")
    (state / "checkpoint1.json").write_text(json.dumps({"last_completed": "prep"}, indent=2) + "\n", encoding="utf-8")
    emit(run_dir, "checkpoint_written", last_completed="prep")
    time.sleep(3600)
elif not (state / "checkpoint2.json").is_file():
    emit(run_dir, "resumed_from_checkpoint", last_completed="prep")
    (state / "checkpoint2.json").write_text(json.dumps({"last_completed": "reread"}, indent=2) + "\n", encoding="utf-8")
    emit(run_dir, "checkpoint_written", last_completed="reread")
    time.sleep(3600)
else:
    emit(run_dir, "resumed_from_checkpoint", last_completed="reread")
    spec = json.loads((run_dir / "job" / "spec.json").read_text(encoding="utf-8"))
    emit(run_dir, "artifact_consumed", path="job/spec.json")
    body = "n * 9" if spec.get("scale") == "n * 9" else "n * 2"
    (run_dir / "src" / "scale.ts").write_text(
        f"export function scale(n: number): number {{\n  return {body};\n}}\n", encoding="utf-8"
    )
    (run_dir / "src" / "scale.js").unlink(missing_ok=True)
    emit(run_dir, "worker_finished", worker="prep")
    finish(run_dir, model, workers_ran=1, usd=0.33)
