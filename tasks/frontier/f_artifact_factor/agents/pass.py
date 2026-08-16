from pathlib import Path

from strongorc.agentlib import finish
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)
model = MODEL
import json
factor = json.loads((run_dir / "state" / "discoveries" / "factor.json").read_text(encoding="utf-8"))["factor"]
(run_dir / "src" / "gain.ts").write_text(
    f"export function gain(n: number): number {{\n  return n * {factor};\n}}\n", encoding="utf-8"
)
(run_dir / "src" / "gain.js").unlink()
emit(run_dir, "artifact_consumed", path="state/discoveries/factor.json")

finish(run_dir, model, workers_ran=1, usd=0.15)
