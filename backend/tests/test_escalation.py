"""Escalation: when a Theater's Pressure has risen enough against the window before."""

from backend.api.pressure import is_escalating


def test_escalating_needs_both_a_one_and_a_half_times_rise_and_a_rise_of_1_6():
    assert is_escalating(current=4.8, previous=3.2)        # 1.5×, +1.6
    assert not is_escalating(current=4.7, previous=3.2)    # under 1.5×
    assert not is_escalating(current=3.0, previous=1.5)    # 2×, but only +1.5
    assert not is_escalating(current=20.0, previous=15.0)  # +5, but only 1.33×


def test_from_zero_only_the_1_6_floor_applies():
    assert is_escalating(current=1.6, previous=0.0)  # one single-Source critical Event
    assert not is_escalating(current=1.2, previous=0.0)
    assert not is_escalating(current=0.0, previous=0.0)


def test_falling_pressure_is_not_escalating():
    assert not is_escalating(current=1.0, previous=8.0)
