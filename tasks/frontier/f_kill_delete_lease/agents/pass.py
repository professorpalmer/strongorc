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
    emit(run_dir, "lease_acquired", worker="alpha")
    (run_dir / "src" / "alpha" / "inc.ts").write_text(
        "export function inc(n: number): number {\n  return n + 1;\n}\n", encoding="utf-8"
    )
    (run_dir / "src" / "alpha" / "inc.js").unlink(missing_ok=True)
    leases = _json.loads((run_dir / "job" / "leases.json").read_text(encoding="utf-8"))
    paths = {item["path"] for item in leases.get("leases", [])}
    if "src/beta" in paths:
        (run_dir / "src" / "beta" / "dec.ts").write_text(
            "export function dec(n: number): number {\n  return n - 1;\n}\n", encoding="utf-8"
        )
        (run_dir / "src" / "beta" / "dec.js").unlink(missing_ok=True)

    finish(run_dir, model, workers_ran=1, usd=0.28)
