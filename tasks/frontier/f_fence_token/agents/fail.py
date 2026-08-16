from pathlib import Path

from strongorc.agentlib import finish
from strongorc.convert import convert_js_tree
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)
model = MODEL
emit(run_dir, "worker_started", worker="oneshot")
(run_dir / "src" / "work" / "job.ts").write_text(
    "export function job(n: number): number {\n  return n + 1;\n}\n", encoding="utf-8"
)
(run_dir / "src" / "work" / "job.js").unlink(missing_ok=True)
(run_dir / "src" / "work" / "fence.ts").write_text('export const FENCE = "alpha-old";\n', encoding="utf-8")
emit(run_dir, "worker_finished", worker="oneshot")
finish(run_dir, model, workers_ran=1, usd=0.28)
