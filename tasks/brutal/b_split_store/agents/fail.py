from pathlib import Path

from strongorc.agentlib import finish

run_dir = Path(RUN_DIR)
(run_dir / "binbox").mkdir(parents=True, exist_ok=True)
(run_dir / "namemap").mkdir(parents=True, exist_ok=True)
(run_dir / "binbox" / "__init__.py").write_text(
    """
import hashlib
class Store:
    def __init__(self):
        self.d = {}
    def put(self, data):
        key = hashlib.sha1(data).hexdigest()
        self.d[key] = data
        return key
    def get(self, blob_id):
        return self.d[blob_id]
""",
    encoding="utf-8",
)
(run_dir / "namemap" / "__init__.py").write_text(
    """
class Index:
    def __init__(self):
        self.d = {}
    def add(self, token, blob_id):
        self.d.setdefault(token, []).append(blob_id)
    def search(self, query):
        return list(self.d.get(query, []))
    def remove(self, blob_id):
        return None
""",
    encoding="utf-8",
)
finish(run_dir, MODEL, workers_ran=1, usd=0.07)
