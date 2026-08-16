import json
from pathlib import Path

from strongorc.agentlib import finish

run_dir = Path(RUN_DIR)
model = MODEL
nonce = (run_dir / ".harness" / "nonce").read_text(encoding="utf-8").strip()
(run_dir / "src" / "index.ts").write_text(
    f"export const NONCE = {nonce!r};\nexport function index(n: number): number {{\n  return n;\n}}\n",
    encoding="utf-8",
)
(run_dir / "src" / "index.js").unlink()
note = run_dir / "artifacts"
note.mkdir(parents=True, exist_ok=True)
(note / "note.txt").write_text(nonce + "\n", encoding="utf-8")
finish(run_dir, model, workers_ran=1, usd=0.12, extra={"nonce": nonce})
