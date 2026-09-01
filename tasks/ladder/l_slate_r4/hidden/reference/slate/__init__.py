from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class Pad:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.path = self.root / "state" / "slate.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._state: dict[str, Any] = {}
        self._cmds: dict[str, tuple[str, Any]] = {}
        if self.path.is_file():
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            self._state = raw.get("state") or {}
            self._cmds = {key: tuple(value) for key, value in (raw.get("cmds") or {}).items()}

    def apply(self, cmd_id: str, key: str, payload: Any) -> None:
        if not cmd_id:
            raise ValueError("empty cmd_id")
        prev = self._cmds.get(cmd_id)
        if prev is not None:
            raise ValueError("replay")
        self._cmds[cmd_id] = (key, payload)
        self._state[key] = payload
        self._persist()

    def get(self, key: str) -> Any:
        return self._state.get(key)

    def seen(self) -> set[str]:
        return set(self._cmds)

    def _persist(self) -> None:
        payload = {"state": self._state, "cmds": {key: list(value) for key, value in self._cmds.items()}}
        self.path.write_text(json.dumps(payload), encoding="utf-8")
