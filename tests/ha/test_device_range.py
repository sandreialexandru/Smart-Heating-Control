"""A thermostat whose entity goes no lower than a minimum (a heat pump at 16 for a 12 vacation).

Home Assistant refuses a temperature outside the range of the entity: the room
is held at the minimum, told once, and nothing is sent again and again.
"""

from __future__ import annotations

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import Context, HomeAssistant
from pytest_homeassistant_custom_component.common import async_mock_service

from tests.ha.test_ha_devices import _house, _room, _tick, _unload

HP = {
    "hvac_modes": ["heat", "off"],
    "min_temp": 16.0,
    "max_temp": 30.0,
    "current_temperature": 20.0,
}
ROOM = {"source": "climate", "command_mode": "temperature", "climates": ["climate.daikin"]}


def _sent(calls) -> list[float]:
    return [c.data["temperature"] for c in calls if c.data["entity_id"] == "climate.daikin"]


async def test_vacation_below_the_minimum_of_the_entity(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    temps = async_mock_service(hass, "climate", "set_temperature")
    async_mock_service(hass, "climate", "set_hvac_mode")
    hass.states.async_set("climate.daikin", "heat", {**HP, "temperature": 21.0})
    entry = await _house(hass, freezer, [("Living", ROOM)])
    house = entry.runtime_data
    room = _room(entry, "Living")
    await house.async_set_mode("vacation")
    await _tick(hass, freezer, 5)
    assert room.decision.key == "vacation"
    assert _sent(temps)[-1] == 16.0  # not 12: Home Assistant would refuse it
    alert = house.notifier.active["range_climate.daikin_min"]
    assert alert["code"] == "device_range_min"
    assert alert["params"] == {"entity": "climate.daikin", "value": "16 °C", "target": "12 °C"}
    # It holds 16: nothing more is sent, no manual change.
    hass.states.async_set("climate.daikin", "heat", {**HP, "temperature": 16.0}, Context())
    await _tick(hass, freezer, 5)
    count = len(temps)
    await _tick(hass, freezer, 65)
    await _tick(hass, freezer, 600)
    assert len(temps) == count
    assert not room.override

    # The minimum lowered on the device: 12 is sent, the alert ends.
    hass.states.async_set(
        "climate.daikin", "heat", {**HP, "min_temp": 10.0, "temperature": 16.0}, Context()
    )
    await _tick(hass, freezer, 5)
    await _tick(hass, freezer, 65)
    assert _sent(temps)[-1] == 12.0
    assert "range_climate.daikin_min" not in house.notifier.active
    await _unload(hass, entry)


async def test_within_the_range_nothing_changes(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    temps = async_mock_service(hass, "climate", "set_temperature")
    async_mock_service(hass, "climate", "set_hvac_mode")
    hass.states.async_set("climate.daikin", "heat", {**HP, "min_temp": 5.0, "temperature": 18.0})
    entry = await _house(hass, freezer, [("Living", ROOM)])
    await entry.runtime_data.async_set_mode("vacation")
    await _tick(hass, freezer, 5)
    assert _sent(temps)[-1] == 12.0
    assert not [k for k in entry.runtime_data.notifier.active if k.startswith("range_")]
    await _unload(hass, entry)
