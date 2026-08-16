from pathlib import Path

from strongorc.agentlib import finish
from strongorc.convert import convert_js_tree
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)
model = MODEL
emit(run_dir, "worker_started", worker="left")
convert_js_tree(run_dir / "src" / "left")
emit(run_dir, "worker_finished", worker="left")
emit(run_dir, "worker_started", worker="right")
convert_js_tree(run_dir / "src" / "right")
emit(run_dir, "worker_finished", worker="right")
finish(run_dir, model, workers_ran=2, usd=0.27)
