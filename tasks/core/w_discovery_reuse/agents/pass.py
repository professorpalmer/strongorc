import json
from pathlib import Path

from durable_orch_bench.protocol import emit, write_receipt

run_dir = Path(RUN_DIR)
model = MODEL
out = run_dir / "output"
out.mkdir(parents=True, exist_ok=True)

discovery = json.loads((run_dir / "state" / "discoveries" / "name.json").read_text(encoding="utf-8"))
emit(run_dir, "llm_call", purpose="locate-discovery")
emit(run_dir, "artifact_consumed", path="state/discoveries/name.json")
(out / "first.txt").write_text(f"{discovery['name']}\n{discovery['nonce']}\n", encoding="utf-8")
emit(run_dir, "discovery_reused", path="state/discoveries/name.json")
(out / "second.txt").write_text(f"{discovery['name']}\n{discovery['nonce']}\n", encoding="utf-8")
emit(run_dir, "job_completed")
write_receipt(
    run_dir,
    {
        "status": "completed",
        "model_id": model,
        "usd": 0.01,
        "tokens_in": 80,
        "tokens_out": 10,
        "workers_ran": 1,
    },
)
