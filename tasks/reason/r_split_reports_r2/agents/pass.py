import json
import time
from pathlib import Path

from strongorc.agentlib import finish, write_checkpoint
from strongorc.env import getenv
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)
model = MODEL
interrupt = True
board = 'from __future__ import annotations\n\nimport hashlib\nimport json\nfrom pathlib import Path\n\n\nclass Board:\n    def __init__(self, root: str | Path) -> None:\n        self.root = Path(root)\n\n    def resolve(self) -> object:\n        reports = self._reports()\n        seals = self._seals()\n        eligible = list(seals.get("eligible") or [])\n        hashes = seals.get("sha256") or {}\n        matched = []\n        for name in eligible:\n            path = self._report_path(name)\n            if not path.is_file():\n                continue\n            actual = hashlib.sha256(path.read_bytes()).hexdigest()\n            if hashes.get(name) == actual:\n                matched.append(reports[name])\n        if len(matched) == 1:\n            return matched[0]["value"]\n        reply = self.root / "state" / "lab_reply.json"\n        if reply.is_file():\n            cells = json.loads(reply.read_text(encoding="utf-8")).get("cells") or []\n            want = {cell.get("sha256") for cell in cells if cell.get("eligible")}\n            for name, rec in reports.items():\n                path = self._report_path(name)\n                if hashlib.sha256(path.read_bytes()).hexdigest() in want:\n                    return rec["value"]\n        raise PermissionError("underdetermined")\n\n    def _seals(self) -> dict:\n        path = self.root / "job" / "seals.json"\n        if not path.is_file():\n            return {}\n        return json.loads(path.read_text(encoding="utf-8"))\n\n    def _reports(self) -> dict:\n        folder = self.root / "state" / "reports"\n        out = {}\n        if not folder.is_dir():\n            return out\n        for path in sorted(folder.glob("*.json")):\n            out[path.stem] = json.loads(path.read_text(encoding="utf-8"))\n        return out\n\n    def _report_path(self, name: str) -> Path:\n        return self.root / "state" / "reports" / f"{name}.json"\n'

def _undetermined():
    seals = json.loads((run_dir / "job" / "seals.json").read_text(encoding="utf-8"))
    return not (seals.get("eligible") or [])

if interrupt and getenv("RESUME") != "1":
    emit(run_dir, "worker_started", worker="alpha")
    if _undetermined():
        alpha = run_dir / "state" / "reports" / "alpha.json"
        import hashlib
        digest = hashlib.sha256(alpha.read_bytes()).hexdigest()
        (run_dir / "state").mkdir(parents=True, exist_ok=True)
        (run_dir / "state" / "probe.json").write_text(
            json.dumps({"worker": "alpha", "sha256": digest}, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    write_checkpoint(run_dir, "checkpoint.json", {"phase": 1})
    time.sleep(3600)
else:
    if interrupt:
        emit(run_dir, "resumed_from_checkpoint")
    emit(run_dir, "worker_started", worker="alpha")
    dest = run_dir / "ledger"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "__init__.py").write_text(board, encoding="utf-8")
    emit(run_dir, "worker_finished", worker="alpha")
    finish(run_dir, model, workers_ran=1, usd=0.36)
