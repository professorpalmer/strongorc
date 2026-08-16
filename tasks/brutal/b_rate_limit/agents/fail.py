from pathlib import Path

from strongorc.agentlib import finish
from strongorc.protocol import emit

pkg = Path(RUN_DIR) / "admit"
pkg.mkdir(parents=True, exist_ok=True)
(pkg / "__init__.py").write_text(
    """
class Gate:
    def __init__(self, **kwargs):
        self.hits = []
    def allow(self, now):
        self.hits = [stamp for stamp in self.hits if now - stamp < 60]
        if len(self.hits) >= 10:
            return False
        self.hits.append(now)
        return True
""",
    encoding="utf-8",
)
emit(Path(RUN_DIR), "artifact_consumed")
finish(Path(RUN_DIR), MODEL, workers_ran=1, usd=0.04)
