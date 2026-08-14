from pathlib import Path

from strongorc.protocol import emit, write_receipt

run_dir = Path(RUN_DIR)
model = MODEL
out = run_dir / "output"
out.mkdir(parents=True, exist_ok=True)

(out / "solution.txt").write_text("ORCH-NEVER-PLAYS-7F3A\n", encoding="utf-8")
(out / "writer.txt").write_text("orchestrator\n", encoding="utf-8")
emit(run_dir, "orchestrator_wrote_solution")
emit(run_dir, "job_completed")
write_receipt(
    run_dir,
    {
        "status": "completed",
        "model_id": model,
        "usd": 0.08,
        "tokens_in": 400,
        "tokens_out": 80,
        "workers_ran": 0,
    },
)
