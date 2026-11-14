"""The minimum of a thermostat entity combined with the other features (rc14)."""

from __future__ import annotations

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import Context, HomeAssistant
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.advanced_climate.const import DOMAIN
from tests.ha.test_ha_devices import _house, _room, _tick, _unload

HP = {
    "hvac_modes": ["heat", "off"],
    "min_temp": 16.0,
    "max_temp": 30.0,
    "current_temperature": 20.0,
}
ROOM = {"source": "climate", "command_mode": "temperature", "climates": ["climate.daikin"]}


def _sent(calls, entity_id: str = "climate.daikin") -> list[float]:
    return [c.data["temperature"] for c in calls if c.data["entity_id"] == entity_id]


def _mock(hass: HomeAssistant):
    temps = async_mock_service(hass, "climate", "set_temperature")
    async_mock_service(hass, "climate", "set_hvac_mode")
    async_mock_service(hass, "climate", "set_preset_mode")
    return temps


async def test_two_thermostats_with_different_minimums(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    temps = _mock(hass)
    hass.states.async_set("climate.daikin", "heat", {**HP, "temperature": 21.0})
    hass.states.async_set("climate.trv", "heat", {**HP, "min_temp": 5.0, "temperature": 21.0})
    entry = await _house(
        hass, freezer, [("Living", {**ROOM, "climates": ["climate.daikin", "climate.trv"]})]
    )
    await entry.runtime_data.async_set_mode("vacation")
    await _tick(hass, freezer, 5)
    assert _sent(temps)[-1] == 16.0
    assert _sent(temps, "climate.trv")[-1] == 12.0
    active = entry.runtime_data.notifier.active
    assert "range_climate.daikin_min" in active and "range_climate.trv_min" not in active
    assert hass.states.get("sensor.living_decision").attributes["held_at"] == 16.0
    await _unload(hass, entry)


async def test_a_manual_change_for_a_while_below_the_minimum(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    temps = _mock(hass)
    hass.states.async_set("climate.daikin", "heat", {**HP, "temperature": 21.0})
    entry = await _house(hass, freezer, [("Living", ROOM)])
    await _tick(hass, freezer, 5)
    await hass.services.async_call(
        DOMAIN, "set_override", {"room": "Living", "temperature": 12}, blocking=True
    )
    await _tick(hass, freezer, 5)
    room = _room(entry, "Living")
    assert room.override
    assert _sent(temps)[-1] == 16.0
    # The device shows 16: still the same manual change, nothing sent again.
    hass.states.async_set("climate.daikin", "heat", {**HP, "temperature": 16.0}, Context())
    await _tick(hass, freezer, 5)
    count = len(temps)
    await _tick(hass, freezer, 600)
    assert len(temps) == count
    assert room.override["target"]["temperature"] == 12.0
    await _unload(hass, entry)


async def test_exactly_at_the_minimum_is_no_alert(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    temps = _mock(hass)
    hass.states.async_set("climate.daikin", "heat", {**HP, "min_temp": 12.0, "temperature": 21.0})
    entry = await _house(hass, freezer, [("Living", ROOM)])
    await entry.runtime_data.async_set_mode("vacation")
    await _tick(hass, freezer, 5)
    assert _sent(temps)[-1] == 12.0
    assert not [k for k in entry.runtime_data.notifier.active if k.startswith("range_")]
    assert hass.states.get("sensor.living_decision").attributes["held_at"] is None
    await _unload(hass, entry)


async def test_a_higher_minimum_later_is_told_again(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    temps = _mock(hass)
    hass.states.async_set("climate.daikin", "heat", {**HP, "temperature": 21.0})
    entry = await _house(hass, freezer, [("Living", ROOM)])
    house = entry.runtime_data
    await house.async_set_mode("vacation")
    await _tick(hass, freezer, 5)
    hass.states.async_set(
        "climate.daikin", "heat", {**HP, "min_temp": 18.0, "temperature": 16.0}, Context()
    )
    await _tick(hass, freezer, 5)
    await _tick(hass, freezer, 65)
    assert _sent(temps)[-1] == 18.0
    assert house.notifier.active["range_climate.daikin_min"]["params"]["value"] == "18 °C"
    await _unload(hass, entry)


async def test_mode_off_is_frost_protection_held_at_the_minimum(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Mode Off is frost protection (7 °C): a device that goes no lower than 16 holds 16."""
    temps = _mock(hass)
    hass.states.async_set("climate.daikin", "heat", {**HP, "temperature": 21.0})
    entry = await _house(hass, freezer, [("Living", ROOM)])
    await entry.runtime_data.async_set_mode("off")
    await _tick(hass, freezer, 5)
    assert _sent(temps)[-1] == 16.0
    attrs = hass.states.get("sensor.living_decision").attributes
    assert attrs["target_temperature"] == 7.0 and attrs["held_at"] == 16.0
    params = entry.runtime_data.notifier.active["range_climate.daikin_min"]["params"]
    assert params["target"] == "7 °C"
    await _unload(hass, entry)


async def test_a_level_sent_as_a_temperature_when_the_preset_is_missing(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Preset mode, but the device has no away preset: its temperature, within the range."""
    temps = _mock(hass)
    hass.states.async_set(
        "climate.daikin",
        "heat",
        {**HP, "preset_modes": ["home", "eco"], "preset_mode": "home", "temperature": 21.0},
    )
    entry = await _house(hass, freezer, [("Living", {**ROOM, "command_mode": "preset"})])
    await entry.runtime_data.async_set_mode("vacation")
    await _tick(hass, freezer, 5)
    assert _sent(temps)[-1] == 16.0
    assert hass.states.get("sensor.living_decision").attributes["held_at"] == 16.0
    await _unload(hass, entry)


async def test_trv_boost_with_a_minimum(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """The boost goes up to the maximum; back at the base it is held at the minimum."""
    temps = _mock(hass)
    hass.states.async_set(
        "sensor.living", "11.0", {"device_class": "temperature", "unit_of_measurement": "°C"}
    )
    hass.states.async_set("climate.daikin", "heat", {**HP, "temperature": 21.0})
    entry = await _house(
        hass,
        freezer,
        [("Living", {**ROOM, "trv_boost": True, "temperature_sensors": ["sensor.living"]})],
    )
    await entry.runtime_data.async_set_mode("vacation")
    await _tick(hass, freezer, 5)
    assert _sent(temps)[-1] == 25.0  # cold (11 < 12): boosted to the maximum of the house
    hass.states.async_set("climate.daikin", "heat", {**HP, "temperature": 25.0}, Context())
    hass.states.async_set(
        "sensor.living", "13.0", {"device_class": "temperature", "unit_of_measurement": "°C"}
    )
    await _tick(hass, freezer, 5)
    await _tick(hass, freezer, 65)
    assert _sent(temps)[-1] == 16.0
    assert not _room(entry, "Living").override
    await _unload(hass, entry)


async def test_minimum_in_fahrenheit(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    from homeassistant.util.unit_system import US_CUSTOMARY_SYSTEM

    hass.config.units = US_CUSTOMARY_SYSTEM
    temps = _mock(hass)
    hass.states.async_set(
        "climate.daikin",
        "heat",
        {**HP, "min_temp": 61.0, "max_temp": 86.0, "current_temperature": 68.0, "temperature": 70},
    )
    entry = await _house(hass, freezer, [("Living", ROOM)])
    await entry.runtime_data.async_set_mode("vacation")
    await _tick(hass, freezer, 5)
    assert _sent(temps)[-1] == 61.0  # not 53.6 (12 °C)
    alert = entry.runtime_data.notifier.active["range_climate.daikin_min"]
    assert alert["params"]["value"] == "61 °F"
    held = hass.states.get("sensor.living_decision").attributes["held_at"]
    assert held is not None
    await _unload(hass, entry)
