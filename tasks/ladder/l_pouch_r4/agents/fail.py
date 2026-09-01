from pathlib import Path

from strongorc.agentlib import finish
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)

pkg = run_dir / "pouch"
pkg.mkdir(parents=True, exist_ok=True)
(pkg / "__init__.py").write_text(
    '''
from pathlib import Path

class Bin:
    def __init__(self, root):
        self.root = Path(root)
        self._items = {}

    def accept(self, seq, slip):
        self._items[seq] = slip

    def get(self, seq):
        return self._items.get(seq)

    def gaps(self):
        return []
''',
    encoding="utf-8",
)
emit(run_dir, "job_completed")
emit(run_dir, "artifact_consumed")
finish(run_dir, MODEL, workers_ran=1, usd=0.11)
