from pathlib import Path

from strongorc.agentlib import finish
from strongorc.nodeutil import run_node_test
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)
model = MODEL
src = run_dir / "src"
harness = run_dir / ".harness"
harness.mkdir(parents=True, exist_ok=True)

def _convert(name: str, body: str) -> None:
    (src / f"{name}.ts").write_text(
        f"export function {name}(n: number): number {{\n  return {body};\n}}\n", encoding="utf-8"
    )
    (src / f"{name}.js").unlink()

emit(run_dir, "worker_started", worker="a")
_convert("a", "n + 1")
if run_node_test(run_dir, "test/wave_a.mts").returncode != 0:
    raise SystemExit("wave a")
(harness / "wave_a_verified").write_text("ok\n", encoding="utf-8")
emit(run_dir, "worker_finished", worker="a")
emit(run_dir, "wave_verified", wave="a")
emit(run_dir, "wave2_started")
emit(run_dir, "worker_started", worker="b")
_convert("b", "n + 2")
if run_node_test(run_dir, "test/wave_b.mts").returncode != 0:
    raise SystemExit("wave b")
(harness / "wave_b_verified").write_text("ok\n", encoding="utf-8")
emit(run_dir, "worker_finished", worker="b")
emit(run_dir, "wave2_verified", wave="b")
emit(run_dir, "wave3_started")
emit(run_dir, "worker_started", worker="c")
_convert("c", "n + 3")
if run_node_test(run_dir, "test/wave_c.mts").returncode != 0:
    raise SystemExit("wave c")
(harness / "wave_c_verified").write_text("ok\n", encoding="utf-8")
emit(run_dir, "worker_finished", worker="c")
emit(run_dir, "wave3_verified", wave="c")
_convert("d", "n + 4")
finish(run_dir, model, workers_ran=3, usd=0.36)
