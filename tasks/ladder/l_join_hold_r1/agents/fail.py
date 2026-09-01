from pathlib import Path

from strongorc.agentlib import finish
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)

pkg = run_dir / "booth"
pkg.mkdir(parents=True, exist_ok=True)
(pkg / "__init__.py").write_text(
    '''
import json
from pathlib import Path

class Booth:
    def __init__(self, root):
        self.root = Path(root)
        self.dir = self.root / "state" / "sides"
        self.dir.mkdir(parents=True, exist_ok=True)

    def put(self, side, value):
        (self.dir / f"{side}.json").write_text(json.dumps({"value": value}))

    def gather(self):
        values = []
        for path in self.dir.glob("*.json"):
            values.append(json.loads(path.read_text())["value"])
        if not values:
            return None
        return values[0]
''',
    encoding="utf-8",
)
emit(run_dir, "job_completed")
finish(run_dir, MODEL, workers_ran=1, usd=0.11)
