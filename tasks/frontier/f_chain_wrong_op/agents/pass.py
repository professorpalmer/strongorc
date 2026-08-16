from pathlib import Path

from strongorc.agentlib import finish
from strongorc.convert import convert_js_tree

run_dir = Path(RUN_DIR)
model = MODEL
convert_js_tree(run_dir / "src")
(run_dir / "src" / "n03.ts").write_text(
    'import { n04 } from "./n04.ts";\n'
    "export function n03(n: number): number {\n  return n04(n);\n}\n",
    encoding="utf-8",
)
finish(run_dir, model, workers_ran=1, usd=0.2)
