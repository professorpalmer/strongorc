from __future__ import annotations

from typing import Any


class Ledger:
    def __init__(self) -> None:
        self._fence: dict[str, int] = {}
        self._owner: dict[str, str] = {}
        self._payload: dict[str, Any] = {}

    def acquire(self, resource: str, owner: str) -> int:
        if resource in self._owner:
            raise PermissionError(f"{resource} held by {self._owner[resource]}")
        nxt = self._fence.get(resource, 0) + 1
        self._fence[resource] = nxt
        self._owner[resource] = owner
        return nxt

    def write(self, resource: str, owner: str, fence: int, payload: Any) -> None:
        self._require(resource, owner, fence)
        self._payload[resource] = payload

    def release(self, resource: str, owner: str, fence: int) -> None:
        self._require(resource, owner, fence)
        self._owner.pop(resource, None)

    def expire(self, resource: str) -> None:
        self._owner.pop(resource, None)

    def get(self, resource: str) -> Any:
        return self._payload.get(resource)

    def holder(self, resource: str) -> dict[str, Any] | None:
        if resource not in self._owner:
            return None
        return {"owner": self._owner[resource], "fence": self._fence[resource]}

    def _require(self, resource: str, owner: str, fence: int) -> None:
        if self._owner.get(resource) != owner or self._fence.get(resource) != fence:
            raise PermissionError("stale lease")
