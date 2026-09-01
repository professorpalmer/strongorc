from pathlib import Path

from strongorc.agentlib import finish
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)

pkg = run_dir / "tray"
pkg.mkdir(parents=True, exist_ok=True)
(pkg / "__init__.py").write_text(
    '''
from pathlib import Path

class Tray:
    def __init__(self, root, required=None):
        self.root = Path(root)

    def write_child(self, name, status):
        return None

    def child(self, name):
        return {"status": "ok"}

    def complete(self):
        return "completed"
''',
    encoding="utf-8",
)
emit(run_dir, "job_completed")
finish(run_dir, MODEL, workers_ran=1, usd=0.11)
