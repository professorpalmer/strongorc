from pathlib import Path

from strongorc.agentlib import finish
from strongorc.protocol import emit

pkg = Path(RUN_DIR) / "ink"
pkg.mkdir(parents=True, exist_ok=True)
(pkg / "__init__.py").write_text(
    "import json\n\ndef parse(text, root=None, filename='<stdin>'):\n    return json.loads(text)\n",
    encoding="utf-8",
)
emit(Path(RUN_DIR), "artifact_consumed")
finish(Path(RUN_DIR), MODEL, workers_ran=1, usd=0.03)
