"""The values sent to the devices and their reports, on their own (no Home Assistant running)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from homeassistant.core import State

from custom_components.advanced_climate.device_echo import (
    DeviceLimits,
    SentValues,
    close,
    limit_kind,
    step_margin,
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


def test_a_preset_sent_brings_its_own_temperature() -> None:
    """A TRV on a preset sent again takes the preset's temperature, reported with its own context."""
    sent = _sent()

    def trv(temperature: float, preset: str) -> State:
        return State(
            TRV,
            "heat",
            {"temperature": temperature, "preset_mode": preset, "target_temp_step": 0.5},
        )

    sent.start(TRV)
    sent.record(TRV, "preset_mode", "Comfort", "Comfort", T0)
    # Comfort (with 18 °C from before) goes back to Comfort's own 21 °C.
    assert sent.is_echo(TRV, trv(18, "Comfort"), trv(21, "Comfort"), T0 + timedelta(seconds=5))
    # Shown for a minute: a new temperature on the same preset is a person's.
    sent.confirm(TRV, trv(21, "Comfort"), T0 + timedelta(seconds=5))
    assert not sent.is_echo(TRV, trv(21, "Comfort"), trv(23, "Comfort"), T0 + timedelta(seconds=70))
    # Another preset than the one sent is a person's too.
    assert not sent.is_echo(TRV, trv(21, "Comfort"), trv(15, "Away"), T0 + timedelta(seconds=10))


# What the mutation tests found untested (a change in the code no test noticed).


def test_the_margin_without_a_step_of_the_device() -> None:
    """Without target_temp_step only a rounding to the tenth is a value sent (0.05)."""
    bare = State(TRV, "heat", {"temperature": 21.0})
    assert step_margin(bare) == 0.05
    assert step_margin(_trv(21)) == pytest.approx(0.26)  # half of 0.5, and a little more
    assert close(21.04, 21.0, 0.05)
    assert not close(21.1, 21.0, 0.05)
    assert not close("unknown", 21.0, 0.05)


def test_only_a_shown_value_other_than_the_one_sent_is_kept() -> None:
    sent = _sent()
    sent.record(TRV, "temperature", 21.0, None, T0)
    assert sent.recent_values(TRV, "temperature", T0) == [21.0]
    sent.record(TRV, "temperature", 21.0, 21.0, T0 + timedelta(seconds=1))
    assert sent.recent_values(TRV, "temperature", T0 + timedelta(seconds=1)) == [21.0, 21.0]
    # The preset is apart from the temperature.
    sent.record(TRV, "preset_mode", "Eco", "Comfort", T0 + timedelta(seconds=2))
    assert sent.recent_values(TRV, "preset_mode", T0 + timedelta(seconds=2)) == ["Comfort", "Eco"]
    assert sent.recent_values(TRV, "temperature", T0 + timedelta(seconds=2)) == [21.0, 21.0]
    # Older than the recent minutes: no longer.
    assert sent.recent_values(TRV, "preset_mode", T0 + timedelta(minutes=6)) == []


def test_a_preset_shown_for_a_minute_ends_the_bounces() -> None:
    """The preset is confirmed as the temperature is: the old one later is a person's."""
    sent = _sent()

    def trv(preset: str) -> State:
        return State(TRV, "heat", {"temperature": 20.0, "preset_mode": preset})

    sent.start(TRV)
    sent.record(TRV, "preset_mode", "Eco", "Comfort", T0)
    sent.confirm(TRV, trv("Eco"), T0 + timedelta(seconds=5))
    assert sent.is_confirmed(TRV, "preset_mode")
    # Back to Comfort 20 s later: a bounce.
    assert sent.is_echo(TRV, trv("Eco"), trv("Comfort"), T0 + timedelta(seconds=25))
    # Eco shown for a minute: Comfort now is a person's.
    assert not sent.is_echo(TRV, trv("Eco"), trv("Comfort"), T0 + timedelta(seconds=70))
    # Another preset shown: not confirmed.
    sent.confirm(TRV, trv("Comfort"), T0 + timedelta(seconds=80))
    assert not sent.is_confirmed(TRV, "preset_mode")


def test_limit_kind_at_its_edges() -> None:
    """Exactly at the margin is not past it (margins that are exact in binary)."""
    # Reported exactly one margin below what was sent: not lower.
    assert limit_kind(25, 24.75, 0.25, target=21, exercising=False, lowest_level=12) is None
    # Sent exactly one margin above the target: not above it.
    assert limit_kind(21.25, 20.9, 0.25, target=21, exercising=False, lowest_level=12) is None
    # Reported exactly one margin below the target: still the device's maximum.
    assert limit_kind(22, 20.75, 0.25, target=21, exercising=False, lowest_level=12) == "max"
    # Reported exactly one margin above what was sent: not higher.
    assert limit_kind(7, 7.25, 0.25, target=7, exercising=False, lowest_level=12) is None
    # Reported exactly one margin below the lowest level: not below it.
    assert limit_kind(7, 11.75, 0.25, target=7, exercising=False, lowest_level=12) is None
    # Without the lowest level there is no minimum.
    assert limit_kind(7, 10, 0.25, target=7, exercising=False, lowest_level=None) is None


def test_a_person_picking_a_preset_sent_earlier_sets_their_own_temperature() -> None:
    """Only the preset of the command now brings its temperature (#28)."""
    sent = _sent()

    def trv(temperature: float, preset: str) -> State:
        return State(TRV, "heat", {"temperature": temperature, "preset_mode": preset})

    sent.start(TRV)
    sent.record(TRV, "preset_mode", "Away", "Comfort", T0)
    sent.start(TRV)  # the next command: Comfort, then its temperature
    sent.record(TRV, "preset_mode", "Comfort", "Comfort", T0 + timedelta(seconds=30))
    sent.record(TRV, "temperature", 21.0, 21.0, T0 + timedelta(seconds=31))
    # A person picks Away with 15 °C: a manual change.
    assert not sent.is_echo(TRV, trv(21, "Comfort"), trv(15, "Away"), T0 + timedelta(seconds=40))
    # The device on Comfort, the preset sent now, takes its own temperature: ours.
    assert sent.is_echo(TRV, trv(18, "Comfort"), trv(20, "Comfort"), T0 + timedelta(seconds=40))
