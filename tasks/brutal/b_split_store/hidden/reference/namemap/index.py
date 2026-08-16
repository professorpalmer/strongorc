from __future__ import annotations

from collections import defaultdict


class Index:
    def __init__(self) -> None:
        self._postings: dict[str, set[str]] = defaultdict(set)

    def add(self, token: str, blob_id: str) -> None:
        folded = token.casefold().strip()
        if not folded:
            return
        self._postings[folded].add(blob_id)

    def search(self, query: str) -> list[str]:
        terms = [part.casefold() for part in query.split() if part.strip()]
        if not terms:
            return []
        hits = set(self._postings.get(terms[0], set()))
        for term in terms[1:]:
            hits &= self._postings.get(term, set())
        return sorted(hits)

    def remove(self, blob_id: str) -> None:
        for bucket in self._postings.values():
            bucket.discard(blob_id)
