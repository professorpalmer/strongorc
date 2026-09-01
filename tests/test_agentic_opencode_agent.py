from __future__ import annotations

import importlib.util
from pathlib import Path

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "agentic_opencode_agent.py"


def _load():
    spec = importlib.util.spec_from_file_location("agentic_opencode_agent", EXAMPLE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pin_is_opencode_go_without_auto_route(tmp_path: Path) -> None:
    module = _load()
    argv = module.build_agentic_argv(
        puppetmaster="puppetmaster",
        run_dir=tmp_path,
        state_dir=tmp_path / ".pm-state",
        provider="opencode-go",
        go_model="ox-alpha-free",
        prompt="do the task",
        max_turns=64,
        timeout_seconds=2400,
        task_id="r_trace_contract_r1",
    )
    assert argv[argv.index("agentic") + 1] == "do the task"
    assert argv[argv.index("--provider") + 1] == "opencode-go"
    assert argv[argv.index("--model") + 1] == "ox-alpha-free"
    assert "--auto-route" not in argv
    assert "--disable-codegraph" in argv
    assert "--disable-memory" in argv
    assert "--allow-dirty" in argv
    assert argv[argv.index("--state-dir") + 1] == str(tmp_path / ".pm-state")
    assert argv[argv.index("--cwd") + 1] == str(tmp_path)


def test_state_dir_is_outside_the_run_cwd(tmp_path: Path) -> None:
    module = _load()
    run_dir = tmp_path / "r_trace_contract_r1"
    run_dir.mkdir()
    assert module.isolate_state_dir(run_dir) == tmp_path / "r_trace_contract_r1.pm-state"


def test_bare_go_model_strips_prefixes() -> None:
    module = _load()
    assert module.bare_go_model("opencode-go/minimax-m2.5") == "minimax-m2.5"
    assert module.bare_go_model("agentic/ox-alpha-free") == "ox-alpha-free"
    assert module.bare_go_model("ox-alpha-free") == "ox-alpha-free"
