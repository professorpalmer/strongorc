from __future__ import annotations

import json
from pathlib import Path


class Booth:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.dir = self.root / "state" / "sides"
        self.dir.mkdir(parents=True, exist_ok=True)
        self._gathered = self.root / "state" / "gathered.json"

    def put(self, side: str, value: int) -> None:
        if side not in {"left", "right"}:
            raise ValueError(side)
        (self.dir / f"{side}.json").write_text(json.dumps({"value": int(value)}), encoding="utf-8")

    def gather(self) -> int | None:
        left = self._side("left")
        right = self._side("right")
        if left is None and right is None:
            return None
        if left is None or right is None:
            raise PermissionError("both sides required")
        if self._gathered.is_file():
            return int(json.loads(self._gathered.read_text(encoding="utf-8"))["value"])
        total = left + right
        self._gathered.write_text(json.dumps({"value": total}), encoding="utf-8")
        return total

    def _side(self, name: str) -> int | None:
        path = self.dir / f"{name}.json"
        if not path.is_file():
            return None
        return int(json.loads(path.read_text(encoding="utf-8"))["value"])
