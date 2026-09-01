from __future__ import annotations

import re
import runpy
from pathlib import Path

from strongorc.catalog import TaskSpec
from strongorc.adapters.base import Adapter

_PERSONA = re.compile(r"^(?:pass|fail(?:_[a-z0-9_]+)?)$")


class ScriptedAdapter(Adapter):
    name = "scripted"

    def __init__(self, persona: str = "pass") -> None:
        if not _PERSONA.fullmatch(persona):
            raise ValueError("invalid scripted persona")
        self.persona = persona

    def run(self, task: TaskSpec, run_dir: Path, model: str) -> None:
        agent = task.agent_path(self.persona)
        if not agent.is_file():
            raise FileNotFoundError(f"missing scripted agent: {agent}")
        runpy.run_path(
            str(agent),
            init_globals={"RUN_DIR": run_dir, "MODEL": model, "TASK_ID": task.id},
        )
