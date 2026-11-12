"""Heating circuits: a pump or zone valve relay per circuit, on the boiler.

The relay of a room's circuit is turned on before the boiler starts for it, and
off only after the boiler stops; the boiler does not start for a room whose
circuit is off.
"""

from __future__ import annotations

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import Context, Event, HomeAssistant, callback
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import async_mock_service

from tests.ha.test_ha_devices import _house, _room, _tick, _unload

TRV = {
    "hvac_modes": ["heat", "off"],
    "current_temperature": 20.0,
    "min_temp": 5.0,
    "max_temp": 30.0,
}
ROOM = {"source": "climate", "command_mode": "temperature"}
RELAYS = ("input_boolean.boiler", "input_boolean.floor", "input_boolean.radiators")


async def _setup(hass: HomeAssistant, freezer: FrozenDateTimeFactory, **rooms_extra):
    async_mock_service(hass, "climate", "set_temperature")
    async_mock_service(hass, "climate", "set_hvac_mode")
    assert await async_setup_component(
        hass,
        "input_boolean",
        {"input_boolean": {"boiler": {}, "floor": {}, "radiators": {}}},
    )
    for entity_id in ("climate.bedroom", "climate.living", "climate.hall"):
        hass.states.async_set(
            entity_id, "heat", {**TRV, "temperature": 21.0, "hvac_action": "idle"}
        )
    order: list[tuple[str, str]] = []

    @callback
    def _changed(event: Event) -> None:
        if event.data["entity_id"] in RELAYS and event.data["new_state"] is not None:
            order.append((event.data["entity_id"], event.data["new_state"].state))

    hass.bus.async_listen("state_changed", _changed)
    entry = await _house(
        hass,
        freezer,
        [
            ("Bedroom", {**ROOM, "climates": ["climate.bedroom"], "circuit": RELAYS[2]}),
            ("Living", {**ROOM, "climates": ["climate.living"], "circuit": RELAYS[1]}),
            ("Hall", {**ROOM, "climates": ["climate.hall"], **rooms_extra}),
        ],
        boiler_entity=RELAYS[0],
        circuits=[RELAYS[1], RELAYS[2]],
    )
    order.clear()
    return entry, order


def _report(hass: HomeAssistant, entity_id: str, action: str, current: float = 20.0) -> None:
    hass.states.async_set(
        entity_id,
        "heat",
        {**TRV, "temperature": 21.0, "hvac_action": action, "current_temperature": current},
        Context(),
    )


def _on(hass: HomeAssistant, entity_id: str) -> bool:
    return hass.states.get(entity_id).state == "on"


