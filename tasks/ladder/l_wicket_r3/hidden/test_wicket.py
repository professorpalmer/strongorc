from __future__ import annotations

from pathlib import Path

from wicket import Latch

TRIP = 5
COOLDOWN = 5.0
SLOW_MS = 120
BEFORE = 4.9


def _trip(latch: Latch, start: float = 0.0) -> None:
    for _ in range(TRIP):
        latch.observe(False, now=start)


def test_wicket_r3_trips_on_three_consecutive(tmp_path: Path) -> None:
    latch = Latch(tmp_path)
    for index in range(TRIP - 1):
        latch.observe(False, now=float(index))
    assert latch.state(float(TRIP - 2)) == "closed"
    latch.observe(False, now=float(TRIP - 1))
    assert latch.state(float(TRIP - 1)) == "open"


def test_wicket_r3_twenty_per_two_minutes_is_wrong(tmp_path: Path) -> None:
    latch = Latch(tmp_path)
    for index in range(19):
        latch.observe(False, now=float(index))
        latch.observe(True, now=float(index) + 0.1)
    assert latch.state(20) == "closed"


def test_wicket_r3_half_open_after_eleven_not_sixty(tmp_path: Path) -> None:
    latch = Latch(tmp_path)
    _trip(latch)
    assert latch.state(BEFORE) == "open"
    assert latch.state(COOLDOWN) == "half_open"


def test_wicket_r3_probe_budget_is_one(tmp_path: Path) -> None:
    latch = Latch(tmp_path)
    _trip(latch)
    assert latch.allow(COOLDOWN) is True
    latch.observe(False, now=COOLDOWN)
    assert latch.allow(COOLDOWN) is False
    assert latch.state(COOLDOWN + 0.5) == "open"


def test_wicket_r3_two_successes_close(tmp_path: Path) -> None:
    latch = Latch(tmp_path)
    _trip(latch)
    assert latch.observe(True, now=COOLDOWN) == "half_open"
    assert latch.observe(True, now=COOLDOWN + 1.0) == "closed"


def test_wicket_r3_slow_call_is_failure(tmp_path: Path) -> None:
    latch = Latch(tmp_path)
    for index in range(TRIP):
        latch.observe(True, duration_ms=SLOW_MS, now=float(index))
    assert latch.state(float(TRIP - 1)) == "open"


def test_wicket_r3_success_in_open_is_ignored(tmp_path: Path) -> None:
    latch = Latch(tmp_path)
    _trip(latch)
    assert latch.observe(True, now=3.0) == "open"
    assert latch.state(3.0) == "open"


def test_wicket_r3_isolated_errors_do_not_trip(tmp_path: Path) -> None:
    latch = Latch(tmp_path)
    latch.observe(False, now=0)
    latch.observe(True, now=1)
    latch.observe(False, now=2)
    assert latch.state(2) == "closed"
