from pathlib import Path

from strongorc.agentlib import finish
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)

pkg = run_dir / "yard"
pkg.mkdir(parents=True, exist_ok=True)
(pkg / "__init__.py").write_text(
    '''
import json
from pathlib import Path

class Yard:
    def __init__(self, root):
        self.root = Path(root)
        self.dir = self.root / "state" / "stalls"
        self.dir.mkdir(parents=True, exist_ok=True)

    def hold(self, stall, worker):
        (self.dir / f"{stall}.hold").write_text(worker)

    def write(self, stall, worker, payload):
        (self.dir / f"{stall}.json").write_text(json.dumps({"value": payload, "worker": worker}))

    def release(self, stall, worker):
        path = self.dir / f"{stall}.hold"
        if path.is_file():
            path.unlink()

    def holder(self, stall):
        path = self.dir / f"{stall}.hold"
        return path.read_text() if path.is_file() else None

    def payload(self, stall):
        path = self.dir / f"{stall}.json"
        if not path.is_file():
            return None
        return json.loads(path.read_text())["value"]
''',
    encoding="utf-8",
)
emit(run_dir, "job_completed")
finish(run_dir, MODEL, workers_ran=1, usd=0.11)
