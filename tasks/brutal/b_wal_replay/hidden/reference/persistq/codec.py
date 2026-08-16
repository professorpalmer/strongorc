from __future__ import annotations

import json
import struct
import zlib
from typing import Any

MAGIC = b"PQ01"
HEADER = struct.Struct(">II")


def encode_record(payload: dict[str, Any]) -> bytes:
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return HEADER.pack(len(body), zlib.crc32(body) & 0xFFFFFFFF) + body


def decode_stream(data: bytes) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    offset = 0
    length = len(data)
    while offset < length:
        if offset + HEADER.size > length:
            break
        size, expected = HEADER.unpack_from(data, offset)
        start = offset + HEADER.size
        end = start + size
        if end > length:
            break
        body = data[start:end]
        if (zlib.crc32(body) & 0xFFFFFFFF) != expected:
            break
        records.append(json.loads(body.decode("utf-8")))
        offset = end
    return records
