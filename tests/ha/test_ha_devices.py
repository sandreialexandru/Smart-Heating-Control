"""The devices of a room as they are used: Generic Thermostat, preset and on / off
thermostats, TRVs, relays, the valve exercise, a Schedule helper and the alerts."""

from __future__ import annotations

import logging

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import Context, HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
    async_mock_service,
)

from custom_components.advanced_climate.const import DOMAIN, PRESETS, SUBENTRY_ROOM

TRV = {
    "hvac_modes": ["heat", "off"],
    "current_temperature": 19.0,
    "temperature": 17.0,
    "min_temp": 5.0,
    "max_temp": 30.0,
}


async def _house(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    rooms: list[tuple[str, dict]],
    **options: object,
) -> MockConfigEntry:
    """A house with the given rooms, Monday 12:00 local time (the schedule asks for home)."""
    await hass.config.async_set_time_zone("Europe/Bucharest")
    freezer.move_to("2026-10-12 09:00:00+00:00")
    hass.states.async_set("person.andrei", "home")
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Home",
        options={"persons": ["person.andrei"], "nearby_zones": [], **options},
        subentries_data=[
            {"data": data, "subentry_type": SUBENTRY_ROOM, "title": title, "unique_id": None}
            for title, data in rooms
        ],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    await _tick(hass, freezer, 15)
    return entry


async def _tick(hass: HomeAssistant, freezer: FrozenDateTimeFactory, seconds: float) -> None:
    await hass.async_block_till_done()
    freezer.tick(seconds)
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()


def _room(entry: MockConfigEntry, name: str):
    return next(r for r in entry.runtime_data.rooms.values() if r.name == name)


