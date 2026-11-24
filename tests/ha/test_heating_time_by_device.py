"""The heating time of a room commanded on / off follows the thermostat (#16).

A real Generic Thermostat with its heater, the room sensor warming while the
heater is on: the time counted is the time the heater was on, whichever way
the room is commanded, and an on / off thermostat already on heats as far as
it can (not at its own lower target).
"""

from __future__ import annotations

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_mock_service

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
    async_mock_service(hass, "climate", "set_hvac_mode")
    async_mock_service(hass, "climate", "set_temperature")
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
    assert all(heating[2:])  # from its first evaluations on
    # Added at each evaluation: the time since the last one is still running.
    assert room._heating_since is not None
    running = (dt_util.utcnow() - room._heating_since).total_seconds()
    assert room.runtime_s + running >= 27 * 60
    await _unload(hass, entry)


# ---------------------------------------------------------------------------
# An on / off thermostat already on: the maximum once, not at each evaluation
# ---------------------------------------------------------------------------
async def _on_off_device(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    attrs: dict,
    on_temperature,
    on_preset,
    command_mode: str = "hvac_mode",
) -> tuple[list, list, object, object]:
    """A thermostat found on, the room cold (19 with a target of 21): returns the
    temperature and preset calls."""
    temps: list = []
    presets: list = []

    @callback
    def _set_temperature(call: ServiceCall) -> None:
        temps.append(call)
        state = hass.states.get("climate.onoff")
        value = on_temperature(state, call.data["temperature"])
        new = {**state.attributes, "temperature": value}
        hass.states.async_set("climate.onoff", state.state, new, context=call.context)

    @callback
    def _set_preset(call: ServiceCall) -> None:
        presets.append(call)
        state = hass.states.get("climate.onoff")
        new = {**state.attributes, "preset_mode": on_preset(call.data["preset_mode"])}
        hass.states.async_set("climate.onoff", state.state, new, context=call.context)

    @callback
    def _set_mode(call: ServiceCall) -> None:
        state = hass.states.get("climate.onoff")
        hass.states.async_set(
            "climate.onoff", call.data["hvac_mode"], state.attributes, context=call.context
        )

    hass.services.async_register("climate", "set_temperature", _set_temperature)
    hass.services.async_register("climate", "set_preset_mode", _set_preset)
    hass.services.async_register("climate", "set_hvac_mode", _set_mode)
    hass.states.async_set("sensor.onoff_room", "19.0", SENSOR)
    hass.states.async_set(
        "climate.onoff",
        "heat",
        {
            "hvac_modes": ["heat", "off"],
            "current_temperature": 19.0,
            "min_temp": 5,
            "max_temp": 30,
            **attrs,
        },
    )
    entry = await _house(
        hass,
        freezer,
        [
            (
                "Gab",
                {
                    "source": "climate",
                    "command_mode": command_mode,
                    "climates": ["climate.onoff"],
                    "temperature_sensors": ["sensor.onoff_room"],
                },
            )
        ],
    )
    for _ in range(48):  # four hours, the room still cold
        await _tick(hass, freezer, 300)
    return temps, presets, entry, _room(entry, "Gab")


