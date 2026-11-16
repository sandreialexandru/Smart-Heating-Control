"""Found by the mutation run on the code of 2.6.5rc27: branches of the new code
no test noticed when changed. Each test names the behaviour it keeps."""

from __future__ import annotations

import math

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant, ServiceCall, callback

from tests.ha.test_ha_devices import _house, _room, _tick, _unload
from tests.ha.test_ha_setup import _learned_cast_iron, _setup

E = "climate.trv"


def _responding(hass: HomeAssistant, keeps_preset_with_temperature: bool = False):
    """A thermostat with presets that answers at once; returns the calls."""
    calls: list[tuple[str, object]] = []

    @callback
    def _temp(call: ServiceCall) -> None:
        calls.append(("temperature", call.data["temperature"]))
        st = hass.states.get(E)
        attrs = {**st.attributes, "temperature": call.data["temperature"]}
        if not keeps_preset_with_temperature and "none" in (attrs.get("preset_modes") or []):
            attrs["preset_mode"] = "none"
        hass.states.async_set(E, st.state, attrs, context=call.context)

    @callback
    def _preset(call: ServiceCall) -> None:
        calls.append(("preset", call.data["preset_mode"]))
        st = hass.states.get(E)
        attrs = {**st.attributes, "preset_mode": call.data["preset_mode"]}
        hass.states.async_set(E, st.state, attrs, context=call.context)

    @callback
    def _mode(call: ServiceCall) -> None:
        calls.append(("mode", call.data["hvac_mode"]))
        st = hass.states.get(E)
        hass.states.async_set(E, call.data["hvac_mode"], st.attributes, context=call.context)

    hass.services.async_register("climate", "set_temperature", _temp)
    hass.services.async_register("climate", "set_preset_mode", _preset)
    hass.services.async_register("climate", "set_hvac_mode", _mode)
    return calls


def _device(hass: HomeAssistant, **attrs) -> None:
    hass.states.async_set(
        E,
        "heat",
        {
            "hvac_modes": ["heat", "off"],
            "current_temperature": 20.0,
            "temperature": 20.0,
            "min_temp": 7,
            "max_temp": 30,
            **attrs,
        },
    )


PRESET_ROOM = {
    "source": "climate",
    "climates": [E],
    "command_mode": "preset",
    "preset_map": {
        "home": "comfort",
        "comfort": "comfort",
        "eco": "eco",
        "sleep": "eco",
        "away": "away",
    },
}


