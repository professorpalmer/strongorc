from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REQUIRED = ('ok_child', 'leaf')


class Tray:
    def __init__(self, root: str | Path, required: tuple[str, ...] | None = None) -> None:
        self.root = Path(root)
        self.dir = self.root / "state" / "children"
        spec = self.root / "job" / "spec.json"
        if required is not None:
            self.required = tuple(required)
        elif spec.is_file():
            data = json.loads(spec.read_text(encoding="utf-8"))
            self.required = tuple(data.get("children") or REQUIRED)
        else:
            self.required = REQUIRED

    def write_child(self, name: str, status: str) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.dir / f"{name}.json").write_text(json.dumps({"status": status}), encoding="utf-8")

    def child(self, name: str) -> dict[str, Any] | None:
        path = self.dir / f"{name}.json"
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def complete(self) -> str:
        for name in self.required:
            rec = self.child(name)
            if rec is None:
                raise PermissionError(f"missing {name}")
            if rec.get("status") != "ok":
                raise PermissionError(f"dead {name}")
        return "completed"
