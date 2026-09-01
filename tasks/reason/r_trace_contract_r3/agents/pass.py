import json
import time
from pathlib import Path

from strongorc.agentlib import finish, write_checkpoint
from strongorc.env import getenv
from strongorc.protocol import emit

run_dir = Path(RUN_DIR)
model = MODEL
pkg = 'flint'
interrupt = True
ignore_rule = False


def _trace_pairs():
    traces = json.loads((run_dir / "state" / "traces.json").read_text(encoding="utf-8"))
    return list(traces.get("pairs") or [])


def _pairs():
    pairs = _trace_pairs()
    reply = run_dir / "state" / "lab_reply.json"
    if reply.is_file():
        data = json.loads(reply.read_text(encoding="utf-8"))
        for cell in data.get("cells") or []:
            pairs.append({"a": cell[0], "b": cell[1], "out": cell[2]})
    return pairs


def _maybe_probe():
    fit = _candidates(_trace_pairs())
    if len(fit) == 1:
        return
    (run_dir / "state").mkdir(parents=True, exist_ok=True)
    (run_dir / "state" / "probe.json").write_text(
        json.dumps(_probe(fit), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _candidates(pairs):
    ops = {
        "add": lambda a, b: a + b,
        "mul": lambda a, b: a * b,
        "max": lambda a, b: a if a >= b else b,
        "min": lambda a, b: a if a <= b else b,
    }
    fit = []
    for name, fn in ops.items():
        if all(fn(item["a"], item["b"]) == item["out"] for item in pairs):
            fit.append(name)
    return fit


def _probe(fit):
    ops = {
        "add": lambda a, b: a + b,
        "mul": lambda a, b: a * b,
        "max": lambda a, b: a if a >= b else b,
        "min": lambda a, b: a if a <= b else b,
    }
    for a in range(0, 6):
        for b in range(0, 6):
            outs = {name: ops[name](a, b) for name in fit}
            if len(set(outs.values())) > 1:
                return {"a": a, "b": b}
    return {"a": 3, "b": 1}


def _write(name):
    expr = {
        "add": "a + b",
        "mul": "a * b",
        "max": "a if a >= b else b",
        "min": "a if a <= b else b",
    }[name]
    dest = run_dir / pkg
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "__init__.py").write_text(
        "class Pair:\n    def apply(self, a, b):\n        return " + expr + "\n",
        encoding="utf-8",
    )


if interrupt and getenv("RESUME") != "1":
    emit(run_dir, "artifact_consumed", path="state/traces.json")
    emit(run_dir, "worker_started", worker="alpha")
    _maybe_probe()
    write_checkpoint(run_dir, "checkpoint.json", {"phase": 1})
    time.sleep(3600)
else:
    if interrupt:
        emit(run_dir, "resumed_from_checkpoint")
    emit(run_dir, "artifact_consumed", path="state/traces.json")
    emit(run_dir, "worker_started", worker="alpha")
    if ignore_rule:
        rule = run_dir / "state" / "rule.json"
        if rule.is_file():
            emit(run_dir, "artifact_consumed", path="state/rule.json")
    _maybe_probe()
    fit = _candidates(_pairs())
    if len(fit) != 1:
        raise SystemExit("underdetermined after evidence")
    _write(fit[0])
    emit(run_dir, "worker_finished", worker="alpha")
    finish(run_dir, model, workers_ran=1, usd=0.31)
