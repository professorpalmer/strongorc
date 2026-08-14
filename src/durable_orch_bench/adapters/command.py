from __future__ import annotations

import os
import subprocess
from pathlib import Path

from durable_orch_bench.catalog import TaskSpec
from durable_orch_bench.adapters.base import Adapter
from durable_orch_bench.protocol import emit, receipt_path, write_receipt


class CommandAdapter(Adapter):
    name = "command"

    def __init__(self, cmd: str | None = None) -> None:
        self.cmd = cmd

    def run(self, task: TaskSpec, run_dir: Path, model: str) -> None:
        if not self.cmd:
            raise ValueError("command adapter requires --cmd")
        env = os.environ.copy()
        env["DURABLE_ORCH_RUN_DIR"] = str(run_dir)
        env["DURABLE_ORCH_TASK_ID"] = task.id
        env["DURABLE_ORCH_TRACK"] = task.track
        env["DURABLE_ORCH_MODEL"] = model
        env["DURABLE_ORCH_PROMPT"] = str(run_dir / "PROMPT.md")
        (run_dir / "PROMPT.md").write_text(task.prompt(), encoding="utf-8")
        try:
            completed = subprocess.run(
                self.cmd,
                shell=True,
                cwd=run_dir,
                env=env,
                check=False,
                timeout=task.timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            _record_adapter_failure(run_dir, model, "timeout")
            return
        if completed.returncode != 0:
            _record_adapter_failure(run_dir, model, f"exit {completed.returncode}")


def _record_adapter_failure(run_dir: Path, model: str, reason: str) -> None:
    emit(run_dir, "job_failed", reason=reason)
    if receipt_path(run_dir).is_file():
        return
    write_receipt(
        run_dir,
        {
            "status": "failed",
            "model_id": model,
            "usd": 0.0,
            "tokens_in": 0,
            "tokens_out": 0,
            "workers_ran": 0,
        },
    )
