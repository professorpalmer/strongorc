from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class Kiln:
    def __init__(self, root: Path, token: str) -> None:
        self.root = Path(root)
        self.token = token
        self.dir = self.root / "state" / "kiln"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / "store.json"
        self._state: dict[str, Any] = {}
        if self.path.is_file():
            self._state = json.loads(self.path.read_text(encoding="utf-8"))

    @classmethod
    def open(cls, root: str | Path, token: str) -> Kiln:
        root = Path(root)
        live = json.loads((root / "job" / "leases.json").read_text(encoding="utf-8")).get("fence")
        if token != live:
            raise PermissionError("stale token")
        return cls(root, token)

    def mutate(self, key: str, value: Any) -> None:
        self._state[key] = value
        self.path.write_text(json.dumps(self._state), encoding="utf-8")

    def get(self, key: str) -> Any:
        return self._state.get(key)
