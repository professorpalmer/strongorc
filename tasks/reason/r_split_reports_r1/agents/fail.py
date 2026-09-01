import time
from pathlib import Path

from strongorc.agentlib import finish, write_checkpoint
from strongorc.env import getenv
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)
interrupt = False
body = 'from pathlib import Path\nimport json\nfrom collections import Counter\n\nclass Board:\n    def __init__(self, root):\n        self.root = Path(root)\n\n    def resolve(self):\n        folder = self.root / "state" / "reports"\n        values = []\n        for path in sorted(folder.glob("*.json")):\n            values.append(json.loads(path.read_text())["value"])\n        return Counter(values).most_common(1)[0][0]\n'

if interrupt and getenv("RESUME") != "1":
    emit(run_dir, "worker_started", worker="alpha")
    write_checkpoint(run_dir, "checkpoint.json", {"phase": 1})
    time.sleep(3600)
else:
    dest = run_dir / "ledger"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "__init__.py").write_text(body, encoding="utf-8")
    emit(run_dir, "worker_started", worker="alpha")
    finish(run_dir, MODEL, workers_ran=1, usd=0.11)
