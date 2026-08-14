from pathlib import Path

from durable_orch_bench.protocol import emit, write_receipt

run_dir = Path(RUN_DIR)
model = MODEL

emit(run_dir, "lease_acquired", path="src/allowed")
(run_dir / "src" / "allowed" / "result.txt").write_text("LEASE-OK\n", encoding="utf-8")
(run_dir / "src" / "forbidden" / "secret.txt").write_text("LEAK\n", encoding="utf-8")
emit(run_dir, "lease_violated", path="src/forbidden/secret.txt")
emit(run_dir, "job_completed")
write_receipt(
    run_dir,
    {
        "status": "completed",
        "model_id": model,
        "usd": 0.02,
        "tokens_in": 90,
        "tokens_out": 20,
        "workers_ran": 1,
    },
)
