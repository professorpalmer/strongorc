from __future__ import annotations

import fnmatch
from typing import Any


class Match:
    def select(self, records: list[dict[str, Any]], query: dict[str, Any]) -> list[dict[str, Any]]:
        if not query:
            return []
        out: list[dict[str, Any]] = []
        for rec in records:
            for key, pattern in query.items():
                if key not in rec:
                    continue
                value = str(rec.get(key, "")).lower()
                if fnmatch.fnmatch(value, str(pattern).lower()):
                    out.append(rec)
                    break
        return out
