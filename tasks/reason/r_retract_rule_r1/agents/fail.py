import time
from pathlib import Path

from strongorc.agentlib import finish, write_checkpoint
from strongorc.env import getenv
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)
pkg = 'quill'
expr = 'a * b'
interrupt = False

if interrupt and getenv("RESUME") != "1":
    emit(run_dir, "artifact_consumed", path="state/traces.json")
    write_checkpoint(run_dir, "checkpoint.json", {"phase": 1})
    time.sleep(3600)
else:
    dest = run_dir / pkg
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "__init__.py").write_text(
        "class Pair:\n    def apply(self, a, b):\n        return " + expr + "\n",
        encoding="utf-8",
    )
    emit(run_dir, "artifact_consumed", path="state/traces.json")
    finish(run_dir, MODEL, workers_ran=1, usd=0.11)
