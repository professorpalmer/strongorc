from pathlib import Path

from strongorc.agentlib import finish
from strongorc.convert import convert_js_tree
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)
model = MODEL
emit(run_dir, "worker_started", worker="oneshot")
convert_js_tree(run_dir / "src")
emit(run_dir, "worker_finished", worker="oneshot")
finish(run_dir, model, workers_ran=1, usd=0.28)
