"""Resolve reason-slice package surfaces without leaked class names.

Hidden tests still check the construct (traces over lying README, sealed
reports over majority, repair the real fault). They do not require the
scripted-pass class names Pair / Clinic / Board.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, Callable


def load_pair(module_name: str) -> type:
    module = importlib.import_module(module_name)
    existing = getattr(module, "Pair", None)
    if isinstance(existing, type):
        return existing
    apply = _binary_apply(module)
    if apply is None:
        raise ImportError(f"{module_name} has no Pair and no binary apply")

    class AdaptivePair:
        def apply(self, a: Any, b: Any) -> Any:
            return apply(a, b)

    return AdaptivePair


def load_clinic(module_name: str = "hearth") -> type:
    module = importlib.import_module(module_name)
    existing = getattr(module, "Clinic", None)
    if isinstance(existing, type):
        return existing
    for name in dir(module):
        obj = getattr(module, name)
        if isinstance(obj, type) and callable(getattr(obj, "repair", None)):
            return obj
    repair = getattr(module, "repair", None)
    if not callable(repair):
        raise ImportError(f"{module_name} has no Clinic and no repair(root)")

    class AdaptiveClinic:
        def __init__(self, root: str | Path) -> None:
            self.root = root

        def repair(self) -> Any:
            return repair(self.root)

    return AdaptiveClinic


def load_board(module_name: str = "ledger") -> type:
    module = importlib.import_module(module_name)
    existing = getattr(module, "Board", None)
    if isinstance(existing, type):
        return existing
    for name in dir(module):
        obj = getattr(module, name)
        if isinstance(obj, type) and callable(getattr(obj, "resolve", None)):
            return obj
    resolve = getattr(module, "resolve", None)
    if not callable(resolve):
        raise ImportError(f"{module_name} has no Board and no resolve(root)")

    class AdaptiveBoard:
        def __init__(self, root: str | Path) -> None:
            self.root = root

        def resolve(self) -> Any:
            return resolve(self.root)

    return AdaptiveBoard


def _binary_apply(module: Any) -> Callable[..., Any] | None:
    for name in ("apply", "combine", "run", "op", "evaluate"):
        candidate = getattr(module, name, None)
        if callable(candidate):
            return candidate
    return None
