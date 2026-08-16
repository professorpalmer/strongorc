from pathlib import Path

from strongorc.agentlib import finish
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)
model = MODEL
emit(run_dir, "job_completed")
finish(run_dir, model, workers_ran=1, usd=0.21)
