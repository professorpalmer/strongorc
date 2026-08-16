from pathlib import Path

from strongorc.agentlib import finish
from strongorc.protocol import emit

pkg = Path(RUN_DIR) / "tally"
pkg.mkdir(parents=True, exist_ok=True)
(pkg / "__init__.py").write_text(
    """
class Tally:
    def __init__(self):
        self.total = 0
    def inc(self, replica, n=1):
        self.total += n
    def dec(self, replica, n=1):
        self.total -= n
    def merge(self, other):
        self.total += other.total
    def value(self):
        return self.total
    def payload(self):
        return {"p": {"x": self.total}, "n": {}}
""",
    encoding="utf-8",
)
emit(Path(RUN_DIR), "job_completed")
finish(Path(RUN_DIR), MODEL, workers_ran=1, usd=0.05)
