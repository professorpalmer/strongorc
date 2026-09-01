from __future__ import annotations

import types
from pathlib import Path


def load_source_module(path: Path, module_name: str) -> types.ModuleType:
    """Load trusted harness code without writing bytecode into its bank."""
    source_path = Path(path)
    module = types.ModuleType(module_name)
    module.__file__ = str(source_path)
    source = source_path.read_text(encoding="utf-8")
    exec(compile(source, str(source_path), "exec"), module.__dict__)
    return module
