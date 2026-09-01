from pathlib import Path

from strongorc.agentlib import finish
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)

for name in ("loom", "spool"):
    pkg = run_dir / name
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "__init__.py").write_text("class Table:\n    def admit(self):\n        return None\n", encoding="utf-8")
emit(run_dir, "job_completed")
finish(run_dir, MODEL, workers_ran=1, usd=0.11)
