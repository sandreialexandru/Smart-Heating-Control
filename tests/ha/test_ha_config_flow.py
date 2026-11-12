"""Config flow and room subentry flow tests."""

from __future__ import annotations

import pytest
from homeassistant.config_entries import SOURCE_RECONFIGURE, SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.advanced_climate.const import DOMAIN, SUBENTRY_ROOM


def _keys(result) -> set[str]:
    return {str(k) for k in result["data_schema"].schema}


async def _until(hass, result, flow, *, stop: set[str], data=None, limit: int = 15):
    """Submit empty forms until one of ``stop`` (a step id or a result type) is reached."""
    for _ in range(limit):
        if result["type"] is not FlowResultType.FORM or result["step_id"] in stop:
            return result
        result = await flow.async_configure(result["flow_id"], data or {})
    return result


async def test_user_flow(hass: HomeAssistant) -> None:
    """The house is created with people, nearby zones and a relay zone."""
    flow = hass.config_entries.flow
    result = await flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    result = await flow.async_configure(
        result["flow_id"],
        {"name": "Home", "persons": [], "nearby_zones": [], "home_rule": "any"},
    )
    assert result["step_id"] == "heating"
    assert _keys(result) == {"source"}
    result = await flow.async_configure(result["flow_id"], {"source": "switch"})
    assert result["step_id"] == "heating_devices"
    assert _keys(result) == {"switches"}
    result = await flow.async_configure(result["flow_id"], {"switches": []})
    assert result["errors"] == {"switches": "no_devices"}
    result = await flow.async_configure(result["flow_id"], {"switches": ["input_boolean.heater"]})
    assert result["step_id"] == "heating_on_off"
    # A relay needs a temperature sensor.
    result = await flow.async_configure(result["flow_id"], {})
    assert result["errors"] == {"temperature_sensors": "sensor_required"}
    result = await flow.async_configure(
        result["flow_id"], {"temperature_sensors": ["sensor.room"], "hysteresis": 0.5}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Home"
    assert result["options"]["home_rule"] == "any"
    zone = next(iter(result["result"].subentries.values()))
    assert zone.title == "Whole house"
    assert zone.unique_id == "whole_house"
    assert zone.data["switches"] == ["input_boolean.heater"]
    assert zone.data["temperature_sensors"] == ["sensor.room"]
    assert zone.data["hysteresis"] == 0.5


async def test_user_flow_without_devices(hass: HomeAssistant) -> None:
    """A house can be created without heating devices."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": "Home", "persons": [], "nearby_zones": []}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"source": "none"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert not result["result"].subentries


async def test_options_heating_adds_zone(hass: HomeAssistant) -> None:
    """The options add the whole-house zone to an existing house, then edit it."""
    entry = MockConfigEntry(domain=DOMAIN, title="Home 101", options={})
    entry.add_to_hass(hass)
    flow = hass.config_entries.options
    result = await flow.async_init(entry.entry_id)
    result = await flow.async_configure(result["flow_id"], {"next_step_id": "heating"})
    assert result["step_id"] == "heating"
    result = await flow.async_configure(result["flow_id"], {"source": "climate"})
    assert _keys(result) == {"climates", "command_mode", "trv_boost"}
    result = await flow.async_configure(
        result["flow_id"], {"climates": ["climate.trv"], "command_mode": "temperature"}
    )
    assert result["step_id"] == "heating_thermostat"
    # climate.trv is not available now: the hysteresis is asked for.
    assert _keys(result) == {"hysteresis"}
    result = await flow.async_configure(result["flow_id"], {"hysteresis": 0.4})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    zone = next(iter(entry.subentries.values()))
    assert zone.title == "Whole house"
    assert zone.data["hysteresis"] == 0.4
    # Editing again updates the same zone; the other devices are cleared.
    result = await flow.async_init(entry.entry_id)
    result = await flow.async_configure(result["flow_id"], {"next_step_id": "heating"})
    result = await flow.async_configure(result["flow_id"], {"source": "switch"})
    result = await flow.async_configure(
        result["flow_id"], {"switches": ["input_boolean.heater", "input_boolean.other"]}
    )
    assert result["step_id"] == "heating_on_off"
    result = await flow.async_configure(result["flow_id"], {"temperature_sensors": ["sensor.room"]})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert len(entry.subentries) == 1
    data = next(iter(entry.subentries.values())).data
    assert data["switches"] == ["input_boolean.heater", "input_boolean.other"]
    assert data["climates"] == []


async def test_options_follow_up_only_when_needed(hass: HomeAssistant) -> None:
    """The second form only appears with the values that apply."""
    entry = MockConfigEntry(domain=DOMAIN, title="Home", options={"persons": []})
    entry.add_to_hass(hass)
    flow = hass.config_entries.options
    result = await flow.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.MENU
    result = await flow.async_configure(result["flow_id"], {"next_step_id": "behavior"})
    assert "override_hours" not in _keys(result)
    result = await flow.async_configure(
        result["flow_id"], {"override_mode": "until_next_reevaluation"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["override_mode"] == "until_next_reevaluation"
    # Fixed duration asks for the hours.
    result = await flow.async_init(entry.entry_id)
    result = await flow.async_configure(result["flow_id"], {"next_step_id": "behavior"})
    result = await flow.async_configure(result["flow_id"], {"override_mode": "fixed"})
    assert result["step_id"] == "behavior_details"
    assert _keys(result) == {"override_hours"}
    result = await flow.async_configure(result["flow_id"], {"override_hours": 3})
    assert entry.options["override_hours"] == 3
    # Energy without sensors has no second form.
    result = await flow.async_init(entry.entry_id)
    result = await flow.async_configure(result["flow_id"], {"next_step_id": "energy"})
    assert _keys(result) == {"price_sensor", "pv_sensor"}
    result = await flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_weather_validation(hass: HomeAssistant) -> None:
    """Season dates are asked only for 'between dates' and are validated."""
    entry = MockConfigEntry(domain=DOMAIN, title="Home", options={})
    entry.add_to_hass(hass)
    flow = hass.config_entries.options
    result = await flow.async_init(entry.entry_id)
    result = await flow.async_configure(result["flow_id"], {"next_step_id": "weather"})
    assert "season_start" not in _keys(result)
    result = await flow.async_configure(
        result["flow_id"],
        {
            "season_mode": "dates",
            "cutoff_enabled": False,
            "forecast_enabled": False,
            "compensation_enabled": False,
        },
    )
    assert result["step_id"] == "weather_details"
    assert _keys(result) == {"season_start", "season_end"}
    result = await flow.async_configure(
        result["flow_id"], {"season_start": "13-40", "season_end": "04-15"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"season_start": "invalid_month_day"}
    result = await flow.async_configure(
        result["flow_id"], {"season_start": "10-15", "season_end": "04-15"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["season_start"] == "10-15"


async def test_weather_needs_an_outdoor_source(hass: HomeAssistant) -> None:
    """Weather functions are refused without an outdoor sensor or a weather entity."""
    entry = MockConfigEntry(domain=DOMAIN, title="Home", options={})
    entry.add_to_hass(hass)
    flow = hass.config_entries.options
    result = await flow.async_init(entry.entry_id)
    result = await flow.async_configure(result["flow_id"], {"next_step_id": "weather"})
    result = await flow.async_configure(
        result["flow_id"],
        {
            "cutoff_enabled": True,
            "forecast_enabled": True,
            "season_mode": "auto",
            "compensation_enabled": True,
            "window_ignore_above": 15,
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "weather"
    assert result["errors"] == {
        "cutoff_enabled": "outdoor_required",
        "season_mode": "outdoor_required",
        "compensation_enabled": "outdoor_required",
        "window_ignore_above": "outdoor_required",
        "forecast_enabled": "weather_required",
    }
    # An outdoor sensor is enough for everything but the forecast.
    result = await flow.async_configure(
        result["flow_id"],
        {
            "outdoor_sensor": "sensor.outdoor",
            "cutoff_enabled": True,
            "forecast_enabled": True,
            "season_mode": "auto",
            "compensation_enabled": True,
        },
    )
    assert result["errors"] == {"forecast_enabled": "weather_required"}
    # The forecast needs the cutoff too.
    result = await flow.async_configure(
        result["flow_id"],
        {
            "weather": "weather.home",
            "cutoff_enabled": False,
            "forecast_enabled": True,
            "season_mode": "always",
            "compensation_enabled": False,
        },
    )
    assert result["errors"] == {"forecast_enabled": "cutoff_required"}
    result = await flow.async_configure(
        result["flow_id"],
        {
            "weather": "weather.home",
            "cutoff_enabled": True,
            "forecast_enabled": True,
            "season_mode": "always",
            "compensation_enabled": False,
        },
    )
    assert result["step_id"] == "weather_details"


async def test_room_subentry_flow(hass: HomeAssistant) -> None:
    """A relay room is added and then reconfigured."""
    # An outdoor sensor (the optimal stop needs it), no weather (no solar gain), a
    # nearby zone (the room's nearby choices).
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Home",
        options={"outdoor_sensor": "sensor.outdoor", "nearby_zones": ["zone.city"]},
    )
    entry.add_to_hass(hass)
    flow = hass.config_entries.subentries

    result = await flow.async_init((entry.entry_id, SUBENTRY_ROOM), context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "basics"
    result = await flow.async_configure(result["flow_id"], {"name": "Bedroom", "source": "switch"})
    assert result["step_id"] == "devices"
    result = await flow.async_configure(result["flow_id"], {"switches": []})
    assert result["errors"] == {"switches": "no_devices"}
    result = await flow.async_configure(result["flow_id"], {"switches": ["input_boolean.heater"]})
    # Relays: only the on / off settings.
    assert result["step_id"] == "control_on_off"
    assert _keys(result) == {"hysteresis", "min_on_minutes", "min_off_minutes", "inertia_control"}
    result = await flow.async_configure(result["flow_id"], {})
    assert result["step_id"] == "levels"
    assert "nearby_temp" not in _keys(result)
    # Eco named "home" would take the place of home in the schedule: refused.
    result = await flow.async_configure(
        result["flow_id"], {"name_home": "Acasă", "name_eco": "home", "nearby_mode": "preset"}
    )
    assert result["errors"] == {"base": "level_name_is_key"}
    result = await flow.async_configure(
        result["flow_id"], {"name_home": "Day", "name_sleep": "Night", "nearby_mode": "temperature"}
    )
    assert result["step_id"] == "levels_nearby"
    result = await flow.async_configure(result["flow_id"], {"nearby_temp": 18})
    assert result["step_id"] == "sensors"
    assert _keys(result) == {"temperature_sensors", "occupancy_sensors", "humidity_sensor"}
    result = await flow.async_configure(result["flow_id"], {})
    assert result["errors"] == {"temperature_sensors": "sensor_required"}
    result = await flow.async_configure(result["flow_id"], {"temperature_sensors": ["sensor.room"]})
    # One sensor and no occupancy sensors: no details form.
    assert result["step_id"] == "windows"
    result = await flow.async_configure(result["flow_id"], {})
    # No window sensors and no detection: no delays form.
    assert result["step_id"] == "schedule"
    assert _keys(result) == {"schedule_source", "optimal_start", "optimal_stop"}
    result = await flow.async_configure(
        result["flow_id"], {"optimal_start": True, "optimal_stop": True}
    )
    assert result["step_id"] == "schedule_internal"
    result = await flow.async_configure(
        result["flow_id"], {"schedule": "workday: 06:00 Day, 25:00 Night"}
    )
    assert result["errors"] == {"schedule": "invalid_schedule"}
    result = await flow.async_configure(
        result["flow_id"], {"schedule": "workday: 00:00 Night, 06:00 Day, 22:00 Night"}
    )
    assert result["step_id"] == "schedule_optimal"
    # A relay keeps its hysteresis as the comfort of the optimal stop.
    assert _keys(result) == {"optimal_start_max_minutes", "optimal_stop_minutes"}
    result = await flow.async_configure(result["flow_id"], {})
    # No weather entity (no solar gain) and no TRVs: nothing more to ask.
    assert result["type"] is FlowResultType.CREATE_ENTRY

    subentry = next(iter(entry.subentries.values()))
    assert subentry.title == "Bedroom"
    assert subentry.data["switches"] == ["input_boolean.heater"]
    assert subentry.data["preset_names"]["home"] == "Day"
    assert subentry.data["nearby_temp"] == 18

    result = await entry.start_subentry_reconfigure_flow(hass, subentry.subentry_id)
    assert result["step_id"] == "basics"
    result = await flow.async_configure(
        result["flow_id"], {"name": "Master bedroom", "source": "switch"}
    )
    result = await _until(hass, result, flow, stop=set())
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.subentries[subentry.subentry_id].title == "Master bedroom"
    assert SOURCE_RECONFIGURE


async def test_room_with_thermostat_presets(hass: HomeAssistant) -> None:
    """With preset control the levels pick thermostat presets and keep temperatures."""
    hass.states.async_set(
        "climate.trv",
        "heat",
        {"preset_modes": ["none", "comfort", "eco", "away", "boost"], "preset_mode": "none"},
    )
    entry = MockConfigEntry(domain=DOMAIN, title="Home", options={"weather": "weather.home"})
    entry.add_to_hass(hass)
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_ROOM), context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"name": "Office", "source": "climate"}
    )
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"climates": ["climate.trv"], "command_mode": "preset"}
    )
    # This TRV does not report hvac_action: its heat demand uses the hysteresis.
    assert result["step_id"] == "control_thermostat"
    assert {str(k) for k in result["data_schema"].schema} == {"hysteresis"}
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"hysteresis": 0.4}
    )
    assert result["step_id"] == "levels"
    assert result["description_placeholders"]["presets"] == "comfort, eco, away, boost"
    schema = result["data_schema"].schema
    assert any(str(key) == "device_home" for key in schema)
    assert not any(str(key) == "name_home" for key in schema)

    # Two levels on the same preset are refused.
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"device_home": "comfort", "device_comfort": "comfort"}
    )
    assert result["errors"] == {"base": "duplicate_names"}
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            "device_home": "comfort",
            "device_eco": "eco",
            "device_comfort": "boost",
            "temp_sleep": 18.5,
        },
    )
    assert result["step_id"] == "sensors"
    assert "calibration_mode" in _keys(result)
    flow = hass.config_entries.subentries
    result = await _until(hass, result, flow, stop={"schedule_internal"})
    assert result["step_id"] == "schedule_internal"
    result = await flow.async_configure(
        result["flow_id"], {"schedule": "workday: 00:00 sleep, 07:00 comfort, 22:00 sleep"}
    )
    assert result["step_id"] == "extras"
    assert _keys(result) == {"solar_offset", "valve_exercise"}
    result = await flow.async_configure(result["flow_id"], {"valve_exercise": True})
    assert result["step_id"] == "extras_valves"
    result = await flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY

    subentry = next(iter(entry.subentries.values()))
    assert subentry.data["preset_map"] == {"home": "comfort", "eco": "eco", "comfort": "boost"}
    assert subentry.data["levels"]["sleep"] == 18.5
    assert subentry.data["preset_names"] == {}
    assert subentry.data["hysteresis"] == 0.4


async def test_fahrenheit_forms(hass: HomeAssistant) -> None:
    """Forms of a °F house show and accept °F; values are stored in °C."""
    entry = MockConfigEntry(
        domain=DOMAIN, title="Home", options={"temperature_unit": "fahrenheit", "frost_temp": 7.0}
    )
    entry.add_to_hass(hass)
    flow = hass.config_entries.options
    result = await flow.async_init(entry.entry_id)
    result = await flow.async_configure(result["flow_id"], {"next_step_id": "behavior"})
    schema = {str(k): k for k in result["data_schema"].schema}
    # 7 °C is shown as 44.6 °F
    assert schema["frost_temp"].default() == 44.6
    selector_config = result["data_schema"].schema[schema["frost_temp"]].config
    assert selector_config["unit_of_measurement"] == "°F"
    # 3 … 15 °C, rounded outwards to a tenth of a degree.
    assert (selector_config["min"], selector_config["max"]) == (37.4, 59.0)
    result = await flow.async_configure(
        result["flow_id"], {"override_mode": "until_next_reevaluation", "frost_temp": 46.4}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert round(entry.options["frost_temp"], 2) == 8.0


async def test_reconfigure_unit(hass: HomeAssistant) -> None:
    """The unit of the house is changed with Reconfigure."""
    entry = MockConfigEntry(domain=DOMAIN, title="Home", options={"persons": []})
    entry.add_to_hass(hass)
    result = await entry.start_reconfigure_flow(hass)
    assert result["step_id"] == "reconfigure"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"temperature_unit": "fahrenheit"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.options["temperature_unit"] == "fahrenheit"
    assert entry.options["persons"] == []


async def test_optimal_stop_tolerance_only_with_hvac_action(hass: HomeAssistant) -> None:
    """Thermostats without hvac_action use the hysteresis as the comfort of the optimal stop."""
    entry = MockConfigEntry(
        domain=DOMAIN, title="Home", options={"outdoor_sensor": "sensor.outdoor"}
    )
    entry.add_to_hass(hass)
    flow = hass.config_entries.subentries
    for attributes, expected in (
        ({"hvac_action": "idle"}, {"optimal_stop_minutes", "stop_tolerance"}),
        ({}, {"optimal_stop_minutes"}),
    ):
        hass.states.async_set("climate.trv", "heat", {"hvac_modes": ["heat", "off"], **attributes})
        result = await flow.async_init(
            (entry.entry_id, SUBENTRY_ROOM), context={"source": SOURCE_USER}
        )
        result = await flow.async_configure(
            result["flow_id"], {"name": "Office", "source": "climate"}
        )
        result = await flow.async_configure(
            result["flow_id"], {"climates": ["climate.trv"], "command_mode": "temperature"}
        )
        result = await _until(hass, result, flow, stop={"schedule"})
        result = await flow.async_configure(result["flow_id"], {"optimal_stop": True})
        result = await _until(hass, result, flow, stop={"schedule_optimal"})
        assert result["step_id"] == "schedule_optimal"
        assert _keys(result) == expected
        flow.async_abort(result["flow_id"])


def _house_with_rooms(
    hass: HomeAssistant, options: dict | None = None, rooms=()
) -> MockConfigEntry:
    """A house with the given rooms: (title, data)."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Home",
        options=options or {},
        subentries_data=[
            {"data": data, "subentry_type": SUBENTRY_ROOM, "title": title, "unique_id": None}
            for title, data in rooms
        ],
    )
    entry.add_to_hass(hass)
    return entry


