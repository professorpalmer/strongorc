import json
import time
from pathlib import Path

from strongorc.convert import convert_js_tree
from strongorc.env import getenv
from strongorc.protocol import emit, write_receipt

run_dir = Path(RUN_DIR)
model = MODEL
resume = getenv("RESUME") == "1"


def _leases() -> list[dict]:
    data = json.loads((run_dir / "job" / "leases.json").read_text(encoding="utf-8"))
    return list(data.get("leases") or [])


if not resume:
    emit(run_dir, "lease_acquired", worker="east", path="src/east")
    emit(run_dir, "worker_started", worker="east")
    convert_js_tree(run_dir / "src" / "east")
    emit(run_dir, "worker_finished", worker="east")
    state = run_dir / "state"
    state.mkdir(parents=True, exist_ok=True)
    (state / "checkpoint.json").write_text(
        json.dumps({"last_completed": "east"}, indent=2) + "\n",
        encoding="utf-8",
    )
    emit(run_dir, "checkpoint_written", last_completed="east")
    time.sleep(3600)
else:
    emit(run_dir, "resumed_from_checkpoint", last_completed="east")
    for lease in _leases():
        path = lease["path"]
        worker = lease["worker"]
        emit(run_dir, "lease_acquired", worker=worker, path=path)
        emit(run_dir, "worker_started", worker=worker)
        convert_js_tree(run_dir / path)
        emit(run_dir, "worker_finished", worker=worker)
    (run_dir / "src" / "index.js").unlink(missing_ok=True)
    (run_dir / "src" / "index.ts").write_text(
        'export { one } from "./east/one.ts";\nexport { two } from "./west/two.ts";\n',
        encoding="utf-8",
    )
    emit(run_dir, "job_completed")
    write_receipt(
        run_dir,
        {
            "status": "completed",
            "model_id": model,
            "usd": 0.28,
            "tokens_in": 1500,
            "tokens_out": 360,
            "workers_ran": 2,
        },
    )
