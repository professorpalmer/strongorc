from __future__ import annotations

import os
import subprocess
from pathlib import Path

from strongorc.adapters.base import Adapter
from strongorc.catalog import TaskSpec
from strongorc.env import bind_run
from strongorc.protocol import emit, receipt_path, write_receipt


class CommandAdapter(Adapter):
    name = "command"

    def __init__(self, cmd: str | None = None) -> None:
        self.cmd = cmd

    def run(self, task: TaskSpec, run_dir: Path, model: str) -> None:
        if not self.cmd:
            raise ValueError("command adapter requires --cmd")
        env = os.environ.copy()
        prompt = run_dir / "PROMPT.md"
        prompt.write_text(task.prompt(), encoding="utf-8")
        bind_run(
            env,
            run_dir=str(run_dir),
            task_id=task.id,
            track=task.track,
            model=model,
            prompt=str(prompt),
        )
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
