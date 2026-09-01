from pathlib import Path

from strongorc.agentlib import finish
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)

pkg = run_dir / "wick"
pkg.mkdir(parents=True, exist_ok=True)
(pkg / "__init__.py").write_text(
    '''
from pathlib import Path
import fnmatch

class Match:
    def select(self, records, query):
        if not query:
            return []
        out = []
        for rec in records:
            for key, pattern in query.items():
                value = str(rec.get(key, "")).lower()
                if fnmatch.fnmatch(value, str(pattern).lower()):
                    out.append(rec)
                    break
        return out
''',
    encoding="utf-8",
)
emit(run_dir, "job_completed")
finish(run_dir, MODEL, workers_ran=1, usd=0.11)