async def _unload(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


# ---------------------------------------------------------------------------
# Generic Thermostat
# ---------------------------------------------------------------------------
GT_OPTIONS = {
    "heater": "input_boolean.gt_heater",
    "home_temp": 21.5,
    "eco_temp": 18.0,
    "away_temp": 16.0,
    "sleep_temp": 19.0,
    "comfort_temp": 22.0,
    "cold_tolerance": 0.2,
    "hot_tolerance": 0.4,
    "min_temp": 7.0,
}
GT_STATE = {
    "hvac_modes": ["heat", "off"],
    # No "activity": the thermostat does not have it, and no temperature is set for it.
    "preset_modes": ["none", "home", "eco", "away", "sleep", "comfort"],
    "preset_mode": "none",
    "current_temperature": 20.0,
    "temperature": 20.0,
    "hvac_action": "idle",
}


def _gt(hass: HomeAssistant, options: dict | None) -> str:
    """A Generic Thermostat climate entity; with ``options`` set up in the UI, else in YAML."""
    registry = er.async_get(hass)
    if options is None:
        entity_id = "climate.living_gt"
    else:
        gt_entry = MockConfigEntry(domain="generic_thermostat", options=options)
        gt_entry.add_to_hass(hass)
        entity_id = registry.async_get_or_create(
            "climate",
            "generic_thermostat",
            gt_entry.entry_id,
            config_entry=gt_entry,
            suggested_object_id="living_gt",
        ).entity_id
    hass.states.async_set(entity_id, "heat", GT_STATE)
    return entity_id


async def test_generic_thermostat_room_picks_its_presets(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Only the preset is chosen; the temperatures and tolerances come from the GT."""
    presets = async_mock_service(hass, "climate", "set_preset_mode")
    gt = _gt(hass, GT_OPTIONS)
    entry = await _house(
        hass, freezer, [("Living", {"source": "generic_thermostat", "climates": [gt]})]
    )
    room = _room(entry, "Living")
    assert presets[-1].data == {"entity_id": gt, "preset_mode": "home"}
    assert hass.states.get("sensor.living_target_temperature").state == "21.5"
    # Every level is kept by the thermostat; none is edited here.
    assert room.device_levels == list(PRESETS)
    assert room.editable_levels == []
    assert room.level_of_device_preset("eco") == "eco"
    assert room.level_of_device_preset("none") is None
    # The frost protection is the minimum of the GT, the band its tolerances.
    assert room.frost_temp() == 7.0
    assert room.prediction_band() == (0.2, 0.4, False)
    assert room.stop_tolerance() == 0.2
    assert room.sends_preset("home")

    # A preset chosen on the thermostat is a manual change.
    hass.states.async_set(gt, "heat", {**GT_STATE, "preset_mode": "comfort"}, context=Context())
    await _tick(hass, freezer, 5)
    assert hass.states.get("sensor.living_decision").state == "manual_override"
    held = hass.states.get("sensor.living_decision").attributes["override"]
    assert held["description"] == "preset comfort"
    assert held["preset"] == "comfort"
    assert held["temperature"] == 22.0

    # A level the thermostat does not have, and whose temperature is unknown: an alert.
    await hass.services.async_call(
        DOMAIN, "set_override", {"room": "Living", "preset": "activity"}, blocking=True
    )
    await _tick(hass, freezer, 5)
    assert f"preset_{room.id}_activity" in entry.runtime_data.active_alerts
    await _unload(hass, entry)


async def test_generic_thermostat_from_yaml_has_no_known_band(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Without a config entry the tolerances cannot be read: no band, no stop tolerance."""
    async_mock_service(hass, "climate", "set_preset_mode")
    gt = _gt(hass, None)
    entry = await _house(
        hass, freezer, [("Living", {"source": "generic_thermostat", "climates": [gt]})]
    )
    room = _room(entry, "Living")
    assert room.prediction_band() is None
    assert room.stop_tolerance() == 0.0
    # The frost protection of the house, and the temperatures seen on the thermostat.
    assert room.frost_temp() == 7.0
    assert room.level_temp("home") is None
    hass.states.async_set(gt, "heat", {**GT_STATE, "preset_mode": "home", "temperature": 21.0})
    await _tick(hass, freezer, 5)
    assert room.level_temp("home") == 21.0
    await _unload(hass, entry)


# ---------------------------------------------------------------------------
# Thermostats commanded by preset, or on / off
# ---------------------------------------------------------------------------
SMART = {
    "hvac_modes": ["heat", "off"],
    "preset_modes": ["Comfort", "Eco", "Away"],
    "preset_mode": "Eco",
    "current_temperature": 20.0,
    "temperature": 18.0,
    "hvac_action": "idle",
}


async def test_preset_thermostat_uses_its_own_preset_names(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Levels with a device preset are sent as that preset, the others as a temperature."""
    presets = async_mock_service(hass, "climate", "set_preset_mode")
    temperatures = async_mock_service(hass, "climate", "set_temperature")
    hass.states.async_set("climate.smart", "heat", SMART)
    entry = await _house(
        hass,
        freezer,
        [
            (
                "Office",
                {
                    "source": "climate",
                    "climates": ["climate.smart"],
                    "command_mode": "preset",
                    "preset_map": {"home": "Comfort", "eco": "Eco", "away": "Away"},
                },
            )
        ],
    )
    room = _room(entry, "Office")
    assert presets[-1].data == {"entity_id": "climate.smart", "preset_mode": "Comfort"}
    assert set(room.device_levels) == {"home", "eco", "away"}
    assert "sleep" in room.editable_levels
    assert room.level_of_device_preset("Eco") == "eco"
    assert room.level_of_device_preset("Boost") is None
    assert room.sends_preset("home")
    assert not room.sends_preset("sleep")
    assert room.display_name("home") == "Comfort"

    # The thermostat shows the temperature of its preset: the level uses it.
    hass.states.async_set(
        "climate.smart", "heat", {**SMART, "preset_mode": "Comfort", "temperature": 21.5}
    )
    await _tick(hass, freezer, 5)
    assert room.level_temp("home") == 21.5

    # Sleep has no device preset: it is sent as its temperature (18 °C by default).
    await hass.services.async_call(
        DOMAIN, "set_override", {"room": "Office", "preset": "sleep"}, blocking=True
    )
    await _tick(hass, freezer, 5)
    assert temperatures[-1].data == {"entity_id": "climate.smart", "temperature": 18.0}
    await _unload(hass, entry)


async def test_on_off_thermostat_waits_for_its_minimum_on_time(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Commanded by hvac_mode: on below the band, off above it once the minimum time ended."""
    modes = async_mock_service(hass, "climate", "set_hvac_mode")
    onoff = {"hvac_modes": ["heat", "off"], "current_temperature": 19.0, "temperature": 21.0}
    hass.states.async_set("climate.onoff", "off", onoff)
    entry = await _house(
        hass,
        freezer,
        [
            (
                "Office",
                {
                    "source": "climate",
                    "climates": ["climate.onoff"],
                    "command_mode": "hvac_mode",
                    "min_on_minutes": 10,
                    "min_off_minutes": 0,
                },
            )
        ],
    )
    room = _room(entry, "Office")
    assert modes[-1].data == {"entity_id": "climate.onoff", "hvac_mode": "heat"}
    assert room.prediction_band() == (0.3, 0.3, True)
    assert not room.supports_valve_exercise
    hass.states.async_set("climate.onoff", "heat", onoff)
    await _tick(hass, freezer, 5)

    # Warm: off only after the 10 minutes on.
    sent = len(modes)
    hass.states.async_set("climate.onoff", "heat", {**onoff, "current_temperature": 21.5})
    await _tick(hass, freezer, 5)
    assert len(modes) == sent
    assert room.relay_waiting == "min_on"
    await _tick(hass, freezer, 600)
    assert modes[-1].data == {"entity_id": "climate.onoff", "hvac_mode": "off"}
    await _unload(hass, entry)


async def test_summer_turns_off_or_lowers_each_trv(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Summer: a TRV with an off mode is turned off, one without gets its minimum."""
    modes = async_mock_service(hass, "climate", "set_hvac_mode")
    temperatures = async_mock_service(hass, "climate", "set_temperature")
    hass.states.async_set("climate.trv_a", "heat", TRV)
    hass.states.async_set("climate.trv_b", "heat", {**TRV, "hvac_modes": ["heat"]})
    entry = await _house(
        hass,
        freezer,
        [
            (
                "Office",
                {
                    "source": "climate",
                    "climates": ["climate.trv_a", "climate.trv_b"],
                    "command_mode": "temperature",
                },
            )
        ],
    )
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": "select.home_mode", "option": "summer"},
        blocking=True,
    )
    await _tick(hass, freezer, 5)
    assert {"entity_id": "climate.trv_a", "hvac_mode": "off"} in [c.data for c in modes]
    assert temperatures[-1].data == {"entity_id": "climate.trv_b", "temperature": 5.0}
    # Already there: nothing is sent again.
    hass.states.async_set("climate.trv_a", "off", TRV)
    hass.states.async_set(
        "climate.trv_b", "heat", {**TRV, "hvac_modes": ["heat"], "temperature": 5.0}
    )
    await _tick(hass, freezer, 5)
    sent = len(modes) + len(temperatures)
    await _tick(hass, freezer, 300)
    assert len(modes) + len(temperatures) == sent
    await _unload(hass, entry)


# ---------------------------------------------------------------------------
# Relays
# ---------------------------------------------------------------------------
async def _relay_house(hass, freezer, temperature: float, **room: object) -> MockConfigEntry:
    assert await async_setup_component(hass, "input_boolean", {"input_boolean": {"heater": {}}})
    hass.states.async_set("sensor.room_temp", str(temperature), {"unit_of_measurement": "°C"})
    hass.states.async_set("binary_sensor.window", "off")
    data = {
        "source": "switch",
        "switches": ["input_boolean.heater"],
        "temperature_sensors": ["sensor.room_temp"],
        "window_sensors": ["binary_sensor.window"],
        "min_on_minutes": 0,
        "min_off_minutes": 0,
        **room,
    }
    return await _house(hass, freezer, [("Bedroom", data)])


async def test_relay_turned_on_by_hand_comes_back_after_a_window(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """A relay turned on by a person is respected, off with the window, on again after it."""
    entry = await _relay_house(hass, freezer, 21.5)
    assert hass.states.get("input_boolean.heater").state == "off"
    await hass.services.async_call(
        "input_boolean",
        "turn_on",
        {"entity_id": "input_boolean.heater"},
        blocking=True,
        context=Context(),
    )
    await _tick(hass, freezer, 5)
    decision = hass.states.get("sensor.bedroom_decision")
    assert decision.state == "manual_override"
    assert decision.attributes["override"]["description"] == "switch on"
    assert hass.states.get("input_boolean.heater").state == "on"

    hass.states.async_set("binary_sensor.window", "on")
    await _tick(hass, freezer, 65)
    assert hass.states.get("input_boolean.heater").state == "off"
    hass.states.async_set("binary_sensor.window", "off")
    await _tick(hass, freezer, 65)
    assert hass.states.get("sensor.bedroom_decision").state == "manual_override"
    assert hass.states.get("input_boolean.heater").state == "on"
    await _unload(hass, entry)


async def test_a_failing_relay_command_is_logged(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, caplog: pytest.LogCaptureFixture
) -> None:
    """A switch that does not answer: a warning, and the room goes on deciding."""

    async def offline(_call: ServiceCall) -> None:
        raise HomeAssistantError("the device does not answer")

    # A domain of its own, so no real integration answers instead.
    hass.services.async_register("relay_test", "turn_on", offline)
    hass.states.async_set("relay_test.heater", "off")
    hass.states.async_set("sensor.room_temp", "18.0", {"unit_of_measurement": "°C"})
    with caplog.at_level(logging.WARNING):
        entry = await _house(
            hass,
            freezer,
            [
                (
                    "Bedroom",
                    {
                        "source": "switch",
                        "switches": ["relay_test.heater"],
                        "temperature_sensors": ["sensor.room_temp"],
                    },
                )
            ],
        )
    assert "Bedroom: relay_test.turn_on failed: the device does not answer" in caplog.text
    assert hass.states.get("sensor.bedroom_decision").state == "schedule"
    assert hass.states.get("relay_test.heater").state == "off"
    await _unload(hass, entry)


# ---------------------------------------------------------------------------
# TRVs: child lock, whole-house manual changes, until the next reevaluation
# ---------------------------------------------------------------------------
async def _trv_house(hass, freezer, rooms: dict[str, str], **options) -> tuple:
    calls = async_mock_service(hass, "climate", "set_temperature")
    for entity_id in rooms.values():
        hass.states.async_set(entity_id, "heat", TRV)
    entry = await _house(
        hass,
        freezer,
        [
            (title, {"source": "climate", "climates": [entity_id], "command_mode": "temperature"})
            for title, entity_id in rooms.items()
        ],
        **options,
    )
    return entry, calls


async def test_child_lock_sets_the_trv_back(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """With the child lock on, a temperature set on the TRV is undone."""
    entry, calls = await _trv_house(hass, freezer, {"Office": "climate.trv"})
    room = _room(entry, "Office")
    assert calls[-1].data["temperature"] == 21.0
    await room.async_set_child_lock(True)
    hass.states.async_set("climate.trv", "heat", {**TRV, "temperature": 25.0}, context=Context())
    await _tick(hass, freezer, 5)
    assert hass.states.get("sensor.office_decision").state != "manual_override"
    assert calls[-1].data == {"entity_id": "climate.trv", "temperature": 21.0}
    await room.async_set_child_lock(False)
    assert not room.child_lock
    await _unload(hass, entry)


async def test_manual_change_for_the_whole_house(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """With the whole-house scope a change on one TRV is a manual change of every room."""
    entry, _calls = await _trv_house(
        hass,
        freezer,
        {"Office": "climate.trv", "Kitchen": "climate.trv2"},
        override_scope="house",
    )
    hass.states.async_set("climate.trv", "heat", {**TRV, "temperature": 23.0}, context=Context())
    await _tick(hass, freezer, 5)
    office = hass.states.get("sensor.office_decision")
    kitchen = hass.states.get("sensor.kitchen_decision")
    assert office.state == kitchen.state == "manual_override"
    # Both say where it was made.
    assert office.attributes["override"]["description"] == "23.0 °C (Office)"
    assert kitchen.attributes["override"]["description"] == "23.0 °C (Office)"
    # Only the room of the TRV keeps its value to set again after an interruption.
    assert office.attributes["override"]["devices"] == ["climate.trv"]
    assert kitchen.attributes["override"]["devices"] == []
    await _unload(hass, entry)


async def test_manual_change_until_the_next_reevaluation(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Without an end time a manual change lasts until something it depends on changes."""
    entry, _calls = await _trv_house(
        hass, freezer, {"Office": "climate.trv"}, override_mode="until_next_reevaluation"
    )
    room = _room(entry, "Office")
    hass.states.async_set("climate.trv", "heat", {**TRV, "temperature": 23.0}, context=Context())
    await _tick(hass, freezer, 5)
    assert room.override is not None
    assert room.override["until"] is None
    # Hours later, the same situation: it stays.
    for _ in range(3):
        await _tick(hass, freezer, 600)
    assert room.override is not None
    # The mode changes: it ends.
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": "select.home_mode", "option": "summer"},
        blocking=True,
    )
    await _tick(hass, freezer, 5)
    assert room.override is None
    await _unload(hass, entry)


async def test_nearby_temperature_set_from_its_number(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """The fixed nearby temperature is kept by the room."""
    entry, _calls = await _trv_house(hass, freezer, {"Office": "climate.trv"})
    room = _room(entry, "Office")
    await room.async_set_level("nearby", 16.5)
    assert room.nearby_temp == 16.5
    await room.async_set_level("eco", 17.5)
    assert room.levels["eco"] == 17.5
    await _unload(hass, entry)


# ---------------------------------------------------------------------------
# Valve exercise and the Schedule helper
# ---------------------------------------------------------------------------
async def test_weekly_valve_exercise(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    """On its day and time the TRVs open fully for 5 minutes, once that day."""
    calls = async_mock_service(hass, "climate", "set_temperature")
    hass.states.async_set("climate.trv", "heat", TRV)
    entry = await _house(
        hass,
        freezer,
        [
            (
                "Office",
                {
                    "source": "climate",
                    "climates": ["climate.trv"],
                    "command_mode": "temperature",
                    "valve_exercise": True,
                    "valve_exercise_day": "mon",
                    "valve_exercise_time": "11:00:00",
                },
            )
        ],
    )
    assert hass.states.get("sensor.office_decision").state == "valve_exercise"
    # The highest temperature the TRV accepts, above the maximum of the house.
    assert calls[-1].data == {"entity_id": "climate.trv", "temperature": 30.0}
    await _tick(hass, freezer, 301)
    assert hass.states.get("sensor.office_decision").state == "schedule"
    assert calls[-1].data == {"entity_id": "climate.trv", "temperature": 21.0}
    # Not again the same day.
    for _ in range(3):
        await _tick(hass, freezer, 600)
    assert hass.states.get("sensor.office_decision").state == "schedule"
    await _unload(hass, entry)


async def test_schedule_from_a_schedule_helper(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """A Schedule helper: on = home (or the level in its data), off = sleep."""
    calls = async_mock_service(hass, "climate", "set_temperature")
    hass.states.async_set("climate.trv", "heat", TRV)
    next_event = "2026-10-12T15:00:00+03:00"
    hass.states.async_set("schedule.heating", "on", {"next_event": next_event})
    entry = await _house(
        hass,
        freezer,
        [
            (
                "Office",
                {
                    "source": "climate",
                    "climates": ["climate.trv"],
                    "command_mode": "temperature",
                    "schedule_source": "helper",
                    "schedule_helper": "schedule.heating",
                },
            )
        ],
    )
    decision = hass.states.get("sensor.office_decision")
    assert decision.attributes["preset"] == "home"
    assert [p["preset"] for p in decision.attributes["plan"]] == ["home", "sleep"]
    assert calls[-1].data["temperature"] == 21.0

    hass.states.async_set("schedule.heating", "on", {"next_event": next_event, "preset": "Eco"})
    await _tick(hass, freezer, 5)
    assert hass.states.get("sensor.office_decision").attributes["preset"] == "eco"
    hass.states.async_set("schedule.heating", "off", {"next_event": "2026-10-13T06:00:00+03:00"})
    await _tick(hass, freezer, 5)
    assert hass.states.get("sensor.office_decision").attributes["preset"] == "sleep"
    assert calls[-1].data["temperature"] == 18.0
    await _unload(hass, entry)


# ---------------------------------------------------------------------------
# Alerts: unavailable devices and low batteries
# ---------------------------------------------------------------------------
async def test_unavailable_trv_alert(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    """A TRV unavailable for 15 minutes is told; the alert ends when it is back."""
    entry, _calls = await _trv_house(hass, freezer, {"Office": "climate.trv"})
    house = entry.runtime_data
    hass.states.async_set("climate.trv", "unavailable")
    for _ in range(10):
        await _tick(hass, freezer, 60)
    assert "unavailable_climate.trv" not in house.active_alerts
    for _ in range(12):
        await _tick(hass, freezer, 60)
    assert house.active_alerts["unavailable_climate.trv"]["code"] == "device_unavailable"
    hass.states.async_set("climate.trv", "heat", TRV)
    for _ in range(6):
        await _tick(hass, freezer, 60)
    assert "unavailable_climate.trv" not in house.active_alerts
    await _unload(hass, entry)


async def test_low_battery_alert(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    """A battery sensor of a room device below the threshold (20 %) is told, once back up it ends."""
    zigbee = MockConfigEntry(domain="zha")
    zigbee.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=zigbee.entry_id, identifiers={("zha", "trv1")}, name="Office TRV"
    )
    registry = er.async_get(hass)
    registry.async_get_or_create(
        "climate", "zha", "trv1", device_id=device.id, suggested_object_id="trv"
    )
    battery = registry.async_get_or_create(
        "sensor",
        "zha",
        "trv1_battery",
        device_id=device.id,
        original_device_class="battery",
        suggested_object_id="trv_battery",
    ).entity_id
    hass.states.async_set(battery, "12", {"unit_of_measurement": "%"})
    entry, _calls = await _trv_house(hass, freezer, {"Office": "climate.trv"})
    house = entry.runtime_data
    room = _room(entry, "Office")
    room.check_batteries()
    alert = house.active_alerts[f"battery_{battery}"]
    assert alert["code"] == "battery_low"
    assert alert["params"] == {"device": "Office TRV", "level": 12}
    hass.states.async_set(battery, "85", {"unit_of_measurement": "%"})
    room.check_batteries()
    assert f"battery_{battery}" not in house.active_alerts
    await _unload(hass, entry)


# ---------------------------------------------------------------------------
# The house: a thermostat as the heat source, tariff and solar, calendar, alerts
# ---------------------------------------------------------------------------
async def _reevaluate(hass: HomeAssistant) -> None:
    await hass.services.async_call(DOMAIN, "reevaluate", {}, blocking=True)
    await hass.async_block_till_done()


async def test_thermostat_as_the_heat_source(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """A boiler thermostat as the heat source: only its mode is switched, never its target.

    A TRV room heats only while the thermostat really heats (its hvac_action).
    """
    modes = async_mock_service(hass, "climate", "set_hvac_mode")
    temperatures = async_mock_service(hass, "climate", "set_temperature")
    hive = {"hvac_modes": ["heat", "off"], "current_temperature": 21.0, "temperature": 25.0}
    hass.states.async_set("climate.hive", "off", {**hive, "hvac_action": "off"})
    cold = {**TRV, "current_temperature": 18.0, "temperature": 21.0, "hvac_action": "heating"}
    hass.states.async_set("climate.trv", "heat", cold)
    entry = await _house(
        hass,
        freezer,
        [
            (
                "Office",
                {"source": "climate", "climates": ["climate.trv"], "command_mode": "temperature"},
            )
        ],
        boiler_entity="climate.hive",
    )
    room = _room(entry, "Office")
    assert modes[-1].data == {"entity_id": "climate.hive", "hvac_mode": "heat"}
    assert all(c.data["entity_id"] != "climate.hive" for c in temperatures)

    # Switched to heat, but its own sensor is warm enough: it does not heat yet.
    hass.states.async_set("climate.hive", "heat", {**hive, "hvac_action": "idle"})
    await _reevaluate(hass)
    assert room.heat_demand
    assert not room.heating
    hass.states.async_set("climate.hive", "heat", {**hive, "hvac_action": "heating"})
    await _reevaluate(hass)
    assert room.heating

    # The room is warm, its TRV closes: the thermostat is switched off.
    hass.states.async_set(
        "climate.trv", "heat", {**cold, "current_temperature": 21.5, "hvac_action": "idle"}
    )
    await _reevaluate(hass)
    assert modes[-1].data == {"entity_id": "climate.hive", "hvac_mode": "off"}
    await _unload(hass, entry)


async def test_tariff_and_solar_adjust_the_target(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """A high price lowers the target, a low price and a PV surplus raise it."""
    assert await async_setup_component(hass, "input_boolean", {"input_boolean": {"heater": {}}})
    hass.states.async_set("sensor.room_temp", "20.0", {"unit_of_measurement": "°C"})
    hass.states.async_set("sensor.price", "0.30")
    hass.states.async_set("sensor.pv", "200", {"unit_of_measurement": "W"})
    entry = await _house(
        hass,
        freezer,
        [
            (
                "Bedroom",
                {
                    "source": "switch",
                    "switches": ["input_boolean.heater"],
                    "temperature_sensors": ["sensor.room_temp"],
                },
            )
        ],
        price_sensor="sensor.price",
        price_high=0.5,
        price_low=0.1,
        pv_sensor="sensor.pv",
    )
    target = lambda: hass.states.get("sensor.bedroom_target_temperature").state
    assert target() == "21.0"
    # 21 − 1 at a high price.
    hass.states.async_set("sensor.price", "0.70")
    await _reevaluate(hass)
    assert target() == "20.0"
    # 21 + 0.5 at a low price, + 0.5 more with 1500 W of surplus (from 1000 W).
    hass.states.async_set("sensor.price", "0.05")
    hass.states.async_set("sensor.pv", "1500", {"unit_of_measurement": "W"})
    await _reevaluate(hass)
    assert target() == "22.0"
    offsets = [o[0] for o in hass.states.get("sensor.bedroom_decision").attributes["offsets"]]
    assert offsets == ["tariff_low", "pv_surplus"]
    await _unload(hass, entry)


async def test_calendar_event_names_the_level(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """An event titled with a level name sets that level while it runs."""
    calls = async_mock_service(hass, "climate", "set_temperature")
    hass.states.async_set("climate.trv", "heat", TRV)
    hass.states.async_set(
        "calendar.heating", "on", {"message": "Eco", "end_time": "2026-10-12 14:00:00"}
    )
    entry = await _house(
        hass,
        freezer,
        [
            (
                "Office",
                {"source": "climate", "climates": ["climate.trv"], "command_mode": "temperature"},
            )
        ],
        calendar="calendar.heating",
    )
    await _reevaluate(hass)
    assert hass.states.get("sensor.office_decision").attributes["preset"] == "eco"
    assert hass.states.get("sensor.office_target_temperature").state == "17.0"
    hass.states.async_set("calendar.heating", "off", {})
    await _reevaluate(hass)
    assert hass.states.get("sensor.office_decision").attributes["preset"] == "home"
    assert calls[-1].data["temperature"] == 21.0
    await _unload(hass, entry)


async def test_alerts_to_a_notify_entity_and_a_failing_service(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, caplog: pytest.LogCaptureFixture
) -> None:
    """A notify entity gets send_message; a service that fails is logged instead."""
    sent = async_mock_service(hass, "notify", "send_message")
    hass.states.async_set("notify.living_tv", "unknown")
    entry, _calls = await _trv_house(
        hass,
        freezer,
        {"Office": "climate.trv"},
        notify_critical=["notify.living_tv"],
        notify_warning=["notify.missing"],
    )
    house = entry.runtime_data
    room = _room(entry, "Office")
    house.notify(
        "dev",
        "x",
        code="device_unavailable",
        params={"entity": "climate.trv", "minutes": 15},
        room=room.id,
    )
    house.notify("win", "x", code="window_long", params={"minutes": 30}, room=room.id)
    await hass.async_block_till_done()
    assert sent[-1].data == {
        "entity_id": "notify.living_tv",
        "title": "Home",
        "message": "Office: climate.trv has been unavailable for more than 15 min.",
    }
    assert "Notification via notify.missing failed" in caplog.text
    await _unload(hass, entry)


async def test_buttons_of_the_house_and_the_room(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Clear the manual changes (house or room), the vacation, and evaluate again."""
    entry, _calls = await _trv_house(hass, freezer, {"Office": "climate.trv"})
    room = _room(entry, "Office")
    house_buttons = hass.states.get("sensor.home_presence").attributes["house_entities"]
    room_buttons = hass.states.get("sensor.office_decision").attributes["entities"]

    async def press(entity_id: str) -> None:
        await hass.services.async_call("button", "press", {"entity_id": entity_id}, blocking=True)
        await hass.async_block_till_done()

    for clear in (room_buttons["clear_override"], house_buttons["clear_overrides"]):
        await hass.services.async_call(
            DOMAIN, "set_override", {"room": "Office", "temperature": 23}, blocking=True
        )
        await hass.async_block_till_done()
        assert room.override is not None
        await press(clear)
        assert room.override is None
    await hass.services.async_call(
        DOMAIN,
        "set_vacation",
        {"start": "2026-10-20T08:00:00+03:00", "end": "2026-10-25T18:00:00+03:00"},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert entry.runtime_data.vacation_end is not None
    await press(house_buttons["clear_vacation"])
    assert entry.runtime_data.vacation_end is None
    await press(house_buttons["reevaluate"])
    assert hass.states.get("sensor.office_decision").state == "schedule"
    await _unload(hass, entry)


async def test_an_invalid_schedule_uses_the_default_and_is_told(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """A schedule that cannot be read: the default one, an alert and the error shown."""
    hass.states.async_set("climate.trv", "heat", TRV)
    async_mock_service(hass, "climate", "set_temperature")
    entry = await _house(
        hass,
        freezer,
        [
            (
                "Office",
                {
                    "source": "climate",
                    "climates": ["climate.trv"],
                    "command_mode": "temperature",
                    "schedule": "workday: 25:00 home",
                },
            )
        ],
    )
    room = _room(entry, "Office")
    assert room.schedule_error
    assert f"schedule_{room.id}" in entry.runtime_data.active_alerts
    # The default schedule: home at noon on a workday.
    assert hass.states.get("sensor.office_decision").attributes["preset"] == "home"
    await _unload(hass, entry)


async def test_schedule_service_refuses_what_it_cannot_use(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Both forms at once, a room with a Schedule helper, a bad text, an unknown level."""
    hass.states.async_set("climate.trv", "heat", TRV)
    hass.states.async_set("climate.trv2", "heat", TRV)
    hass.states.async_set("schedule.heating", "on", {})
    async_mock_service(hass, "climate", "set_temperature")
    entry = await _house(
        hass,
        freezer,
        [
            (
                "Office",
                {"source": "climate", "climates": ["climate.trv"], "command_mode": "temperature"},
            ),
            (
                "Kitchen",
                {
                    "source": "climate",
                    "climates": ["climate.trv2"],
                    "command_mode": "temperature",
                    "schedule_source": "helper",
                    "schedule_helper": "schedule.heating",
                },
            ),
        ],
    )
    for data, key in (
        (
            {"room": "Office", "schedule": "workday: 00:00 home", "profiles": {}},
            "schedule_or_profiles",
        ),
        ({"room": "Kitchen", "schedule": "workday: 00:00 home"}, "schedule_external"),
        ({"room": "Office", "schedule": "workday: later home"}, "invalid_schedule"),
    ):
        with pytest.raises(ServiceValidationError) as err:
            await hass.services.async_call(DOMAIN, "set_schedule", data, blocking=True)
        assert err.value.translation_key == key, data
    with pytest.raises(ServiceValidationError) as err:
        await hass.services.async_call(
            DOMAIN, "set_override", {"room": "Office", "preset": "party"}, blocking=True
        )
    assert err.value.translation_key == "unknown_preset"
    await _unload(hass, entry)


async def test_services_with_two_houses(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """With two houses a house service needs the house; an unknown one is refused."""
    hass.states.async_set("climate.trv", "heat", TRV)
    async_mock_service(hass, "climate", "set_temperature")
    first = await _house(
        hass,
        freezer,
        [
            (
                "Office",
                {"source": "climate", "climates": ["climate.trv"], "command_mode": "temperature"},
            )
        ],
    )
    second = MockConfigEntry(
        domain=DOMAIN,
        title="Cabin",
        options={"persons": ["person.andrei"], "nearby_zones": []},
    )
    second.add_to_hass(hass)
    assert await hass.config_entries.async_setup(second.entry_id)
    await hass.async_block_till_done()
    vacation = {"start": "2026-10-20T08:00:00+03:00", "end": "2026-10-25T18:00:00+03:00"}
    with pytest.raises(ServiceValidationError) as err:
        await hass.services.async_call(DOMAIN, "set_vacation", vacation, blocking=True)
    assert err.value.translation_key == "house_ambiguous"
    with pytest.raises(ServiceValidationError) as err:
        await hass.services.async_call(
            DOMAIN, "set_vacation", {**vacation, "config_entry_id": "nope"}, blocking=True
        )
    assert err.value.translation_key == "house_not_found"
    await hass.services.async_call(
        DOMAIN, "set_vacation", {**vacation, "config_entry_id": second.entry_id}, blocking=True
    )
    await hass.async_block_till_done()
    assert second.runtime_data.vacation_end is not None
    assert first.runtime_data.vacation_end is None
    await _unload(hass, second)
    await _unload(hass, first)


async def test_calibration_offset_from_the_trv_on_the_same_device(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Offset calibration: the difference between the room sensor and the TRV of that device."""
    zigbee = MockConfigEntry(domain="zha")
    zigbee.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=zigbee.entry_id, identifiers={("zha", "trv1")}, name="Office TRV"
    )
    registry = er.async_get(hass)
    registry.async_get_or_create(
        "climate", "zha", "trv1", device_id=device.id, suggested_object_id="trv"
    )
    registry.async_get_or_create(
        "number", "zha", "trv1_offset", device_id=device.id, suggested_object_id="trv_offset"
    )
    # The TRV next to the radiator reads 22 °C, the room 20 °C.
    hass.states.async_set(
        "climate.trv", "heat", {**TRV, "current_temperature": 22.0, "hvac_action": "idle"}
    )
    hass.states.async_set("sensor.office_temp", "20.0", {"unit_of_measurement": "°C"})
    hass.states.async_set("number.trv_offset", "0.0", {"min": -5, "max": 5, "step": 0.1})
    async_mock_service(hass, "climate", "set_temperature")
    entry = await _house(
        hass,
        freezer,
        [
            (
                "Office",
                {
                    "source": "climate",
                    "climates": ["climate.trv"],
                    "command_mode": "temperature",
                    "temperature_sensors": ["sensor.office_temp"],
                    "calibration_mode": "offset",
                    "calibration_entities": ["number.trv_offset"],
                },
            )
        ],
    )
    # Mocked after the setup: the integration's own number platform registers the service.
    numbers = async_mock_service(hass, "number", "set_value")
    await _tick(hass, freezer, 601)  # written at most every 10 minutes
    # 0 + (20 − 22) = −2.0.
    assert numbers[-1].data == {"entity_id": "number.trv_offset", "value": -2.0}
    await _unload(hass, entry)
