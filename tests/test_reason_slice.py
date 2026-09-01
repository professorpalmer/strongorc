import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from strongorc.cards import build_card
from strongorc.catalog import get_task, list_tasks
from strongorc.harness import _adapter_env, run_slice, run_task, seed_run
from strongorc.oracle_lib import discover_hidden_test_names, hidden_pytest_cases

REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / "tasks" / "reason"
MANIFEST = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
REASON_IDS = [item["id"] for item in MANIFEST["tasks"]]
EXPECTED_FAIL_CHECK = {item["id"]: item["fail_check"] for item in MANIFEST["tasks"]}
FAMILIES = ("diagnose_kill", "split_reports", "trace_contract", "retract_rule")
RUNGS = ("r1", "r2", "r3")
EXPECTED_IDS = [
    "r_diagnose_kill_r1",
    "r_diagnose_kill_r2",
    "r_diagnose_kill_r3",
    "r_retract_rule_r1",
    "r_retract_rule_r2",
    "r_retract_rule_r3",
    "r_split_reports_r1",
    "r_split_reports_r2",
    "r_split_reports_r3",
    "r_trace_contract_r1",
    "r_trace_contract_r2",
    "r_trace_contract_r3",
]
OPAQUE = re.compile(r"^test_case_\d{3}$")


def test_reason_r1_does_not_expect_interrupt() -> None:
    for family in FAMILIES:
        r1 = get_task(f"r_{family}_r1")
        r2 = get_task(f"r_{family}_r2")
        assert r1.interrupt_steps() == []
        assert r2.interrupt_steps()
        env1 = _adapter_env(r1, Path("/tmp"), "m")
        env2 = _adapter_env(r2, Path("/tmp"), "m")
        assert env1["STRONGORC_EXPECT_INTERRUPT"] == "0"
        assert env2["STRONGORC_EXPECT_INTERRUPT"] == "1"


def test_reason_slice_census() -> None:
    tasks = list_tasks("reason")
    ids = [task.id for task in tasks]
    assert ids == sorted(REASON_IDS)
    assert ids == EXPECTED_IDS
    assert len(ids) == 12
    orch = [task for task in tasks if task.track == "orchestrator"]
    leaf = [task for task in tasks if task.track == "worker"]
    assert len(orch) == 6
    assert len(leaf) == 6
    assert {task.family for task in tasks} == set(FAMILIES)
    assert Counter(task.family for task in tasks) == {name: 3 for name in FAMILIES}
    assert Counter(task.rung for task in tasks) == {rung: 4 for rung in RUNGS}
    assert get_task("r_diagnose_kill_r1").track == "orchestrator"
    assert get_task("r_split_reports_r2").track == "orchestrator"
    assert get_task("r_trace_contract_r1").track == "worker"
    assert get_task("r_retract_rule_r3").track == "worker"
    for task in tasks:
        assert task.slice == "reason"
        assert task.family in FAMILIES
        assert task.rung in RUNGS
        assert task.timeout_seconds >= 1800
        meta = json.loads((task.root / "task.json").read_text(encoding="utf-8"))
        assert meta["family"] == task.family
        assert meta["rung"] == task.rung


def test_scripted_pass_clears_reason(tmp_path: Path) -> None:
    results = run_slice(
        "reason",
        adapter_name="scripted",
        model="scripted-pass",
        runs_root=tmp_path / "pass",
        adapter_kwargs={"persona": "pass"},
    )
    failed = [
        (grade.task_id, [check.name for check in grade.checks if not check.passed])
        for _, grade in results
        if not grade.passed
    ]
    assert failed == []
    assert len(results) == 12
    card = build_card(
        [trial for trial, _ in results],
        [grade for _, grade in results],
        model="scripted-pass",
        slice_name="reason",
        card_date="2026-08-20",
    )
    assert card.hidden_rate == 1.0
    assert card.interrupt_rate == 1.0
    assert card.hard_rate == 1.0
    assert card.n_hidden == 96
    assert card.family_scores == {name: 1.0 for name in FAMILIES}
    assert card.rung_scores == {rung: 1.0 for rung in RUNGS}


