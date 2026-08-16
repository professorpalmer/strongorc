from __future__ import annotations

from collections import defaultdict, deque
from typing import Callable


class Runner:
    def __init__(self) -> None:
        self._deps: dict[str, set[str]] = {}
        self._fns: dict[str, Callable[[], None]] = {}

    def add(self, job_id: str, deps: list[str], fn: Callable[[], None]) -> None:
        self._deps[job_id] = set(deps)
        self._fns[job_id] = fn

    def waves(self) -> list[list[str]]:
        remaining = {job: set(deps) for job, deps in self._deps.items()}
        layers: list[list[str]] = []
        while remaining:
            ready = sorted(job for job, deps in remaining.items() if not deps)
            if not ready:
                raise ValueError("cycle")
            layers.append(ready)
            ready_set = set(ready)
            remaining = {
                job: deps - ready_set
                for job, deps in remaining.items()
                if job not in ready_set
            }
        return layers

    def run(self) -> dict[str, str]:
        children: dict[str, list[str]] = defaultdict(list)
        for job, deps in self._deps.items():
            for dep in deps:
                children[dep].append(job)
        status: dict[str, str] = {}
        blocked: set[str] = set()
        for wave in self.waves():
            for job in wave:
                if job in blocked:
                    status[job] = "skipped"
                    continue
                try:
                    self._fns[job]()
                except Exception:
                    status[job] = "failed"
                    stack = deque(children[job])
                    while stack:
                        node = stack.popleft()
                        if node in blocked:
                            continue
                        blocked.add(node)
                        stack.extend(children[node])
                    continue
                status[job] = "ok"
        for job in blocked:
            status.setdefault(job, "skipped")
        return status