async def test_circuit_opens_before_and_closes_after_the_boiler(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    entry, order = await _setup(hass, freezer)
    _report(hass, "climate.bedroom", "heating")
    await _tick(hass, freezer, 5)
    await _tick(hass, freezer, 5)
    assert _on(hass, "input_boolean.radiators")
    assert _on(hass, "input_boolean.boiler")
    assert not _on(hass, "input_boolean.floor")
    assert order[:2] == [("input_boolean.radiators", "on"), ("input_boolean.boiler", "on")]
    assert _room(entry, "Bedroom").heating

    order.clear()
    _report(hass, "climate.bedroom", "idle")
    await _tick(hass, freezer, 5)
    await _tick(hass, freezer, 5)
    assert not _on(hass, "input_boolean.boiler")
    assert not _on(hass, "input_boolean.radiators")
    assert order[:2] == [("input_boolean.boiler", "off"), ("input_boolean.radiators", "off")]
    await _unload(hass, entry)


async def test_circuit_stays_open_while_the_boiler_waits_its_minimum_time(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    entry, _ = await _setup(hass, freezer)
    entry.runtime_data.options["boiler_min_on"] = 10
    _report(hass, "climate.bedroom", "heating")
    await _tick(hass, freezer, 5)
    await _tick(hass, freezer, 5)
    assert _on(hass, "input_boolean.boiler")
    _report(hass, "climate.bedroom", "idle")
    await _tick(hass, freezer, 30)
    # The boiler still runs its minimum time: its circuit stays open.
    assert _on(hass, "input_boolean.boiler")
    assert _on(hass, "input_boolean.radiators")
    await _tick(hass, freezer, 600)
    await _tick(hass, freezer, 5)
    assert not _on(hass, "input_boolean.boiler")
    assert not _on(hass, "input_boolean.radiators")
    await _unload(hass, entry)


async def test_boiler_not_started_for_a_room_whose_circuit_is_unavailable(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    entry, _ = await _setup(hass, freezer)
    hass.states.async_set("input_boolean.radiators", "unavailable")
    _report(hass, "climate.bedroom", "heating")
    await _tick(hass, freezer, 5)
    await _tick(hass, freezer, 5)
    assert not _on(hass, "input_boolean.boiler")
    bedroom = _room(entry, "Bedroom")
    assert not bedroom.heating
    assert bedroom.no_heat_reason() == {
        "code": "circuit_closed",
        "entity": "input_boolean.radiators",
    }
    await _unload(hass, entry)


async def test_room_without_circuit_starts_the_boiler_alone(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    entry, _ = await _setup(hass, freezer)
    _report(hass, "climate.hall", "heating")
    await _tick(hass, freezer, 5)
    await _tick(hass, freezer, 5)
    assert _on(hass, "input_boolean.boiler")
    assert not _on(hass, "input_boolean.floor")
    assert not _on(hass, "input_boolean.radiators")
    assert _room(entry, "Hall").heating
    await _unload(hass, entry)


async def test_one_circuit_closes_while_the_other_keeps_the_boiler(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    entry, _ = await _setup(hass, freezer)
    _report(hass, "climate.bedroom", "heating")
    _report(hass, "climate.living", "heating")
    await _tick(hass, freezer, 5)
    await _tick(hass, freezer, 5)
    assert _on(hass, "input_boolean.floor") and _on(hass, "input_boolean.radiators")
    _report(hass, "climate.bedroom", "idle")
    await _tick(hass, freezer, 5)
    await _tick(hass, freezer, 5)
    # The floor circuit is still open, so the radiator circuit can close.
    assert _on(hass, "input_boolean.boiler")
    assert _on(hass, "input_boolean.floor")
    assert not _on(hass, "input_boolean.radiators")
    await _unload(hass, entry)


async def test_a_secondary_room_does_not_open_its_circuit(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    entry, _ = await _setup(hass, freezer, circuit=RELAYS[2], starts_house_source=False)
    _report(hass, "climate.hall", "heating")
    await _tick(hass, freezer, 5)
    await _tick(hass, freezer, 5)
    assert not _on(hass, "input_boolean.radiators")
    assert not _on(hass, "input_boolean.boiler")
    # Another room of the same circuit opens it: the secondary room heats too.
    _report(hass, "climate.bedroom", "heating")
    await _tick(hass, freezer, 5)
    await _tick(hass, freezer, 5)
    assert _on(hass, "input_boolean.radiators") and _on(hass, "input_boolean.boiler")
    assert _room(entry, "Hall").heating
    await _unload(hass, entry)


async def test_the_room_kept_open_keeps_its_circuit_open(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Keep the last TRV open: the leftover heat needs the circuit of that room."""
    entry, _ = await _setup(hass, freezer)
    entry.runtime_data.options["keep_last_open"] = True
    _report(hass, "climate.bedroom", "heating")
    await _tick(hass, freezer, 5)
    await _tick(hass, freezer, 5)
    _report(hass, "climate.bedroom", "idle", 21.1)
    await _tick(hass, freezer, 5)
    await _tick(hass, freezer, 5)
    await _tick(hass, freezer, 5)
    assert entry.runtime_data.keep_open_room == _room(entry, "Bedroom").id
    assert not _on(hass, "input_boolean.boiler")
    assert _on(hass, "input_boolean.radiators")
    await _unload(hass, entry)
