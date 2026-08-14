from durable_orch_bench.adapters.base import Adapter
from durable_orch_bench.adapters.command import CommandAdapter
from durable_orch_bench.adapters.scripted import ScriptedAdapter

ADAPTERS = {
    "scripted": ScriptedAdapter,
    "command": CommandAdapter,
}


def get_adapter(name: str, **kwargs) -> Adapter:
    try:
        cls = ADAPTERS[name]
    except KeyError as exc:
        known = ", ".join(sorted(ADAPTERS))
        raise KeyError(f"unknown adapter {name!r}; known: {known}") from exc
    return cls(**kwargs)