def test_scripted_fail_misses_hidden_pytest(tmp_path: Path) -> None:
    results = run_slice(
        "reason",
        adapter_name="scripted",
        model="scripted-fail",
        runs_root=tmp_path / "fail",
        adapter_kwargs={"persona": "fail"},
    )
    assert len(results) == 12
    for trial, grade in results:
        assert grade.passed is False, trial.task_id
        names = {check.name for check in grade.checks if not check.passed}
        expected = EXPECTED_FAIL_CHECK[trial.task_id]
        hit = any(name == expected or name.startswith(expected + ":") for name in names)
        assert hit, f"{trial.task_id} failed {sorted(names)}, expected {expected}"


def test_hidden_denominator_is_stable() -> None:
    names: list[str] = []
    for task_id in REASON_IDS:
        found = discover_hidden_test_names(ROOT / task_id / "hidden")
        assert len(found) == 8, task_id
        names.extend(found)
        for name in found:
            assert OPAQUE.fullmatch(name), name
            assert not any(family in name for family in FAMILIES)
            assert not any(rung in name for rung in RUNGS)
    assert len(names) == 96


def test_no_hidden_reference_packages() -> None:
    for task_id in REASON_IDS:
        task_dir = ROOT / task_id
        assert not (task_dir / "hidden" / "reference").exists()
        assert not (task_dir / "reference").exists()
        assert "copy_reference" not in (task_dir / "agents" / "pass.py").read_text(encoding="utf-8")


def test_r2_r3_use_interrupt_and_sealed_checks() -> None:
    for task in list_tasks("reason"):
        if task.rung == "r1":
            assert task.interrupt_steps() == []
        else:
            assert len(task.interrupt_steps()) == 1
            assert task.interrupt_steps()[0]["resume"] is True


def test_r2_pass_receives_sealed_kill(tmp_path: Path) -> None:
    trial, grade = run_task(
        get_task("r_trace_contract_r2"),
        adapter_name="scripted",
        model="scripted-pass",
        runs_root=tmp_path / "sealed",
        adapter_kwargs={"persona": "pass"},
    )
    assert grade.passed, [check for check in grade.checks if not check.passed]
    names = {check.name: check.passed for check in grade.checks}
    assert names["sealed:harness_killed"] is True
    assert names["sealed:pre_kill_1"] is True
    assert names["sealed:kill_count"] is True


def test_worker_oracles_omit_kill_events() -> None:
    for task in list_tasks("reason"):
        if task.track != "worker":
            continue
        text = (task.root / "oracle.py").read_text(encoding="utf-8")
        assert "harness_killed" not in text
        assert "resumed_from_checkpoint" not in text


def _plant_r3_reply(family: str, run_dir: Path) -> None:
    dest = run_dir / "state" / "lab_reply.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if family == "diagnose_kill":
        dest.write_text(json.dumps({"causal": "hash_drift"}, indent=2) + "\n", encoding="utf-8")
        return
    if family == "split_reports":
        alpha = run_dir / "state" / "reports" / "alpha.json"
        digest = hashlib.sha256(alpha.read_bytes()).hexdigest()
        dest.write_text(
            json.dumps({"cells": [{"eligible": True, "sha256": digest}]}, indent=2) + "\n",
            encoding="utf-8",
        )
        return
    dest.write_text(json.dumps({"cells": [[1, 2, 3]]}, indent=2) + "\n", encoding="utf-8")


def _wrong_r3_probe(family: str, run_dir: Path) -> None:
    dest = run_dir / "state" / "probe.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if family == "diagnose_kill":
        dest.write_text(json.dumps({"inspect": "dead_child"}, indent=2) + "\n", encoding="utf-8")
        return
    if family == "split_reports":
        dest.write_text(
            json.dumps({"worker": "gamma", "sha256": "ffff"}, indent=2) + "\n",
            encoding="utf-8",
        )
        return
    dest.write_text(json.dumps({"a": 0, "b": 0}, indent=2) + "\n", encoding="utf-8")


def test_r3_hidden_requires_probe_even_if_both_hypotheses_work(tmp_path: Path) -> None:
    for task in list_tasks("reason"):
        if task.rung != "r3":
            continue
        run_dir = tmp_path / task.id
        seed_run(task, run_dir)
        _write_both_hypotheses(task.family, run_dir)
        assert not (run_dir / "state" / "probe.json").exists()
        cases = hidden_pytest_cases(run_dir, task.root / "hidden")
        failed = [check.name for check in cases if not check.passed]
        assert any(name.endswith("test_case_001") for name in failed), (task.id, failed)


