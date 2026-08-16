from pathlib import Path

from strongorc.agentlib import finish

pkg = Path(RUN_DIR) / "jobnet"
pkg.mkdir(parents=True, exist_ok=True)
(pkg / "__init__.py").write_text(
    """
class Runner:
    def __init__(self):
        self.jobs = []
    def add(self, job_id, deps, fn):
        self.jobs.append((job_id, deps, fn))
    def waves(self):
        return [[job_id] for job_id, _, _ in self.jobs]
    def run(self):
        status = {}
        for job_id, _, fn in self.jobs:
            try:
                fn()
                status[job_id] = "ok"
            except Exception:
                status[job_id] = "failed"
        return status
""",
    encoding="utf-8",
)
finish(Path(RUN_DIR), MODEL, workers_ran=1, usd=0.09)