def _gt_climate(hass: HomeAssistant, heater: str) -> str:
    """A Generic Thermostat entry with its climate entity; returns the entity id."""
    from homeassistant.helpers import entity_registry as er

    gt_entry = MockConfigEntry(domain="generic_thermostat", options={"heater": heater})
    gt_entry.add_to_hass(hass)
    item = er.async_get(hass).async_get_or_create(
        "climate", "generic_thermostat", gt_entry.entry_id, config_entry=gt_entry
    )
    return item.entity_id


RELAY_ROOM = {
    "source": "switch",
    "switches": ["input_boolean.heater"],
    "climates": [],
    "temperature_sensors": ["sensor.room"],
}


async def test_a_device_is_commanded_by_one_room_only(hass: HomeAssistant) -> None:
    """A relay of a room cannot be chosen again for another room, but stays in its own."""
    entry = _house_with_rooms(hass, rooms=[("Bedroom", RELAY_ROOM)])
    flow = hass.config_entries.subentries
    result = await flow.async_init((entry.entry_id, SUBENTRY_ROOM), context={"source": SOURCE_USER})
    result = await flow.async_configure(result["flow_id"], {"name": "Office", "source": "switch"})
    result = await flow.async_configure(result["flow_id"], {"switches": ["input_boolean.heater"]})
    assert result["errors"] == {"switches": "entity_in_room"}
    assert result["description_placeholders"]["owner"] == "Home → Bedroom"
    result = await flow.async_configure(result["flow_id"], {"switches": ["input_boolean.other"]})
    assert result["step_id"] == "control_on_off"
    # Reconfiguring the room itself keeps its relay.
    subentry = next(iter(entry.subentries.values()))
    result = await entry.start_subentry_reconfigure_flow(hass, subentry.subentry_id)
    result = await flow.async_configure(result["flow_id"], {"name": "Bedroom", "source": "switch"})
    result = await flow.async_configure(result["flow_id"], {"switches": ["input_boolean.heater"]})
    assert result["step_id"] == "control_on_off"


