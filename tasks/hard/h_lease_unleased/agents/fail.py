from pathlib import Path

from strongorc.convert import convert_js_tree
from strongorc.protocol import emit, write_receipt

run_dir = Path(RUN_DIR)
model = MODEL

emit(run_dir, "lease_acquired", worker="alpha", path="src/alpha")
convert_js_tree(run_dir / "src" / "alpha")
emit(run_dir, "lease_acquired", worker="beta", path="src/beta")
convert_js_tree(run_dir / "src" / "beta")
convert_js_tree(run_dir / "src" / "gamma")
(run_dir / "src" / "index.js").unlink()
(run_dir / "src" / "index.ts").write_text(
    'export { one } from "./alpha/one.ts";\n'
    'export { inc } from "./alpha/inc.ts";\n'
    'export { two } from "./beta/two.ts";\n'
    'export { dec } from "./beta/dec.ts";\n',
    encoding="utf-8",
)
emit(run_dir, "job_completed")
write_receipt(
    run_dir,
    {
        "status": "completed",
        "model_id": model,
        "usd": 0.24,
        "tokens_in": 1300,
        "tokens_out": 340,
        "workers_ran": 2,
    },
)
