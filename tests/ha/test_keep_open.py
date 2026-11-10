"""Keep the last TRV open: when no room asks for heat any more, the TRVs of the
last room that asked stay open, until another room asks or a stronger rule
takes the room; the room asks for no heat meanwhile and learns nothing."""

from __future__ import annotations

from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import Context, HomeAssistant
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
        # The boiler relay, in the order it is switched (its state follows).
        self.boiler: list[str] = []

        def switch(state: str):
            async def handler(_call) -> None:
                self.boiler.append(state)
                hass.states.async_set("switch.boiler", state)

            return handler

        hass.services.async_register("switch", "turn_on", switch("on"))
        hass.services.async_register("switch", "turn_off", switch("off"))

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
    # The TRV opens and says heating: the room still asks for no heat, the boiler stays off.
    observed.clear()
    trvs.report("climate.bedroom", "heating", 21.2)
    await _tick(hass, freezer, 5)
    assert not bedroom.heat_demand
    assert not house.heat_demand
    assert trvs.boiler[-1] == "off"
    assert hass.states.get("switch.boiler").state == "off"
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