async def test_room_asks_for_the_house_heat_source_only_with_one(hass: HomeAssistant) -> None:
    """The room form asks whether the room heats from the heat source only when the house has one."""
    flow = hass.config_entries.subentries
    for options, shown in (({}, False), ({"boiler_entity": "switch.boiler"}, True)):
        entry = _house_with_rooms(hass, options=options)
        result = await flow.async_init(
            (entry.entry_id, SUBENTRY_ROOM), context={"source": SOURCE_USER}
        )
        result = await flow.async_configure(result["flow_id"], {"name": "Bath", "source": "switch"})
        assert ("use_house_source" in _keys(result)) is shown
        if shown:
            result = await flow.async_configure(
                result["flow_id"],
                {"switches": ["input_boolean.bath_heater"], "use_house_source": False},
            )
            assert result["step_id"] == "control_on_off"


async def test_room_of_the_heat_source_may_be_a_secondary_room(hass: HomeAssistant) -> None:
    """Only a room of the heat source is asked whether it may start it (on by default)."""
    flow = hass.config_entries.subentries
    entry = _house_with_rooms(hass, options={"boiler_entity": "switch.boiler"})
    result = await flow.async_init((entry.entry_id, SUBENTRY_ROOM), context={"source": SOURCE_USER})
    result = await flow.async_configure(result["flow_id"], {"name": "Bath", "source": "switch"})
    result = await flow.async_configure(
        result["flow_id"],
        {"switches": ["input_boolean.bath_heater"], "use_house_source": True},
    )
    assert result["step_id"] == "house_source"
    assert _keys(result) == {"starts_house_source", "top_up"}
    default = next(k for k in result["data_schema"].schema if str(k) == "starts_house_source")
    assert default.default() is True
    default = next(k for k in result["data_schema"].schema if str(k) == "top_up")
    assert default.default() is False
    result = await flow.async_configure(result["flow_id"], {"starts_house_source": False})
    assert result["step_id"] == "control_on_off"
    # A room with its own heat is not asked.
    result = await flow.async_init((entry.entry_id, SUBENTRY_ROOM), context={"source": SOURCE_USER})
    result = await flow.async_configure(result["flow_id"], {"name": "Hall", "source": "switch"})
    result = await flow.async_configure(
        result["flow_id"],
        {"switches": ["input_boolean.hall_heater"], "use_house_source": False},
    )
    assert result["step_id"] == "control_on_off"


