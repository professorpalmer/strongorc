from pathlib import Path

from strongorc.convert import convert_js_tree
from strongorc.protocol import emit, write_receipt

run_dir = Path(RUN_DIR)
model = MODEL

emit(run_dir, "worker_started", worker="left")
convert_js_tree(run_dir / "src" / "left")
emit(run_dir, "worker_finished", worker="left")
emit(run_dir, "worker_started", worker="right")
convert_js_tree(run_dir / "src" / "right")
emit(run_dir, "worker_finished", worker="right")
(run_dir / "src" / "index.js").unlink()
(run_dir / "src" / "index.ts").write_text(
    'export { add } from "./left/add.ts";\nexport { mul } from "./right/mul.ts";\n',
    encoding="utf-8",
)
emit(run_dir, "job_completed")
write_receipt(
    run_dir,
    {
        "status": "completed",
        "model_id": model,
        "usd": 0.19,
        "tokens_in": 1000,
        "tokens_out": 260,
        "workers_ran": 2,
    },
)
