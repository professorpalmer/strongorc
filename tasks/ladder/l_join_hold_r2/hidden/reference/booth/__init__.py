from __future__ import annotations

import json
from pathlib import Path

REQUIRED = ('left', 'right', 'center')


class Booth:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.dir = self.root / "state" / "sides"
        self.dir.mkdir(parents=True, exist_ok=True)
        self._gathered = self.root / "state" / "gathered.json"
        spec = self.root / "job" / "spec.json"
        if spec.is_file():
            data = json.loads(spec.read_text(encoding="utf-8"))
            listed = data.get("sides")
            self.required = tuple(listed) if listed else REQUIRED
        else:
            self.required = REQUIRED

    def put(self, side: str, value: int) -> None:
        if side not in self.required:
            raise ValueError(side)
        (self.dir / f"{side}.json").write_text(json.dumps({"value": int(value)}), encoding="utf-8")

    def gather(self) -> int | None:
        found = [self._side(name) for name in self.required]
        if all(item is None for item in found):
            return None
        if any(item is None for item in found):
            raise PermissionError("all sides required")
        if self._gathered.is_file():
            return int(json.loads(self._gathered.read_text(encoding="utf-8"))["value"])
        total = sum(int(item) for item in found)
        self._gathered.write_text(json.dumps({"value": total}), encoding="utf-8")
        return total

    def _side(self, name: str) -> int | None:
        path = self.dir / f"{name}.json"
        if not path.is_file():
            return None
        return int(json.loads(path.read_text(encoding="utf-8"))["value"])
