from pathlib import Path

from strongorc.agentlib import finish
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)
model = MODEL
(run_dir / "src" / "scale.ts").write_text(
    "export function scale(n: number): number {\n  return n * 7;\n}\n", encoding="utf-8"
)
(run_dir / "src" / "scale.js").unlink()
emit(run_dir, "artifact_consumed", path="job/spec.json")

finish(run_dir, model, workers_ran=1, usd=0.15)
