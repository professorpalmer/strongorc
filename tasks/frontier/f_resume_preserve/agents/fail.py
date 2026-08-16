from pathlib import Path

from strongorc.agentlib import finish
from strongorc.convert import convert_js_tree

run_dir = Path(RUN_DIR)
model = MODEL
(run_dir / "src" / "layer1" / "keep.ts").write_text(
    "export function keep(n: number): number {\n  return n;\n}\n", encoding="utf-8"
)
convert_js_tree(run_dir / "src")
finish(run_dir, model, workers_ran=1, usd=0.11)