async def test_a_secondary_room_is_not_offered_as_the_reference_room(hass: HomeAssistant) -> None:
    """Only a room that may start the heat source can decide alone when it runs."""
    second = {**RELAY_ROOM, "switches": ["input_boolean.hall"], "starts_house_source": False}
    entry = _house_with_rooms(
        hass,
        options={"boiler_entity": "switch.boiler"},
        rooms=[
            ("Bedroom", RELAY_ROOM),
            ("Office", {**RELAY_ROOM, "switches": ["input_boolean.office"]}),
            ("Hall", second),
        ],
    )
    options = hass.config_entries.options
    result = await options.async_init(entry.entry_id)
    result = await options.async_configure(result["flow_id"], {"next_step_id": "boiler"})
    result = await options.async_configure(result["flow_id"], {"boiler_entity": "switch.boiler"})
    assert result["step_id"] == "boiler_details"
    field = next(k for k in result["data_schema"].schema if str(k) == "reference_room")
    offered = [o["label"] for o in result["data_schema"].schema[field].config["options"]]
    assert offered == ["Bedroom", "Office"]
    # Rooms needed: at most the rooms that may start the heat source.
    field = next(k for k in result["data_schema"].schema if str(k) == "boiler_min_rooms")
    assert result["data_schema"].schema[field].config["max"] == 2


