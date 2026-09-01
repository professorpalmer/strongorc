from pathlib import Path

from strongorc.agentlib import finish
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)

pkg = run_dir / "wick"
pkg.mkdir(parents=True, exist_ok=True)
(pkg / "__init__.py").write_text(
    '''
class Match:
    def select(self, records, query):
        if not query:
            return list(records)
        out = []
        for rec in records:
            ok = True
            for key, pattern in query.items():
                if key not in rec:
                    ok = False
                    break
                if not str(rec[key]).startswith(str(pattern)):
                    ok = False
                    break
            if ok:
                out.append(rec)
        return out
''',
    encoding="utf-8",
)
emit(run_dir, "job_completed")
finish(run_dir, MODEL, workers_ran=1, usd=0.11)
