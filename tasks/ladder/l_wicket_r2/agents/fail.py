from pathlib import Path

from strongorc.agentlib import finish
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)

pkg = run_dir / "wicket"
pkg.mkdir(parents=True, exist_ok=True)
(pkg / "__init__.py").write_text(
    '''
from pathlib import Path

class Latch:
    def __init__(self, root):
        self.root = Path(root)
        self.fails = []

    def observe(self, success, duration_ms=0, now=0.0):
        if not success:
            self.fails.append(now)
        self.fails = [stamp for stamp in self.fails if now - stamp <= 120]
        return self.state(now)

    def state(self, now):
        recent = [stamp for stamp in self.fails if now - stamp <= 120]
        if len(recent) >= 20:
            return "open"
        return "closed"

    def allow(self, now):
        return self.state(now) != "open"
''',
    encoding="utf-8",
)
emit(run_dir, "job_completed")
finish(run_dir, MODEL, workers_ran=1, usd=0.11)
