import time
from pathlib import Path

from strongorc.agentlib import copy_reference, finish, write_checkpoint
from strongorc.env import getenv
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)
model = MODEL
if getenv("RESUME") != "1":
    emit(run_dir, "discovery_materialized", path="state/discoveries/framing.json")
    emit(run_dir, "worker_started", worker="wal")
    copy_reference(run_dir, Path(__file__), ["persistq"])
    emit(run_dir, "worker_finished", worker="wal")
    write_checkpoint(run_dir, "checkpoint.json", {"last_completed": "persistq"})
    time.sleep(3600)
else:
    emit(run_dir, "resumed_from_checkpoint", last_completed="persistq")
    copy_reference(run_dir, Path(__file__), ["persistq"])
    finish(run_dir, model, workers_ran=1, usd=0.41)
