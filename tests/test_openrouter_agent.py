import importlib.util
from pathlib import Path

import pytest

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "openrouter_agent.py"


def _load():
    spec = importlib.util.spec_from_file_location("openrouter_agent", EXAMPLE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_confined_rejects_parent_escape(tmp_path: Path) -> None:
    module = _load()
    with pytest.raises(ValueError, match="escapes"):
        module.confined(tmp_path, "../secret")
    inside = module.confined(tmp_path, "pkg/mod.py")
    assert inside == (tmp_path / "pkg" / "mod.py").resolve()
