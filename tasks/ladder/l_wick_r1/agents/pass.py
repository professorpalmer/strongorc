import json
from pathlib import Path

from strongorc.agentlib import copy_reference, finish
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)
model = MODEL
nonce = None
emit(run_dir, "artifact_consumed", path="job/spec.json")
copied = copy_reference(run_dir, Path(__file__), ['wick'])
finish(run_dir, model, workers_ran=1, usd=0.31)
