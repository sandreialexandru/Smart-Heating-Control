"""Keep the last TRV open: when no room asks for heat any more, the TRVs of the
last room that asked stay open, until another room asks or a stronger rule
takes the room; the room asks for no heat meanwhile and learns nothing."""

from __future__ import annotations

from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import Context, HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.advanced_climate.learning import ThermalLearner
from tests.ha.test_ha_devices import _house, _room, _tick, _unload

TRV = {
    "hvac_modes": ["heat", "off"],
    "current_temperature": 20.0,
    "min_temp": 5.0,
    "max_temp": 30.0,
}
ROOM = {"source": "climate", "command_mode": "temperature"}


class Trvs:
    """Two TRV rooms (Bedroom, Office) and a boiler relay; the calls they get."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self.temperature = async_mock_service(hass, "climate", "set_temperature")
        async_mock_service(hass, "climate", "set_hvac_mode")

    def sent(self, entity_id: str) -> float | None:
        """The last temperature sent to a TRV."""
        for call in reversed(self.temperature):
            if call.data["entity_id"] == entity_id:
                return call.data["temperature"]
        return None

    def report(self, entity_id: str, action: str, current: float = 20.0) -> None:
        """The TRV reports what it does, holding the temperature it was sent."""
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


async def _setup(hass: HomeAssistant, freezer: FrozenDateTimeFactory, keep: bool = True):
    trvs = Trvs(hass)
    hass.states.async_set("switch.boiler", "on")
    for entity_id in ("climate.bedroom", "climate.office"):
        hass.states.async_set(
            entity_id, "heat", {**TRV, "temperature": 17.0, "hvac_action": "idle"}
        )
    entry = await _house(
        hass,
        freezer,
        [
            ("Bedroom", {**ROOM, "climates": ["climate.bedroom"]}),
            ("Office", {**ROOM, "climates": ["climate.office"]}),
        ],
        boiler_entity="switch.boiler",
        keep_last_open=keep,
    )
    return entry, trvs


async def _bedroom_heats_then_stops(hass, freezer, trvs: Trvs) -> None:
    """The bedroom asks for heat (the office does not), then reaches its target."""
    trvs.report("climate.office", "idle")
    trvs.report("climate.bedroom", "heating", 20.0)
    await _tick(hass, freezer, 5)
    trvs.report("climate.bedroom", "idle", 21.1)
    await _tick(hass, freezer, 5)
    await _tick(hass, freezer, 2)


async def test_the_last_room_stays_open_and_asks_for_no_heat(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    entry, trvs = await _setup(hass, freezer)
    bedroom = _room(entry, "Bedroom")
    observed: list[bool] = []
    original = ThermalLearner.observe

    def spy(self, *args, **kwargs):
        if self is bedroom.learner:
            observed.append(args[4])  # disturbed
        return original(self, *args, **kwargs)

    patcher = patch.object(ThermalLearner, "observe", spy)
    patcher.start()
    await _bedroom_heats_then_stops(hass, freezer, trvs)
    house = entry.runtime_data
    assert house.keep_open_room == bedroom.id
    assert bedroom.kept_open
    # The TRV gets the maximum of the room (the house maximum, 25, below the TRV's 30).
    assert trvs.sent("climate.bedroom") == 25.0
    # Its target stays the one of the schedule; the reason says why it is open.
    decision = hass.states.get("sensor.bedroom_decision")
    assert decision.attributes["reason_key"] == "keep_open"
    assert decision.attributes["target_temperature"] == 21.0
    # The TRV opens and says heating: the room still asks for no heat, the house neither.
    observed.clear()
    trvs.report("climate.bedroom", "heating", 21.2)
    await _tick(hass, freezer, 5)
    assert not bedroom.heat_demand
    assert not house.heat_demand
    # Its learning skips that time.
    assert observed and all(observed)
    patcher.stop()
    await _unload(hass, entry)


async def test_another_room_asks_and_the_last_one_closes(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    entry, trvs = await _setup(hass, freezer)
    await _bedroom_heats_then_stops(hass, freezer, trvs)
    house = entry.runtime_data
    assert house.keep_open_room == _room(entry, "Bedroom").id
    # The TRV holds the maximum it got, then the office asks for heat.
    trvs.report("climate.bedroom", "heating", 21.2)
    await _tick(hass, freezer, 5)
    trvs.report("climate.office", "heating", 19.0)
    await _tick(hass, freezer, 5)
    await _tick(hass, freezer, 2)
    assert house.keep_open_room is None
    assert not _room(entry, "Bedroom").kept_open
    assert trvs.sent("climate.bedroom") == 21.0
    assert house.heat_demand
    await _unload(hass, entry)


async def test_a_manual_change_ends_it(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    entry, trvs = await _setup(hass, freezer)
    await _bedroom_heats_then_stops(hass, freezer, trvs)
    bedroom = _room(entry, "Bedroom")
    assert bedroom.kept_open
    await hass.services.async_call(
        "advanced_climate",
        "set_override",
        {"room": bedroom.id, "temperature": 19.0, "duration_hours": 1},
        blocking=True,
    )
    await _tick(hass, freezer, 2)
    await _tick(hass, freezer, 2)
    assert entry.runtime_data.keep_open_room is None
    assert not bedroom.kept_open
    await _unload(hass, entry)


async def test_the_room_cold_again_asks_for_heat_itself(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    entry, trvs = await _setup(hass, freezer)
    await _bedroom_heats_then_stops(hass, freezer, trvs)
    bedroom = _room(entry, "Bedroom")
    assert bedroom.kept_open
    # Below its target by the hysteresis: no longer kept open, its target is sent.
    trvs.report("climate.bedroom", "heating", 20.0)
    await _tick(hass, freezer, 5)
    await _tick(hass, freezer, 2)
    assert entry.runtime_data.keep_open_room is None
    assert trvs.sent("climate.bedroom") == 21.0
    await _unload(hass, entry)


async def test_off_by_default(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    entry, trvs = await _setup(hass, freezer, keep=False)
    await _bedroom_heats_then_stops(hass, freezer, trvs)
    assert entry.runtime_data.keep_open_room is None
    assert trvs.sent("climate.bedroom") == 21.0
    await _unload(hass, entry)


async def test_an_on_off_trv_kept_open_does_not_go_on_heating_after(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """On / off TRV: on only to be kept open; once that ends it is not left on in the band."""
    hvac = async_mock_service(hass, "climate", "set_hvac_mode")
    async_mock_service(hass, "climate", "set_temperature")
    sensor = {"unit_of_measurement": "°C", "device_class": "temperature"}
    hass.states.async_set("switch.boiler", "on")
    hass.states.async_set("sensor.bedroom_temp", "20.0", sensor)
    hass.states.async_set("climate.bedroom", "off", {**TRV, "temperature": 21.0})
    hass.states.async_set(
        "climate.office", "heat", {**TRV, "temperature": 17.0, "hvac_action": "idle"}
    )
    entry = await _house(
        hass,
        freezer,
        [
            (
                "Bedroom",
                {
                    "source": "climate",
                    "command_mode": "hvac_mode",
                    "climates": ["climate.bedroom"],
                    "temperature_sensors": ["sensor.bedroom_temp"],
                    "min_on_minutes": 10,
                },
            ),
            ("Office", {**ROOM, "climates": ["climate.office"]}),
        ],
        boiler_entity="switch.boiler",
        keep_last_open=True,
    )
    bedroom = _room(entry, "Bedroom")

    def last(entity_id: str) -> str | None:
        calls = [c.data["hvac_mode"] for c in hvac if c.data["entity_id"] == entity_id]
        return calls[-1] if calls else None

    async def trv(state: str) -> None:
        hass.states.async_set("climate.bedroom", state, {**TRV, "temperature": 21.0}, Context())
        await _tick(hass, freezer, 5)

    # Below the band: on, asks for heat.
    assert last("climate.bedroom") == "heat"
    await trv("heat")
    assert bedroom.heat_demand
    # Above it (after its minimum on time): off; nobody asks any more, so it is
    # turned on again to be kept open.
    await _tick(hass, freezer, 601)
    hass.states.async_set("sensor.bedroom_temp", "21.4", sensor)
    await _tick(hass, freezer, 5)
    assert last("climate.bedroom") == "off"
    await trv("off")
    await _tick(hass, freezer, 2)
    assert bedroom.kept_open
    assert last("climate.bedroom") == "heat"
    await trv("heat")
    assert not bedroom.heat_demand
    # The office asks; the bedroom (21.0, inside the band) is turned off at once,
    # without its minimum on time and without asking for heat.
    hass.states.async_set("sensor.bedroom_temp", "21.0", sensor)
    hass.states.async_set(
        "climate.office", "heat", {**TRV, "temperature": 21.0, "hvac_action": "heating"}, Context()
    )
    await _tick(hass, freezer, 5)
    await _tick(hass, freezer, 2)
    assert not bedroom.kept_open
    assert last("climate.bedroom") == "off"
    assert not bedroom.heat_demand
    await _unload(hass, entry)


async def test_a_secondary_room_neither_starts_the_boiler_nor_ends_the_room_kept_open(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    trvs = Trvs(hass)
    hass.states.async_set("switch.boiler", "on")
    for entity_id in ("climate.bedroom", "climate.office"):
        hass.states.async_set(
            entity_id, "heat", {**TRV, "temperature": 17.0, "hvac_action": "idle"}
        )
    entry = await _house(
        hass,
        freezer,
        [
            ("Bedroom", {**ROOM, "climates": ["climate.bedroom"]}),
            ("Office", {**ROOM, "climates": ["climate.office"], "starts_house_source": False}),
        ],
        boiler_entity="switch.boiler",
        keep_last_open=True,
    )
    house = entry.runtime_data
    office = _room(entry, "Office")
    # The secondary room alone asks: the house asks for no heat.
    trvs.report("climate.bedroom", "idle", 21.1)
    trvs.report("climate.office", "heating", 19.0)
    await _tick(hass, freezer, 5)
    assert office.heat_demand
    assert not house.heat_demand
    assert office.no_heat_reason() in ({"code": "secondary"}, None)
    # The bedroom asks: the house asks for heat, the office takes it too.
    trvs.report("climate.bedroom", "heating", 20.0)
    await _tick(hass, freezer, 5)
    assert house.heat_demand
    # The bedroom stops: it is kept open; the office still asking does not end that.
    trvs.report("climate.bedroom", "idle", 21.1)
    await _tick(hass, freezer, 5)
    await _tick(hass, freezer, 2)
    assert house.keep_open_room == _room(entry, "Bedroom").id
    trvs.report("climate.bedroom", "heating", 21.2)
    trvs.report("climate.office", "heating", 19.0)
    await _tick(hass, freezer, 5)
    assert house.keep_open_room == _room(entry, "Bedroom").id
    assert not house.heat_demand
    # Frost protection of the secondary room starts the boiler, for safety.
    office.heat_demand = True
    office.target_temperature = office.frost_temp()
    assert office.frost_demand
    await house._async_control_boiler(dt_util.utcnow())
    assert house.heat_demand
    await _unload(hass, entry)
