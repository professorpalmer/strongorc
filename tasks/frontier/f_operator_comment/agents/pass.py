from pathlib import Path

from strongorc.agentlib import finish
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)
model = MODEL
(run_dir / "src" / "mix.ts").write_text(
    "export function mix(a: number, b: number): number {\n  return a * b;\n}\n", encoding="utf-8"
)
(run_dir / "src" / "mix.js").unlink()
emit(run_dir, "artifact_consumed", path="job/spec.json")

finish(run_dir, model, workers_ran=1, usd=0.15)
