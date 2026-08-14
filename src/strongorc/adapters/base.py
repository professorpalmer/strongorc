from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from strongorc.catalog import TaskSpec


class Adapter(ABC):
    name: str

    @abstractmethod
    def run(self, task: TaskSpec, run_dir: Path, model: str) -> None:
        """Execute the agent against an already-seeded run directory."""
