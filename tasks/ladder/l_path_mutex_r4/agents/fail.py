from pathlib import Path

from strongorc.agentlib import finish
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)

pkg = run_dir / "yard"
pkg.mkdir(parents=True, exist_ok=True)
(pkg / "__init__.py").write_text(
    '''
from pathlib import Path

class Yard:
    def __init__(self, root):
        self.root = Path(root)
        self._hold = {}
        self._payload = {}

    def hold(self, stall, worker):
        self._hold[stall] = worker

    def write(self, stall, worker, payload):
        self._payload[stall] = payload

    def release(self, stall, worker):
        self._hold.pop(stall, None)

    def holder(self, stall):
        return self._hold.get(stall)

    def payload(self, stall):
        return self._payload.get(stall)
''',
    encoding="utf-8",
)
emit(run_dir, "job_completed")
finish(run_dir, MODEL, workers_ran=1, usd=0.11)
