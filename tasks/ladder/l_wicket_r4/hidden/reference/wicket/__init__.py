from __future__ import annotations

import json
from pathlib import Path


class Latch:
    TRIP = 2
    COOLDOWN = 1.0
    CLOSE_SUCCESSES = 2
    SLOW_MS = 10000

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.path = self.root / "state" / "latch.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data = {
            "state": "closed",
            "consecutive_fails": 0,
            "half_successes": 0,
            "opened_at": None,
        }
        if self.path.is_file():
            self._data.update(json.loads(self.path.read_text(encoding="utf-8")))

    def observe(self, success: bool, duration_ms: float = 0, now: float = 0.0) -> str:
        if duration_ms >= self.SLOW_MS:
            success = False
        current = self.state(now)
        if current == "open":
            self._persist()
            return "open"
        if current == "half_open":
            if success:
                self._data["half_successes"] = int(self._data.get("half_successes") or 0) + 1
                if self._data["half_successes"] >= self.CLOSE_SUCCESSES:
                    self._data.update({"state": "closed", "consecutive_fails": 0, "half_successes": 0, "opened_at": None})
            else:
                self._data.update({"state": "open", "half_successes": 0, "opened_at": now, "consecutive_fails": self.TRIP})
            self._persist()
            return self._data["state"]
        if success:
            self._data["consecutive_fails"] = 0
        else:
            self._data["consecutive_fails"] = int(self._data.get("consecutive_fails") or 0) + 1
            if self._data["consecutive_fails"] >= self.TRIP:
                self._data.update({"state": "open", "opened_at": now, "half_successes": 0})
        self._persist()
        return self._data["state"]

    def state(self, now: float) -> str:
        current = self._data.get("state") or "closed"
        opened_at = self._data.get("opened_at")
        if current == "open" and opened_at is not None and now - float(opened_at) >= self.COOLDOWN:
            self._data["state"] = "half_open"
            self._data["half_successes"] = 0
            self._persist()
            return "half_open"
        return current

    def allow(self, now: float) -> bool:
        return self.state(now) != "open"

    def _persist(self) -> None:
        self.path.write_text(json.dumps(self._data), encoding="utf-8")
