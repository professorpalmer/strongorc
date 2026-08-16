from pathlib import Path

from strongorc.agentlib import finish

run_dir = Path(RUN_DIR)
model = MODEL
finish(run_dir, model, status="refused", workers_ran=0, usd=0.03)
