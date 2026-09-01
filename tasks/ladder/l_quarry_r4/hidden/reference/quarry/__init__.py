from __future__ import annotations

from pathlib import Path
from typing import Any

KNOWN = {"helper": {"mass": 0}}


class Pit:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def extract(self, name: str) -> dict[str, Any]:
        if name not in KNOWN:
            raise KeyError(name)
        return dict(KNOWN[name])

    def names(self) -> frozenset[str]:
        return frozenset(KNOWN)

    def sealed(self) -> bool:
        return True
