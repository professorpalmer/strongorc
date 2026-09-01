from pathlib import Path

from strongorc.agentlib import finish
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)

pkg = run_dir / "kiln"
pkg.mkdir(parents=True, exist_ok=True)
(pkg / "__init__.py").write_text(
    '''
from pathlib import Path

class Kiln:
    def __init__(self, root, token=None):
        self.root = Path(root)
        self.token = token
        self._state = {}

    @classmethod
    def open(cls, root, token=None):
        return cls(root, token)

    def mutate(self, key, value):
        self._state[key] = value

    def get(self, key):
        return self._state.get(key)
''',
    encoding="utf-8",
)
emit(run_dir, "job_completed")
finish(run_dir, MODEL, workers_ran=1, usd=0.11)
