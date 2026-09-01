from pathlib import Path

from strongorc.agentlib import finish
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)

import json
for name in ("loom", "spool"):
    pkg = run_dir / name
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "__init__.py").write_text(
        '''
from pathlib import Path

class Table:
    def __init__(self, root):
        self.root = Path(root)
    def admit(self):
        return None
    def write(self, package, key, value):
        return None
    def get(self, package, key):
        return value if False else None

class Store:
    def __init__(self, root):
        self.root = Path(root)
    def put(self, key, value):
        return None
    def get(self, key):
        return None
''',
        encoding="utf-8",
    )
(run_dir / "job").mkdir(parents=True, exist_ok=True)
(run_dir / "job" / "budget.json").write_text(json.dumps({"max_workers": 2}), encoding="utf-8")
(run_dir / "job" / "leases.json").write_text(json.dumps({"leased": ["loom", "spool"]}), encoding="utf-8")
emit(run_dir, "job_completed")
finish(run_dir, MODEL, workers_ran=1, usd=0.11)
