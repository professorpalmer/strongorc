from __future__ import annotations

from typing import Any


class Spool:
    def __init__(self, items: list[dict[str, Any]]) -> None:
        self._items = list(items)
        self._acked: set[str] = set()

    @classmethod
    def from_snapshot(cls, items: list[dict[str, Any]], snapshot: dict[str, Any]) -> Spool:
        spool = cls(items)
        spool._acked = set(snapshot.get("acked") or [])
        return spool

    def pending(self) -> list[dict[str, Any]]:
        return [item for item in self._items if item["id"] not in self._acked]

    def ack(self, item_id: str) -> None:
        ids = {item["id"] for item in self._items}
        if item_id not in ids:
            raise KeyError(item_id)
        self._acked.add(item_id)

    def snapshot(self) -> dict[str, Any]:
        return {"acked": sorted(self._acked)}
