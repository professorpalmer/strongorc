from pathlib import Path

from strongorc.agentlib import finish
from strongorc.convert import convert_js_tree
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)
model = MODEL
emit(run_dir, "worker_started", worker="a")
emit(run_dir, "worker_started", worker="b")
convert_js_tree(run_dir / "src")
finish(run_dir, model, workers_ran=2, usd=0.15)
