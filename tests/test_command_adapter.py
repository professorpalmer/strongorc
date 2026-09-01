import sys
from pathlib import Path

from strongorc.catalog import get_task
from strongorc.harness import checkout_root, isolated_runs_root, run_task

DRIVER = """
import os
import runpy
from pathlib import Path

runpy.run_path(
    os.environ["STRONGORC_AGENT"],
    init_globals={
        "RUN_DIR": Path(os.environ["STRONGORC_RUN_DIR"]),
        "MODEL": os.environ["STRONGORC_MODEL"],
        "TASK_ID": os.environ["STRONGORC_TASK_ID"],
    },
)
"""


def test_command_adapter_can_drive_a_core_task(tmp_path: Path, monkeypatch) -> None:
    task = get_task("o_dead_swarm")
    driver = tmp_path / "driver.py"
    driver.write_text(DRIVER, encoding="utf-8")
    monkeypatch.setenv("STRONGORC_AGENT", str(task.agent_path("pass")))
    trial, grade = run_task(
        task,
        adapter_name="command",
        model="scripted-pass",
        runs_root=tmp_path / "runs",
        adapter_kwargs={"cmd": f"{sys.executable} {driver}"},
    )
    assert grade.passed, [check for check in grade.checks if not check.passed]
    assert trial.adapter == "command"


def test_command_runs_inside_checkout_are_relocated(tmp_path: Path) -> None:
    inside = checkout_root() / "runs" / "live-test"
    jail = isolated_runs_root(inside, "command")
    assert checkout_root() not in jail.parents
    assert jail != inside.resolve()
    outside = (tmp_path / "runs").resolve()
    assert isolated_runs_root(outside, "command") == outside
    assert isolated_runs_root(inside, "scripted") == inside.resolve()


def test_command_adapter_passes_explicit_environment(tmp_path: Path) -> None:
    task = get_task("o_dead_swarm")
    driver = tmp_path / "write_budget.py"
    driver.write_text(
        "import os\n"
        "from pathlib import Path\n"
        "Path(os.environ['STRONGORC_RUN_DIR'], 'budget.txt').write_text("
        "os.environ['STRONGORC_MAX_USD'], encoding='utf-8')\n",
        encoding="utf-8",
    )
    trial, _ = run_task(
        task,
        adapter_name="command",
        model="budget-probe",
        runs_root=tmp_path / "runs",
        adapter_kwargs={
            "cmd": f"{sys.executable} {driver}",
            "extra_env": {"STRONGORC_MAX_USD": "0.75"},
        },
    )
    assert trial.files["budget.txt"] == "0.75"


def test_command_adapter_never_exposes_private_overlay_environment(
    tmp_path: Path, monkeypatch
) -> None:
    task = get_task("o_dead_swarm")
    driver = tmp_path / "inspect_overlay_env.py"
    driver.write_text(
        "import os\n"
        "from pathlib import Path\n"
        "Path(os.environ['STRONGORC_RUN_DIR'], 'overlay-visible.txt').write_text("
        "str('STRONGORC_HOLDOUT' in os.environ), encoding='utf-8')\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("STRONGORC_HOLDOUT", str(tmp_path / "private-overlay"))
    trial, _ = run_task(
        task,
        adapter_name="command",
        model="environment-probe",
        runs_root=tmp_path / "runs",
        adapter_kwargs={"cmd": f"{sys.executable} {driver}"},
    )
    assert trial.files["overlay-visible.txt"] == "False"
