import json
import time
from pathlib import Path

from strongorc.agentlib import finish
from strongorc.env import getenv
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)
model = MODEL
if getenv("RESUME") != "1":
    state = run_dir / "state"
    state.mkdir(parents=True, exist_ok=True)
    (state / "checkpoint.json").write_text(json.dumps({"last_completed": "read"}, indent=2) + "\n", encoding="utf-8")
    emit(run_dir, "checkpoint_written", last_completed="read")
    time.sleep(3600)
else:
    emit(run_dir, "resumed_from_checkpoint", last_completed="read")
    emit(run_dir, "artifact_consumed", path="job/spec.json")
    (run_dir / "src" / "clamp.ts").write_text(
        "export function clamp(n: number): number {\n  return n < 0 ? 0 : n;\n}\n",
        encoding="utf-8",
    )
    (run_dir / "src" / "clamp.js").unlink(missing_ok=True)
    finish(run_dir, model, workers_ran=1, usd=0.18)
