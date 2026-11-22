"""Found by a review of 2.6.5rc20 with simulated devices: each case as it was,
and as it is now."""

from __future__ import annotations

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import Context, HomeAssistant, ServiceCall, callback
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_mock_service

from tests.ha.test_ha_devices import _house, _room, _tick, _unload

E = "climate.trv"


# ---------------------------------------------------------------- 1. preset
async def test_a_preset_kept_with_a_temperature_is_sent_again(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """A thermostat commanded by preset, without off, that keeps its preset when
    sent a temperature: after the window it was left at the frost temperature
    on "comfort". Now the preset is sent again, and the temperature known for
    it; that temperature is not learned as the one of the level."""
    temps: list[float] = []
    presets: list[str] = []

    @callback
    def _temp(call: ServiceCall) -> None:
        temps.append(call.data["temperature"])
        st = hass.states.get(E)
        hass.states.async_set(
            E,
            st.state,
            {**st.attributes, "temperature": call.data["temperature"]},
            context=call.context,
        )

    @callback
    def _preset(call: ServiceCall) -> None:
        presets.append(call.data["preset_mode"])
        st = hass.states.get(E)
        # The preset is a mode: its temperature stays the last one set.
        hass.states.async_set(
            E,
            st.state,
            {**st.attributes, "preset_mode": call.data["preset_mode"]},
            context=call.context,
        )

    hass.services.async_register("climate", "set_temperature", _temp)
    hass.services.async_register("climate", "set_preset_mode", _preset)
    hass.states.async_set("binary_sensor.window", "off")
    hass.states.async_set(
        E,
        "heat",
        {
            "hvac_modes": ["heat"],
            "preset_modes": ["comfort", "eco", "sleep", "away", "boost"],
            "preset_mode": "comfort",
            "temperature": 21.0,
            "current_temperature": 20.0,
            "min_temp": 7.0,
            "max_temp": 30.0,
        },
    )
    entry = await _house(
        hass,
        freezer,
        [
            (
                "Office",
                {
                    "source": "climate",
                    "climates": [E],
                    "command_mode": "preset",
                    "preset_map": {
                        "home": "comfort",
                        "comfort": "comfort",
                        "eco": "eco",
                        "sleep": "eco",
                        "away": "eco",
                    },
                    "window_sensors": ["binary_sensor.window"],
                },
            )
        ],
    )
    await _tick(hass, freezer, 5)
    room = _room(entry, "Office")
    # It reports (its room temperature): the temperature of "comfort" is learned.
    hass.states.async_set(E, "heat", {**hass.states.get(E).attributes, "current_temperature": 20.1})
    await _tick(hass, freezer, 5)
    assert room.observed_temps.get("home") == 21.0
    hass.states.async_set("binary_sensor.window", "on")
    for _ in range(4):
        await _tick(hass, freezer, 60)
    assert temps and temps[-1] == 7.0
    assert hass.states.get(E).attributes["preset_mode"] == "comfort"
    # Not learned: "comfort" is still 21.
    assert room.observed_temps.get("home") == 21.0
    hass.states.async_set("binary_sensor.window", "off")
    for _ in range(4):
        await _tick(hass, freezer, 60)
    state = hass.states.get(E)
    assert presets and presets[-1] == "comfort"
    assert state.attributes["temperature"] == 21.0
    assert room.decision.rule != "manual_override"
    assert room.preset_stale == {}
    await _unload(hass, entry)


# ---------------------------------------------------------------- 2. source range
async def _water_source(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, low: float, high: float
):
    calls: list[tuple[str, dict]] = []

    def _reg(service: str) -> None:
        @callback
        def _h(call: ServiceCall) -> None:
            calls.append((service, dict(call.data)))
            st = hass.states.get("climate.boiler")
            attrs = dict(st.attributes)
            state = st.state
            if service == "set_temperature":
                attrs["temperature"] = call.data["temperature"]
                state = call.data.get("hvac_mode", state)
            else:
                state = call.data["hvac_mode"]
            hass.states.async_set("climate.boiler", state, attrs, context=call.context)

        hass.services.async_register("climate", service, _h)

    _reg("set_temperature")
    _reg("set_hvac_mode")
    hass.states.async_set(
        "climate.boiler",
        "off",
        {
            "hvac_modes": ["off", "heat"],
            "temperature": 45.0,
            "min_temp": low,
            "max_temp": high,
            "supported_features": 1,
        },
    )
    async_mock_service(hass, "climate", "set_preset_mode")
    hass.states.async_set(
        E,
        "heat",
        {
            "hvac_modes": ["heat", "off"],
            "temperature": 21.0,
            "hvac_action": "heating",
            "current_temperature": 19.0,
            "min_temp": 5,
            "max_temp": 30,
        },
    )
    entry = await _house(
        hass,
        freezer,
        [("Office", {"source": "climate", "climates": [E], "command_mode": "temperature"})],
        boiler_entity="climate.boiler",
    )
    for _ in range(3):
        await _tick(hass, freezer, 5)
    return entry, calls


async def test_a_heat_source_with_a_water_range_is_switched_by_its_mode(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """30-80 °C: 25 °C was refused again and again; now its mode, and told once."""
    entry, calls = await _water_source(hass, freezer, 30.0, 80.0)
    assert not any(s == "set_temperature" for s, _ in calls)
    assert ("set_hvac_mode", {"entity_id": "climate.boiler", "hvac_mode": "heat"}) in calls
    assert hass.states.get("climate.boiler").state == "heat"
    alert = entry.runtime_data.notifier.active["source_mode_climate.boiler"]
    assert alert["code"] == "source_by_mode"
    assert alert["params"]["range"] == "30–80 °C"
    await _unload(hass, entry)


async def test_a_heat_source_whose_start_and_stop_are_the_same(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """25-60 °C: start and stop both 25, it never heated; now by its mode."""
    entry, calls = await _water_source(hass, freezer, 25.0, 60.0)
    assert hass.states.get("climate.boiler").state == "heat"
    assert not any(s == "set_temperature" for s, _ in calls)
    assert "source_mode_climate.boiler" in entry.runtime_data.notifier.active
    await _unload(hass, entry)


# ---------------------------------------------------------------- 4. on / off
async def test_turned_on_it_gets_the_maximum_of_the_room(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """On / off: its own target (20) closed it before the room (21) was warm."""
    temps = async_mock_service(hass, "climate", "set_temperature")
    async_mock_service(hass, "climate", "set_hvac_mode")
    hass.states.async_set(
        "sensor.room", "19.0", {"unit_of_measurement": "°C", "device_class": "temperature"}
    )
    hass.states.async_set(
        E,
        "off",
        {
            "hvac_modes": ["heat", "off"],
            "temperature": 20.0,
            "min_temp": 5,
            "max_temp": 30,
            "target_temp_step": 0.5,
        },
    )
    entry = await _house(
        hass,
        freezer,
        [
            (
                "Office",
                {
                    "source": "climate",
                    "climates": [E],
                    "command_mode": "hvac_mode",
                    "temperature_sensors": ["sensor.room"],
                },
            )
        ],
    )
    await _tick(hass, freezer, 5)
    room = _room(entry, "Office")
    assert temps and temps[-1].data["temperature"] == room.max_temp() == 25.0
    await _unload(hass, entry)


async def test_turned_on_at_its_maximum_already_gets_no_temperature(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    temps = async_mock_service(hass, "climate", "set_temperature")
    async_mock_service(hass, "climate", "set_hvac_mode")
    hass.states.async_set(
        "sensor.room", "19.0", {"unit_of_measurement": "°C", "device_class": "temperature"}
    )
    hass.states.async_set(
        E,
        "off",
        {"hvac_modes": ["heat", "off"], "temperature": 25.0, "min_temp": 5, "max_temp": 30},
    )
    entry = await _house(
        hass,
        freezer,
        [
            (
                "Office",
                {
                    "source": "climate",
                    "climates": [E],
                    "command_mode": "hvac_mode",
                    "temperature_sensors": ["sensor.room"],
                },
            )
        ],
    )
    await _tick(hass, freezer, 5)
    assert not temps
    await _unload(hass, entry)


# ---------------------------------------------------------------- 6. pending
async def test_not_sent_again_before_the_trv_confirms(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """A TRV that reports the new temperature late: sent once, not at every
    evaluation meanwhile; the verification sends it again if it never does."""
    temps = async_mock_service(hass, "climate", "set_temperature")
    hass.states.async_set(
        E,
        "heat",
        {
            "hvac_modes": ["heat", "off"],
            "temperature": 18.0,
            "hvac_action": "idle",
            "current_temperature": 19.0,
            "min_temp": 5,
            "max_temp": 30,
        },
    )
    entry = await _house(
        hass,
        freezer,
        [("Office", {"source": "climate", "climates": [E], "command_mode": "temperature"})],
    )
    await _tick(hass, freezer, 5)
    assert len(temps) == 1
    # Other reports meanwhile (its room temperature): evaluated again, not sent again.
    for value in (19.1, 19.2, 19.3):
        hass.states.async_set(
            E, "heat", {**hass.states.get(E).attributes, "current_temperature": value}, Context()
        )
        await _tick(hass, freezer, 5)
    assert len(temps) == 1
    # Never confirmed: the verification sends it again.
    await _tick(hass, freezer, 120)
    assert len(temps) == 2
    await _unload(hass, entry)


async def test_a_different_value_reported_meanwhile_is_answered(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    temps = async_mock_service(hass, "climate", "set_temperature")
    hass.states.async_set(
        E,
        "heat",
        {
            "hvac_modes": ["heat", "off"],
            "temperature": 18.0,
            "hvac_action": "idle",
            "current_temperature": 19.0,
            "min_temp": 5,
            "max_temp": 30,
        },
    )
    entry = await _house(
        hass,
        freezer,
        [
            (
                "Office",
                {
                    "source": "climate",
                    "climates": [E],
                    "command_mode": "temperature",
                    "child_lock": True,
                },
            )
        ],
    )
    await _tick(hass, freezer, 5)
    assert len(temps) == 1
    room = _room(entry, "Office")
    await room.async_set_child_lock(True)
    hass.states.async_set(
        E, "heat", {**hass.states.get(E).attributes, "temperature": 23.0}, Context()
    )
    await _tick(hass, freezer, 5)
    assert temps[-1].data["temperature"] == 21.0 and len(temps) == 2
    await _unload(hass, entry)


# ---------------------------------------------------------------- 8, 9. alerts end
async def test_the_paused_commands_alert_ends_after_a_calm_hour(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    async_mock_service(hass, "climate", "set_temperature")
    hass.states.async_set(
        E,
        "heat",
        {
            "hvac_modes": ["heat", "off"],
            "temperature": 21.0,
            "hvac_action": "idle",
            "current_temperature": 20.5,
            "min_temp": 5,
            "max_temp": 30,
        },
    )
    entry = await _house(
        hass,
        freezer,
        [("Office", {"source": "climate", "climates": [E], "command_mode": "temperature"})],
    )
    await _tick(hass, freezer, 5)
    room = _room(entry, "Office")
    house = entry.runtime_data
    for _ in range(45):
        room._command_allowed(E)
    assert f"commands_{E}" in house.notifier.active
    # No command at all afterwards: it ends at an evaluation, not at a next command.
    await _tick(hass, freezer, 15 * 60)
    await _tick(hass, freezer, 60 * 60 + 60)
    assert f"commands_{E}" not in house.notifier.active
    await _unload(hass, entry)


async def test_the_device_minimum_alert_ends_when_the_target_is_above_it(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    async_mock_service(hass, "climate", "set_temperature")
    async_mock_service(hass, "climate", "set_hvac_mode")
    hass.states.async_set(
        E,
        "heat",
        {
            "hvac_modes": ["heat", "off", "cool"],
            "temperature": 21.0,
            "current_temperature": 20.5,
            "min_temp": 16,
            "max_temp": 30,
        },
    )
    entry = await _house(
        hass,
        freezer,
        [("Office", {"source": "climate", "climates": [E], "command_mode": "temperature"})],
    )
    await _tick(hass, freezer, 5)
    room = _room(entry, "Office")
    house = entry.runtime_data
    state = hass.states.get(E)
    room._within_entity_range(state, 12.0)
    assert f"range_{E}_min" in house.notifier.active
    room._within_entity_range(state, 21.0)
    assert f"range_{E}_min" not in house.notifier.active
    await _unload(hass, entry)


# ---------------------------------------------------------------- 10. switch at
async def test_the_switch_time_is_never_in_the_past(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    assert await async_setup_component(
        hass, "input_boolean", {"input_boolean": {"boiler": {}, "pump": {}, "cheap": {}}}
    )
    async_mock_service(hass, "climate", "set_temperature")
    hass.states.async_set(
        E,
        "heat",
        {
            "hvac_modes": ["heat", "off"],
            "temperature": 21.0,
            "hvac_action": "idle",
            "current_temperature": 20.5,
            "min_temp": 5,
            "max_temp": 30,
        },
    )
    entry = await _house(
        hass,
        freezer,
        [("Office", {"source": "climate", "climates": [E], "command_mode": "temperature"})],
        boiler_entity="input_boolean.boiler",
        secondary_source="input_boolean.pump",
        source_criterion="entity",
        source_criterion_entity="input_boolean.cheap",
        source_switch_minutes=15,
    )
    house = entry.runtime_data
    await hass.services.async_call(
        "input_boolean", "turn_on", {"entity_id": "input_boolean.cheap"}, blocking=True
    )
    await _tick(hass, freezer, 5)
    assert house.source_switch_at is not None
    # The pump is unavailable: past the switch time the boiler still heats.
    hass.states.async_set("input_boolean.pump", "unavailable")
    await _tick(hass, freezer, 20 * 60)
    at = house.source_switch_at
    assert at is None or at > dt_util.utcnow()
    await _unload(hass, entry)


# ---------------------------------------------------------------- 7. saved times
async def test_the_time_of_the_heat_source_saved_before_is_read(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, hass_storage: dict
) -> None:
    """Saved before 2.6.5: one time; it is that of the primary heat source, and
    is now saved for each source."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.advanced_climate.const import DOMAIN

    entry_id = "house_saved_before"
    hass_storage[f"{DOMAIN}.{entry_id}"] = {
        "version": 1,
        "key": f"{DOMAIN}.{entry_id}",
        "data": {"house": {"boiler_changed": "2026-10-12T08:57:00+00:00"}, "rooms": {}},
    }
    freezer.move_to("2026-10-12 09:00:00+00:00")
    hass.states.async_set("switch.boiler", "on")
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Home",
        minor_version=2,
        options={"boiler_entity": "switch.boiler"},
        entry_id=entry_id,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    house = entry.runtime_data
    assert house.source_changed["switch.boiler"].isoformat() == "2026-10-12T08:57:00+00:00"
    assert house.boiler_changed == house.source_changed["switch.boiler"]
    saved = house._data_to_save()["house"]
    assert saved["source_changed"] == {"switch.boiler": "2026-10-12T08:57:00+00:00"}
    assert "boiler_changed" not in saved
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


# ---------------------------------------------------------------- 3, 11. back to auto
async def test_a_thermostat_whose_manual_time_ends_is_set_again(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Like Netatmo: a temperature puts it in heat by itself; three hours later it
    goes back to its schedule (another temperature). Before, a manual change kept
    the room at the schedule of the thermostat for two hours; now the target is
    sent again."""
    temps: list[float] = []

    @callback
    def _temp(call: ServiceCall) -> None:
        temps.append(call.data["temperature"])
        st = hass.states.get(E)
        hass.states.async_set(
            E,
            "heat",
            {**st.attributes, "temperature": call.data["temperature"]},
            context=call.context,
        )

    hass.services.async_register("climate", "set_temperature", _temp)
    async_mock_service(hass, "climate", "set_hvac_mode")
    hass.states.async_set(
        E,
        "auto",
        {
            "hvac_modes": ["auto", "heat", "off"],
            "temperature": 19.0,
            "hvac_action": "idle",
            "current_temperature": 20.0,
            "min_temp": 5,
            "max_temp": 30,
        },
    )
    entry = await _house(
        hass,
        freezer,
        [("Office", {"source": "climate", "climates": [E], "command_mode": "temperature"})],
    )
    await _tick(hass, freezer, 5)
    assert hass.states.get(E).state == "heat" and temps == [21.0]
    await _tick(hass, freezer, 3 * 3600)
    hass.states.async_set(
        E, "auto", {**hass.states.get(E).attributes, "temperature": 19.0}, Context()
    )
    await _tick(hass, freezer, 5)
    room = _room(entry, "Office")
    assert room.decision.rule != "manual_override"
    assert temps[-1] == 21.0 and len(temps) == 2
    assert hass.states.get(E).state == "heat"
    await _unload(hass, entry)


async def test_a_trv_that_reports_heat_late_is_not_left_in_auto(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Put in heat, it reports it only 90 s later; evaluated meanwhile it was taken
    as one that stays in auto. Now only a seen return to auto counts."""
    modes: list[str] = []

    @callback
    def _mode(call: ServiceCall) -> None:
        modes.append(call.data["hvac_mode"])

    hass.services.async_register("climate", "set_hvac_mode", _mode)
    async_mock_service(hass, "climate", "set_temperature")
    hass.states.async_set(
        E,
        "auto",
        {
            "hvac_modes": ["auto", "heat", "off"],
            "temperature": 21.0,
            "hvac_action": "idle",
            "current_temperature": 20.0,
            "min_temp": 5,
            "max_temp": 30,
        },
    )
    entry = await _house(
        hass,
        freezer,
        [("Office", {"source": "climate", "climates": [E], "command_mode": "temperature"})],
    )
    await _tick(hass, freezer, 5)
    assert modes == ["heat"]
    for value in (20.1, 20.2):
        hass.states.async_set(
            E, "auto", {**hass.states.get(E).attributes, "current_temperature": value}, Context()
        )
        await _tick(hass, freezer, 30)
    assert modes == ["heat"]  # not sent again while it has not reported
    hass.states.async_set(E, "heat", hass.states.get(E).attributes, Context())
    await _tick(hass, freezer, 5)
    room = _room(entry, "Office")
    assert E not in room.keeps_auto
    assert room.decision.rule != "manual_override"
    await _unload(hass, entry)


async def test_a_trv_turned_on_by_hand_in_auto_is_a_manual_change(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """From off to auto on the device: turned on by a person, not a return."""
    temps = async_mock_service(hass, "climate", "set_temperature")
    async_mock_service(hass, "climate", "set_hvac_mode")
    hass.states.async_set(
        E,
        "heat",
        {
            "hvac_modes": ["auto", "heat", "off"],
            "temperature": 21.0,
            "hvac_action": "idle",
            "current_temperature": 20.0,
            "min_temp": 5,
            "max_temp": 30,
        },
    )
    entry = await _house(
        hass,
        freezer,
        [("Office", {"source": "climate", "climates": [E], "command_mode": "temperature"})],
    )
    await _tick(hass, freezer, 5)
    await _tick(hass, freezer, 6 * 60)
    hass.states.async_set(E, "off", hass.states.get(E).attributes, Context())
    await _tick(hass, freezer, 5)
    room = _room(entry, "Office")
    assert room.decision.rule == "manual_override"
    await _tick(hass, freezer, 6 * 60)
    hass.states.async_set(E, "auto", hass.states.get(E).attributes, Context())
    await _tick(hass, freezer, 5)
    assert room.decision.rule == "manual_override"
    assert not temps or temps[-1].data["temperature"] == 21.0
    await _unload(hass, entry)


async def test_a_cloud_thermostat_put_on_away_gets_no_temperature_after_it(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Commanded by preset (away for the vacation), temperatures for the other
    levels, reporting late (a heat pump through its cloud): the away preset is
    not followed by a temperature, which could take it out of its holiday mode."""
    temps = async_mock_service(hass, "climate", "set_temperature")
    presets = async_mock_service(hass, "climate", "set_preset_mode")
    hass.states.async_set(
        E,
        "heat",
        {
            "hvac_modes": ["heat", "off"],
            "preset_modes": ["none", "away"],
            "preset_mode": "away",
            "temperature": 16.0,
            "current_temperature": 20.0,
            "min_temp": 16,
            "max_temp": 30,
        },
    )
    entry = await _house(
        hass,
        freezer,
        [
            (
                "Office",
                {
                    "source": "climate",
                    "climates": [E],
                    "command_mode": "preset",
                    "preset_map": {"away": "away"},
                },
            )
        ],
    )
    await _tick(hass, freezer, 5)
    room = _room(entry, "Office")
    # It learned away = 16 (the state at start); now on a temperature (21).
    room.observed_temps["away"] = 16.0
    assert temps and temps[-1].data["temperature"] == 21.0
    hass.states.async_set(
        E, "heat", {**hass.states.get(E).attributes, "preset_mode": "none", "temperature": 21.0}
    )
    await _tick(hass, freezer, 5)
    sent = len(temps)
    # Vacation: away is sent; the state does not change yet (it reports late).
    await entry.runtime_data.async_set_mode("vacation")
    await _tick(hass, freezer, 5)
    assert presets and presets[-1].data["preset_mode"] == "away"
    assert len(temps) == sent
    await _unload(hass, entry)


async def test_a_trv_left_in_auto_stays_so_after_a_restart(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, hass_storage: dict
) -> None:
    """Left in auto is saved: after a restart it is not tried in heat again (for
    a TRV602Z, a moment of its valve fully open)."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.advanced_climate.const import DOMAIN, SUBENTRY_ROOM

    async_mock_service(hass, "climate", "set_temperature")
    modes = async_mock_service(hass, "climate", "set_hvac_mode")
    hass.states.async_set(
        E,
        "auto",
        {
            "hvac_modes": ["auto", "heat", "off"],
            "temperature": 21.0,
            "hvac_action": "idle",
            "current_temperature": 20.0,
            "min_temp": 5,
            "max_temp": 30,
        },
    )
    entry_id = "house_keeps_auto"
    hass_storage[f"{DOMAIN}.{entry_id}"] = {
        "version": 1,
        "key": f"{DOMAIN}.{entry_id}",
        "data": {"house": {}, "rooms": {"office": {"keeps_auto": [E]}}},
    }
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Home",
        minor_version=2,
        options={"persons": [], "nearby_zones": []},
        entry_id=entry_id,
        subentries_data=[
            {
                "data": {"source": "climate", "climates": [E], "command_mode": "temperature"},
                "subentry_type": SUBENTRY_ROOM,
                "subentry_id": "office",
                "title": "Office",
                "unique_id": None,
            }
        ],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    await _tick(hass, freezer, 5)
    room = _room(entry, "Office")
    assert E in room.keeps_auto
    assert not modes
    assert room.as_dict()["keeps_auto"] == [E]
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def _daikin(hass: HomeAssistant, freezer: FrozenDateTimeFactory, refuses_on_away: bool):
    """A heat pump through its cloud: away (its holiday mode) for the vacation,
    temperatures for the other levels; it reports a second late."""
    calls: list[tuple[str, object]] = []

    def _later(changes: dict) -> None:
        # Reported a second later, on top of what it shows then.
        def _report() -> None:
            st = hass.states.get(E)
            hass.states.async_set(E, st.state, {**st.attributes, **changes})

        hass.loop.call_later(1, _report)

    @callback
    def _temp(call: ServiceCall) -> None:
        calls.append(("temperature", call.data["temperature"]))
        # What it holds when the command arrives (the cloud applies it in order).
        if not (refuses_on_away and hass.data.setdefault("daikin_preset", "none") == "away"):
            _later({"temperature": call.data["temperature"]})

    @callback
    def _preset(call: ServiceCall) -> None:
        calls.append(("preset", call.data["preset_mode"]))
        hass.data["daikin_preset"] = call.data["preset_mode"]
        changes = {"preset_mode": call.data["preset_mode"]}
        if call.data["preset_mode"] == "away":
            changes["temperature"] = 16.0
        _later(changes)

    hass.services.async_register("climate", "set_temperature", _temp)
    hass.services.async_register("climate", "set_preset_mode", _preset)
    hass.states.async_set(
        E,
        "heat",
        {
            "hvac_modes": ["heat", "off"],
            "preset_modes": ["none", "away"],
            "preset_mode": "none",
            "temperature": 20.0,
            "current_temperature": 20.0,
            "min_temp": 16,
            "max_temp": 30,
        },
    )
    entry = await _house(
        hass,
        freezer,
        [
            (
                "Office",
                {
                    "source": "climate",
                    "climates": [E],
                    "command_mode": "preset",
                    "preset_map": {"away": "away"},
                },
            )
        ],
    )
    for _ in range(5):
        await _tick(hass, freezer, 60)
    house = entry.runtime_data
    await house.async_set_mode("vacation")
    for _ in range(10):
        await _tick(hass, freezer, 60)
    assert ("preset", "away") in calls
    assert hass.states.get(E).attributes["preset_mode"] == "away"
    sent = len(calls)
    await house.async_set_mode("auto")
    for _ in range(30):
        await _tick(hass, freezer, 60)
    return entry, calls[sent:]


async def test_after_the_vacation_the_away_preset_is_left(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """It kept away (its holiday mode) with 21 °C, or refused 21 °C on away and
    was sent it again and again; now it is taken off away first."""
    for refuses in (True, False):
        entry, after = await _daikin(hass, freezer, refuses)
        state = hass.states.get(E)
        assert after[0] == ("preset", "none"), after
        assert state.attributes["preset_mode"] == "none"
        assert state.attributes["temperature"] == 21.0
        assert len(after) <= 3, after
        assert _room(entry, "Office").decision.rule != "manual_override"
        await _unload(hass, entry)
        await _tick(hass, freezer, 5)


async def test_a_preset_of_no_level_is_not_left(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Only the presets the room uses for its levels are taken back: another one
    (e.g. its own eco, not mapped) is not touched by the temperature."""
    presets = async_mock_service(hass, "climate", "set_preset_mode")
    async_mock_service(hass, "climate", "set_temperature")
    hass.states.async_set(
        E,
        "heat",
        {
            "hvac_modes": ["heat", "off"],
            "preset_modes": ["none", "away", "eco"],
            "preset_mode": "eco",
            "temperature": 20.0,
            "current_temperature": 20.0,
            "min_temp": 16,
            "max_temp": 30,
        },
    )
    entry = await _house(
        hass,
        freezer,
        [
            (
                "Office",
                {
                    "source": "climate",
                    "climates": [E],
                    "command_mode": "preset",
                    "preset_map": {"away": "away"},
                },
            )
        ],
    )
    for _ in range(3):
        await _tick(hass, freezer, 60)
    assert not any(c.data["preset_mode"] == "none" for c in presets)
    await _unload(hass, entry)


# ---------------------------------------------------------------- left in auto: not for good
async def _trv_in_heat(hass: HomeAssistant, freezer: FrozenDateTimeFactory):
    """A TRV in auto that takes heat when told (the state follows the command)."""
    modes: list[str] = []

    @callback
    def _mode(call: ServiceCall) -> None:
        modes.append(call.data["hvac_mode"])
        st = hass.states.get(E)
        hass.states.async_set(E, call.data["hvac_mode"], st.attributes, context=call.context)

    @callback
    def _temp(call: ServiceCall) -> None:
        st = hass.states.get(E)
        attrs = {**st.attributes, "temperature": call.data["temperature"]}
        hass.states.async_set(E, st.state, attrs, context=call.context)

    hass.services.async_register("climate", "set_hvac_mode", _mode)
    hass.services.async_register("climate", "set_temperature", _temp)
    hass.states.async_set(
        E,
        "auto",
        {
            "hvac_modes": ["auto", "heat", "off"],
            "temperature": 21.0,
            "hvac_action": "idle",
            "current_temperature": 20.0,
            "min_temp": 5,
            "max_temp": 30,
        },
    )
    entry = await _house(
        hass,
        freezer,
        [("Office", {"source": "climate", "climates": [E], "command_mode": "temperature"})],
    )
    await _tick(hass, freezer, 5)
    assert modes == ["heat"]
    return entry, modes


async def _auto_on_the_device(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    hass.states.async_set(E, "auto", hass.states.get(E).attributes, Context())
    await _tick(hass, freezer, 5)
    await _tick(hass, freezer, 5)


async def test_auto_pressed_on_the_trv_a_day_apart_does_not_leave_it_in_auto(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Auto pressed on the TRV, then again 20 hours later: each time it is put in
    heat again (it can stay in heat), never left in auto for good."""
    entry, modes = await _trv_in_heat(hass, freezer)
    room = _room(entry, "Office")
    for _ in range(3):
        await _tick(hass, freezer, 20 * 3600)
        await _auto_on_the_device(hass, freezer)
        assert room.decision.rule != "manual_override"
        assert E not in room.keeps_auto
        assert hass.states.get(E).state == "heat"
    assert modes == ["heat"] * 4
    await _unload(hass, entry)


async def test_a_late_return_starts_the_count_again(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Back within the hour (1), then after two hours (counted again from 0), then
    within the hour (1): not left in auto; one more within the hour: left."""
    entry, _modes = await _trv_in_heat(hass, freezer)
    room = _room(entry, "Office")
    for wait, kept in ((10 * 60, False), (2 * 3600, False), (10 * 60, False), (10 * 60, True)):
        await _tick(hass, freezer, wait)
        await _auto_on_the_device(hass, freezer)
        assert (E in room.keeps_auto) is kept, (wait, room.auto_returns)
    assert hass.states.get(E).state == "auto"
    await _unload(hass, entry)


async def test_reconfiguring_the_room_tries_its_trvs_in_heat_again(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    from homeassistant.data_entry_flow import FlowResultType

    entry, _modes = await _trv_in_heat(hass, freezer)
    room = _room(entry, "Office")
    for _ in range(2):
        await _tick(hass, freezer, 60)
        await _auto_on_the_device(hass, freezer)
    assert E in room.keeps_auto
    assert hass.states.get(E).state == "auto"
    subentry = next(iter(entry.subentries.values()))
    flow = hass.config_entries.subentries
    result = await entry.start_subentry_reconfigure_flow(hass, subentry.subentry_id)
    for _ in range(20):
        if result["type"] is not FlowResultType.FORM:
            break
        result = await flow.async_configure(result["flow_id"], {})
    assert result["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()
    for _ in range(3):
        await _tick(hass, freezer, 30)
    room = _room(entry, "Office")
    assert E not in room.keeps_auto
    assert hass.states.get(E).state == "heat"
    await _unload(hass, entry)


# ---------------------------------------------------------------- top up, a new target
async def test_topped_up_after_its_target_went_up(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """At 20.8 °C on a target of 18 it had reached it; at 06:00 the target is 21:
    in the band 20.7-21 it is topped up while the boiler runs for another room."""
    from tests.ha.test_top_up import _setup as _top_up_setup
    from tests.ha.test_top_up import _steps

    entry, trvs = await _top_up_setup(hass, freezer)
    office = _room(entry, "Office")
    await office.async_set_level("home", 18.0)
    trvs.report("climate.office", "idle", 20.8)
    await _steps(hass, freezer)
    assert office.target_temperature == 18.0
    trvs.report("climate.bedroom", "heating", 20.0)
    await _steps(hass, freezer)
    assert not office.topped_up
    await office.async_set_level("home", 21.0)
    await _steps(hass, freezer)
    assert office.target_temperature == 21.0
    assert office.topped_up
    await _unload(hass, entry)


async def test_a_preset_sent_again_takes_its_temperature_again(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """A battery thermostat commanded by preset, whose presets have their own
    temperature (comfort is 22 on the device) and that keeps a preset with a
    temperature set on it, reports late. Turned on again with "comfort" and the
    temperature known for it (21), it had not reported yet at the verification:
    the command was repeated without the temperature, the preset took it back
    to its own 22, taken for a manual change. Now the temperature goes again."""
    from homeassistant.helpers import entity_registry as er
    from homeassistant.helpers.event import async_call_later

    own = {"comfort": 22.0, "eco": 17.0}
    sent: list[tuple[str, object]] = []
    pending: dict = {}

    def _late(change: dict) -> None:
        first = not pending
        if first:
            state = hass.states.get(E)
            pending["state"], pending["attrs"] = state.state, dict(state.attributes)
        pending["attrs"].update({k: v for k, v in change.items() if k != "state"})
        if "state" in change:
            pending["state"] = change["state"]
        if first:

            @callback
            def _report(_now) -> None:
                hass.states.async_set(
                    E, pending.pop("state"), pending.pop("attrs"), context=Context()
                )

            # It reports after the verification (two minutes).
            async_call_later(hass, 150, _report)

    @callback
    def _temp(call: ServiceCall) -> None:
        sent.append(("temperature", call.data["temperature"]))
        _late({"temperature": call.data["temperature"]})

    @callback
    def _preset(call: ServiceCall) -> None:
        preset = call.data["preset_mode"]
        sent.append(("preset", preset))
        _late({"preset_mode": preset, "temperature": own.get(preset, 21.0)})

    @callback
    def _mode(call: ServiceCall) -> None:
        sent.append(("mode", call.data["hvac_mode"]))
        _late({"state": call.data["hvac_mode"]})

    hass.services.async_register("climate", "set_temperature", _temp)
    hass.services.async_register("climate", "set_preset_mode", _preset)
    hass.services.async_register("climate", "set_hvac_mode", _mode)
    hass.states.async_set("binary_sensor.window", "off")
    hass.states.async_set(
        E,
        "heat",
        {
            "hvac_modes": ["heat", "off"],
            "preset_modes": ["comfort", "eco"],
            "preset_mode": "comfort",
            "temperature": 21.0,
            "current_temperature": 20.0,
            "min_temp": 7.0,
            "max_temp": 30.0,
        },
    )
    entry = await _house(
        hass,
        freezer,
        [
            (
                "Office",
                {
                    "source": "climate",
                    "climates": [E],
                    "command_mode": "preset",
                    "preset_map": {
                        "home": "comfort",
                        "comfort": "comfort",
                        "eco": "eco",
                        "sleep": "eco",
                        "away": "eco",
                    },
                    "window_sensors": ["binary_sensor.window"],
                    "window_action": "off",
                },
            )
        ],
    )
    await _tick(hass, freezer, 5)
    room = _room(entry, "Office")
    hass.states.async_set(E, "heat", {**hass.states.get(E).attributes, "current_temperature": 20.1})
    await _tick(hass, freezer, 5)
    assert room.observed_temps.get("home") == 21.0
    mode = next(
        e.entity_id
        for e in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
        if e.unique_id == f"{entry.entry_id}_mode"
    )

    async def _settle() -> None:
        for _ in range(6):
            await _tick(hass, freezer, 60)

    # The house off: the frost temperature on "comfort" (it keeps the preset).
    await hass.services.async_call(
        "select", "select_option", {"entity_id": mode, "option": "off"}, blocking=True
    )
    await _settle()
    assert hass.states.get(E).attributes["temperature"] == 7.0
    # A window open (heating off): the thermostat off; then auto, still open.
    hass.states.async_set("binary_sensor.window", "on")
    await _settle()
    await hass.services.async_call(
        "select", "select_option", {"entity_id": mode, "option": "auto"}, blocking=True
    )
    await _settle()
    assert hass.states.get(E).state == "off"
    # The window closed: on, "comfort" and its temperature; it reports late.
    sent.clear()
    hass.states.async_set("binary_sensor.window", "off")
    await _settle()
    first = sent[: sent.index(("temperature", 21.0)) + 1]
    again = sent[len(first) :]
    assert ("preset", "comfort") in first and ("preset", "comfort") in again, sent
    # Repeated with the temperature after the preset.
    assert again[again.index(("preset", "comfort")) + 1 :][:1] == [("temperature", 21.0)], sent
    state = hass.states.get(E)
    assert (state.state, state.attributes["preset_mode"], state.attributes["temperature"]) == (
        "heat",
        "comfort",
        21.0,
    )
    assert room.override is None
    assert room.decision.rule != "manual_override"
    await _unload(hass, entry)
