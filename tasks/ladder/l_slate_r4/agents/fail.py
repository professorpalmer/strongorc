from pathlib import Path

from strongorc.agentlib import finish
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)

pkg = run_dir / "slate"
pkg.mkdir(parents=True, exist_ok=True)
(pkg / "__init__.py").write_text(
    '''
class Pad:
    def __init__(self, root):
        self._state = {}
        self._seen = set()

    def apply(self, cmd_id, key, payload):
        self._seen.add(cmd_id)
        self._state[key] = self._state.get(key, 0) + payload

    def get(self, key):
        return self._state.get(key)

    def seen(self):
        return self._seen
''',
    encoding="utf-8",
)
emit(run_dir, "job_completed")
finish(run_dir, MODEL, workers_ran=1, usd=0.11)
