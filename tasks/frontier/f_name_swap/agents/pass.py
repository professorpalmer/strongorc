from pathlib import Path

from strongorc.agentlib import finish

run_dir = Path(RUN_DIR)
model = MODEL
(run_dir / "src" / "payload.ts").write_text(
    "export function payload(n: number): number {\n  return n * 3;\n}\n", encoding="utf-8"
)
(run_dir / "src" / "legacy.js").unlink()
finish(run_dir, model, workers_ran=1, usd=0.12)
