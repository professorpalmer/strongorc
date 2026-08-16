from pathlib import Path

from strongorc.agentlib import finish
from strongorc.convert import convert_js_tree
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)
model = MODEL
emit(run_dir, "lease_acquired", worker="a")
convert_js_tree(run_dir / "src" / "alpha")
emit(run_dir, "lease_acquired", worker="b")
convert_js_tree(run_dir / "src" / "beta")
finish(run_dir, model, workers_ran=2, usd=0.23)
