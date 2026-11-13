"""The limits of the heat demand and of the heat source, one by one.

Written after the mutation run: each test pins a comparison or a default the
other tests let slip (a ``<=`` that could be ``<``, a default that could be the
opposite, a value rounded to the wrong digit).
"""

from __future__ import annotations

from datetime import timedelta

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import Context, HomeAssistant, State
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_mock_service

from tests.ha.test_ha_devices import _house, _room, _tick, _unload

# A TRV that does not report hvac_action: its demand comes from the hysteresis.
TRV = {"hvac_modes": ["heat", "off"], "min_temp": 5.0, "max_temp": 30.0}
ROOM = {
    "source": "climate",
    "command_mode": "temperature",
    "climates": ["climate.bedroom"],
    "hysteresis": 0.5,
}


def _trv(hass: HomeAssistant, current: float | None, target: float = 21.0, state="heat") -> None:
    attrs = {**TRV, "temperature": target}
    if current is not None:
        attrs["current_temperature"] = current
    hass.states.async_set("climate.bedroom", state, attrs, Context())


async def _relays(hass: HomeAssistant, *names: str) -> None:
    async_mock_service(hass, "climate", "set_temperature")
    async_mock_service(hass, "climate", "set_hvac_mode")
    assert await async_setup_component(
        hass, "input_boolean", {"input_boolean": {name: {} for name in names}}
    )


