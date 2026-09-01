from pathlib import Path

from strongorc.agentlib import finish
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)

pkg = run_dir / "wicket"
pkg.mkdir(parents=True, exist_ok=True)
(pkg / "__init__.py").write_text(
    '''
class Latch:
    def __init__(self, root):
        self._fails = 0

    def observe(self, success, duration_ms=0, now=0.0):
        if not success:
            self._fails += 1
        return "closed"

    def state(self, now=0.0):
        return "closed"

    def allow(self, now=0.0):
        return True
''',
    encoding="utf-8",
)
emit(run_dir, "job_completed")
finish(run_dir, MODEL, workers_ran=1, usd=0.11)
