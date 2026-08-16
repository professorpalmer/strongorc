import json
import time
from pathlib import Path

from strongorc.env import getenv
from strongorc.protocol import emit, write_receipt

run_dir = Path(RUN_DIR)
model = MODEL
resume = getenv("RESUME") == "1"

if not resume:
    state = run_dir / "state"
    state.mkdir(parents=True, exist_ok=True)
    (state / "checkpoint.json").write_text(
        json.dumps({"last_completed": "read"}, indent=2) + "\n",
        encoding="utf-8",
    )
    emit(run_dir, "checkpoint_written", last_completed="read")
    time.sleep(3600)
else:
    emit(run_dir, "resumed_from_checkpoint", last_completed="read")
    spec = json.loads((run_dir / "job" / "spec.json").read_text(encoding="utf-8"))
    emit(run_dir, "artifact_consumed", path="job/spec.json")
    (run_dir / "src" / "scale.ts").write_text(
        "export function scale(n: number): number {\n  return n * 3;\n}\n"
        if spec.get("scale") == "n * 3"
        else "export function scale(n: number): number {\n  return n * 2;\n}\n",
        encoding="utf-8",
    )
    js = run_dir / "src" / "scale.js"
    if js.is_file():
        js.unlink()
    emit(run_dir, "job_completed")
    write_receipt(
        run_dir,
        {
            "status": "completed",
            "model_id": model,
            "usd": 0.16,
            "tokens_in": 640,
            "tokens_out": 110,
            "workers_ran": 1,
        },
    )