async def test_demand_by_the_hysteresis_of_a_trv_without_hvac_action(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    await _relays(hass, "boiler")
    _trv(hass, 20.6)
    entry = await _house(hass, freezer, [("Bedroom", ROOM)], boiler_entity="input_boolean.boiler")
    room = _room(entry, "Bedroom")
    assert not room.heat_demand  # above 21 − 0.5
    _trv(hass, 20.5)  # exactly the lower limit: asks
    await _tick(hass, freezer, 5)
    assert room.heat_demand
    _trv(hass, 21.4)  # between the limits while asking: keeps asking
    await _tick(hass, freezer, 5)
    assert room.heat_demand
    _trv(hass, 21.5)  # the upper limit: stops
    await _tick(hass, freezer, 5)
    assert not room.heat_demand
    _trv(hass, 21.0)  # between the limits while not asking: does not ask
    await _tick(hass, freezer, 5)
    assert not room.heat_demand
    _trv(hass, 18.0, state="off")  # off: never asks
    await _tick(hass, freezer, 5)
    assert not room.heat_demand
    _trv(hass, 18.0)
    await _tick(hass, freezer, 5)
    assert room.heat_demand
    _trv(hass, None)  # no temperature (while asking): does not ask
    await _tick(hass, freezer, 5)
    assert not room.heat_demand
    await _unload(hass, entry)


async def test_heating_time_counts_only_while_heating(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    await _relays(hass, "boiler")
    _trv(hass, 19.0)
    entry = await _house(hass, freezer, [("Bedroom", ROOM)], boiler_entity="input_boolean.boiler")
    house = entry.runtime_data
    room = _room(entry, "Bedroom")
    await _tick(hass, freezer, 5)
    assert room.heating
    start_room, start_house = room.runtime_s, house.boiler_runtime_s
    await _tick(hass, freezer, 600)
    await _tick(hass, freezer, 5)
    assert room.runtime_s - start_room >= 600
    assert house.boiler_runtime_s - start_house >= 600
    _trv(hass, 22.0)
    await _tick(hass, freezer, 5)
    await _tick(hass, freezer, 5)  # the boiler stopped: evaluated again
    assert not room.heating
    stopped_room, stopped_house = room.runtime_s, house.boiler_runtime_s
    await _tick(hass, freezer, 600)
    await _tick(hass, freezer, 5)
    assert room.runtime_s == stopped_room
    assert house.boiler_runtime_s == stopped_house
    await _unload(hass, entry)


async def test_source_unknown_only_for_a_room_of_the_heat_source(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    await _relays(hass, "boiler")
    _trv(hass, 19.0)
    hass.states.async_set("climate.own", "heat", {**TRV, "temperature": 21.0})
    entry = await _house(
        hass,
        freezer,
        [
            ("Bedroom", ROOM),
            ("Own", {**ROOM, "climates": ["climate.own"], "use_house_source": False}),
        ],
        boiler_entity="input_boolean.boiler",
    )
    hass.states.async_set("input_boolean.boiler", "unavailable")
    await _tick(hass, freezer, 5)
    assert _room(entry, "Bedroom").source_unknown
    assert not _room(entry, "Own").source_unknown
    hass.states.async_set("input_boolean.boiler", "off")
    await _tick(hass, freezer, 5)
    assert not _room(entry, "Bedroom").source_unknown
    await _unload(hass, entry)


async def test_no_room_that_can_start_the_source_never_starts_it(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Only secondary rooms asking (no frost): the boiler stays off."""
    await _relays(hass, "boiler")
    _trv(hass, 19.0)
    entry = await _house(
        hass,
        freezer,
        [("Bedroom", {**ROOM, "starts_house_source": False})],
        boiler_entity="input_boolean.boiler",
    )
    room = _room(entry, "Bedroom")
    await _tick(hass, freezer, 5)
    assert room.heat_demand and not room.starts_house_source
    assert hass.states.get("input_boolean.boiler").state == "off"
    await _unload(hass, entry)


async def test_room_defaults_of_the_heat_source(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    await _relays(hass, "boiler", "floor")
    _trv(hass, 21.0)
    hass.states.async_set("input_boolean.bath", "off")
    room_data = {k: v for k, v in ROOM.items()}
    entry = await _house(
        hass,
        freezer,
        [
            ("Bedroom", room_data),  # no use / starts keys: the defaults
            (
                "Bath",
                {
                    "source": "switch",
                    "switches": ["input_boolean.bath"],
                    "temperature_sensors": ["sensor.bath"],
                    "circuit": "input_boolean.floor",
                },
            ),
            (
                "Own",
                {
                    **ROOM,
                    "climates": ["climate.own"],
                    "use_house_source": False,
                    "circuit": "input_boolean.floor",
                },
            ),
        ],
        boiler_entity="input_boolean.boiler",
        circuits=["input_boolean.floor"],
    )
    bedroom, bath, own = (_room(entry, n) for n in ("Bedroom", "Bath", "Own"))
    assert bedroom.uses_house_source and bedroom.starts_house_source
    assert bedroom.can_keep_open
    # A relay room cannot be kept open; nor a TRV room with its own heat.
    assert bath.uses_house_source and not bath.can_keep_open
    assert not own.can_keep_open and not own.starts_house_source
    # Its own heat: no circuit of the house, even if one is set.
    assert bath.circuit == "input_boolean.floor"
    assert own.circuit is None
    await _unload(hass, entry)


async def test_temperature_gap_and_the_bands(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    await _relays(hass, "boiler")
    hass.states.async_set(
        "sensor.bedroom", "20.123", {"device_class": "temperature", "unit_of_measurement": "°C"}
    )
    _trv(hass, 20.123)
    entry = await _house(
        hass,
        freezer,
        [("Bedroom", {**ROOM, "temperature_sensors": ["sensor.bedroom"], "top_up": True})],
        boiler_entity="input_boolean.boiler",
    )
    room = _room(entry, "Bedroom")
    target = room.target_temperature
    assert target is not None
    room.current_temp = 20.123
    assert room.temperature_gap() == round(target - 20.123, 2)
    assert room.temperature_gap() != round(target - 20.123, 3)

    def at(value: float) -> None:
        room.current_temp = value

    # Kept open: cold enough to ask again exactly at the lower limit.
    at(target - 0.5)
    assert room.keep_open_needs_heat
    at(target - 0.49)
    assert not room.keep_open_needs_heat
    # Topped up: strictly inside the hysteresis, below the target.
    assert room._in_top_up_band()
    at(target - 0.5)
    assert not room._in_top_up_band()
    at(target)
    assert not room._in_top_up_band()
    at(None)  # type: ignore[arg-type]
    assert not room._in_top_up_band()
    assert room.temperature_gap() is None
    assert not room.keep_open_needs_heat
    # Not decided yet: no gap.
    room.current_temp = 18.0
    room.decision = None
    assert room.temperature_gap() is None
    await _unload(hass, entry)


async def test_alerts_exactly_at_the_unavailable_time(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    await _relays(hass, "boiler", "floor")
    _trv(hass, 21.0)
    entry = await _house(
        hass,
        freezer,
        [("Bedroom", {**ROOM, "circuit": "input_boolean.floor"})],
        boiler_entity="input_boolean.boiler",
        circuits=["input_boolean.floor"],
        alert_unavailable_minutes=15,
    )
    house = entry.runtime_data
    hass.states.async_set("input_boolean.boiler", "unavailable")
    hass.states.async_set("input_boolean.floor", "unavailable")
    now = dt_util.utcnow()
    house._check_source_available(now)
    house._check_circuits_available(now)
    later = now + timedelta(minutes=15)
    house._check_source_available(later - timedelta(seconds=1))
    house._check_circuits_available(later - timedelta(seconds=1))
    assert "unavailable_input_boolean.boiler" not in house.notifier.active
    house._check_source_available(later)
    house._check_circuits_available(later)
    active = house.notifier.active
    assert active["unavailable_input_boolean.boiler"]["params"]["minutes"] == 15
    assert active["circuit_unavailable_input_boolean.floor"]["params"]["minutes"] == 15
    # Back: the alerts end.
    hass.states.async_set("input_boolean.boiler", "off")
    hass.states.async_set("input_boolean.floor", "off")
    house._check_source_available(later)
    house._check_circuits_available(later)
    assert "unavailable_input_boolean.boiler" not in house.notifier.active
    assert "circuit_unavailable_input_boolean.floor" not in house.notifier.active
    await _unload(hass, entry)


async def test_boost_of_a_thermostat_source(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    await _relays(hass)
    _trv(hass, 21.0)
    hass.states.async_set("climate.boiler", "heat", {**TRV, "temperature": 7.0})
    entry = await _house(
        hass,
        freezer,
        [("Bedroom", ROOM)],
        boiler_entity="climate.boiler",
        max_temp=25.2,
        frost_temp=7.2,
    )
    house = entry.runtime_data
    attrs = {"hvac_modes": ["heat", "off"], "supported_features": 1, "temperature": 7.0}

    def boost(**extra):
        return house._source_boost(State("climate.boiler", "heat", {**attrs, **extra}))

    # The boost is on by default; without a step: 0.5 °C, inside the limits of the device.
    assert boost() == (25.0, 7.5)
    assert boost(max_temp=24.0) == (24.0, 7.5)
    assert boost(min_temp=8.0) == (25.0, 8.0)
    assert boost(target_temp_step=1.0) == (25.0, 8.0)
    on = State("climate.boiler", "heat", {**attrs, "temperature": 24.95})
    assert house._source_is_on(on, (25.0, 7.5))  # within 0.05
    low = State("climate.boiler", "heat", {**attrs, "temperature": 24.5})
    assert not house._source_is_on(low, (25.0, 7.5))
    off = State("climate.boiler", "off", {**attrs, "temperature": 25.0})
    assert not house._source_is_on(off, (25.0, 7.5))
    idle = State("climate.boiler", "heat", {**attrs, "temperature": 8.0})
    assert not house._source_settled(idle, (25.0, 7.0), False)
    idle = State("climate.boiler", "heat", {**attrs, "temperature": 7.0})
    assert house._source_settled(idle, (25.0, 7.0), False)
    await _unload(hass, entry)


async def test_minimum_off_time_waits_until_its_end(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    await _relays(hass, "boiler")
    _trv(hass, 19.0)
    entry = await _house(
        hass,
        freezer,
        [("Bedroom", ROOM)],
        boiler_entity="input_boolean.boiler",
        boiler_min_off=10,
    )
    house = entry.runtime_data
    await _tick(hass, freezer, 5)
    assert hass.states.get("input_boolean.boiler").state == "on"
    assert not house._frost_started  # started for the rooms, not for frost in a pause
    _trv(hass, 22.0)
    await _tick(hass, freezer, 5)
    assert hass.states.get("input_boolean.boiler").state == "off"
    stopped = house.boiler_changed
    _trv(hass, 19.0)
    await _tick(hass, freezer, 5)
    assert hass.states.get("input_boolean.boiler").state == "off"
    assert house.source_waiting == "min_off"
    assert house._source_wait_until == stopped + timedelta(minutes=10)
    await _unload(hass, entry)


async def test_keep_open_and_top_up_report_their_changes(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """_update_keep_open / _update_top_up return True only when something changed."""
    await _relays(hass, "boiler")
    _trv(hass, 21.0)
    entry = await _house(
        hass,
        freezer,
        [("Bedroom", {**ROOM, "top_up": True})],
        boiler_entity="input_boolean.boiler",
        keep_last_open=True,
    )
    house = entry.runtime_data
    room = _room(entry, "Bedroom")
    await _tick(hass, freezer, 5)
    # Nobody asks, nobody asked: nothing to change, again and again.
    assert house.keep_open_room is None
    assert house._update_keep_open() is False
    assert house._update_keep_open() is False
    # Asking: remembered, not yet kept open.
    room.heat_demand = True
    assert house._update_keep_open() is False
    # The boiler off: nobody topped up, nothing changed.
    assert house._update_top_up() is False
    await _unload(hass, entry)


async def test_after_frost_protection_in_a_pause_the_thermostat_is_left_alone(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """A boosted thermostat started for frost in a pause, then stopped: set by hand, it stays."""
    temps = async_mock_service(hass, "climate", "set_temperature")
    async_mock_service(hass, "climate", "set_hvac_mode")
    source = {"hvac_modes": ["heat", "off"], "supported_features": 1, "min_temp": 5.0}
    hass.states.async_set("climate.boiler", "heat", {**source, "temperature": 7.0})
    cold = {**TRV, "temperature": 7.0, "current_temperature": 5.0}
    hass.states.async_set("climate.bedroom", "heat", {**cold, "hvac_action": "heating"})
    entry = await _house(
        hass, freezer, [("Bedroom", ROOM)], boiler_entity="climate.boiler", frost_temp=7.0
    )
    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": "switch.home_pause"}, blocking=True
    )
    await _tick(hass, freezer, 5)
    sent = [c.data["temperature"] for c in temps if c.data["entity_id"] == "climate.boiler"]
    assert sent[-1] == 25.0  # started for frost protection
    hass.states.async_set("climate.boiler", "heat", {**source, "temperature": 25.0})
    hass.states.async_set(
        "climate.bedroom", "heat", {**cold, "current_temperature": 9.0, "hvac_action": "idle"}
    )
    await _tick(hass, freezer, 5)
    sent = [c.data["temperature"] for c in temps if c.data["entity_id"] == "climate.boiler"]
    assert sent[-1] == 7.0  # stopped again
    assert not entry.runtime_data._frost_started
    hass.states.async_set("climate.boiler", "heat", {**source, "temperature": 7.0})
    await _tick(hass, freezer, 5)
    # Set by hand in the pause: left alone.
    count = len(temps)
    hass.states.async_set("climate.boiler", "heat", {**source, "temperature": 22.0}, Context())
    await _tick(hass, freezer, 5)
    await _tick(hass, freezer, 65)
    assert len(temps) == count
    await _unload(hass, entry)
