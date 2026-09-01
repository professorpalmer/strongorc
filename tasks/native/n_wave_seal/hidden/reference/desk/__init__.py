from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class Board:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self._seals = self.root / "state" / "seals"
        self._seals.mkdir(parents=True, exist_ok=True)

    def open(self, lane: int) -> None:
        if lane < 1:
            raise ValueError("lane must be >= 1")
        if lane > 1 and not self._sealed(lane - 1):
            raise PermissionError(f"lane {lane - 1} is unsealed")

    def seal(self, lane: int, receipt: Any) -> None:
        if not isinstance(receipt, dict):
            raise ValueError("hollow print is not a seal")
        if receipt.get("status") != "ok" or not receipt.get("worker"):
            raise ValueError("seal needs a real receipt")
        if self._sealed(lane):
            return
        if lane > 1 and not self._sealed(lane - 1):
            raise PermissionError(f"lane {lane - 1} is unsealed")
        path = self._seals / f"{lane}.json"
        path.write_text(json.dumps(dict(receipt), indent=2) + "\n", encoding="utf-8")

    def receipt(self, lane: int) -> dict[str, Any] | None:
        path = self._seals / f"{lane}.json"
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def _sealed(self, lane: int) -> bool:
        rec = self.receipt(lane)
        return bool(rec and rec.get("status") == "ok" and rec.get("worker"))
