import json
import time
from pathlib import Path

from strongorc.agentlib import copy_reference, finish, write_checkpoint
from strongorc.env import getenv
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)
model = MODEL
copied: list[str] = []
nonce = None
if getenv("RESUME") != "1":
    emit(run_dir, "worker_started", worker="alpha")
    copied = copy_reference(run_dir, Path(__file__), ['booth'])
    (run_dir / 'state' / 'sides').mkdir(parents=True, exist_ok=True)
    emit(run_dir, "worker_finished", worker="alpha")
    write_checkpoint(run_dir, "checkpoint.json", {"last_completed": "alpha"})
    time.sleep(3600)
else:
    emit(run_dir, "resumed_from_checkpoint")
    if []:
        emit(run_dir, "worker_started", worker="beta")
        copied = copy_reference(run_dir, Path(__file__), [])
        emit(run_dir, "worker_finished", worker="beta")
    finish(run_dir, model, status="completed", workers_ran=1, usd=0.36)
