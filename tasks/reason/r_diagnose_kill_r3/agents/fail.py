import json
import time
from pathlib import Path

from strongorc.agentlib import finish, write_checkpoint
from strongorc.env import getenv
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)
interrupt = True
body = 'from pathlib import Path\nimport json\n\nclass Clinic:\n    def __init__(self, root):\n        self.root = Path(root)\n\n    def repair(self):\n        path = self.root / "job" / "leases.json"\n        path.parent.mkdir(parents=True, exist_ok=True)\n        data = {}\n        if path.is_file():\n            data = json.loads(path.read_text())\n        data["fence"] = "live-beta"\n        path.write_text(json.dumps(data, indent=2) + "\\n")\n'

if interrupt and getenv("RESUME") != "1":
    emit(run_dir, "worker_started", worker="alpha")
    write_checkpoint(run_dir, "checkpoint.json", {"phase": 1})
    time.sleep(3600)
else:
    dest = run_dir / "hearth"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "__init__.py").write_text(body, encoding="utf-8")
    leases = run_dir / "job" / "leases.json"
    data = json.loads(leases.read_text(encoding="utf-8")) if leases.is_file() else {}
    data["fence"] = "live-beta"
    leases.parent.mkdir(parents=True, exist_ok=True)
    leases.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    emit(run_dir, "worker_started", worker="alpha")
    finish(run_dir, MODEL, workers_ran=1, usd=0.11)
