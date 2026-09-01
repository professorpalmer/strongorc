from __future__ import annotations

from pathlib import Path

from wicket import Latch


def _trip(latch: Latch, start: float = 0.0) -> None:
    latch.observe(False, now=start)
    latch.observe(False, now=start)
    latch.observe(False, now=start)


def test_trips_on_three_consecutive(tmp_path: Path) -> None:
    latch = Latch(tmp_path)
    latch.observe(False, now=0)
    latch.observe(False, now=1)
    assert latch.state(1) == "closed"
    latch.observe(False, now=2)
    assert latch.state(2) == "open"


def test_twenty_per_two_minutes_is_wrong(tmp_path: Path) -> None:
    latch = Latch(tmp_path)
    for index in range(19):
        latch.observe(False, now=float(index))
        latch.observe(True, now=float(index) + 0.1)
    assert latch.state(20) == "closed"


def test_half_open_after_eleven_not_sixty(tmp_path: Path) -> None:
    latch = Latch(tmp_path)
    _trip(latch)
    assert latch.state(10.9) == "open"
    assert latch.state(11.0) == "half_open"


def test_probe_budget_is_one(tmp_path: Path) -> None:
    latch = Latch(tmp_path)
    _trip(latch)
    assert latch.allow(11.0) is True
    latch.observe(False, now=11.0)
    assert latch.allow(11.0) is False
    assert latch.state(11.5) == "open"


def test_two_successes_close(tmp_path: Path) -> None:
    latch = Latch(tmp_path)
    _trip(latch)
    assert latch.observe(True, now=11.0) == "half_open"
    assert latch.observe(True, now=12.0) == "closed"


def test_slow_call_is_failure(tmp_path: Path) -> None:
    latch = Latch(tmp_path)
    latch.observe(True, duration_ms=400, now=0)
    latch.observe(True, duration_ms=400, now=1)
    latch.observe(True, duration_ms=400, now=2)
    assert latch.state(2) == "open"


def test_success_in_open_is_ignored(tmp_path: Path) -> None:
    latch = Latch(tmp_path)
    _trip(latch)
    assert latch.observe(True, now=3.0) == "open"
    assert latch.state(3.0) == "open"


def test_isolated_errors_do_not_trip(tmp_path: Path) -> None:
    latch = Latch(tmp_path)
    latch.observe(False, now=0)
    latch.observe(True, now=1)
    latch.observe(False, now=2)
    assert latch.state(2) == "closed"
