from pathlib import Path

from strongorc.agentlib import finish

pkg = Path(RUN_DIR) / "holdbook"
pkg.mkdir(parents=True, exist_ok=True)
(pkg / "__init__.py").write_text(
    """
class Ledger:
    def __init__(self):
        self.clock = 0
        self.held = {}
        self.data = {}
    def acquire(self, resource, owner):
        self.clock += 1
        self.held[resource] = (owner, self.clock)
        return self.clock
    def write(self, resource, owner, fence, payload):
        self.data[resource] = payload
    def release(self, resource, owner, fence):
        self.held.pop(resource, None)
        self.clock = 0
    def expire(self, resource):
        self.held.pop(resource, None)
        self.clock = 0
    def get(self, resource):
        return self.data.get(resource)
    def holder(self, resource):
        if resource not in self.held:
            return None
        owner, fence = self.held[resource]
        return {"owner": owner, "fence": fence}
""",
    encoding="utf-8",
)
finish(Path(RUN_DIR), MODEL, workers_ran=1, usd=0.08)
