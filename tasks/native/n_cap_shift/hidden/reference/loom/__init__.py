from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class Table:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.dir = self.root / "state" / "loom"
        self.dir.mkdir(parents=True, exist_ok=True)
        self._admits = self.dir / "admits.json"
        self._store = self.dir / "store.json"

    def admit(self) -> None:
        budget = json.loads((self.root / "job" / "budget.json").read_text(encoding="utf-8"))
        cap = int(budget["max_workers"])
        count = self._count()
        if count >= cap:
            raise PermissionError("cap")
        self._admits.write_text(json.dumps({"count": count + 1}), encoding="utf-8")

    def write(self, package: str, key: str, value: Any) -> None:
        leases = json.loads((self.root / "job" / "leases.json").read_text(encoding="utf-8"))
        if package not in (leases.get("leased") or []):
            raise PermissionError("unleased")
        data = self._payloads()
        bucket = data.setdefault(package, {})
        bucket[key] = value
        self._store.write_text(json.dumps(data), encoding="utf-8")

    def get(self, package: str, key: str) -> Any:
        return self._payloads().get(package, {}).get(key)

    def _count(self) -> int:
        if not self._admits.is_file():
            return 0
        return int(json.loads(self._admits.read_text(encoding="utf-8")).get("count", 0))

    def _payloads(self) -> dict[str, dict[str, Any]]:
        if not self._store.is_file():
            return {}
        return json.loads(self._store.read_text(encoding="utf-8"))
