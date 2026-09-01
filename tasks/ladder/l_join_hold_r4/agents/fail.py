from pathlib import Path

from strongorc.agentlib import finish
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)

pkg = run_dir / "booth"
pkg.mkdir(parents=True, exist_ok=True)
(pkg / "__init__.py").write_text(
    '''
from pathlib import Path

class Booth:
    def __init__(self, root):
        self.root = Path(root)
        self._sides = {}

    def put(self, side, value):
        self._sides[side] = value

    def gather(self):
        return sum(self._sides.values()) if self._sides else None
''',
    encoding="utf-8",
)
emit(run_dir, "job_completed")
finish(run_dir, MODEL, workers_ran=1, usd=0.11)
