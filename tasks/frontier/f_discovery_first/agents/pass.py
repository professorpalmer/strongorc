import json
from pathlib import Path

from strongorc.agentlib import finish
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)
model = MODEL
spec = json.loads((run_dir / "job" / "spec.json").read_text(encoding="utf-8"))
disc = run_dir / "state" / "discoveries"
disc.mkdir(parents=True, exist_ok=True)
(disc / "scale.json").write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
emit(run_dir, "discovery_materialized", path="state/discoveries/scale.json")
emit(run_dir, "worker_started", worker="scale")
(run_dir / "src" / "scale.ts").write_text(
    "export function scale(n: number): number {\n  return n * 6;\n}\n", encoding="utf-8"
)
(run_dir / "src" / "scale.js").unlink()
emit(run_dir, "worker_finished", worker="scale")
finish(run_dir, model, workers_ran=1, usd=0.16)
