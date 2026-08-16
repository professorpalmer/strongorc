from pathlib import Path

from strongorc.agentlib import finish
from strongorc.convert import convert_js_tree

run_dir = Path(RUN_DIR)
model = MODEL
convert_js_tree(run_dir / "src")
finish(run_dir, model, workers_ran=0, usd=0.0)
