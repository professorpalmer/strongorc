from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class Yard:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.dir = self.root / "state" / "stalls"
        self.dir.mkdir(parents=True, exist_ok=True)

    def hold(self, stall: str, worker: str) -> None:
        current = self.holder(stall)
        if current and current != worker:
            raise PermissionError(f"{stall} held by {current}")
        (self.dir / f"{stall}.hold").write_text(worker, encoding="utf-8")

    def write(self, stall: str, worker: str, payload: Any) -> None:
        if self.holder(stall) != worker:
            raise PermissionError("write without hold")
        (self.dir / f"{stall}.json").write_text(json.dumps({"value": payload}), encoding="utf-8")

    def release(self, stall: str, worker: str) -> None:
        if self.holder(stall) != worker:
            raise PermissionError("release by non-holder")
        path = self.dir / f"{stall}.hold"
        if path.is_file():
            path.unlink()

    def holder(self, stall: str) -> str | None:
        path = self.dir / f"{stall}.hold"
        if not path.is_file():
            return None
        return path.read_text(encoding="utf-8")

    def payload(self, stall: str) -> Any:
        path = self.dir / f"{stall}.json"
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))["value"]
