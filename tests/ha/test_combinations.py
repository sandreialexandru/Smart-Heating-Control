"""Combinations of the heat source options: circuits, secondary rooms, rooms
needed, the reference room, keep the last TRV open, top up and the pause."""

from __future__ import annotations

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import Context, HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_mock_service

from tests.ha.test_ha_devices import _house, _room, _tick, _unload

TRV = {
    "hvac_modes": ["heat", "off"],
    "current_temperature": 20.0,
    "min_temp": 5.0,
    "max_temp": 30.0,
}
ROOM = {"source": "climate", "command_mode": "temperature"}
BOILER, FLOOR, RADIATORS = "input_boolean.boiler", "input_boolean.floor", "input_boolean.radiators"


class Trvs:
    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self.temperature = async_mock_service(hass, "climate", "set_temperature")
        async_mock_service(hass, "climate", "set_hvac_mode")

    def sent(self, entity_id: str) -> float | None:
        for call in reversed(self.temperature):
            if call.data["entity_id"] == entity_id:
                return call.data["temperature"]
        return None

    def report(self, entity_id: str, action: str, current: float = 20.0) -> None:
        self.hass.states.async_set(
            entity_id,
            "heat",
            {
                **TRV,
                "hvac_action": action,
                "current_temperature": current,
                "temperature": self.sent(entity_id) or 21.0,
            },
            Context(),
        )


async def _setup(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    rooms: dict[str, dict],
    **options: object,
):
    trvs = Trvs(hass)
    assert await async_setup_component(
        hass,
        "input_boolean",
        {"input_boolean": {"boiler": {}, "floor": {}, "radiators": {}}},
    )
    hass.states.async_set("binary_sensor.window", "off")
    for name in rooms:
        hass.states.async_set(
            f"climate.{name.lower()}", "heat", {**TRV, "temperature": 21.0, "hvac_action": "idle"}
        )
    entry = await _house(
        hass,
        freezer,
        [
            (name, {**ROOM, "climates": [f"climate.{name.lower()}"], **extra})
            for name, extra in rooms.items()
        ],
        boiler_entity=BOILER,
        **options,
    )
    return entry, trvs


async def _steps(hass: HomeAssistant, freezer: FrozenDateTimeFactory, n: int = 3) -> None:
    for _ in range(n):
        await _tick(hass, freezer, 5)


def _on(hass: HomeAssistant, entity_id: str) -> bool:
    return hass.states.get(entity_id).state == "on"


# ---------------------------------------------------------------------------
# Circuits with rooms needed, the reference room and the pause
# ---------------------------------------------------------------------------


