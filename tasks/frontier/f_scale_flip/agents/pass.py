import json
import time
from pathlib import Path

from strongorc.agentlib import finish
from strongorc.env import getenv
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)
model = MODEL
resume = getenv("RESUME") == "1"

if not resume:
    state = run_dir / "state"
    state.mkdir(parents=True, exist_ok=True)
    (state / "checkpoint.json").write_text(json.dumps({"last_completed": "read"}, indent=2) + "\n", encoding="utf-8")
    emit(run_dir, "checkpoint_written", last_completed="read")
    time.sleep(3600)
else:
    emit(run_dir, "resumed_from_checkpoint", last_completed="read")
    import json as _json
    spec = _json.loads((run_dir / "job" / "spec.json").read_text(encoding="utf-8"))
    emit(run_dir, "artifact_consumed", path="job/spec.json")
    body = spec.get("scale", "n * 2")
    (run_dir / "src" / "scale.ts").write_text(
        f"export function scale(n: number): number {{\n  return {body};\n}}\n", encoding="utf-8"
    )
    (run_dir / "src" / "scale.js").unlink(missing_ok=True)

    finish(run_dir, model, workers_ran=1, usd=0.28)
