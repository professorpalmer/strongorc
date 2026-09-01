"""Stdlib-only fixture generator. Not a secret bank."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def materialize(run_dir: Path, nonce: str) -> None:
    spec = json.loads((run_dir / "job" / "spec.json").read_text(encoding="utf-8"))
    live = run_dir / "state" / "live.json"
    live.parent.mkdir(parents=True, exist_ok=True)
    live.write_text(
        json.dumps({"base": spec["base"], "nonce": nonce}, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def after_interrupt(run_dir: Path, nonce: str, step_index: int) -> None:
    live = run_dir / "state" / "live.json"
    payload = json.loads(live.read_text(encoding="utf-8"))
    payload["interrupt_step"] = step_index
    payload["nonce"] = nonce
    live.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def generate(run_dir: Path, nonce: str) -> Path:
    overlay_hidden = Path(__file__).resolve().parents[1] / "hidden"
    formula = (overlay_hidden / "formula.txt").read_text(encoding="utf-8").strip()
    if formula != "sha256(base:nonce)":
        raise ValueError(f"unexpected fixture formula {formula!r}")
    spec = json.loads((run_dir / "job" / "spec.json").read_text(encoding="utf-8"))
    base = spec["base"]
    expected = hashlib.sha256(f"{base}:{nonce}".encode("utf-8")).hexdigest()
    dest = run_dir / ".holdout" / "generated"
    dest.mkdir(parents=True, exist_ok=True)
    payload = {"expected": expected}
    (dest / "case.json").write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    return dest
