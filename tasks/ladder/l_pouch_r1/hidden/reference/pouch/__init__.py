from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class Bin:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.path = self.root / "state" / "pouch.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._items: dict[int, Any] = {}
        if self.path.is_file():
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            self._items = {int(key): value for key, value in raw.items()}

    def accept(self, seq: int, slip: Any) -> None:
        seq = int(seq)
        if seq < 1:
            raise ValueError("seq must be >= 1")
        if seq in self._items:
            raise ValueError("sealed")
        expected = (max(self._items) + 1) if self._items else 1
        if seq != expected:
            raise ValueError("gap")
        self._items[seq] = slip
        self._persist()

    def get(self, seq: int) -> Any:
        return self._items.get(int(seq))

    def gaps(self) -> list[int]:
        if not self._items:
            return []
        return [index for index in range(1, max(self._items) + 1) if index not in self._items]

    def _persist(self) -> None:
        self.path.write_text(json.dumps({str(key): value for key, value in self._items.items()}), encoding="utf-8")