async def test_temperature_on_off_sends_room_target_and_turns_off_when_warm(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    temps, _, entry, room = await _on_off_device(
        hass,
        freezer,
        {"temperature": 17.0},
        lambda _, value: value,
        lambda preset: preset,
        command_mode="temperature_on_off",
    )
    assert [c.data["temperature"] for c in temps] == [21.0]
    await room.async_set_level("home", 22.0)
    await _tick(hass, freezer, 300)
    assert [c.data["temperature"] for c in temps] == [21.0, 22.0]
    hass.states.async_set("sensor.onoff_room", "23.0", SENSOR)
    await _tick(hass, freezer, 300)
    assert hass.states.get("climate.onoff").state == "off"
    hass.states.async_set("sensor.onoff_room", "19.0", SENSOR)
    await _tick(hass, freezer, 300)
    assert hass.states.get("climate.onoff").state == "heat"
    assert hass.states.get("climate.onoff").attributes["temperature"] == 22.0
    await _unload(hass, entry)


async def test_an_on_off_thermostat_with_its_own_limit_gets_the_maximum_once(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """It reports a maximum of 30 but keeps 22: not sent 25 again and again."""
    temps, _presets, entry, _r = await _on_off_device(
        hass,
        freezer,
        {"temperature": 20.0},
        lambda state, value: min(value, 22.0),
        lambda preset: preset,
    )
    assert len(temps) == 1
    assert hass.states.get("climate.onoff").attributes["temperature"] == 22.0
    await _unload(hass, entry)


async def test_an_on_off_thermostat_on_its_schedule_preset_is_put_on_manual_once(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """On its schedule preset it ignores the temperature: put on manual, then it
    takes the maximum; nothing sent again and again."""

    def on_temperature(state, value):
        on_schedule = state.attributes.get("preset_mode") == "schedule"
        return state.attributes["temperature"] if on_schedule else value

    temps, presets, entry, room = await _on_off_device(
        hass,
        freezer,
        {"temperature": 18.0, "preset_modes": ["schedule", "manual"], "preset_mode": "schedule"},
        on_temperature,
        lambda preset: preset,
    )
    state = hass.states.get("climate.onoff")
    assert [c.data["preset_mode"] for c in presets] == ["manual"]
    assert state.attributes["preset_mode"] == "manual"
    assert state.attributes["temperature"] == room.max_temp()
    assert len(temps) == 1
    await _unload(hass, entry)


async def test_an_on_off_thermostat_that_ignores_the_temperature_is_not_sent_it_forever(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """On its schedule preset, without manual, it keeps its own target: sent once."""
    temps, presets, entry, _r = await _on_off_device(
        hass,
        freezer,
        {"temperature": 18.0, "preset_modes": ["schedule", "eco"], "preset_mode": "schedule"},
        lambda state, value: state.attributes["temperature"],
        lambda preset: preset,
    )
    assert not presets
    assert len(temps) == 1
    await _unload(hass, entry)


async def test_a_change_on_the_on_off_thermostat_gets_the_maximum_again(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Turned off, it is forgotten: turned on again, it gets the maximum again."""
    temps, _presets, entry, room = await _on_off_device(
        hass,
        freezer,
        {"temperature": 20.0},
        lambda state, value: value,
        lambda preset: preset,
    )
    assert len(temps) == 1
    # The room warms: turned off; cold again: turned on, the maximum once more.
    hass.states.async_set("sensor.onoff_room", "23.0", SENSOR)
    for _ in range(3):
        await _tick(hass, freezer, 300)
    assert hass.states.get("climate.onoff").state == "off"
    assert "climate.onoff" not in room.on_setpoints
    hass.states.async_set("sensor.onoff_room", "19.0", SENSOR)
    for _ in range(6):
        await _tick(hass, freezer, 300)
    assert hass.states.get("climate.onoff").state == "heat"
    assert "climate.onoff" in room.on_setpoints
    assert hass.states.get("climate.onoff").attributes["temperature"] == room.max_temp()
    await _unload(hass, entry)


# ---------------------------------------------------------------------------
# hvac_action trusted only once seen heating
# ---------------------------------------------------------------------------
async def test_an_hvac_action_stuck_on_idle_does_not_stop_the_heating_time(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """It always says idle: the heating time follows the on / off decision, as
    before, and the thermostat is not trusted."""
    _temps, _presets, entry, room = await _on_off_device(
        hass,
        freezer,
        {"temperature": 20.0, "hvac_action": "idle"},
        lambda state, value: value,
        lambda preset: preset,
    )
    assert room.heating
    assert room.runtime_s >= 3.5 * 3600
    assert "climate.onoff" not in room.reports_heating
    await _unload(hass, entry)


async def test_seen_heating_is_saved(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, hass_storage: dict
) -> None:
    """Once it reported heating it is trusted, also after a restart; forgotten when
    the room is reconfigured."""
    _temps, _presets, entry, room = await _on_off_device(
        hass,
        freezer,
        {"temperature": 20.0, "hvac_action": "heating"},
        lambda state, value: value,
        lambda preset: preset,
    )
    assert "climate.onoff" in room.reports_heating
    await _tick(hass, freezer, 60)
    saved = next(v for k, v in hass_storage.items() if k.startswith("advanced_climate."))["data"][
        "rooms"
    ]
    assert any("climate.onoff" in r.get("reports_heating", []) for r in saved.values())
    room.forget_auto_returns()
    assert not room.reports_heating
    await _unload(hass, entry)
