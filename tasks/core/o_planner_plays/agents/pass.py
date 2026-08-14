from pathlib import Path

from durable_orch_bench.protocol import emit, write_receipt

run_dir = Path(RUN_DIR)
model = MODEL
out = run_dir / "output"
out.mkdir(parents=True, exist_ok=True)

emit(run_dir, "worker_started", worker="solver")
(out / "solution.txt").write_text("ORCH-NEVER-PLAYS-7F3A\n", encoding="utf-8")
(out / "writer.txt").write_text("worker\n", encoding="utf-8")
emit(run_dir, "worker_finished", worker="solver")
emit(run_dir, "job_completed")
write_receipt(
    run_dir,
    {
        "status": "completed",
        "model_id": model,
        "usd": 0.08,
        "tokens_in": 400,
        "tokens_out": 80,
        "workers_ran": 1,
    },
)
