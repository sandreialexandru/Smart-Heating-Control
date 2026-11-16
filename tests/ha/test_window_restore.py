"""A window and the thermostat's old target when it comes back.

A TRV keeps its target while a window turns it off or to the frost protection.
When the window closes, a sleepy TRV may report that old target again (or go
back to auto with it): that is not a person's change, and the room must follow
the schedule of that moment.
"""

from __future__ import annotations

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import Context, HomeAssistant
from pytest_homeassistant_custom_component.common import async_mock_service

from tests.ha.test_ha_devices import _house, _room, _tick, _unload

TRV = {
    "hvac_modes": ["auto", "heat", "off"],
    "preset_modes": ["none", "manual"],
    "preset_mode": "manual",
    "current_temperature": 19.0,
    "temperature": 17.0,
    "min_temp": 7.0,
    "max_temp": 30.0,
    "target_temp_step": 0.5,
}
ROOM = {
    "source": "climate",
    "climates": ["climate.trv"],
    "command_mode": "temperature",
    "window_sensors": ["binary_sensor.window"],
    "window_action": "off",
    "schedule": "day: 00:00 sleep, 06:00 eco, 20:00 sleep",
}


async def _window_house(hass: HomeAssistant, freezer: FrozenDateTimeFactory):
    """A TRV, a window, and a manual change at 17:30 (until 19:30)."""
    hass.states.async_set("binary_sensor.window", "off")
    hass.states.async_set("climate.trv", "heat", TRV)
    modes = async_mock_service(hass, "climate", "set_hvac_mode")
    temperatures = async_mock_service(hass, "climate", "set_temperature")
    # 17:20 local (Europe/Bucharest, +3 in October).
    entry = await _house(hass, freezer, [("Office", ROOM)], at="2026-10-12 14:20:00+00:00")
    await _tick(hass, freezer, 10 * 60)  # 17:30
    hass.states.async_set("climate.trv", "heat", {**TRV, "temperature": 22.0}, context=Context())
    await _tick(hass, freezer, 5)
    room = _room(entry, "Office")
    assert room.override is not None
    return entry, room, modes, temperatures


async def _open_window(hass: HomeAssistant, freezer: FrozenDateTimeFactory, modes) -> None:
    """Open the window at 19:00 and let the TRV take the off command."""
    await _tick(hass, freezer, 90 * 60)  # 19:00
    hass.states.async_set("binary_sensor.window", "on")
    await _tick(hass, freezer, 65)  # open delay
    assert modes and modes[-1].data["hvac_mode"] == "off"
    hass.states.async_set(
        "climate.trv", "off", {**TRV, "temperature": 22.0}, context=modes[-1].context
    )
    await _tick(hass, freezer, 5)


async def test_a_trv_reporting_its_old_target_after_a_window_is_not_manual(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """The 17:30 manual change ends at 19:30; after the window the schedule is eco."""
    entry, room, modes, _temperatures = await _window_house(hass, freezer)
    await _open_window(hass, freezer, modes)
    await _tick(hass, freezer, 35 * 60)  # 19:35: the fixed 2 h manual change ended
    assert room.override is None

    await _tick(hass, freezer, 10 * 3600 + 55 * 60)  # 06:30 next day
    hass.states.async_set("binary_sensor.window", "off")
    await _tick(hass, freezer, 65)  # close delay

    # The TRV wakes and goes back to auto with the target it had before the
    # window (22), not with the eco of 06:30 (17).
    hass.states.async_set(
        "climate.trv",
        "auto",
        {**TRV, "temperature": 22.0, "current_temperature": 19.0},
    )
    await _tick(hass, freezer, 5)

    assert room.override is None
    assert room.decision is not None
    assert room.decision.rule == "schedule"
    assert room.target_temperature == 17.0
    await _unload(hass, entry)


async def test_a_manual_change_during_a_window_is_still_respected(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """A different target set during the window is a person's, not the old one."""
    entry, room, modes, _temperatures = await _window_house(hass, freezer)
    await _open_window(hass, freezer, modes)

    hass.states.async_set("climate.trv", "heat", {**TRV, "temperature": 24.0}, context=Context())
    await _tick(hass, freezer, 5)
    assert room.override is not None
    assert room.override["devices"]["climate.trv"]["temperature"] == 24.0
    await _unload(hass, entry)
