import sys
from pathlib import Path

from durable_orch_bench.catalog import get_task
from durable_orch_bench.harness import run_task

DRIVER = """
import os
import runpy
from pathlib import Path

runpy.run_path(
    os.environ["DURABLE_ORCH_AGENT"],
    init_globals={
        "RUN_DIR": Path(os.environ["DURABLE_ORCH_RUN_DIR"]),
        "MODEL": os.environ["DURABLE_ORCH_MODEL"],
        "TASK_ID": os.environ["DURABLE_ORCH_TASK_ID"],
    },
)
"""


def test_command_adapter_can_drive_a_core_task(tmp_path: Path, monkeypatch) -> None:
    task = get_task("o_dead_swarm")
    driver = tmp_path / "driver.py"
    driver.write_text(DRIVER, encoding="utf-8")
    monkeypatch.setenv("DURABLE_ORCH_AGENT", str(task.agent_path("pass")))
    trial, grade = run_task(
        task,
        adapter_name="command",
        model="scripted-pass",
        runs_root=tmp_path / "runs",
        adapter_kwargs={"cmd": f"{sys.executable} {driver}"},
    )
    assert grade.passed, [check for check in grade.checks if not check.passed]
    assert trial.adapter == "command"
