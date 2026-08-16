from __future__ import annotations

import pytest

from jobnet import Runner


def test_diamond_waves() -> None:
    sched = Runner()
    sched.add("a", [], lambda: None)
    sched.add("b", ["a"], lambda: None)
    sched.add("c", ["a"], lambda: None)
    sched.add("d", ["b", "c"], lambda: None)
    assert sched.waves() == [["a"], ["b", "c"], ["d"]]
    assert sched.run() == {"a": "ok", "b": "ok", "c": "ok", "d": "ok"}


def test_fail_closed_does_not_run_descendants() -> None:
    ran: list[str] = []

    def boom() -> None:
        ran.append("root")
        raise RuntimeError("boom")

    sched = Runner()
    sched.add("root", [], boom)
    sched.add("mid", ["root"], lambda: ran.append("mid"))
    sched.add("leaf", ["mid"], lambda: ran.append("leaf"))
    sched.add("ok", [], lambda: ran.append("ok"))
    result = sched.run()
    assert result["root"] == "failed"
    assert result["mid"] == "skipped"
    assert result["leaf"] == "skipped"
    assert result["ok"] == "ok"
    assert ran == ["root", "ok"] or ran == ["ok", "root"]


def test_cycle_raises() -> None:
    sched = Runner()
    sched.add("a", ["b"], lambda: None)
    sched.add("b", ["a"], lambda: None)
    with pytest.raises(ValueError):
        sched.waves()
    with pytest.raises(ValueError):
        sched.run()


def test_empty_run() -> None:
    assert Runner().run() == {}
    assert Runner().waves() == []


def test_self_cycle() -> None:
    sched = Runner()
    sched.add("loop", ["loop"], lambda: None)
    with pytest.raises(ValueError):
        sched.run()


def test_unknown_dependency_raises() -> None:
    sched = Runner()
    sched.add("leaf", ["missing"], lambda: None)
    with pytest.raises(ValueError):
        sched.run()


def test_insertion_order_is_wrong() -> None:
    order: list[str] = []
    sched = Runner()
    sched.add("late", ["early"], lambda: order.append("late"))
    sched.add("early", [], lambda: order.append("early"))
    sched.run()
    assert order == ["early", "late"]
