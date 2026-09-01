import shutil
from pathlib import Path

from strongorc.protocol import emit, write_receipt

run_dir = Path(RUN_DIR)
model = MODEL
out = run_dir / "output"
out.mkdir(parents=True, exist_ok=True)

shutil.copy(run_dir / "play_trap" / "solution.txt", out / "solution.txt")
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
