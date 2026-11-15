"""Heating circuits without a heat source: zone valves wired to the boiler.

The valves start the boiler themselves when they open (MaffSmith, #10): SHC
opens the valve of a circuit while a room of it asks for heat and closes it as
soon as none does. There is no boiler to wait for, so nothing waits for it.
"""

from __future__ import annotations

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import async_mock_service

from tests.ha.test_circuits import ROOM, _on, _report
from tests.ha.test_ha_devices import _house, _room, _tick, _unload

UP = "input_boolean.upstairs"
DOWN = "input_boolean.downstairs"
TRV = {
    "hvac_modes": ["heat", "off"],
    "current_temperature": 20.0,
    "min_temp": 5.0,
    "max_temp": 30.0,
}


async def _setup(hass: HomeAssistant, freezer: FrozenDateTimeFactory, **options):
    async_mock_service(hass, "climate", "set_temperature")
    async_mock_service(hass, "climate", "set_hvac_mode")
    assert await async_setup_component(
        hass, "input_boolean", {"input_boolean": {"upstairs": {}, "downstairs": {}}}
    )
    for entity_id in ("climate.bedroom", "climate.office", "climate.living", "climate.hall"):
        hass.states.async_set(
            entity_id, "heat", {**TRV, "temperature": 21.0, "hvac_action": "idle"}
        )
    return await _house(
        hass,
        freezer,
        [
            ("Bedroom", {**ROOM, "climates": ["climate.bedroom"], "circuit": UP}),
            ("Office", {**ROOM, "climates": ["climate.office"], "circuit": UP}),
            ("Living", {**ROOM, "climates": ["climate.living"], "circuit": DOWN}),
            ("Hall", {**ROOM, "climates": ["climate.hall"]}),
        ],
        circuits=[UP, DOWN],
        **options,
    )


async def _settle(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    await _tick(hass, freezer, 5)
    await _tick(hass, freezer, 5)


async def test_the_valve_of_a_floor_opens_and_closes_with_its_rooms(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    entry = await _setup(hass, freezer)
    house = entry.runtime_data
    assert house.circuits == [UP, DOWN]
    _report(hass, "climate.bedroom", "heating")
    await _settle(hass, freezer)
    assert _on(hass, UP) and not _on(hass, DOWN)
    assert _room(entry, "Bedroom").heating
    # A second room of the same floor: the valve stays open until both are done.
    _report(hass, "climate.office", "heating")
    _report(hass, "climate.bedroom", "idle", 21.1)
    await _settle(hass, freezer)
    assert _on(hass, UP)
    _report(hass, "climate.office", "idle", 21.1)
    await _settle(hass, freezer)
    # No boiler to wait for: closed at once.
    assert not _on(hass, UP) and not _on(hass, DOWN)
    await _unload(hass, entry)


async def test_each_floor_has_its_own_valve(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    entry = await _setup(hass, freezer)
    _report(hass, "climate.living", "heating")
    await _settle(hass, freezer)
    assert _on(hass, DOWN) and not _on(hass, UP)
    _report(hass, "climate.bedroom", "heating")
    await _settle(hass, freezer)
    assert _on(hass, DOWN) and _on(hass, UP)
    _report(hass, "climate.living", "idle", 21.1)
    await _settle(hass, freezer)
    assert not _on(hass, DOWN) and _on(hass, UP)
    await _unload(hass, entry)


async def test_a_room_without_a_circuit_opens_no_valve(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    entry = await _setup(hass, freezer)
    _report(hass, "climate.hall", "heating")
    await _settle(hass, freezer)
    assert not _on(hass, UP) and not _on(hass, DOWN)
    assert _room(entry, "Hall").heating
    await _unload(hass, entry)


async def test_the_boiler_settings_left_behind_do_not_apply(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Rooms needed and a room once set as secondary (with a heat source
    removed later) do not keep a valve closed."""
    entry = await _setup(hass, freezer, boiler_min_rooms=3)
    house = entry.runtime_data
    bedroom = _room(entry, "Bedroom")
    bedroom.config["starts_house_source"] = False
    bedroom.config["use_house_source"] = False
    _report(hass, "climate.bedroom", "heating")
    await _settle(hass, freezer)
    assert bedroom.circuit == UP
    assert _on(hass, UP)
    assert "boiler_min_rooms" not in house.active_alerts
    await _unload(hass, entry)


async def test_an_unavailable_valve_is_told(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    entry = await _setup(hass, freezer)
    hass.states.async_set(UP, "unavailable")
    _report(hass, "climate.bedroom", "heating")
    await _settle(hass, freezer)
    bedroom = _room(entry, "Bedroom")
    assert not bedroom.heating
    assert bedroom.no_heat_reason() == {"code": "circuit_closed", "entity": UP}
    await _unload(hass, entry)


async def test_a_valve_closed_by_hand_is_opened_again(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    entry = await _setup(hass, freezer)
    _report(hass, "climate.bedroom", "heating")
    await _settle(hass, freezer)
    assert _on(hass, UP)
    await hass.services.async_call("input_boolean", "turn_off", {"entity_id": UP}, blocking=True)
    await _settle(hass, freezer)
    assert _on(hass, UP)
    await _unload(hass, entry)
