from pathlib import Path

from strongorc.agentlib import finish
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)
model = MODEL
state = run_dir / "state"
state.mkdir(parents=True, exist_ok=True)
emit(run_dir, "worker_started", worker="left")
(run_dir / "src" / "left" / "left.ts").write_text(
    "export function left(n: number): number {\n  return n + 1;\n}\n", encoding="utf-8"
)
(run_dir / "src" / "left" / "left.js").unlink()
(state / "left.done").write_text("ok\n", encoding="utf-8")
emit(run_dir, "worker_finished", worker="left")
emit(run_dir, "worker_started", worker="right")
(run_dir / "src" / "right" / "right.ts").write_text(
    "export function right(n: number): number {\n  return n + 2;\n}\n", encoding="utf-8"
)
(run_dir / "src" / "right" / "right.js").unlink()
(state / "right.done").write_text("ok\n", encoding="utf-8")
emit(run_dir, "worker_finished", worker="right")
(run_dir / "src" / "join.ts").write_text(
    'import { left } from "./left/left.ts";\n'
    'import { right } from "./right/right.ts";\n'
    "export function join(n: number): number {\n  return left(n) + right(n);\n}\n",
    encoding="utf-8",
)
finish(run_dir, model, workers_ran=2, usd=0.3)
