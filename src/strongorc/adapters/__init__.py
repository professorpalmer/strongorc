from strongorc.adapters.base import Adapter
from strongorc.adapters.command import CommandAdapter
from strongorc.adapters.scripted import ScriptedAdapter

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
