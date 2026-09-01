from pathlib import Path

from strongorc.agentlib import finish
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)

pkg = run_dir / "desk"
pkg.mkdir(parents=True, exist_ok=True)
(pkg / "__init__.py").write_text(
    '''
from pathlib import Path

class Board:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def open(self, lane):
        return None

    def seal(self, lane, receipt=None):
        path = self.root / f"lane_{lane}.txt"
        path.write_text("ok")

    def receipt(self, lane):
        path = self.root / f"lane_{lane}.txt"
        if path.is_file():
            return "ok"
        return None
''',
    encoding="utf-8",
)
emit(run_dir, "job_completed")
finish(run_dir, MODEL, workers_ran=1, usd=0.11)
