from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from strongorc.schema import ProtocolEvent, Receipt

PROTOCOL_NAME = "protocol.jsonl"
RECEIPT_PATH = Path("receipts") / "job.json"


def protocol_path(run_dir: Path) -> Path:
    return run_dir / PROTOCOL_NAME


def receipt_path(run_dir: Path) -> Path:
    return run_dir / RECEIPT_PATH


def emit(run_dir: Path, event_type: str, **payload: Any) -> None:
    path = protocol_path(run_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"type": event_type, "payload": payload}, sort_keys=True) + "\n")


def read_events(run_dir: Path) -> list[ProtocolEvent]:
    path = protocol_path(run_dir)
    if not path.is_file():
        return []
    events: list[ProtocolEvent] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        events.append(ProtocolEvent.from_dict(json.loads(line)))
    return events


def event_types(events: Iterable[ProtocolEvent]) -> list[str]:
    return [event.type for event in events]


def write_receipt(run_dir: Path, receipt: dict[str, Any]) -> None:
    path = receipt_path(run_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    emit(run_dir, "receipt_written", status=receipt.get("status"), model_id=receipt.get("model_id"))


def read_receipt(run_dir: Path) -> Receipt | None:
    path = receipt_path(run_dir)
    if not path.is_file():
        return None
    return Receipt.from_dict(json.loads(path.read_text(encoding="utf-8")))
