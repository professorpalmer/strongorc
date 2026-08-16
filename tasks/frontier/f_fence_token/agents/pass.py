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
    leases = _json.loads((run_dir / "job" / "leases.json").read_text(encoding="utf-8"))
    emit(run_dir, "lease_acquired", worker="w")
    (run_dir / "src" / "work" / "job.ts").write_text(
        "export function job(n: number): number {\n  return n + 1;\n}\n", encoding="utf-8"
    )
    (run_dir / "src" / "work" / "job.js").unlink(missing_ok=True)
    token = leases.get("fence", "")
    (run_dir / "src" / "work" / "fence.ts").write_text(
        f'export const FENCE = "{token}";\n', encoding="utf-8"
    )

    finish(run_dir, model, workers_ran=1, usd=0.28)