# ------------------------------------------------- on the preset of another level
async def test_left_on_away_a_level_with_its_own_preset_gets_that_preset(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """On away after a vacation, the level has a preset of its own (comfort):
    that one is sent directly, the device is not taken to none first."""
    calls = _responding(hass)
    _device(hass, preset_modes=["none", "comfort", "eco", "away"], preset_mode="away")
    entry = await _house(hass, freezer, [("Office", PRESET_ROOM)])
    for _ in range(10):
        await _tick(hass, freezer, 60)
    presets = [v for k, v in calls if k == "preset"]
    assert presets == ["comfort"], calls
    assert hass.states.get(E).attributes["preset_mode"] == "comfort"
    await _unload(hass, entry)


async def test_commanded_by_temperature_a_preset_of_the_device_is_not_left(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """With the Temperature command, a device on its away preset is not taken off
    it by SHC (only the Preset command uses the presets of the levels)."""
    calls = _responding(hass, keeps_preset_with_temperature=True)
    _device(hass, preset_modes=["none", "away"], preset_mode="away")
    room = {"source": "climate", "climates": [E], "command_mode": "temperature"}
    entry = await _house(hass, freezer, [("Office", room)])
    for _ in range(10):
        await _tick(hass, freezer, 60)
    assert ("preset", "none") not in calls, calls
    await _unload(hass, entry)


# ------------------------------------------------- a preset already held
async def test_a_preset_already_held_is_not_sent_again(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """On the preset of the level (comfort), whatever its own temperature for it:
    nothing is sent, neither the preset nor a temperature, for hours."""
    calls = _responding(hass)
    _device(
        hass, preset_modes=["none", "comfort", "eco", "away"], preset_mode="comfort", temperature=19
    )
    entry = await _house(hass, freezer, [("Office", PRESET_ROOM)])
    for _ in range(36):
        await _tick(hass, freezer, 300)
    assert calls == []
    assert _room(entry, "Office").decision.rule != "manual_override"
    await _unload(hass, entry)


# ------------------------------------------------- the temperature known for a preset
async def test_after_the_window_the_preset_and_its_temperature_are_sent_once(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """A device that keeps its preset when sent a temperature (no off mode): after
    the window, the preset and the temperature known for it are sent once; that
    temperature does not mark the preset to be sent again."""
    calls = _responding(hass, keeps_preset_with_temperature=True)
    hass.states.async_set("binary_sensor.window", "off")
    hass.states.async_set(
        E,
        "heat",
        {
            "hvac_modes": ["heat"],
            "preset_modes": ["comfort", "eco", "away"],
            "preset_mode": "comfort",
            "temperature": 21.0,
            "current_temperature": 20.0,
            "min_temp": 7.0,
            "max_temp": 30.0,
        },
    )
    room_cfg = {**PRESET_ROOM, "window_sensors": ["binary_sensor.window"]}
    entry = await _house(hass, freezer, [("Office", room_cfg)])
    await _tick(hass, freezer, 5)
    room = _room(entry, "Office")
    hass.states.async_set(E, "heat", {**hass.states.get(E).attributes, "current_temperature": 20.1})
    await _tick(hass, freezer, 5)
    assert room.observed_temps.get("home") == 21.0
    hass.states.async_set("binary_sensor.window", "on")
    for _ in range(4):
        await _tick(hass, freezer, 60)
    sent = len(calls)
    hass.states.async_set("binary_sensor.window", "off")
    for _ in range(12):
        await _tick(hass, freezer, 300)
    after = calls[sent:]
    assert after.count(("preset", "comfort")) == 1, after
    assert after.count(("temperature", 21.0)) == 1, after
    assert room.preset_stale == {}
    await _unload(hass, entry)


# ------------------------------------------------- the stop by the learned inertia
async def test_the_stop_by_the_inertia_is_shown_and_cleared_when_heating_again(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """A relay room with cast iron radiators: stopped early by the learned inertia,
    the card is told why (inertia, with the peak expected); once it heats again
    that reason is gone."""
    hass.states.async_set("sensor.room_temp", "20.5", {"unit_of_measurement": "°C"})
    entry = await _setup(hass, freezer)
    room = next(iter(entry.runtime_data.rooms.values()))
    room.learner = _learned_cast_iron()
    temp, q = 20.5, 0.0
    seen_stop = told = False
    cleared_on_heating = None
    for _ in range(8 * 60):
        on = hass.states.get("input_boolean.heater").state == "on"
        u = 1.0 if on else 0.0
        q = u + (q - u) * math.exp(-1 / 60)
        temp += (2.0 * q - 0.05 * (temp - 5.0)) / 60
        hass.states.async_set(
            "sensor.room_temp", str(round(temp, 1)), {"unit_of_measurement": "°C"}
        )
        await _tick(hass, freezer, 60)
        reason = hass.states.get("sensor.bedroom_decision").attributes.get("no_heat_reason")
        if room.inertia_stop is not None:
            seen_stop = True
            assert hass.states.get("input_boolean.heater").state == "off"
            if reason and reason["code"] == "inertia":
                told = True
        if seen_stop and hass.states.get("input_boolean.heater").state == "on":
            cleared_on_heating = room.inertia_stop is None
            break
    assert seen_stop
    assert told
    assert cleared_on_heating is True
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


# ------------------------------------------------- the brake on command loops
async def test_the_brake_tells_how_many_commands_it_counted(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """The alert of the brake gives the number of commands in the window (the
    one that tripped it not counted), the window and the pause in minutes."""
    from custom_components.advanced_climate import room_devices

    _responding(hass)
    _device(hass)
    room = {"source": "climate", "climates": [E], "command_mode": "temperature"}
    entry = await _house(hass, freezer, [("Office", room)])
    office = _room(entry, "Office")
    office.command_times.pop(E, None)
    told: dict = {}
    house = entry.runtime_data
    notify = house.notify

    def _notify(key, message, **kwargs):
        told[key] = kwargs.get("params")
        notify(key, message, **kwargs)

    house.notify = _notify
    for _ in range(room_devices.COMMAND_LIMIT):
        assert office._command_allowed(E)
    assert not office._command_allowed(E)
    params = told[f"commands_{E}"]
    assert params["count"] == room_devices.COMMAND_LIMIT
    assert params["window"] == round(room_devices.COMMAND_WINDOW.total_seconds() / 60)
    assert params["pause"] == round(room_devices.COMMAND_PAUSE.total_seconds() / 60)
    await _unload(hass, entry)
