from __future__ import annotations

from pathlib import Path

from wicket import Latch


def test_wicket_r4_trips_on_two_consecutive(tmp_path: Path) -> None:
    latch = Latch(tmp_path)
    assert latch.observe(False, now=1) == "closed"
    assert latch.observe(False, now=2) == "open"


def test_wicket_r4_twenty_successes_stay_closed(tmp_path: Path) -> None:
    latch = Latch(tmp_path)
    for index in range(20):
        latch.observe(True, now=float(index))
    assert latch.state(20) == "closed"


def test_wicket_r4_half_open_immediately(tmp_path: Path) -> None:
    latch = Latch(tmp_path)
    latch.observe(False, now=1)
    latch.observe(False, now=2)
    assert latch.state(3) == "half_open"


def test_wicket_r4_probe_budget_is_one(tmp_path: Path) -> None:
    latch = Latch(tmp_path)
    latch.observe(False, now=1)
    latch.observe(False, now=2)
    assert latch.allow(2) is False
    assert latch.observe(False, now=2) == "open"
    assert latch.state(2) == "open"


def test_wicket_r4_two_successes_close(tmp_path: Path) -> None:
    latch = Latch(tmp_path)
    latch.observe(False, now=1)
    latch.observe(False, now=2)
    latch.observe(True, now=3)
    latch.observe(True, now=4)
    assert latch.state(4) == "closed"


def test_wicket_r4_slow_call_is_success(tmp_path: Path) -> None:
    latch = Latch(tmp_path)
    assert latch.observe(True, duration_ms=400, now=1) == "closed"


def test_wicket_r4_success_in_open_is_ignored(tmp_path: Path) -> None:
    latch = Latch(tmp_path)
    latch.observe(False, now=1)
    latch.observe(False, now=2)
    assert latch.observe(True, now=2) == "open"
    assert latch.state(2) == "open"


def test_wicket_r4_isolated_errors_do_not_trip(tmp_path: Path) -> None:
    latch = Latch(tmp_path)
    latch.observe(False, now=1)
    latch.observe(True, now=2)
    latch.observe(False, now=3)
    assert latch.state(3) == "closed"
