from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from strongorc.env import getenv

Track = Literal["orchestrator", "worker"]


def tasks_root() -> Path:
    env = getenv("TASKS")
    if env:
        return Path(env)
    here = Path(__file__).resolve()
    for candidate in (here.parents[2] / "tasks", here.parents[1] / "tasks"):
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError("tasks/ not found; set STRONGORC_TASKS")


TASKS_ROOT = tasks_root()


@dataclass(frozen=True)
class TaskSpec:
    id: str
    track: Track
    slice: str
    title: str
    timeout_seconds: int
    root: Path
    bind: dict | None = None
    interrupt: dict | list | None = None

    def interrupt_steps(self) -> list[dict]:
        raw = self.interrupt
        if raw is None:
            return []
        if isinstance(raw, list):
            return [dict(item) for item in raw]
        return [dict(raw)]

    @property
    def prompt_path(self) -> Path:
        return self.root / "prompt.md"

    @property
    def seed_dir(self) -> Path:
        return self.root / "seed"

    @property
    def oracle_path(self) -> Path:
        return self.root / "oracle.py"

    def agent_path(self, persona: str) -> Path:
        return self.root / "agents" / f"{persona}.py"

    def prompt(self) -> str:
        return self.prompt_path.read_text(encoding="utf-8")


def _load_task(task_dir: Path) -> TaskSpec:
    meta = json.loads((task_dir / "task.json").read_text(encoding="utf-8"))
    return TaskSpec(
        id=meta["id"],
        track=meta["track"],
        slice=meta["slice"],
        title=meta["title"],
        timeout_seconds=int(meta.get("timeout_seconds", 30)),
        root=task_dir,
        bind=meta.get("bind"),
        interrupt=meta.get("interrupt"),
    )


def list_tasks(slice_name: str = "core") -> list[TaskSpec]:
    slice_dir = TASKS_ROOT / slice_name
    if not slice_dir.is_dir():
        return []
    tasks = [
        _load_task(path)
        for path in sorted(slice_dir.iterdir())
        if path.is_dir() and (path / "task.json").is_file()
    ]
    return tasks


def get_task(task_id: str, slice_name: str | None = None) -> TaskSpec:
    slices = [slice_name] if slice_name else ["core", "hard", "holdout"]
    for name in slices:
        for task in list_tasks(name):
            if task.id == task_id:
                return task
    raise KeyError(f"unknown task: {task_id}")
