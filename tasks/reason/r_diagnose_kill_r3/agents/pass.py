import json
import time
from pathlib import Path

from strongorc.agentlib import finish, write_checkpoint
from strongorc.env import getenv
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)
model = MODEL
interrupt = True
clinic = 'from __future__ import annotations\n\nimport hashlib\nimport json\nfrom pathlib import Path\n\n\nclass Clinic:\n    def __init__(self, root: str | Path) -> None:\n        self.root = Path(root)\n\n    def repair(self) -> None:\n        causes = self._causes()\n        if len(causes) > 1:\n            raise PermissionError("underdetermined")\n        if len(causes) == 1:\n            self._fix(causes[0])\n\n    def _causes(self) -> list[str]:\n        found: list[str] = []\n        leases = self.root / "job" / "leases.json"\n        if leases.is_file():\n            fence = json.loads(leases.read_text(encoding="utf-8")).get("fence")\n            if not fence or fence == "stale":\n                found.append("stale_lease")\n        child = self.root / "state" / "children" / "leaf.json"\n        if child.is_file():\n            status = json.loads(child.read_text(encoding="utf-8")).get("status")\n            if status != "ok":\n                found.append("dead_child")\n        budget = self.root / "job" / "budget.json"\n        if budget.is_file():\n            cap = int(json.loads(budget.read_text(encoding="utf-8")).get("max_workers") or 0)\n            if cap <= 0:\n                found.append("cap")\n        payload = self.root / "state" / "payload.json"\n        digest = self.root / "state" / "digest.json"\n        if payload.is_file() and digest.is_file():\n            actual = hashlib.sha256(payload.read_bytes()).hexdigest()\n            listed = json.loads(digest.read_text(encoding="utf-8")).get("sha256")\n            if listed != actual:\n                found.append("hash_drift")\n        return found\n\n    def _fix(self, cause: str) -> None:\n        if cause == "dead_child":\n            path = self.root / "state" / "children" / "leaf.json"\n            path.parent.mkdir(parents=True, exist_ok=True)\n            path.write_text(json.dumps({"status": "ok"}, indent=2, sort_keys=True) + "\\n", encoding="utf-8")\n        elif cause == "stale_lease":\n            path = self.root / "job" / "leases.json"\n            data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}\n            data["fence"] = "live-alpha"\n            path.parent.mkdir(parents=True, exist_ok=True)\n            path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\\n", encoding="utf-8")\n        elif cause == "cap":\n            path = self.root / "job" / "budget.json"\n            data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}\n            data["max_workers"] = 2\n            path.parent.mkdir(parents=True, exist_ok=True)\n            path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\\n", encoding="utf-8")\n        elif cause == "hash_drift":\n            payload = self.root / "state" / "payload.json"\n            digest = hashlib.sha256(payload.read_bytes()).hexdigest()\n            path = self.root / "state" / "digest.json"\n            path.parent.mkdir(parents=True, exist_ok=True)\n            path.write_text(json.dumps({"sha256": digest}, indent=2, sort_keys=True) + "\\n", encoding="utf-8")\n'

if interrupt and getenv("RESUME") != "1":
    emit(run_dir, "worker_started", worker="alpha")
    write_checkpoint(run_dir, "checkpoint.json", {"phase": 1})
    time.sleep(3600)
else:
    if interrupt:
        emit(run_dir, "resumed_from_checkpoint")
        reply = run_dir / "state" / "lab_reply.json"
        if reply.is_file():
            causal = json.loads(reply.read_text(encoding="utf-8")).get("causal")
            if causal:
                (run_dir / "state").mkdir(parents=True, exist_ok=True)
                (run_dir / "state" / "probe.json").write_text(
                    json.dumps({"inspect": causal}, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
    emit(run_dir, "worker_started", worker="alpha")
    dest = run_dir / "hearth"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "__init__.py").write_text(clinic, encoding="utf-8")
    import sys
    sys.path.insert(0, str(run_dir))
    from hearth import Clinic
    Clinic(run_dir).repair()
    emit(run_dir, "worker_finished", worker="alpha")
    finish(run_dir, model, workers_ran=1, usd=0.36)
