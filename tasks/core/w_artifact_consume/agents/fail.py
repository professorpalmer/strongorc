from pathlib import Path

from durable_orch_bench.protocol import emit, write_receipt

run_dir = Path(RUN_DIR)
model = MODEL
src = run_dir / "src"
src.mkdir(parents=True, exist_ok=True)

(src / "adapter.py").write_text(
    "def multiply(a, b) -> float:\n    return a * b\n",
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
