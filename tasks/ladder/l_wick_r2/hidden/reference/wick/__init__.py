from __future__ import annotations

from typing import Any


class Match:
    def select(self, records: list[dict[str, Any]], query: dict[str, Any]) -> list[dict[str, Any]]:
        if not query:
            return list(records)
        out: list[dict[str, Any]] = []
        for rec in records:
            if self._matches(rec, query):
                out.append(rec)
        return out

    def _matches(self, rec: dict[str, Any], query: dict[str, Any]) -> bool:
        for key, pattern in query.items():
            if key not in rec:
                continue
            value = rec[key]
            if not isinstance(value, str) or not isinstance(pattern, str):
                if value == pattern:
                    return True
                continue
            if value.startswith(pattern):
                return True
        return False
