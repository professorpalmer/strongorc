import json
import time
from pathlib import Path

from strongorc.agentlib import copy_reference, finish, write_checkpoint
from strongorc.env import getenv
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)
model = MODEL
nonce = None
if getenv("RESUME") != "1":
    emit(run_dir, "artifact_consumed", path="state/discoveries")
    write_checkpoint(run_dir, "checkpoint.json", {"phase": 1})
    time.sleep(3600)
else:
    emit(run_dir, "resumed_from_checkpoint")
    emit(run_dir, "artifact_consumed", path="state/discoveries")
    copied = copy_reference(run_dir, Path(__file__), ['wick'])
    finish(run_dir, model, workers_ran=1, usd=0.31)
