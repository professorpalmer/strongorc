from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class Store:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.path = self.root / "state" / "spool.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def put(self, key: str, value: Any) -> None:
        data = self._data()
        data[key] = value
        self.path.write_text(json.dumps(data), encoding="utf-8")

    def get(self, key: str) -> Any:
        return self._data().get(key)

    def _data(self) -> dict[str, Any]:
        if not self.path.is_file():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))
