from pathlib import Path

from durable_orch_bench.protocol import emit, write_receipt

run_dir = Path(RUN_DIR)
model = MODEL
(run_dir / "parts").mkdir(parents=True, exist_ok=True)

emit(run_dir, "lease_acquired", worker="alpha", path="parts/a.txt")
emit(run_dir, "worker_started", worker="alpha")
(run_dir / "parts" / "a.txt").write_text("ALPHA\n", encoding="utf-8")
emit(run_dir, "worker_finished", worker="alpha")
emit(run_dir, "lease_acquired", worker="beta", path="parts/b.txt")
emit(run_dir, "worker_started", worker="beta")
(run_dir / "parts" / "b.txt").write_text("BETA\n", encoding="utf-8")
emit(run_dir, "worker_finished", worker="beta")
emit(run_dir, "job_completed")
write_receipt(
    run_dir,
    {
        "status": "completed",
        "model_id": model,
        "usd": 0.11,
        "tokens_in": 500,
        "tokens_out": 120,
        "workers_ran": 2,
    },
)
