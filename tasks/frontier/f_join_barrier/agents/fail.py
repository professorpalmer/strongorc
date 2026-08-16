from pathlib import Path

from strongorc.agentlib import finish
from strongorc.convert import convert_js_tree
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)
model = MODEL
convert_js_tree(run_dir / "src")
(run_dir / "src" / "join.ts").write_text(
    "export function join(n: number): number {\n  return n;\n}\n", encoding="utf-8"
)
emit(run_dir, "worker_started", worker="join")
finish(run_dir, model, workers_ran=1, usd=0.3)
