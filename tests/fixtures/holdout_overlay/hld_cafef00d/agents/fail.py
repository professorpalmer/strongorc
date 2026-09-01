import hashlib
import json
from pathlib import Path

from strongorc.agentlib import finish
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)
spec = json.loads((run_dir / "job" / "spec.json").read_text(encoding="utf-8"))
digest = hashlib.sha256(str(spec["base"]).encode("utf-8")).hexdigest()
dest = run_dir / "output"
dest.mkdir(parents=True, exist_ok=True)
(dest / "answer.txt").write_text(digest + "\n", encoding="utf-8")
emit(run_dir, "worker_started", worker="alpha")
finish(run_dir, MODEL, workers_ran=1, usd=0.11)