async def test_heat_source_and_generic_thermostat_relay(hass: HomeAssistant) -> None:
    """The heat source is not a room device, nor the relay of a Generic Thermostat room."""
    climate = _gt_climate(hass, "switch.gt_relay")
    entry = _house_with_rooms(
        hass,
        options={"boiler_entity": "switch.boiler"},
        rooms=[
            ("Bedroom", RELAY_ROOM),
            ("Living", {"source": "generic_thermostat", "climates": [climate], "switches": []}),
        ],
    )
    options = hass.config_entries.options
    for boiler, error in (
        ("input_boolean.heater", "entity_in_room"),
        ("switch.gt_relay", "entity_is_gt_heater"),
    ):
        result = await options.async_init(entry.entry_id)
        result = await options.async_configure(result["flow_id"], {"next_step_id": "boiler"})
        result = await options.async_configure(result["flow_id"], {"boiler_entity": boiler})
        assert result["errors"] == {"boiler_entity": error}, boiler
    # The own heat source of the house is no conflict.
    result = await options.async_init(entry.entry_id)
    result = await options.async_configure(result["flow_id"], {"next_step_id": "boiler"})
    result = await options.async_configure(result["flow_id"], {"boiler_entity": "switch.boiler"})
    assert result["step_id"] == "boiler_details"
    # Rooms needed: at most the number of rooms of the house.
    field = next(k for k in result["data_schema"].schema if str(k) == "boiler_min_rooms")
    assert result["data_schema"].schema[field].config["max"] == 2
    # The boost is only for a thermostat as the heat source.
    assert "boiler_boost" not in {str(k) for k in result["data_schema"].schema}

    rooms = hass.config_entries.subentries
    for switch, error in (
        ("switch.boiler", "entity_is_source"),
        ("switch.gt_relay", "entity_is_gt_heater"),
    ):
        result = await rooms.async_init(
            (entry.entry_id, SUBENTRY_ROOM), context={"source": SOURCE_USER}
        )
        result = await rooms.async_configure(
            result["flow_id"], {"name": "Office", "source": "switch"}
        )
        result = await rooms.async_configure(result["flow_id"], {"switches": [switch]})
        assert result["errors"] == {"switches": error}, switch

    # A thermostat as the heat source: the boost, on by default.
    hass.states.async_set("climate.hive", "heat", {"hvac_modes": ["heat", "off"]})
    result = await options.async_init(entry.entry_id)
    result = await options.async_configure(result["flow_id"], {"next_step_id": "boiler"})
    result = await options.async_configure(result["flow_id"], {"boiler_entity": "climate.hive"})
    keys = {str(k): k for k in result["data_schema"].schema}
    assert "boiler_boost" in keys
    assert keys["boiler_boost"].default() is True
    result = await options.async_configure(
        result["flow_id"],
        {"boiler_min_rooms": 1, "boiler_min_on": 0, "boiler_min_off": 0, "boiler_boost": False},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["boiler_boost"] is False
    await hass.async_block_till_done()
    # The idle temperature: below the maximum of the house, kept in °C.
    result = await options.async_init(entry.entry_id)
    result = await options.async_configure(result["flow_id"], {"next_step_id": "boiler"})
    result = await options.async_configure(result["flow_id"], {"boiler_entity": "climate.hive"})
    assert "boiler_idle_temp" in {str(k) for k in result["data_schema"].schema}
    base = {"boiler_min_rooms": 1, "boiler_min_on": 0, "boiler_min_off": 0, "boiler_boost": True}
    result = await options.async_configure(result["flow_id"], {**base, "boiler_idle_temp": 25.0})
    assert result["errors"] == {"boiler_idle_temp": "idle_not_below_max"}
    result = await options.async_configure(result["flow_id"], {**base, "boiler_idle_temp": 17.5})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["boiler_idle_temp"] == 17.5
    await hass.async_block_till_done()


def _house_with_zone(
    hass: HomeAssistant, zone: dict, options: dict | None = None
) -> MockConfigEntry:
    """A house whose whole-house zone has the given data."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Home",
        options=options or {},
        subentries_data=[
            {
                "data": zone,
                "subentry_type": SUBENTRY_ROOM,
                "title": "Whole house",
                "unique_id": "whole_house",
            }
        ],
    )
    entry.add_to_hass(hass)
    return entry


@pytest.mark.parametrize(
    "zone",
    [
        {"source": "generic_thermostat", "climates": ["climate.gt"], "switches": []},
        RELAY_ROOM,
    ],
)
async def test_no_heat_source_menu_when_the_whole_house_starts_the_boiler(
    hass: HomeAssistant, zone: dict
) -> None:
    """A Generic Thermostat or relay on the whole house starts the boiler: no heat source menu."""
    entry = _house_with_zone(hass, zone)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert "boiler" not in result["menu_options"]
    assert "alerts" in result["menu_options"]


async def test_saving_a_generic_thermostat_whole_house_drops_the_heat_source(
    hass: HomeAssistant,
) -> None:
    """A heat source chosen before is removed when the whole-house heating is saved as GT."""
    climate = _gt_climate(hass, "switch.gt_relay")
    entry = _house_with_zone(
        hass,
        {"source": "generic_thermostat", "climates": [climate], "switches": []},
        options={"boiler_entity": "switch.boiler", "room_diff_alert": 2.0},
    )
    options = hass.config_entries.options
    result = await options.async_init(entry.entry_id)
    result = await options.async_configure(result["flow_id"], {"next_step_id": "heating"})
    result = await options.async_configure(result["flow_id"], {"source": "generic_thermostat"})
    result = await options.async_configure(result["flow_id"], {"climates": [climate]})
    assert result["type"] == "create_entry"
    assert "boiler_entity" not in entry.options
    assert entry.options["room_diff_alert"] == 2.0


async def test_heat_source_shown_for_trvs_on_the_whole_house(hass: HomeAssistant) -> None:
    """Another thermostat for the whole home: the heat source can be chosen."""
    entry = _house_with_zone(
        hass, {"source": "climate", "climates": ["climate.trv"], "command_mode": "temperature"}
    )
    options = hass.config_entries.options
    result = await options.async_init(entry.entry_id)
    assert "boiler" in result["menu_options"]
    result = await options.async_configure(result["flow_id"], {"next_step_id": "boiler"})
    assert result["step_id"] == "boiler"
    assert _keys(result) == {"boiler_entity"}


async def test_options_that_need_rooms_or_people(hass: HomeAssistant) -> None:
    """The colder-room alert and copying a manual change need two rooms; auto vacation, people."""
    options = hass.config_entries.options
    one = _house_with_rooms(hass, rooms=[("Bedroom", RELAY_ROOM)])
    result = await options.async_init(one.entry_id)
    result = await options.async_configure(result["flow_id"], {"next_step_id": "alerts"})
    assert "room_diff_alert" not in _keys(result)
    result = await options.async_init(one.entry_id)
    result = await options.async_configure(result["flow_id"], {"next_step_id": "behavior"})
    assert "override_scope" not in _keys(result)
    assert "auto_vacation_hours" not in _keys(result)

    two = _house_with_rooms(
        hass,
        options={"persons": ["person.andrei"]},
        rooms=[
            ("Bedroom", RELAY_ROOM),
            ("Office", {**RELAY_ROOM, "switches": ["input_boolean.b"]}),
        ],
    )
    result = await options.async_init(two.entry_id)
    result = await options.async_configure(result["flow_id"], {"next_step_id": "alerts"})
    assert "room_diff_alert" in _keys(result)
    result = await options.async_init(two.entry_id)
    result = await options.async_configure(result["flow_id"], {"next_step_id": "behavior"})
    assert {"override_scope", "auto_vacation_hours"} <= _keys(result)


async def test_nearby_level_only_with_nearby_zones(hass: HomeAssistant) -> None:
    """The room's nearby choices appear only when the house has nearby zones."""
    rooms = hass.config_entries.subentries
    for options, shown in (({}, False), ({"nearby_zones": ["zone.city"]}, True)):
        entry = _house_with_rooms(hass, options=options)
        result = await rooms.async_init(
            (entry.entry_id, SUBENTRY_ROOM), context={"source": SOURCE_USER}
        )
        result = await rooms.async_configure(
            result["flow_id"], {"name": "Bath", "source": "switch"}
        )
        result = await rooms.async_configure(result["flow_id"], {"switches": ["input_boolean.h"]})
        result = await rooms.async_configure(result["flow_id"], {})
        assert result["step_id"] == "levels"
        assert ("nearby_mode" in _keys(result)) is shown
    # A Generic Thermostat room without nearby zones has nothing to ask on the levels page.
    climate = _gt_climate(hass, "switch.gt_relay2")
    entry = _house_with_rooms(hass)
    result = await rooms.async_init(
        (entry.entry_id, SUBENTRY_ROOM), context={"source": SOURCE_USER}
    )
    result = await rooms.async_configure(
        result["flow_id"], {"name": "Living", "source": "generic_thermostat"}
    )
    result = await rooms.async_configure(result["flow_id"], {"climates": [climate]})
    assert result["step_id"] == "sensors_gt"


async def test_outdoor_sensor_is_not_a_room_sensor(hass: HomeAssistant) -> None:
    """The outdoor sensor and the room temperature sensors are different sensors."""
    entry = _house_with_rooms(
        hass, options={"outdoor_sensor": "sensor.outdoor"}, rooms=[("Bedroom", RELAY_ROOM)]
    )
    options = hass.config_entries.options
    result = await options.async_init(entry.entry_id)
    result = await options.async_configure(result["flow_id"], {"next_step_id": "weather"})
    result = await options.async_configure(result["flow_id"], {"outdoor_sensor": "sensor.room"})
    assert result["errors"] == {"outdoor_sensor": "outdoor_is_room_sensor"}

    rooms = hass.config_entries.subentries
    result = await rooms.async_init(
        (entry.entry_id, SUBENTRY_ROOM), context={"source": SOURCE_USER}
    )
    result = await rooms.async_configure(result["flow_id"], {"name": "Office", "source": "switch"})
    result = await rooms.async_configure(result["flow_id"], {"switches": ["input_boolean.other"]})
    result = await _until(hass, result, rooms, stop={"sensors"})
    assert result["step_id"] == "sensors"
    result = await rooms.async_configure(
        result["flow_id"], {"temperature_sensors": ["sensor.outdoor"]}
    )
    assert result["errors"] == {"temperature_sensors": "room_sensor_is_outdoor"}
    result = await rooms.async_configure(
        result["flow_id"], {"temperature_sensors": ["sensor.office"]}
    )
    assert result["step_id"] != "sensors"


async def test_generic_thermostat_room_has_no_temperature_sensors(hass: HomeAssistant) -> None:
    """A Generic Thermostat regulates by its own sensor: the room form does not ask for one.

    Saving the form drops a sensor chosen before.
    """
    climate = _gt_climate(hass, "switch.gt_relay")
    entry = _house_with_rooms(
        hass,
        rooms=[
            (
                "Living",
                {
                    "source": "generic_thermostat",
                    "climates": [climate],
                    "switches": [],
                    "temperature_sensors": ["sensor.living"],
                },
            )
        ],
    )
    rooms = hass.config_entries.subentries
    subentry = next(iter(entry.subentries.values()))
    result = await entry.start_subentry_reconfigure_flow(hass, subentry.subentry_id)
    result = await rooms.async_configure(
        result["flow_id"], {"name": "Living", "source": "generic_thermostat"}
    )
    result = await rooms.async_configure(result["flow_id"], {"climates": [climate]})
    result = await _until(hass, result, rooms, stop={"sensors_gt", "sensors"})
    assert result["step_id"] == "sensors_gt"
    assert _keys(result) == {"occupancy_sensors", "humidity_sensor"}
    result = await rooms.async_configure(result["flow_id"], {"occupancy_sensors": []})
    result = await _until(hass, result, rooms, stop=set())
    assert result["type"] is FlowResultType.ABORT
    assert entry.subentries[subentry.subentry_id].data["temperature_sensors"] == []


async def test_trv_boost_in_the_room_form(hass: HomeAssistant) -> None:
    """The boost is chosen with the devices; then only the boost page is asked."""
    # An outdoor sensor: the optimal stop can be turned on.
    entry = _house_with_rooms(hass, options={"outdoor_sensor": "sensor.outdoor"})
    rooms = hass.config_entries.subentries
    result = await rooms.async_init(
        (entry.entry_id, SUBENTRY_ROOM), context={"source": SOURCE_USER}
    )
    result = await rooms.async_configure(result["flow_id"], {"name": "Office", "source": "climate"})
    assert "trv_boost" in _keys(result)
    # Only with the temperature command.
    result = await rooms.async_configure(
        result["flow_id"],
        {"climates": ["climate.trv"], "command_mode": "preset", "trv_boost": True},
    )
    assert result["errors"] == {"trv_boost": "boost_temperature_only"}
    result = await rooms.async_configure(
        result["flow_id"],
        {"climates": ["climate.trv"], "command_mode": "temperature", "trv_boost": True},
    )
    # No Thermostat page: the tolerances are not used with the boost.
    assert result["step_id"] == "control_boost"
    assert _keys(result) == {"trv_boost_temperature", "hysteresis", "inertia_control"}
    result = await rooms.async_configure(
        result["flow_id"], {"trv_boost_temperature": 23, "hysteresis": 0.2}
    )
    result = await _until(hass, result, rooms, stop={"sensors"})
    assert result["step_id"] == "sensors"
    result = await rooms.async_configure(result["flow_id"], {})
    assert result["errors"] == {"temperature_sensors": "boost_sensor_required"}
    result = await rooms.async_configure(
        result["flow_id"], {"temperature_sensors": ["sensor.office"]}
    )
    # The optimal stop tolerance is not asked either.
    for _ in range(15):
        if result["type"] is not FlowResultType.FORM:
            break
        assert "stop_tolerance" not in _keys(result)
        data = {"optimal_stop": True} if result["step_id"] == "schedule" else {}
        result = await rooms.async_configure(result["flow_id"], data)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    data = next(sub for sub in entry.subentries.values() if sub.title == "Office").data
    assert data["trv_boost"] is True
    assert data["trv_boost_temperature"] == 23
    assert data["hysteresis"] == 0.2


async def test_frost_hysteresis_for_trvs_with_a_room_sensor(hass: HomeAssistant) -> None:
    """A TRV reporting hvac_action, with a room sensor: the hysteresis is asked for frost."""
    hass.states.async_set(
        "climate.trv", "heat", {"hvac_modes": ["heat", "off"], "hvac_action": "idle"}
    )
    entry = _house_with_rooms(hass)
    rooms = hass.config_entries.subentries
    result = await rooms.async_init(
        (entry.entry_id, SUBENTRY_ROOM), context={"source": SOURCE_USER}
    )
    result = await rooms.async_configure(result["flow_id"], {"name": "Office", "source": "climate"})
    result = await rooms.async_configure(
        result["flow_id"], {"climates": ["climate.trv"], "command_mode": "temperature"}
    )
    # hvac_action is reported: nothing to ask on the thermostat step, it is skipped.
    assert result["step_id"] == "levels"
    result = await _until(hass, result, rooms, stop={"sensors"})
    result = await rooms.async_configure(
        result["flow_id"], {"temperature_sensors": ["sensor.office"]}
    )
    assert result["step_id"] == "sensors_details"
    assert "hysteresis" in _keys(result)
    result = await rooms.async_configure(result["flow_id"], {"hysteresis": 0.5})
    result = await _until(hass, result, rooms, stop=set())
    assert result["type"] is FlowResultType.CREATE_ENTRY
    data = next(sub for sub in entry.subentries.values() if sub.title == "Office").data
    assert data["hysteresis"] == 0.5


async def test_options_alerts_recipients(hass: HomeAssistant) -> None:
    """The one service of earlier versions is offered as the recipient; saving replaces it."""
    hass.services.async_register("notify", "mobile_app_phone", lambda call: None)
    entry = MockConfigEntry(
        domain=DOMAIN, title="Home", options={"notify_service": "notify.mobile_app_phone"}
    )
    entry.add_to_hass(hass)
    flow = hass.config_entries.options
    result = await flow.async_init(entry.entry_id)
    result = await flow.async_configure(result["flow_id"], {"next_step_id": "alerts"})
    assert result["step_id"] == "alerts"
    assert {
        "notify_critical",
        "notify_warning",
        "notify_info",
        "notify_resolved",
        "quiet_start",
        "quiet_end",
    } <= _keys(result)
    suggested = {
        str(k): k.description.get("suggested_value")
        for k in result["data_schema"].schema
        if getattr(k, "description", None)
    }
    assert suggested["notify_critical"] == ["notify.mobile_app_phone"]
    assert suggested["notify_warning"] == ["notify.mobile_app_phone"]
    assert not suggested["notify_info"]
    result = await flow.async_configure(
        result["flow_id"],
        {
            "notify_critical": ["notify.mobile_app_phone"],
            "notify_warning": [],
            "notify_resolved": True,
            "quiet_start": "22:00:00",
            "quiet_end": "07:00:00",
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert "notify_service" not in entry.options
    assert entry.options["notify_critical"] == ["notify.mobile_app_phone"]
    assert entry.options["quiet_start"] == "22:00:00"


async def test_options_alerts_email_recipient(hass: HomeAssistant) -> None:
    """A mail service with addresses is accepted; a wrong address is refused."""
    entry = MockConfigEntry(domain=DOMAIN, title="Home", options={})
    entry.add_to_hass(hass)
    flow = hass.config_entries.options
    result = await flow.async_init(entry.entry_id)
    result = await flow.async_configure(result["flow_id"], {"next_step_id": "alerts"})
    result = await flow.async_configure(
        result["flow_id"], {"notify_warning": ["notify.me_gmail_com: ana@example, ion@example.com"]}
    )
    assert result["errors"] == {"notify_warning": "invalid_recipient"}
    assert result["description_placeholders"]["recipient"] == "ana@example"
    result = await flow.async_configure(
        result["flow_id"],
        {"notify_warning": ["notify.me_gmail_com: ana@example.com, ion@example.com"]},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["notify_warning"] == [
        "notify.me_gmail_com: ana@example.com, ion@example.com"
    ]


async def test_options_alerts_recipient_capital_letter(hass: HomeAssistant) -> None:
    """A phone keyboard writes "Notify." with a capital: it is accepted and stored in lower case."""
    entry = MockConfigEntry(domain=DOMAIN, title="Home", options={})
    entry.add_to_hass(hass)
    flow = hass.config_entries.options
    result = await flow.async_init(entry.entry_id)
    result = await flow.async_configure(result["flow_id"], {"next_step_id": "alerts"})
    result = await flow.async_configure(
        result["flow_id"], {"notify_critical": ["Notify.Me_gmail_com: Ana@Example.com"]}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    from custom_components.advanced_climate.alerts import split_recipient, targets

    assert split_recipient(targets(entry.options["notify_critical"])[0]) == (
        "notify.me_gmail_com",
        ["Ana@Example.com"],
    )


async def test_occupancy_and_humidity_fields(hass: HomeAssistant) -> None:
    """The presence time is asked only with occupancy sensors; the humidity sensor can be cleared."""
    hass.states.async_set(
        "sensor.hum", "55", {"device_class": "humidity", "unit_of_measurement": "%"}
    )
    hass.states.async_set("binary_sensor.motion", "off", {"device_class": "motion"})
    entry = _house_with_rooms(hass, rooms=[("Bedroom", RELAY_ROOM)])
    rooms = hass.config_entries.subentries
    subentry = next(iter(entry.subentries.values()))

    async def to_sensors():
        result = await entry.start_subentry_reconfigure_flow(hass, subentry.subentry_id)
        result = await rooms.async_configure(
            result["flow_id"], {"name": "Bedroom", "source": "switch"}
        )
        result = await rooms.async_configure(
            result["flow_id"], {"switches": ["input_boolean.heater"]}
        )
        return await _until(hass, result, rooms, stop={"sensors"})

    result = await to_sensors()
    assert result["step_id"] == "sensors"
    result = await rooms.async_configure(
        result["flow_id"],
        {
            "temperature_sensors": ["sensor.room"],
            "occupancy_sensors": ["binary_sensor.motion"],
            "humidity_sensor": "sensor.hum",
        },
    )
    assert result["step_id"] == "sensors_details"
    assert _keys(result) == {"occupancy_minutes", "occupancy_return_minutes"}
    result = await rooms.async_configure(
        result["flow_id"], {"occupancy_minutes": 20, "occupancy_return_minutes": 5}
    )
    result = await _until(hass, result, rooms, stop=set())
    assert result["type"] is FlowResultType.ABORT
    data = entry.subentries[subentry.subentry_id].data
    assert data["humidity_sensor"] == "sensor.hum"
    assert (data["occupancy_minutes"], data["occupancy_return_minutes"]) == (20, 5)

    # Without occupancy sensors no details form; the humidity sensor is cleared.
    result = await to_sensors()
    result = await rooms.async_configure(
        result["flow_id"], {"temperature_sensors": ["sensor.room"], "occupancy_sensors": []}
    )
    assert result["step_id"] == "windows"
    result = await _until(hass, result, rooms, stop=set())
    assert result["type"] is FlowResultType.ABORT
    assert "humidity_sensor" not in entry.subentries[subentry.subentry_id].data


async def test_whole_house_thermostat_page_skipped_with_hvac_action(hass: HomeAssistant) -> None:
    """A thermostat that reports hvac_action needs no hysteresis: the page is skipped."""
    hass.states.async_set(
        "climate.trv", "heat", {"hvac_modes": ["heat", "off"], "hvac_action": "idle"}
    )
    entry = MockConfigEntry(domain=DOMAIN, title="Home 101", options={})
    entry.add_to_hass(hass)
    flow = hass.config_entries.options
    result = await flow.async_init(entry.entry_id)
    result = await flow.async_configure(result["flow_id"], {"next_step_id": "heating"})
    result = await flow.async_configure(result["flow_id"], {"source": "climate"})
    result = await flow.async_configure(
        result["flow_id"], {"climates": ["climate.trv"], "command_mode": "temperature"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    zone = next(iter(entry.subentries.values()))
    assert "learn_tolerance" not in zone.data


async def test_outdoor_humidity_sensor_is_refused(hass: HomeAssistant) -> None:
    """A humidity sensor of the outdoor sensor's device (a weather station) measures outdoors."""
    from homeassistant.helpers import device_registry as dr
    from homeassistant.helpers import entity_registry as er

    station = MockConfigEntry(domain="station")
    station.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=station.entry_id, identifiers={("station", "garden")}
    )
    ent = er.async_get(hass)
    outdoor = ent.async_get_or_create(
        "sensor", "station", "t", config_entry=station, device_id=device.id
    ).entity_id
    outdoor_humidity = ent.async_get_or_create(
        "sensor", "station", "h", config_entry=station, device_id=device.id
    ).entity_id
    room_humidity = ent.async_get_or_create("sensor", "other", "room_h").entity_id
    entry = _house_with_rooms(
        hass, options={"outdoor_sensor": outdoor}, rooms=[("Bedroom", RELAY_ROOM)]
    )
    rooms = hass.config_entries.subentries
    subentry = next(iter(entry.subentries.values()))
    result = await entry.start_subentry_reconfigure_flow(hass, subentry.subentry_id)
    result = await rooms.async_configure(result["flow_id"], {"name": "Bedroom", "source": "switch"})
    result = await rooms.async_configure(result["flow_id"], {"switches": ["input_boolean.heater"]})
    result = await _until(hass, result, rooms, stop={"sensors"})
    result = await rooms.async_configure(
        result["flow_id"],
        {"temperature_sensors": ["sensor.room"], "humidity_sensor": outdoor_humidity},
    )
    assert result["errors"] == {"humidity_sensor": "humidity_sensor_is_outdoor"}
    result = await rooms.async_configure(
        result["flow_id"],
        {"temperature_sensors": ["sensor.room"], "humidity_sensor": room_humidity},
    )
    assert result["step_id"] != "sensors"


async def test_humidity_sensor_of_a_gateway_or_a_weather_service(hass: HomeAssistant) -> None:
    """A gateway with indoor sensors too: accepted; a weather service device: refused."""
    from homeassistant.helpers import device_registry as dr
    from homeassistant.helpers import entity_registry as er

    source = MockConfigEntry(domain="station")
    source.add_to_hass(hass)
    devices = dr.async_get(hass)
    ent = er.async_get(hass)
    gateway = devices.async_get_or_create(
        config_entry_id=source.entry_id, identifiers={("station", "gateway")}
    )
    outdoor = ent.async_get_or_create(
        "sensor", "station", "out_t", config_entry=source, device_id=gateway.id,
        original_device_class="temperature",
    ).entity_id  # fmt: skip
    ent.async_get_or_create(
        "sensor", "station", "in_t", config_entry=source, device_id=gateway.id,
        original_device_class="temperature",
    )  # fmt: skip
    indoor_humidity = ent.async_get_or_create(
        "sensor", "station", "in_h", config_entry=source, device_id=gateway.id,
        original_device_class="humidity",
    ).entity_id  # fmt: skip
    service = devices.async_get_or_create(
        config_entry_id=source.entry_id, identifiers={("station", "forecast")}
    )
    weather = ent.async_get_or_create(
        "weather", "station", "w", config_entry=source, device_id=service.id
    ).entity_id
    service_humidity = ent.async_get_or_create(
        "sensor", "station", "w_h", config_entry=source, device_id=service.id,
        original_device_class="humidity",
    ).entity_id  # fmt: skip
    entry = _house_with_rooms(
        hass,
        options={"outdoor_sensor": outdoor, "weather": weather},
        rooms=[("Bedroom", RELAY_ROOM)],
    )
    rooms = hass.config_entries.subentries
    subentry = next(iter(entry.subentries.values()))
    result = await entry.start_subentry_reconfigure_flow(hass, subentry.subentry_id)
    result = await rooms.async_configure(result["flow_id"], {"name": "Bedroom", "source": "switch"})
    result = await rooms.async_configure(result["flow_id"], {"switches": ["input_boolean.heater"]})
    result = await _until(hass, result, rooms, stop={"sensors"})
    result = await rooms.async_configure(
        result["flow_id"],
        {"temperature_sensors": ["sensor.room"], "humidity_sensor": service_humidity},
    )
    assert result["errors"] == {"humidity_sensor": "humidity_sensor_is_outdoor"}
    result = await rooms.async_configure(
        result["flow_id"],
        {"temperature_sensors": ["sensor.room"], "humidity_sensor": indoor_humidity},
    )
    assert result["step_id"] != "sensors"


async def test_options_travel_time_takes_one_sensor_per_person(hass: HomeAssistant) -> None:
    """Several travel time sensors can be chosen; a single one saved before is shown in the list."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Home",
        options={"persons": ["person.andrei"], "travel_time": "sensor.waze"},
    )
    entry.add_to_hass(hass)
    flow = hass.config_entries.options
    result = await flow.async_init(entry.entry_id)
    result = await flow.async_configure(result["flow_id"], {"next_step_id": "presence"})
    field = next(k for k in result["data_schema"].schema if str(k) == "travel_time")
    assert field.description["suggested_value"] == ["sensor.waze"]
    assert result["data_schema"].schema[field].config["multiple"] is True
    result = await flow.async_configure(
        result["flow_id"], {"travel_time": ["sensor.waze_andrei", "sensor.waze_laura"]}
    )
    assert result["step_id"] == "presence_details"
    assert "arrival_minutes" in _keys(result)
    result = await flow.async_configure(result["flow_id"], {"arrival_minutes": 25})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["travel_time"] == ["sensor.waze_andrei", "sensor.waze_laura"]
    assert entry.options["arrival_minutes"] == 25
    # Cleared: no travel time any more, and no question about its minutes.
    result = await flow.async_init(entry.entry_id)
    result = await flow.async_configure(result["flow_id"], {"next_step_id": "presence"})
    result = await flow.async_configure(result["flow_id"], {"travel_time": []})
    assert result["type"] is FlowResultType.CREATE_ENTRY or "arrival_minutes" not in _keys(result)


async def test_trv_calibration_needs_a_room_sensor_and_its_entities(hass: HomeAssistant) -> None:
    """A calibration without a room sensor or without entities would do nothing: it is refused."""
    hass.states.async_set(
        "climate.trv", "heat", {"hvac_modes": ["heat", "off"], "hvac_action": "idle"}
    )
    entry = _house_with_rooms(hass)
    rooms = hass.config_entries.subentries
    result = await rooms.async_init(
        (entry.entry_id, SUBENTRY_ROOM), context={"source": SOURCE_USER}
    )
    result = await rooms.async_configure(
        result["flow_id"], {"name": "Bedroom", "source": "climate"}
    )
    result = await rooms.async_configure(
        result["flow_id"], {"climates": ["climate.trv"], "command_mode": "temperature"}
    )
    result = await _until(hass, result, rooms, stop={"sensors"})
    # Offset without a room sensor.
    result = await rooms.async_configure(
        result["flow_id"], {"temperature_sensors": [], "calibration_mode": "offset"}
    )
    assert result["step_id"] == "sensors"
    assert result["errors"] == {"calibration_mode": "calibration_sensor_required"}
    # With a sensor: the entities are asked, and an empty choice is refused.
    result = await rooms.async_configure(
        result["flow_id"], {"temperature_sensors": ["sensor.bedroom"], "calibration_mode": "offset"}
    )
    assert result["step_id"] == "sensors_details"
    result = await rooms.async_configure(
        result["flow_id"], {"calibration_entities": [], "hysteresis": 0.3}
    )
    assert result["step_id"] == "sensors_details"
    assert result["errors"] == {"calibration_entities": "calibration_entities_required"}
    result = await rooms.async_configure(
        result["flow_id"],
        {"calibration_entities": ["number.bedroom_trv_calibration"], "hysteresis": 0.3},
    )
    assert result["step_id"] == "windows"
    result = await _until(hass, result, rooms, stop=set())
    assert result["type"] is FlowResultType.CREATE_ENTRY
    data = next(sub for sub in entry.subentries.values() if sub.title == "Bedroom").data
    assert data["calibration_mode"] == "offset"
    assert data["calibration_entities"] == ["number.bedroom_trv_calibration"]


async def test_trv_calibration_off_needs_nothing(hass: HomeAssistant) -> None:
    """Without calibration a TRV room needs no room sensor and no entities."""
    hass.states.async_set(
        "climate.trv", "heat", {"hvac_modes": ["heat", "off"], "hvac_action": "idle"}
    )
    entry = _house_with_rooms(hass)
    rooms = hass.config_entries.subentries
    result = await rooms.async_init(
        (entry.entry_id, SUBENTRY_ROOM), context={"source": SOURCE_USER}
    )
    result = await rooms.async_configure(result["flow_id"], {"name": "Hall", "source": "climate"})
    result = await rooms.async_configure(
        result["flow_id"], {"climates": ["climate.trv"], "command_mode": "temperature"}
    )
    result = await _until(hass, result, rooms, stop={"sensors"})
    result = await rooms.async_configure(
        result["flow_id"], {"temperature_sensors": [], "calibration_mode": "off"}
    )
    assert result["step_id"] == "windows"


async def test_circuits_of_the_house_and_the_circuit_of_a_room(hass: HomeAssistant) -> None:
    """Circuit relays are set with the heat source; a room of it picks one of them."""
    entry = _house_with_rooms(
        hass, options={"boiler_entity": "switch.boiler"}, rooms=[("Bedroom", RELAY_ROOM)]
    )
    options = hass.config_entries.options
    result = await options.async_init(entry.entry_id)
    result = await options.async_configure(result["flow_id"], {"next_step_id": "boiler"})
    result = await options.async_configure(result["flow_id"], {"boiler_entity": "switch.boiler"})
    assert "circuits" in _keys(result)
    # Not the heat source itself, nor the device of a room.
    result = await options.async_configure(result["flow_id"], {"circuits": ["switch.boiler"]})
    assert result["errors"] == {"circuits": "circuit_is_source"}
    result = await options.async_configure(
        result["flow_id"], {"circuits": [RELAY_ROOM["switches"][0]]}
    )
    assert result["errors"] == {"circuits": "entity_in_room"}
    result = await options.async_configure(
        result["flow_id"], {"circuits": ["switch.floor", "switch.radiators"]}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.options["circuits"] == ["switch.floor", "switch.radiators"]

    # A new room of the heat source: its circuit, among those of the house.
    flow = hass.config_entries.subentries
    result = await flow.async_init((entry.entry_id, SUBENTRY_ROOM), context={"source": SOURCE_USER})
    result = await flow.async_configure(result["flow_id"], {"name": "Bath", "source": "switch"})
    result = await flow.async_configure(
        result["flow_id"],
        {"switches": ["input_boolean.bath_heater"], "use_house_source": True},
    )
    assert result["step_id"] == "house_source"
    assert _keys(result) == {"starts_house_source", "top_up", "circuit"}
    field = next(k for k in result["data_schema"].schema if str(k) == "circuit")
    values = [o["value"] for o in result["data_schema"].schema[field].config["options"]]
    assert values == ["switch.floor", "switch.radiators"]
    # A circuit relay is not a device of a room.
    result2 = await flow.async_init(
        (entry.entry_id, SUBENTRY_ROOM), context={"source": SOURCE_USER}
    )
    result2 = await flow.async_configure(result2["flow_id"], {"name": "Hall", "source": "switch"})
    result2 = await flow.async_configure(
        result2["flow_id"], {"switches": ["switch.floor"], "use_house_source": False}
    )
    assert result2["errors"] == {"switches": "entity_is_circuit"}


async def test_no_circuit_field_without_circuits(hass: HomeAssistant) -> None:
    """Without circuits in the house, the room is asked only whether it may start the source."""
    entry = _house_with_rooms(hass, options={"boiler_entity": "switch.boiler"})
    flow = hass.config_entries.subentries
    result = await flow.async_init((entry.entry_id, SUBENTRY_ROOM), context={"source": SOURCE_USER})
    result = await flow.async_configure(result["flow_id"], {"name": "Bath", "source": "switch"})
    result = await flow.async_configure(
        result["flow_id"],
        {"switches": ["input_boolean.bath_heater"], "use_house_source": True},
    )
    assert _keys(result) == {"starts_house_source", "top_up"}


async def test_top_up_is_not_asked_for_a_generic_thermostat(hass: HomeAssistant) -> None:
    """A Generic Thermostat decides its relay by itself: it cannot be topped up."""
    climate = _gt_climate(hass, "switch.gt_relay")
    entry = _house_with_rooms(hass, options={"boiler_entity": "switch.boiler"})
    flow = hass.config_entries.subentries
    result = await flow.async_init((entry.entry_id, SUBENTRY_ROOM), context={"source": SOURCE_USER})
    result = await flow.async_configure(
        result["flow_id"], {"name": "Living", "source": "generic_thermostat"}
    )
    result = await flow.async_configure(
        result["flow_id"], {"climates": [climate], "use_house_source": True}
    )
    assert result["step_id"] == "house_source"
    assert _keys(result) == {"starts_house_source"}


async def test_top_up_is_saved(hass: HomeAssistant) -> None:
    """Turned on for a relay room of the heat source, kept for the room."""
    entry = _house_with_rooms(hass, options={"boiler_entity": "switch.boiler"})
    flow = hass.config_entries.subentries
    result = await flow.async_init((entry.entry_id, SUBENTRY_ROOM), context={"source": SOURCE_USER})
    result = await flow.async_configure(result["flow_id"], {"name": "Bath", "source": "switch"})
    result = await flow.async_configure(
        result["flow_id"],
        {"switches": ["input_boolean.bath_heater"], "use_house_source": True},
    )
    result = await flow.async_configure(
        result["flow_id"], {"starts_house_source": True, "top_up": True}
    )
    assert result["step_id"] == "control_on_off"
    assert flow._progress[result["flow_id"]]._data["top_up"] is True