def test_r3_wrong_probe_fails_against_planted_reply(tmp_path: Path) -> None:
    for task in list_tasks("reason"):
        if task.rung != "r3":
            continue
        run_dir = tmp_path / f"{task.id}_wrong"
        seed_run(task, run_dir)
        _write_both_hypotheses(task.family, run_dir)
        _plant_r3_reply(task.family, run_dir)
        _wrong_r3_probe(task.family, run_dir)
        cases = hidden_pytest_cases(run_dir, task.root / "hidden")
        failed = [check.name for check in cases if not check.passed]
        assert any(name.endswith("test_case_001") for name in failed), (task.id, failed)


def test_no_mechanical_rung_axis() -> None:
    for family in FAMILIES:
        trees = []
        widths = []
        for rung in RUNGS:
            seed = ROOT / f"r_{family}_{rung}" / "seed"
            rels = tuple(
                sorted(path.relative_to(seed).as_posix() for path in seed.rglob("*") if path.is_file())
            )
            trees.append(rels)
            traces = seed / "state" / "traces.json"
            reports = seed / "state" / "reports"
            children = seed / "state" / "children"
            if traces.is_file():
                widths.append(len(json.loads(traces.read_text(encoding="utf-8"))["pairs"]))
            if reports.is_dir():
                widths.append(len(list(reports.glob("*.json"))))
            if children.is_dir():
                widths.append(len(list(children.glob("*.json"))))
        assert trees[0] == trees[1] == trees[2], family
        assert len(set(widths)) == 1, (family, widths)


def _write_both_hypotheses(family: str, run_dir: Path) -> None:
    if family in {"trace_contract", "retract_rule"}:
        name = "flint" if family == "trace_contract" else "quill"
        dest = run_dir / name
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "__init__.py").write_text(
            "class Pair:\n"
            "    def apply(self, a, b):\n"
            "        added = a + b\n"
            "        biggest = a if a >= b else b\n"
            "        return added if a == 0 or b == 0 else added\n",
            encoding="utf-8",
        )
        return
    if family == "diagnose_kill":
        dest = run_dir / "hearth"
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "__init__.py").write_text(
            "from pathlib import Path\n"
            "import hashlib, json\n"
            "class Clinic:\n"
            "    def __init__(self, root):\n"
            "        self.root = Path(root)\n"
            "    def repair(self):\n"
            "        leaf = self.root / 'state' / 'children' / 'leaf.json'\n"
            "        if leaf.is_file():\n"
            "            leaf.write_text(json.dumps({'status': 'ok'}, indent=2) + '\\n')\n"
            "        payload = self.root / 'state' / 'payload.json'\n"
            "        digest = self.root / 'state' / 'digest.json'\n"
            "        if payload.is_file() and digest.is_file():\n"
            "            digest.write_text(json.dumps({'sha256': hashlib.sha256(payload.read_bytes()).hexdigest()}, indent=2) + '\\n')\n"
            "        leases = self.root / 'job' / 'leases.json'\n"
            "        if leases.is_file():\n"
            "            data = json.loads(leases.read_text())\n"
            "            data['fence'] = 'live-alpha'\n"
            "            leases.write_text(json.dumps(data, indent=2) + '\\n')\n",
            encoding="utf-8",
        )
        return
    dest = run_dir / "ledger"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "__init__.py").write_text(
        "from pathlib import Path\n"
        "import json\n"
        "from collections import Counter\n"
        "class Board:\n"
        "    def __init__(self, root):\n"
        "        self.root = Path(root)\n"
        "    def resolve(self):\n"
        "        values = []\n"
        "        folder = self.root / 'state' / 'reports'\n"
        "        for path in sorted(folder.glob('*.json')):\n"
        "            values.append(json.loads(path.read_text())['value'])\n"
        "        seals = json.loads((self.root / 'job' / 'seals.json').read_text())\n"
        "        if seals.get('eligible'):\n"
        "            name = seals['eligible'][0]\n"
        "            return json.loads((folder / f'{name}.json').read_text())['value']\n"
        "        return Counter(values).most_common(1)[0][0]\n",
        encoding="utf-8",
    )
