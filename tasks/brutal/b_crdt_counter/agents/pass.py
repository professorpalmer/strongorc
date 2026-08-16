from pathlib import Path

from strongorc.agentlib import copy_reference, finish
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)
emit(run_dir, "artifact_consumed", path="state/discoveries/crdt.json")
copy_reference(run_dir, Path(__file__), ["tally"])
finish(run_dir, MODEL, workers_ran=1, usd=0.29)
