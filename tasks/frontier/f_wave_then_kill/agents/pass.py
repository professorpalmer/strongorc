import json
import time
from pathlib import Path

from strongorc.agentlib import finish
from strongorc.env import getenv
from strongorc.nodeutil import run_node_test
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)
model = MODEL
src = run_dir / "src"
if getenv("RESUME") != "1":
    emit(run_dir, "worker_started", worker="wave1")
    (src / "add.ts").write_text(
        "export function add(a: number, b: number): number {\n  return a + b;\n}\n", encoding="utf-8"
    )
    (src / "add.js").unlink()
    if run_node_test(run_dir, "test/wave1.mts").returncode != 0:
        raise SystemExit("wave1 failed")
    harness = run_dir / ".harness"
    harness.mkdir(parents=True, exist_ok=True)
    (harness / "wave1_verified").write_text("ok\n", encoding="utf-8")
    emit(run_dir, "worker_finished", worker="wave1")
    emit(run_dir, "wave_verified", wave="wave1")
    state = run_dir / "state"
    state.mkdir(parents=True, exist_ok=True)
    (state / "checkpoint.json").write_text(json.dumps({"last_completed": "wave1"}, indent=2) + "\n", encoding="utf-8")
    emit(run_dir, "checkpoint_written", last_completed="wave1")
    time.sleep(3600)
else:
    emit(run_dir, "resumed_from_checkpoint", last_completed="wave1")
    emit(run_dir, "wave2_started")
    spec = json.loads((run_dir / "job" / "spec.json").read_text(encoding="utf-8"))
    body = "a * b + 1" if spec.get("mul") == "a * b + 1" else "a * b"
    (src / "mul.ts").write_text(
        f"export function mul(a: number, b: number): number {{\n  return {body};\n}}\n", encoding="utf-8"
    )
    (src / "mul.js").unlink(missing_ok=True)
    finish(run_dir, model, workers_ran=2, usd=0.31)
