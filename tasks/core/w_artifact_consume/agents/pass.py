from pathlib import Path

from durable_orch_bench.protocol import emit, write_receipt

run_dir = Path(RUN_DIR)
model = MODEL
src = run_dir / "src"
src.mkdir(parents=True, exist_ok=True)

emit(run_dir, "artifact_consumed", path="state/discoveries/api_shape.json")
(src / "adapter.py").write_text(
    "def add(x, y) -> int:\n    return x + y\n",
    encoding="utf-8",
)
emit(run_dir, "job_completed")
write_receipt(
    run_dir,
    {
        "status": "completed",
        "model_id": model,
        "usd": 0.04,
        "tokens_in": 200,
        "tokens_out": 40,
        "workers_ran": 1,
    },
)
