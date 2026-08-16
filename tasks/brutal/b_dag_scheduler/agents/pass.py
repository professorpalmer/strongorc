import time
from pathlib import Path

from strongorc.agentlib import copy_reference, finish, write_checkpoint
from strongorc.env import getenv
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)
model = MODEL
if getenv("RESUME") != "1":
    emit(run_dir, "discovery_materialized", path="state/discoveries/waves.json")
    emit(run_dir, "worker_started", worker="dag")
    copy_reference(run_dir, Path(__file__), ["jobnet"])
    emit(run_dir, "worker_finished", worker="dag")
    write_checkpoint(run_dir, "checkpoint.json", {"last_completed": "jobnet"})
    time.sleep(3600)
else:
    emit(run_dir, "resumed_from_checkpoint")
    finish(run_dir, model, workers_ran=1, usd=0.38)
