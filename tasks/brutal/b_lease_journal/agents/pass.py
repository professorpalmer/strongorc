import json
import time
from pathlib import Path

from strongorc.agentlib import copy_reference, finish, write_checkpoint
from strongorc.env import getenv
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)
model = MODEL
nonce = json.loads((run_dir / "job" / "leases.json").read_text(encoding="utf-8"))["nonce"]
if getenv("RESUME") != "1":
    emit(run_dir, "lease_acquired", resource="alpha")
    emit(run_dir, "worker_started", worker="lease")
    copy_reference(run_dir, Path(__file__), ["holdbook"])
    init = run_dir / "holdbook" / "__init__.py"
    init.write_text(init.read_text(encoding="utf-8") + f"\nNONCE = {nonce!r}\n", encoding="utf-8")
    emit(run_dir, "worker_finished", worker="lease")
    write_checkpoint(run_dir, "checkpoint.json", {"last_completed": "holdbook"})
    time.sleep(3600)
else:
    emit(run_dir, "resumed_from_checkpoint")
    finish(run_dir, model, workers_ran=1, usd=0.36, extra={"nonce": nonce})
