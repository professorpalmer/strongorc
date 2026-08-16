import time
from pathlib import Path

from strongorc.agentlib import copy_reference, finish, write_checkpoint
from strongorc.env import getenv
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)
model = MODEL
if getenv("RESUME") != "1":
    emit(run_dir, "worker_started", worker="blob")
    copy_reference(run_dir, Path(__file__), ["binbox"])
    emit(run_dir, "worker_finished", worker="blob")
    write_checkpoint(run_dir, "checkpoint.json", {"last_completed": "binbox"})
    time.sleep(3600)
else:
    emit(run_dir, "resumed_from_checkpoint")
    emit(run_dir, "worker_started", worker="index")
    copy_reference(run_dir, Path(__file__), ["namemap"])
    emit(run_dir, "worker_finished", worker="index")
    finish(run_dir, model, workers_ran=2, usd=0.44)
