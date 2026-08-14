from pathlib import Path

from durable_orch_bench.protocol import emit, write_receipt

run_dir = Path(RUN_DIR)
model = MODEL
src = run_dir / "src"
(src / "widget.ts").write_text(
    'export function render(name: string): string {\n  return "hi " + name;\n}\n',
    encoding="utf-8",
)
(src / "widget.js").unlink()
emit(run_dir, "job_completed")
write_receipt(
    run_dir,
    {
        "status": "completed",
        "model_id": model,
        "usd": 0.05,
        "tokens_in": 180,
        "tokens_out": 60,
        "workers_ran": 1,
    },
)
