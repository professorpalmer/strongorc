from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from persistq.codec import MAGIC, decode_stream, encode_record


class Store:
    def __init__(self, directory: Path, fence: int) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.log_path = self.directory / "log.wal"
        self.meta_path = self.directory / "meta.json"
        self.snapshot_path = self.directory / "snapshot.json"
        self._fence = fence
        self._state: dict[str, Any] = {}
        self._seen: set[str] = set()
        self._load_meta()
        self._load_snapshot()
        self._replay()

    @classmethod
    def open(cls, directory: str | Path, fence: int = 0) -> Store:
        return cls(Path(directory), fence)

    def require_fence(self, token: int) -> None:
        if token < self._fence:
            raise PermissionError(f"stale fence {token} < {self._fence}")

    def append(self, record: dict[str, Any], fence: int) -> None:
        self.require_fence(fence)
        record_id = str(record["id"])
        if record_id in self._seen:
            return
        existing = self.log_path.read_bytes() if self.log_path.is_file() else b""
        if not existing.startswith(MAGIC):
            existing = MAGIC
        self.log_path.write_bytes(existing + encode_record(record))
        self._apply(record)

    def snapshot(self) -> None:
        self.snapshot_path.write_text(json.dumps(self._state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        self._write_meta()

    def truncate(self) -> None:
        self.snapshot()
        self.log_path.write_bytes(b"")

    def get(self, key: str) -> Any:
        return self._state.get(key)

    def items(self) -> dict[str, Any]:
        return dict(self._state)

    def current_fence(self) -> int:
        return self._fence

    def _apply(self, record: dict[str, Any]) -> None:
        record_id = str(record["id"])
        if record_id in self._seen:
            return
        self._seen.add(record_id)
        op = record["op"]
        key = record["key"]
        if op == "delete":
            self._state.pop(key, None)
            return
        if op != "set":
            raise ValueError(f"unknown op {op}")
        self._state[key] = record["value"]

    def _replay(self) -> None:
        if not self.log_path.is_file():
            return
        data = self.log_path.read_bytes()
        if not data.startswith(MAGIC):
            return
        for record in decode_stream(data[len(MAGIC) :]):
            self._apply(record)

    def _load_snapshot(self) -> None:
        if not self.snapshot_path.is_file():
            return
        self._state = json.loads(self.snapshot_path.read_text(encoding="utf-8"))

    def _load_meta(self) -> None:
        if not self.meta_path.is_file():
            self._write_meta()
            return
        meta = json.loads(self.meta_path.read_text(encoding="utf-8"))
        stored = int(meta.get("fence", 0))
        if self._fence < stored:
            raise PermissionError(f"stale open fence {self._fence} < {stored}")
        self._fence = max(self._fence, stored)
        self._seen = set(meta.get("seen") or [])

    def _write_meta(self) -> None:
        payload = {"fence": self._fence, "seen": sorted(self._seen)}
        self.meta_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
