from __future__ import annotations

from admit import Gate


def test_burst_is_three() -> None:
    gate = Gate()
    assert all(gate.allow(index * 0.01) for index in range(3))
    assert gate.allow(0.1) is False


def test_ten_per_minute_is_wrong() -> None:
    gate = Gate()
    assert gate.allow(0) is True
    assert gate.allow(0.01) is True
    assert gate.allow(0.02) is True
    assert gate.allow(0.03) is False


def test_refill_is_one_per_seven_seconds() -> None:
    gate = Gate()
    for index in range(3):
        assert gate.allow(index * 0.01)
    assert gate.allow(6.9) is False
    assert gate.allow(7.1) is True


def test_window_caps_at_eight() -> None:
    gate = Gate()
    times = [0.0, 0.01, 0.02, 7.1, 14.2, 21.3, 28.4, 35.5]
    assert all(gate.allow(stamp) for stamp in times)
    assert gate.allow(42.6) is False
