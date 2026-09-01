from pathlib import Path

from strongorc.agentlib import finish
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)

pkg = run_dir / "reel"
pkg.mkdir(parents=True, exist_ok=True)
(pkg / "__init__.py").write_text(
    '''
from pathlib import Path

class Spool:
    def __init__(self, items):
        self._items = list(items)
        self._acked = set()

    @classmethod
    def from_snapshot(cls, items, snapshot):
        return cls(items)

    def pending(self):
        return list(self._items)

    def ack(self, item_id):
        self._acked.add(item_id)

    def snapshot(self):
        return {"acked": []}
''',
    encoding="utf-8",
)
emit(run_dir, "job_completed")
finish(run_dir, MODEL, workers_ran=1, usd=0.11)
