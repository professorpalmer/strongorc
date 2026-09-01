from __future__ import annotations

from pathlib import Path
from typing import Any


class Yard:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.dir = self.root / "state" / "stalls"
        self.dir.mkdir(parents=True, exist_ok=True)

    def hold(self, stall: str, worker: str) -> None:
        raise PermissionError("closed")

    def write(self, stall: str, worker: str, payload: Any) -> None:
        raise PermissionError("closed")

    def release(self, stall: str, worker: str) -> None:
        path = self.dir / f"{stall}.hold"
        if path.is_file():
            path.unlink()

    def holder(self, stall: str) -> str | None:
        path = self.dir / f"{stall}.hold"
        if not path.is_file():
            return None
        return path.read_text(encoding="utf-8")

    def payload(self, stall: str) -> Any:
        return None
