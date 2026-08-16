from pathlib import Path

from strongorc.agentlib import finish
from strongorc.protocol import emit

pkg = Path(RUN_DIR) / "slotbook"
pkg.mkdir(parents=True, exist_ok=True)
(pkg / "__init__.py").write_text(
    """
from datetime import datetime, timezone

class Book:
    def __init__(self):
        self._slots = []
    def add(self, start, end):
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
            end = end.replace(tzinfo=timezone.utc)
        for other_start, other_end in self._slots:
            if start <= other_end and end >= other_start:
                raise ValueError("overlap")
        self._slots.append((start, end))
        return len(self._slots) - 1
    def add_weekly(self, start, end, count):
        from datetime import timedelta
        ids = []
        for i in range(count):
            ids.append(self.add(start + timedelta(days=7*i), end + timedelta(days=7*i)))
        return ids
    def conflicts(self, start, end):
        return False
    def slots(self):
        return list(self._slots)
""",
    encoding="utf-8",
)
emit(Path(RUN_DIR), "artifact_consumed")
finish(Path(RUN_DIR), MODEL, workers_ran=1, usd=0.06)
