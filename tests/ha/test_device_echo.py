"""The values sent to the devices and their reports, on their own (no Home Assistant running)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from homeassistant.core import State

from custom_components.advanced_climate.device_echo import (
    DeviceLimits,
    SentValues,
    limit_kind,
)

T0 = datetime(2026, 11, 2, 8, 0, tzinfo=UTC)
TRV = "climate.trv"


def _trv(temperature: float, state: str = "heat") -> State:
    return State(TRV, state, {"temperature": temperature, "target_temp_step": 0.5})


def _sent() -> SentValues:
    return SentValues(timedelta(minutes=5), timedelta(seconds=60))


def test_a_late_report_of_the_last_command_is_an_echo() -> None:
    sent = _sent()
    sent.start(TRV)
    sent.record(TRV, "temperature", 21.0, 17.0, T0)
    assert sent.is_echo(TRV, _trv(17), _trv(21), T0 + timedelta(seconds=90))
    # A value never sent is a person's.
    assert not sent.is_echo(TRV, _trv(17), _trv(23), T0 + timedelta(seconds=90))


def test_an_older_command_reported_after_a_newer_one_is_an_echo() -> None:
    sent = _sent()
    sent.record(TRV, "temperature", 21.0, 17.0, T0)
    sent.record(TRV, "temperature", 12.0, 21.0, T0 + timedelta(seconds=30))
    assert sent.is_echo(TRV, _trv(12), _trv(21), T0 + timedelta(seconds=60))
    # After the recent minutes the older value is no longer expected.
    assert not sent.is_echo(TRV, _trv(12), _trv(17), T0 + timedelta(minutes=10))


def test_the_value_shown_before_a_command_is_a_bounce_until_the_new_one_is_stable() -> None:
    sent = _sent()
    sent.start(TRV)
    sent.record(TRV, "temperature", 22.0, 21.5, T0)
    sent.confirm(TRV, _trv(22), T0 + timedelta(seconds=5))
    # Shown again 20 s later: the TRV bounced back once.
    assert sent.is_echo(TRV, _trv(22), _trv(21.5), T0 + timedelta(seconds=25))
    # A bounce restarts the stable time.
    sent.confirm(TRV, _trv(21.5), T0 + timedelta(seconds=25))
    sent.confirm(TRV, _trv(22), T0 + timedelta(seconds=40))
    assert sent.is_echo(TRV, _trv(22), _trv(21.5), T0 + timedelta(seconds=90))
    # Shown for a minute: the old value is now a person's.
    assert not sent.is_echo(TRV, _trv(22), _trv(21.5), T0 + timedelta(seconds=101))


def test_turning_off_is_not_taken_for_a_bounce() -> None:
    sent = _sent()
    sent.start(TRV)
    sent.record(TRV, "state", "heat", None, T0)
    assert not sent.is_echo(TRV, _trv(21), _trv(21, "off"), T0 + timedelta(seconds=30))


def test_a_person_s_change_forgets_what_was_sent() -> None:
    sent = _sent()
    sent.record(TRV, "temperature", 21.0, 17.0, T0)
    sent.forget(TRV)
    assert not sent.is_echo(TRV, _trv(17), _trv(21), T0 + timedelta(seconds=10))
    assert sent.last_value(TRV, "temperature") is None


def test_the_step_of_the_device_is_tolerated() -> None:
    sent = _sent()
    sent.record(TRV, "temperature", 21.3, 17.0, T0)
    assert sent.is_echo(TRV, _trv(17), _trv(21.5), T0 + timedelta(seconds=10))
    assert not sent.is_echo(TRV, _trv(17), _trv(22.0), T0 + timedelta(seconds=10))


def test_limit_kind() -> None:
    # Boost 28 above a 21 target, the TRV holds 25: its maximum.
    assert limit_kind(28, 25, 0.26, target=21, exercising=False, lowest_level=12) == "max"
    # Below the target: a person, not a limit.
    assert limit_kind(28, 20, 0.26, target=21, exercising=False, lowest_level=12) is None
    # The valve exercise: any lower value is the maximum.
    assert limit_kind(35, 30, 0.26, target=None, exercising=True, lowest_level=12) == "max"
    # Frost 7 sent, the TRV holds 10, below every level: its minimum.
    assert limit_kind(7, 10, 0.26, target=7, exercising=False, lowest_level=12) == "min"
    # Above the lowest level: a person.
    assert limit_kind(7, 15, 0.26, target=7, exercising=False, lowest_level=12) is None
    # The value sent: nothing.
    assert limit_kind(21, 21, 0.26, target=21, exercising=False, lowest_level=12) is None


def test_device_limits_are_kept_a_while() -> None:
    limits = DeviceLimits(timedelta(hours=24))
    assert limits.learn(TRV, "max", 25.0, T0) is None
    assert limits.get(TRV, "max", T0 + timedelta(hours=23)) == (25.0, False)
    assert limits.learn(TRV, "max", 26.0, T0 + timedelta(hours=1)) == 25.0
    assert limits.get(TRV, "max", T0 + timedelta(hours=26)) == (None, True)
    assert limits.get(TRV, "max", T0 + timedelta(hours=26)) == (None, False)
