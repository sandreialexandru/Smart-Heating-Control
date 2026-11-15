"""The heating time of a room commanded on / off follows the thermostat (#16).

A real Generic Thermostat with its heater, the room sensor warming while the
heater is on: the time counted is the time the heater was on, whichever way
the room is commanded, and an on / off thermostat already on heats as far as
it can (not at its own lower target).
"""

from __future__ import annotations

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util

from tests.ha.test_ha_devices import _house, _room, _tick, _unload

SENSOR = {"unit_of_measurement": "°C", "device_class": "temperature"}


async def _gt_room(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, room: dict, minutes: int, **house
) -> tuple[int, float, object]:
    """Run a room with a Generic Thermostat at 17; return the minutes the heater
    was on, the minutes counted and the room."""
    # The clock first: the thermostat waits for its cycle from the heater's last change.
    freezer.move_to("2026-10-12 08:59:00+00:00")
    assert await async_setup_component(hass, "homeassistant", {})
    assert await async_setup_component(
        hass, "input_boolean", {"input_boolean": {"heater": {}, "boiler": {}}}
    )
    hass.states.async_set("sensor.gab_temp", "16.8", SENSOR)
    assert await async_setup_component(
        hass,
        "climate",
        {
            "climate": {
                "platform": "generic_thermostat",
                "name": "gab",
                "heater": "input_boolean.heater",
                "target_sensor": "sensor.gab_temp",
                "target_temp": 17,
                "initial_hvac_mode": "heat",
                "cold_tolerance": 0.2,
                "hot_tolerance": 0.2,
                "min_temp": 5,
                "max_temp": 30,
            }
        },
    )
    await hass.async_block_till_done()
    entry = await _house(hass, freezer, [("Gab", {**room, "climates": ["climate.gab"]})], **house)
    on = 0
    temp = 16.8
    for _ in range(minutes):
        heater_on = hass.states.get("input_boolean.heater").state == "on"
        on += heater_on
        temp += 0.06 if heater_on else -0.02
        hass.states.async_set("sensor.gab_temp", f"{temp:.2f}", SENSOR)
        await _tick(hass, freezer, 60)
    room_obj = _room(entry, "Gab")
    counted = room_obj.runtime_s / 60
    await _unload(hass, entry)
    return on, counted, room_obj


@pytest.mark.parametrize(
    "room",
    [
        {"source": "climate", "command_mode": "temperature"},
        {"source": "generic_thermostat"},
        {"source": "climate", "command_mode": "hvac_mode"},
    ],
    ids=["temperature", "preset", "on_off"],
)
async def test_the_time_counted_is_the_time_the_heater_was_on(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, room: dict
) -> None:
    on, counted, _room_obj = await _gt_room(hass, freezer, room, 360)
    assert on > 30
    assert abs(counted - on) <= 3


async def test_an_on_off_thermostat_already_on_heats_to_the_room_target(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """On at the start at its own 17, the room asks for 21: raised to its maximum,
    so the room reaches 21, not the 17 of the thermostat."""
    _on, _counted, room = await _gt_room(
        hass, freezer, {"source": "climate", "command_mode": "hvac_mode"}, 240
    )
    assert room.current_temp is not None and room.current_temp >= 20.5


async def test_on_off_counted_while_the_thermostat_heats_though_told_off(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Told off, but the thermostat says it heats (e.g. turned on by hand): counted."""
    hass.states.async_set(
        "climate.onoff",
        "heat",
        {
            "hvac_modes": ["heat", "off"],
            "temperature": 30,
            "current_temperature": 22.0,
            "hvac_action": "heating",
            "min_temp": 5,
            "max_temp": 30,
        },
    )
    hass.services.async_register("climate", "set_hvac_mode", lambda call: None)
    hass.services.async_register("climate", "set_temperature", lambda call: None)
    entry = await _house(
        hass,
        freezer,
        [
            (
                "Gab",
                {"source": "climate", "command_mode": "hvac_mode", "climates": ["climate.onoff"]},
            )
        ],
    )
    room = _room(entry, "Gab")
    heating = []
    for _ in range(30):
        await _tick(hass, freezer, 60)
        heating.append(room.heating)
    assert not room.heat_demand  # the room at 22 asks for no heat
    assert all(heating)
    # Added at each evaluation: the time since the last one is still running.
    assert room._heating_since is not None
    running = (dt_util.utcnow() - room._heating_since).total_seconds()
    assert room.runtime_s + running >= 29 * 60
    await _unload(hass, entry)
