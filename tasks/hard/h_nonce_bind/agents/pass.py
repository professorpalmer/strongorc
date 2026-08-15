import json
from pathlib import Path

from strongorc.convert import convert_js_tree
from strongorc.protocol import emit, write_receipt

run_dir = Path(RUN_DIR)
model = MODEL
spec = json.loads((run_dir / "job" / "spec.json").read_text(encoding="utf-8"))
nonce = spec["nonce"]

convert_js_tree(run_dir / "src")
index = run_dir / "src" / "index.ts"
index.write_text(index.read_text(encoding="utf-8") + f"// nonce {nonce}\n", encoding="utf-8")
emit(run_dir, "job_completed")
write_receipt(
    run_dir,
    {
        "status": "completed",
        "model_id": model,
        "usd": 0.12,
        "tokens_in": 500,
        "tokens_out": 120,
        "workers_ran": 1,
        "nonce": nonce,
    },
)
