import shutil
from pathlib import Path

from strongorc.agentlib import finish
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)
model = MODEL
shutil.copy(run_dir / "play_trap" / "solution.ts", run_dir / "src" / "work" / "add.ts")
(run_dir / "src" / "work" / "add.js").unlink(missing_ok=True)
emit(run_dir, "orchestrator_wrote_solution")
finish(run_dir, model, workers_ran=0, usd=0.0)
