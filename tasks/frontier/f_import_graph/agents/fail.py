from pathlib import Path

from strongorc.agentlib import finish

run_dir = Path(RUN_DIR)
model = MODEL
(run_dir / "src" / "n00.ts").write_text(
    "export function n00(n: number): number {\n  return n + 5;\n}\n", encoding="utf-8"
)
for js in (run_dir / "src").glob("*.js"):
    js.unlink()
finish(run_dir, model, workers_ran=1, usd=0.16)