async def test_a_pump_is_not_left_on_while_the_boiler_cannot_start(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Two rooms needed; the circuit of one is unavailable: the boiler cannot
    start, so the other circuit's pump does not run for nothing."""
    entry, trvs = await _setup(
        hass,
        freezer,
        {"Bedroom": {"circuit": RADIATORS}, "Living": {"circuit": FLOOR}},
        circuits=[FLOOR, RADIATORS],
        boiler_min_rooms=2,
    )
    hass.states.async_set(RADIATORS, "unavailable")
    trvs.report("climate.bedroom", "heating")
    trvs.report("climate.living", "heating")
    await _steps(hass, freezer)
    assert not _on(hass, BOILER)
    assert not _on(hass, FLOOR)
    await _unload(hass, entry)


async def test_a_pump_is_not_left_on_while_the_reference_room_cannot_start_it(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    entry, trvs = await _setup(
        hass,
        freezer,
        {"Bedroom": {"circuit": RADIATORS}, "Living": {"circuit": FLOOR}},
        circuits=[FLOOR, RADIATORS],
    )
    entry.runtime_data.options["reference_room"] = _room(entry, "Bedroom").id
    hass.states.async_set(RADIATORS, "unavailable")
    trvs.report("climate.bedroom", "heating")
    trvs.report("climate.living", "heating")
    await _steps(hass, freezer)
    assert not _on(hass, BOILER)
    assert not _on(hass, FLOOR)
    await _unload(hass, entry)


async def test_the_pause_does_not_switch_the_circuits(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """In a pause something else controls the heating: neither the heat source
    nor the circuits are switched (frost protection apart)."""
    entry, trvs = await _setup(
        hass,
        freezer,
        {"Bedroom": {"circuit": RADIATORS}, "Living": {"circuit": FLOOR}},
        circuits=[FLOOR, RADIATORS],
    )
    await entry.runtime_data.async_set_pause(True)
    await _steps(hass, freezer)
    trvs.report("climate.bedroom", "heating")
    await _steps(hass, freezer)
    assert not _on(hass, BOILER)
    assert not _on(hass, RADIATORS)
    await _unload(hass, entry)


async def test_the_pause_leaves_running_circuits_alone(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    entry, trvs = await _setup(
        hass,
        freezer,
        {"Bedroom": {"circuit": RADIATORS}, "Living": {"circuit": FLOOR}},
        circuits=[FLOOR, RADIATORS],
    )
    trvs.report("climate.bedroom", "heating")
    await _steps(hass, freezer)
    assert _on(hass, BOILER) and _on(hass, RADIATORS)
    await entry.runtime_data.async_set_pause(True)
    trvs.report("climate.bedroom", "idle", 21.2)
    await _steps(hass, freezer)
    # The boiler is not controlled in the pause; its circuit stays as it is too.
    assert _on(hass, BOILER)
    assert _on(hass, RADIATORS)
    await _unload(hass, entry)


# ---------------------------------------------------------------------------
# Secondary rooms with rooms needed and the reference room
# ---------------------------------------------------------------------------


async def test_a_secondary_reference_room_is_ignored(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    entry, trvs = await _setup(
        hass, freezer, {"Bedroom": {}, "Hall": {"starts_house_source": False}}
    )
    entry.runtime_data.options["reference_room"] = _room(entry, "Hall").id
    trvs.report("climate.hall", "heating")
    await _steps(hass, freezer)
    assert not _on(hass, BOILER)
    trvs.report("climate.bedroom", "heating")
    await _steps(hass, freezer)
    assert _on(hass, BOILER)
    await _unload(hass, entry)


async def test_rooms_needed_counts_only_the_rooms_that_start_it(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    entry, trvs = await _setup(
        hass,
        freezer,
        {"Bedroom": {}, "Hall": {"starts_house_source": False}},
        boiler_min_rooms=2,
    )
    trvs.report("climate.bedroom", "heating")
    trvs.report("climate.hall", "heating")
    await _steps(hass, freezer)
    assert not _on(hass, BOILER)
    assert any(
        alert.get("code") == "boiler_min_rooms"
        for alert in entry.runtime_data.active_alerts.values()
    )
    await _unload(hass, entry)


async def test_a_secondary_room_in_frost_opens_its_circuit_and_starts_the_boiler(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    entry, _ = await _setup(
        hass,
        freezer,
        {"Bedroom": {}, "Hall": {"starts_house_source": False, "circuit": FLOOR}},
        circuits=[FLOOR],
    )
    hall = _room(entry, "Hall")
    hall.heat_demand = True
    hall.target_temperature = hall.frost_temp()
    await entry.runtime_data._async_control_boiler(dt_util.utcnow())
    await hass.async_block_till_done()
    await entry.runtime_data._async_control_boiler(dt_util.utcnow())
    await hass.async_block_till_done()
    assert _on(hass, FLOOR)
    assert _on(hass, BOILER)
    await _unload(hass, entry)


# ---------------------------------------------------------------------------
# Keep the last TRV open with the stronger rules
# ---------------------------------------------------------------------------


async def _kept_open(hass, freezer, trvs: Trvs, name: str = "bedroom") -> None:
    trvs.report(f"climate.{name}", "heating", 20.0)
    await _steps(hass, freezer, 2)
    trvs.report(f"climate.{name}", "idle", 21.1)
    await _steps(hass, freezer)


async def test_a_window_ends_the_room_kept_open(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    entry, trvs = await _setup(
        hass,
        freezer,
        {"Bedroom": {"window_sensors": ["binary_sensor.window"]}, "Office": {}},
        keep_last_open=True,
    )
    await _kept_open(hass, freezer, trvs)
    bedroom = _room(entry, "Bedroom")
    assert bedroom.kept_open
    hass.states.async_set("binary_sensor.window", "on")
    await _tick(hass, freezer, 120)
    await _steps(hass, freezer)
    assert not bedroom.kept_open
    assert entry.runtime_data.keep_open_room is None
    assert trvs.sent("climate.bedroom") != 25.0
    await _unload(hass, entry)


async def test_the_pause_ends_the_room_kept_open(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    entry, trvs = await _setup(hass, freezer, {"Bedroom": {}, "Office": {}}, keep_last_open=True)
    await _kept_open(hass, freezer, trvs)
    bedroom = _room(entry, "Bedroom")
    assert bedroom.kept_open
    await entry.runtime_data.async_set_pause(True)
    await _steps(hass, freezer)
    assert not bedroom.kept_open
    assert entry.runtime_data.keep_open_room is None
    # After the pause it does not come back by itself (nobody asked since).
    await entry.runtime_data.async_set_pause(False)
    await _steps(hass, freezer)
    assert not bedroom.kept_open
    await _unload(hass, entry)


async def test_a_room_with_its_own_heat_is_never_kept_open(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    entry, trvs = await _setup(
        hass,
        freezer,
        {"Bedroom": {"use_house_source": False}, "Office": {}},
        keep_last_open=True,
    )
    await _kept_open(hass, freezer, trvs)
    assert entry.runtime_data.keep_open_room is None
    assert not _room(entry, "Bedroom").kept_open
    await _unload(hass, entry)


async def test_a_secondary_room_is_never_kept_open(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    entry, trvs = await _setup(
        hass,
        freezer,
        {"Bedroom": {}, "Hall": {"starts_house_source": False}},
        keep_last_open=True,
    )
    # Both heat while the bedroom runs the boiler; the hall stops last.
    trvs.report("climate.bedroom", "heating", 20.0)
    trvs.report("climate.hall", "heating", 20.0)
    await _steps(hass, freezer, 2)
    trvs.report("climate.bedroom", "idle", 21.1)
    await _steps(hass, freezer)
    trvs.report("climate.hall", "idle", 21.1)
    await _steps(hass, freezer)
    house = entry.runtime_data
    assert house.keep_open_room in (None, _room(entry, "Bedroom").id)
    assert not _room(entry, "Hall").kept_open
    await _unload(hass, entry)


# ---------------------------------------------------------------------------
# Top up with the pause, the window and a manual change of another room
# ---------------------------------------------------------------------------


async def test_no_top_up_in_a_pause(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    entry, trvs = await _setup(
        hass, freezer, {"Bedroom": {}, "Office": {"top_up": True}}, boiler_min_on=30
    )
    office = _room(entry, "Office")
    trvs.report("climate.office", "idle", 20.8)
    trvs.report("climate.bedroom", "heating", 20.0)
    await _steps(hass, freezer)
    assert office.topped_up
    await entry.runtime_data.async_set_pause(True)
    await _steps(hass, freezer)
    assert not office.topped_up
    await _unload(hass, entry)


async def test_no_top_up_with_the_window_open(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    entry, trvs = await _setup(
        hass,
        freezer,
        {"Bedroom": {}, "Office": {"top_up": True, "window_sensors": ["binary_sensor.window"]}},
    )
    office = _room(entry, "Office")
    hass.states.async_set("binary_sensor.window", "on")
    await _tick(hass, freezer, 120)
    trvs.report("climate.office", "idle", 20.8)
    trvs.report("climate.bedroom", "heating", 20.0)
    await _steps(hass, freezer)
    assert _on(hass, BOILER)
    assert not office.topped_up
    await _unload(hass, entry)


async def test_a_topped_up_room_does_not_hold_the_boiler_with_rooms_needed(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Two rooms needed: the two others start it; the office topped up does not
    keep it running once one of them is warm."""
    entry, trvs = await _setup(
        hass,
        freezer,
        {"Bedroom": {}, "Living": {}, "Office": {"top_up": True}},
        boiler_min_rooms=2,
    )
    office = _room(entry, "Office")
    trvs.report("climate.office", "idle", 20.8)
    trvs.report("climate.bedroom", "heating", 20.0)
    trvs.report("climate.living", "heating", 20.0)
    await _steps(hass, freezer)
    assert _on(hass, BOILER)
    assert office.topped_up
    trvs.report("climate.office", "heating", 20.9)
    trvs.report("climate.living", "idle", 21.1)
    await _steps(hass, freezer)
    assert not _on(hass, BOILER)
    assert not office.topped_up
    await _unload(hass, entry)


async def test_keep_open_top_up_and_secondary_together(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """All three options at once: the starter stops and is kept open, the boiler
    stops, the topped-up room ends, the secondary room waits."""
    entry, trvs = await _setup(
        hass,
        freezer,
        {
            "Bedroom": {},
            "Office": {"top_up": True},
            "Hall": {"starts_house_source": False},
        },
        keep_last_open=True,
    )
    house = entry.runtime_data
    office, hall = _room(entry, "Office"), _room(entry, "Hall")
    trvs.report("climate.office", "idle", 20.8)
    trvs.report("climate.hall", "heating", 19.0)
    trvs.report("climate.bedroom", "heating", 20.0)
    await _steps(hass, freezer)
    assert _on(hass, BOILER)
    assert office.topped_up
    trvs.report("climate.bedroom", "idle", 21.1)
    await _steps(hass, freezer)
    assert not _on(hass, BOILER)
    assert house.keep_open_room == _room(entry, "Bedroom").id
    assert not office.topped_up
    assert hall.heat_demand
    assert hall.no_heat_reason() == {"code": "secondary"}
    await _unload(hass, entry)


async def test_frost_protection_in_a_pause_opens_and_then_closes_its_circuit(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    entry, _ = await _setup(
        hass,
        freezer,
        {"Bedroom": {"circuit": RADIATORS}, "Living": {"circuit": FLOOR}},
        circuits=[FLOOR, RADIATORS],
    )
    house = entry.runtime_data
    await house.async_set_pause(True)
    await _steps(hass, freezer)
    bedroom = _room(entry, "Bedroom")
    bedroom.heat_demand = True
    bedroom.target_temperature = bedroom.frost_temp()
    await house._async_control_boiler(dt_util.utcnow())
    await hass.async_block_till_done()
    await house._async_control_boiler(dt_util.utcnow())
    await hass.async_block_till_done()
    assert _on(hass, RADIATORS)
    assert _on(hass, BOILER)
    assert not _on(hass, FLOOR)
    # Frost protection ends: the boiler stops, then the circuit opened for it.
    bedroom.heat_demand = False
    await house._async_control_boiler(dt_util.utcnow())
    await hass.async_block_till_done()
    await house._async_control_boiler(dt_util.utcnow())
    await hass.async_block_till_done()
    assert not _on(hass, BOILER)
    assert not _on(hass, RADIATORS)
    await _unload(hass, entry)
