from pathlib import Path

from strongorc.convert import js_to_typed_ts
from strongorc.protocol import emit, write_receipt

run_dir = Path(RUN_DIR)
model = MODEL
src = run_dir / "src"

for js_path in sorted(src.glob("*.js")):
    ts_path = js_path.with_suffix(".ts")
    ts_path.write_text(js_to_typed_ts(js_path.read_text(encoding="utf-8")), encoding="utf-8")

emit(run_dir, "job_completed")
write_receipt(
    run_dir,
    {
        "status": "completed",
        "model_id": model,
        "usd": 0.22,
        "tokens_in": 1600,
        "tokens_out": 400,
        "workers_ran": 1,
    },
)
