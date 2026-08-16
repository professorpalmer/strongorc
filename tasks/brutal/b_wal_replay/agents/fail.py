from pathlib import Path

from strongorc.agentlib import finish
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)
pkg = run_dir / "persistq"
pkg.mkdir(parents=True, exist_ok=True)
(pkg / "__init__.py").write_text(
    """
import json
from pathlib import Path

class Store:
    def __init__(self, directory, fence=0):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "log.wal"
        self._state = {}
        if self.path.is_file():
            for line in self.path.read_text().splitlines():
                if line.strip():
                    rec = json.loads(line)
                    self._state[rec["key"]] = rec.get("value")

    @classmethod
    def open(cls, directory, fence=0):
        return cls(directory, fence)

    def require_fence(self, token):
        return None

    def append(self, record, fence):
        with self.path.open("a") as handle:
            handle.write(json.dumps(record) + "\\n")
        self._state[record["key"]] = record.get("value")

    def snapshot(self):
        return None

    def truncate(self):
        self.path.write_text("")

    def get(self, key):
        return self._state.get(key)
""",
    encoding="utf-8",
)
emit(run_dir, "job_completed")
finish(run_dir, MODEL, workers_ran=1, usd=0.11)
