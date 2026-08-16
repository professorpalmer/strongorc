from __future__ import annotations

import hashlib


class Store:
    def __init__(self) -> None:
        self._blobs: dict[str, bytes] = {}

    def put(self, data: bytes) -> str:
        blob_id = hashlib.sha256(data).hexdigest()
        self._blobs[blob_id] = data
        return blob_id

    def get(self, blob_id: str) -> bytes:
        return self._blobs[blob_id]
