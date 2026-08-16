from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from strongorc.protocol import emit, write_receipt


def copy_reference(run_dir: Path, agent_file: Path, names: list[str] | None = None) -> list[str]:
    src = Path(agent_file).resolve().parents[1] / "hidden" / "reference"
    copied: list[str] = []
    if not src.is_dir():
        return copied
    children = [src / name for name in names] if names else sorted(src.iterdir())
    for child in children:
        if not child.exists():
            continue
        dest = run_dir / child.name
        if child.is_dir():
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(child, dest)
        else:
            dest.write_bytes(child.read_bytes())
        copied.append(child.name)
    return copied


def write_checkpoint(run_dir: Path, name: str, payload: dict[str, Any]) -> Path:
    state = run_dir / "state"
    state.mkdir(parents=True, exist_ok=True)
    path = state / name
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    emit(run_dir, "checkpoint_written", path=name)
    return path


def finish(
    run_dir: Path,
    model: str,
    *,
    status: str = "completed",
    workers_ran: int = 1,
    usd: float = 0.22,
    tokens_in: int = 900,
    tokens_out: int = 180,
    extra: dict[str, Any] | None = None,
) -> None:
    event = {"completed": "job_completed", "refused": "job_refused", "failed": "job_failed"}.get(
        status, "job_completed"
    )
    emit(run_dir, event)
    receipt: dict[str, Any] = {
        "status": status,
        "model_id": model,
        "usd": usd,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "workers_ran": workers_ran,
    }
    if extra:
        receipt.update(extra)
    write_receipt(run_dir, receipt)
