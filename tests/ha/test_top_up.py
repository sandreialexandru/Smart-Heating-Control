"""Top up while the heat source runs: a room a little below its target (inside
its hysteresis, so not asking yet) heats up to it while the boiler runs for
other rooms; it asks for no heat meanwhile, so it never starts nor holds the
boiler."""

from __future__ import annotations

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import Context, HomeAssistant
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


class Trvs:
    """TRV rooms and the temperatures they are sent."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self.temperature = async_mock_service(hass, "climate", "set_temperature")
        async_mock_service(hass, "climate", "set_hvac_mode")

    def sent(self, entity_id: str) -> float | None:
        for call in reversed(self.temperature):
            if call.data["entity_id"] == entity_id:
                return call.data["temperature"]
        return None

    def report(self, entity_id: str, action: str, current: float) -> None:
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
    top_up: bool = True,
    boiler: str = "input_boolean.boiler",
    **office,
):
    trvs = Trvs(hass)
    assert await async_setup_component(
        hass, "input_boolean", {"input_boolean": {"boiler": {}, "floor": {}}}
    )
    for entity_id in ("climate.bedroom", "climate.office"):
        hass.states.async_set(
            entity_id, "heat", {**TRV, "temperature": 17.0, "hvac_action": "idle"}
        )
    entry = await _house(
        hass,
        freezer,
        [
            ("Bedroom", {**ROOM, "climates": ["climate.bedroom"]}),
            ("Office", {**ROOM, "climates": ["climate.office"], "top_up": top_up, **office}),
        ],
        boiler_entity=boiler,
        **({"circuits": ["input_boolean.floor"]} if "circuit" in office else {}),
    )
    return entry, trvs


async def _steps(hass: HomeAssistant, freezer: FrozenDateTimeFactory, n: int = 3) -> None:
    for _ in range(n):
        await _tick(hass, freezer, 5)


def _on(hass: HomeAssistant, entity_id: str) -> bool:
    return hass.states.get(entity_id).state == "on"


async def test_topped_up_while_the_boiler_runs_for_another_room(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    entry, trvs = await _setup(hass, freezer)
    house = entry.runtime_data
    office = _room(entry, "Office")
    # The office is just below its target (21, hysteresis 0.3): it does not ask.
    trvs.report("climate.office", "idle", 20.8)
    await _steps(hass, freezer)
    assert not office.topped_up
    assert trvs.sent("climate.office") == 21.0
    # The bedroom asks: the boiler starts, the office is topped up (the house maximum).
    trvs.report("climate.bedroom", "heating", 20.0)
    await _steps(hass, freezer)
    assert _on(hass, "input_boolean.boiler")
    assert office.id in house.top_up_rooms
    assert office.topped_up
    assert trvs.sent("climate.office") == 25.0
    decision = hass.states.get("sensor.office_decision")
    assert decision.attributes["reason_key"] == "top_up"
    assert decision.attributes["target_temperature"] == 21.0
    # Its TRV opens and says heating: the office still asks for no heat.
    trvs.report("climate.office", "heating", 20.9)
    await _steps(hass, freezer)
    assert not office.heat_demand
    # The bedroom is warm: the boiler stops, the office is no longer topped up.
    trvs.report("climate.bedroom", "idle", 21.1)
    await _steps(hass, freezer)
    assert not _on(hass, "input_boolean.boiler")
    assert not office.topped_up
    assert trvs.sent("climate.office") == 21.0
    # Its TRV still heats inside the hysteresis: it does not start the boiler again.
    await _steps(hass, freezer)
    assert not office.heat_demand
    assert not _on(hass, "input_boolean.boiler")
    # Below the hysteresis it asks for heat itself.
    trvs.report("climate.office", "heating", 20.6)
    await _steps(hass, freezer)
    assert office.heat_demand
    assert _on(hass, "input_boolean.boiler")
    await _unload(hass, entry)


async def test_stops_at_the_target(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    entry, trvs = await _setup(hass, freezer)
    office = _room(entry, "Office")
    trvs.report("climate.office", "idle", 20.8)
    trvs.report("climate.bedroom", "heating", 20.0)
    await _steps(hass, freezer)
    assert office.topped_up
    trvs.report("climate.office", "heating", 21.0)
    await _steps(hass, freezer)
    assert not office.topped_up
    assert trvs.sent("climate.office") == 21.0
    # The boiler still runs for the bedroom.
    assert _on(hass, "input_boolean.boiler")
    await _unload(hass, entry)


async def test_never_starts_the_boiler(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    entry, trvs = await _setup(hass, freezer)
    trvs.report("climate.bedroom", "idle", 21.2)
    trvs.report("climate.office", "idle", 20.8)
    await _steps(hass, freezer)
    assert not _on(hass, "input_boolean.boiler")
    assert not _room(entry, "Office").topped_up
    assert not entry.runtime_data.top_up_rooms
    await _unload(hass, entry)


async def test_below_the_hysteresis_the_room_asks_itself(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    entry, trvs = await _setup(hass, freezer)
    office = _room(entry, "Office")
    trvs.report("climate.bedroom", "heating", 20.0)
    trvs.report("climate.office", "heating", 20.5)
    await _steps(hass, freezer)
    assert not office.topped_up
    assert office.heat_demand
    assert trvs.sent("climate.office") == 21.0
    await _unload(hass, entry)


async def test_off_by_default(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    entry, trvs = await _setup(hass, freezer, top_up=False)
    trvs.report("climate.office", "idle", 20.8)
    trvs.report("climate.bedroom", "heating", 20.0)
    await _steps(hass, freezer)
    assert _on(hass, "input_boolean.boiler")
    assert not _room(entry, "Office").topped_up
    assert trvs.sent("climate.office") == 21.0
    await _unload(hass, entry)


async def test_a_manual_change_is_not_topped_up(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    entry, trvs = await _setup(hass, freezer)
    office = _room(entry, "Office")
    await hass.services.async_call(
        "advanced_climate",
        "set_override",
        {"room": office.id, "temperature": 21.0, "duration_hours": 1},
        blocking=True,
    )
    trvs.report("climate.office", "idle", 20.8)
    trvs.report("climate.bedroom", "heating", 20.0)
    await _steps(hass, freezer)
    assert _on(hass, "input_boolean.boiler")
    assert not office.topped_up
    assert trvs.sent("climate.office") == 21.0
    await _unload(hass, entry)


async def test_only_while_its_circuit_is_open(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """The office is on a circuit no room opened: not topped up (no pump for it)."""
    entry, trvs = await _setup(hass, freezer, circuit="input_boolean.floor")
    office = _room(entry, "Office")
    trvs.report("climate.office", "idle", 20.8)
    trvs.report("climate.bedroom", "heating", 20.0)
    await _steps(hass, freezer)
    assert _on(hass, "input_boolean.boiler")
    assert not _on(hass, "input_boolean.floor")
    assert not office.topped_up
    await _unload(hass, entry)


async def test_a_relay_room_is_topped_up(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """A zone valve relay with the room sensor: on while topped up, off at the target."""
    trvs = Trvs(hass)
    assert await async_setup_component(
        hass, "input_boolean", {"input_boolean": {"boiler": {}, "valve": {}}}
    )
    sensor = {"unit_of_measurement": "°C", "device_class": "temperature"}
    hass.states.async_set("sensor.office_temp", "20.8", sensor)
    hass.states.async_set(
        "climate.bedroom", "heat", {**TRV, "temperature": 21.0, "hvac_action": "idle"}
    )
    entry = await _house(
        hass,
        freezer,
        [
            ("Bedroom", {**ROOM, "climates": ["climate.bedroom"]}),
            (
                "Office",
                {
                    "source": "switch",
                    "switches": ["input_boolean.valve"],
                    "temperature_sensors": ["sensor.office_temp"],
                    "top_up": True,
                },
            ),
        ],
        boiler_entity="input_boolean.boiler",
    )
    office = _room(entry, "Office")
    await _steps(hass, freezer)
    assert not _on(hass, "input_boolean.valve")
    trvs.report("climate.bedroom", "heating", 20.0)
    await _steps(hass, freezer)
    assert _on(hass, "input_boolean.boiler")
    assert office.topped_up
    assert _on(hass, "input_boolean.valve")
    assert not office.heat_demand
    hass.states.async_set("sensor.office_temp", "21.0", sensor)
    await _steps(hass, freezer)
    assert not office.topped_up
    assert not _on(hass, "input_boolean.valve")
    await _unload(hass, entry)
