from __future__ import annotations

from typing import Any


class Tally:
    def __init__(self) -> None:
        self._p: dict[str, int] = {}
        self._n: dict[str, int] = {}
        self._reg: set[str] = set()

    def register(self, replica: str) -> None:
        self._reg.add(replica)
        self._p.setdefault(replica, 0)
        self._n.setdefault(replica, 0)

    def inc(self, replica: str, n: int = 1) -> None:
        if replica not in self._reg:
            raise KeyError(replica)
        if n < 0:
            raise ValueError("n must be >= 0")
        self._p[replica] = self._p.get(replica, 0) + n

    def dec(self, replica: str, n: int = 1) -> None:
        if replica not in self._reg:
            raise KeyError(replica)
        if n < 0:
            raise ValueError("n must be >= 0")
        nxt = self._n.get(replica, 0) + n
        if nxt > self._p.get(replica, 0):
            raise ValueError("dec exceeds inc")
        self._n[replica] = nxt

    def merge(self, other: Tally) -> None:
        for replica in set(other._reg) | set(other._p) | set(other._n):
            self.register(replica)
            self._p[replica] = max(self._p.get(replica, 0), other._p.get(replica, 0))
            self._n[replica] = max(self._n.get(replica, 0), other._n.get(replica, 0))
        for replica in list(self._reg):
            if self._n.get(replica, 0) > self._p.get(replica, 0):
                self._n[replica] = self._p[replica]

    def value(self) -> int:
        return max(0, sum(self._p.values()) - sum(self._n.values()))

    def payload(self) -> dict[str, Any]:
        return {"p": dict(self._p), "n": dict(self._n)}
