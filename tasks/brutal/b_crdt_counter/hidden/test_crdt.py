from __future__ import annotations

import pytest

from tally import Tally


def test_merge_is_max_not_sum() -> None:
    left = Tally()
    right = Tally()
    left.register("a")
    left.register("b")
    right.register("a")
    right.register("b")
    left.inc("a", 3)
    right.inc("a", 3)
    right.inc("b", 2)
    left.merge(right)
    left.merge(right)
    assert left.value() == 5
    assert left.payload()["p"] == {"a": 3, "b": 2}


def test_decrement_side() -> None:
    counter = Tally()
    other = Tally()
    counter.register("a")
    other.register("a")
    counter.inc("a", 4)
    counter.dec("a", 1)
    other.inc("a", 3)
    other.dec("a", 3)
    counter.merge(other)
    assert counter.value() == 1


def test_register_required() -> None:
    counter = Tally()
    with pytest.raises(KeyError):
        counter.inc("a", 1)
    with pytest.raises(KeyError):
        counter.dec("a", 1)


def test_dec_cannot_exceed_inc() -> None:
    counter = Tally()
    counter.register("a")
    with pytest.raises(ValueError):
        counter.dec("a", 1)
    counter.inc("a", 2)
    with pytest.raises(ValueError):
        counter.dec("a", 3)


def test_negative_delta_rejected() -> None:
    counter = Tally()
    counter.register("a")
    with pytest.raises(ValueError):
        counter.inc("a", -1)
    with pytest.raises(ValueError):
        counter.dec("a", -1)


def test_summing_replicas_is_wrong() -> None:
    left = Tally()
    right = Tally()
    left.register("a")
    right.register("a")
    left.inc("a", 2)
    right.inc("a", 2)
    left.merge(right)
    assert left.value() == 2
