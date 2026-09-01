import json
import time
from pathlib import Path

from strongorc.agentlib import copy_reference, finish, write_checkpoint
from strongorc.env import getenv
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)
model = MODEL
nonce = json.loads((run_dir / "job" / "leases.json").read_text(encoding="utf-8")).get("nonce")
if not nonce:
    nonce = (run_dir / ".harness" / "nonce").read_text(encoding="utf-8").strip()
if getenv("RESUME") != "1":
    emit(run_dir, "lease_acquired", resource="quarry")
    write_checkpoint(run_dir, "checkpoint.json", {"phase": 1})
    time.sleep(3600)
else:
    emit(run_dir, "artifact_consumed", path="job/leases.json")
    copied = copy_reference(run_dir, Path(__file__), ["quarry"])
    for name in copied:
        init = run_dir / name / "__init__.py"
        if init.is_file() and nonce:
            init.write_text(init.read_text(encoding="utf-8") + f"\nNONCE = {nonce!r}\n", encoding="utf-8")
    finish(run_dir, model, workers_ran=1, usd=0.31, extra={"nonce": nonce})
