from pathlib import Path

from strongorc.convert import convert_js_tree
from strongorc.protocol import emit, write_receipt

run_dir = Path(RUN_DIR)
model = MODEL

emit(run_dir, "lease_acquired", worker="alpha", path="src/alpha")
convert_js_tree(run_dir / "src" / "alpha")
emit(run_dir, "lease_acquired", worker="beta", path="src/beta")
convert_js_tree(run_dir / "src" / "beta")
(run_dir / "src" / "index.js").unlink()
(run_dir / "src" / "index.ts").write_text(
    'export { one } from "./alpha/one.ts";\n'
    'export { inc } from "./alpha/inc.ts";\n'
    'export { two } from "./beta/two.ts";\n'
    'export { dec } from "./beta/dec.ts";\n',
    encoding="utf-8",
)
shared = run_dir / "src" / "shared"
shared.mkdir(parents=True, exist_ok=True)
(shared / "CONFLICT").write_text("alpha and beta both wrote here\n", encoding="utf-8")
emit(run_dir, "job_completed")
write_receipt(
    run_dir,
    {
        "status": "completed",
        "model_id": model,
        "usd": 0.21,
        "tokens_in": 1100,
        "tokens_out": 300,
        "workers_ran": 2,
    },
)
