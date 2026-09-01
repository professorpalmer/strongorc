from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class Kiln:
    def __init__(self, root: Path, token: str, generation: int) -> None:
        self.root = Path(root)
        self.token = token
        self.generation = generation
        self.dir = self.root / "state" / "kiln"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / "store.json"
        self._state: dict[str, Any] = {}
        if self.path.is_file():
            self._state = json.loads(self.path.read_text(encoding="utf-8"))

    @classmethod
    def open(cls, root: str | Path, token: str, generation: int | None = None) -> Kiln:
        root = Path(root)
        leases = json.loads((root / "job" / "leases.json").read_text(encoding="utf-8"))
        if token != leases.get("fence"):
            raise PermissionError("stale token")
        live_gen = int(leases.get("generation") or 0)
        if generation is None or int(generation) != live_gen:
            raise PermissionError("stale generation")
        return cls(root, token, live_gen)

    def mutate(self, key: str, value: Any) -> None:
        self._state[key] = value
        self.path.write_text(json.dumps(self._state), encoding="utf-8")

    def get(self, key: str) -> Any:
        return self._state.get(key)
