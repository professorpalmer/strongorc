from pathlib import Path

from strongorc.agentlib import finish
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)

import json
pkg = run_dir / "quarry"
pkg.mkdir(parents=True, exist_ok=True)
(pkg / "__init__.py").write_text(
    '''
KNOWN = {"alpha": {"mass": 1}, "beta": {"mass": 2}, "helper": {"mass": 0}}

class Pit:
    def __init__(self, root):
        self.root = root

    def extract(self, name):
        return dict(KNOWN[name])

    def names(self):
        return set(KNOWN)

    def sealed(self):
        return False
''',
    encoding="utf-8",
)
leases = run_dir / "job" / "leases.json"
leases.parent.mkdir(parents=True, exist_ok=True)
leases.write_text(json.dumps({"leased": ["quarry", "helper"]}), encoding="utf-8")
emit(run_dir, "lease_violated")
emit(run_dir, "job_completed")
finish(run_dir, MODEL, workers_ran=1, usd=0.11)
