from pathlib import Path

from strongorc.convert import convert_js_tree
from strongorc.protocol import emit, write_receipt

run_dir = Path(RUN_DIR)
model = MODEL

emit(run_dir, "lease_acquired", worker="east", path="src/east")
convert_js_tree(run_dir / "src" / "east")
convert_js_tree(run_dir / "src" / "west")
(run_dir / "src" / "index.js").unlink()
(run_dir / "src" / "index.ts").write_text(
    'export { one } from "./east/one.ts";\nexport { two } from "./west/two.ts";\n',
    encoding="utf-8",
)
emit(run_dir, "job_completed")
write_receipt(
    run_dir,
    {
        "status": "completed",
        "model_id": model,
        "usd": 0.28,
        "tokens_in": 1500,
        "tokens_out": 360,
        "workers_ran": 1,
    },
)
