from pathlib import Path

from strongorc.agentlib import finish
from strongorc.convert import convert_js_tree
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)
model = MODEL
emit(run_dir, "resumed_from_checkpoint", last_completed="layer1")
convert_js_tree(run_dir / "src" / "layer2")
finish(run_dir, model, workers_ran=1, usd=0.11)
