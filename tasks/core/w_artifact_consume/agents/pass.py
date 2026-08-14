import json
from pathlib import Path

from strongorc.protocol import emit, write_receipt

run_dir = Path(RUN_DIR)
model = MODEL
src = run_dir / "src"
src.mkdir(parents=True, exist_ok=True)

shape = json.loads((run_dir / "state" / "discoveries" / "api_shape.json").read_text(encoding="utf-8"))
emit(run_dir, "artifact_consumed", path="state/discoveries/api_shape.json")
args = ", ".join(shape["args"])
(src / "adapter.py").write_text(
    f"def {shape['function']}({args}) -> {shape['returns']}:\n"
    f"    return x + y  # nonce {shape['nonce']}\n",
    encoding="utf-8",
)
emit(run_dir, "job_completed")
write_receipt(
    run_dir,
    {
        "status": "completed",
        "model_id": model,
        "usd": 0.04,
        "tokens_in": 200,
        "tokens_out": 40,
        "workers_ran": 1,
    },
)
