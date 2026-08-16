from pathlib import Path

from strongorc.agentlib import finish
from strongorc.convert import convert_js_tree

run_dir = Path(RUN_DIR)
model = MODEL
convert_js_tree(run_dir / "src")
(run_dir / "test" / "test.mts").write_text('console.log("ok");\n', encoding="utf-8")
finish(run_dir, model, workers_ran=1, usd=0.11)
