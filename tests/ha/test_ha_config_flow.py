"""Config flow and room subentry flow tests."""

from __future__ import annotations

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
    assert _keys(result) == {"climates", "command_mode"}
    result = await flow.async_configure(
        result["flow_id"], {"climates": ["climate.trv"], "command_mode": "temperature"}
    )
    assert result["step_id"] == "heating_thermostat"
    # climate.trv is not available now: the hysteresis is asked for.
    assert _keys(result) == {"learn_tolerance", "hysteresis", "trv_boost"}
    result = await flow.async_configure(result["flow_id"], {"learn_tolerance": 0.3})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    zone = next(iter(entry.subentries.values()))
    assert zone.title == "Whole house"
    assert zone.data["learn_tolerance"] == 0.3
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
    result = await flow.async_configure(result["flow_id"], {"override_mode": "until_next_reevaluation"})
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
        result["flow_id"], {
            "season_mode": "dates",
            "cutoff_enabled": False,
            "forecast_enabled": False,
            "compensation_enabled": False,
        }
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
    # An outdoor sensor (the optimal stop needs it), no weather (no solar gain).
    entry = MockConfigEntry(domain=DOMAIN, title="Home", options={"outdoor_sensor": "sensor.outdoor"})
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
    assert _keys(result) == {"hysteresis", "min_on_minutes", "min_off_minutes"}
    result = await flow.async_configure(result["flow_id"], {})
    assert result["step_id"] == "levels"
    assert "nearby_temp" not in _keys(result)
    result = await flow.async_configure(
        result["flow_id"], {"name_home": "Day", "name_sleep": "Night", "nearby_mode": "temperature"}
    )
    assert result["step_id"] == "levels_nearby"
    result = await flow.async_configure(result["flow_id"], {"nearby_temp": 18})
    assert result["step_id"] == "sensors"
    assert _keys(result) == {"temperature_sensors", "occupancy_sensors"}
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
    result = await flow.async_configure(result["flow_id"], {"schedule": "workday: 06:00 Day, 25:00 Night"})
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
    result = await flow.async_configure(result["flow_id"], {"name": "Master bedroom", "source": "switch"})
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
    # TRV with presets: only the thermostat tolerance.
    assert result["step_id"] == "control_thermostat"
    # This TRV does not report hvac_action: its heat demand uses the hysteresis.
    assert {str(k) for k in result["data_schema"].schema} == {"learn_tolerance", "hysteresis"}
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"learn_tolerance": 0.3}
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
    assert subentry.data["learn_tolerance"] == 0.3


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
    entry = MockConfigEntry(domain=DOMAIN, title="Home", options={"outdoor_sensor": "sensor.outdoor"})
    entry.add_to_hass(hass)
    flow = hass.config_entries.subentries
    for attributes, expected in (
        ({"hvac_action": "idle"}, {"optimal_stop_minutes", "stop_tolerance"}),
        ({}, {"optimal_stop_minutes"}),
    ):
        hass.states.async_set("climate.trv", "heat", {"hvac_modes": ["heat", "off"], **attributes})
        result = await flow.async_init((entry.entry_id, SUBENTRY_ROOM), context={"source": SOURCE_USER})
        result = await flow.async_configure(result["flow_id"], {"name": "Office", "source": "climate"})
        result = await flow.async_configure(
            result["flow_id"], {"climates": ["climate.trv"], "command_mode": "temperature"}
        )
        result = await _until(hass, result, flow, stop={"schedule"})
        result = await flow.async_configure(result["flow_id"], {"optimal_stop": True})
        result = await _until(hass, result, flow, stop={"schedule_optimal"})
        assert result["step_id"] == "schedule_optimal"
        assert _keys(result) == expected
        flow.async_abort(result["flow_id"])


def _house_with_rooms(hass: HomeAssistant, options: dict | None = None, rooms=()) -> MockConfigEntry:
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

    rooms = hass.config_entries.subentries
    for switch, error in (
        ("switch.boiler", "entity_is_source"),
        ("switch.gt_relay", "entity_is_gt_heater"),
    ):
        result = await rooms.async_init((entry.entry_id, SUBENTRY_ROOM), context={"source": SOURCE_USER})
        result = await rooms.async_configure(result["flow_id"], {"name": "Office", "source": "switch"})
        result = await rooms.async_configure(result["flow_id"], {"switches": [switch]})
        assert result["errors"] == {"switches": error}, switch


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
    result = await rooms.async_init((entry.entry_id, SUBENTRY_ROOM), context={"source": SOURCE_USER})
    result = await rooms.async_configure(result["flow_id"], {"name": "Office", "source": "switch"})
    result = await rooms.async_configure(result["flow_id"], {"switches": ["input_boolean.other"]})
    result = await _until(hass, result, rooms, stop={"sensors"})
    assert result["step_id"] == "sensors"
    result = await rooms.async_configure(result["flow_id"], {"temperature_sensors": ["sensor.outdoor"]})
    assert result["errors"] == {"temperature_sensors": "room_sensor_is_outdoor"}
    result = await rooms.async_configure(result["flow_id"], {"temperature_sensors": ["sensor.office"]})
    assert result["step_id"] != "sensors"


async def test_trv_boost_in_the_room_form(hass: HomeAssistant) -> None:
    """The boost is offered for the temperature command and needs a room sensor."""
    entry = _house_with_rooms(hass)
    rooms = hass.config_entries.subentries
    result = await rooms.async_init((entry.entry_id, SUBENTRY_ROOM), context={"source": SOURCE_USER})
    result = await rooms.async_configure(result["flow_id"], {"name": "Office", "source": "climate"})
    result = await rooms.async_configure(
        result["flow_id"], {"climates": ["climate.trv"], "command_mode": "temperature"}
    )
    assert result["step_id"] == "control_thermostat"
    assert "trv_boost" in _keys(result)
    # climate.trv is not available now: the hysteresis is asked here, not again.
    result = await rooms.async_configure(
        result["flow_id"], {"learn_tolerance": 0.0, "hysteresis": 0.2, "trv_boost": True}
    )
    assert result["step_id"] == "control_boost"
    assert _keys(result) == {"trv_boost_temperature"}
    result = await rooms.async_configure(result["flow_id"], {"trv_boost_temperature": 23})
    result = await _until(hass, result, rooms, stop={"sensors"})
    assert result["step_id"] == "sensors"
    result = await rooms.async_configure(result["flow_id"], {})
    assert result["errors"] == {"temperature_sensors": "boost_sensor_required"}
    result = await rooms.async_configure(result["flow_id"], {"temperature_sensors": ["sensor.office"]})
    result = await _until(hass, result, rooms, stop=set())
    assert result["type"] is FlowResultType.CREATE_ENTRY
    data = next(sub for sub in entry.subentries.values() if sub.title == "Office").data
    assert data["trv_boost"] is True
    assert data["trv_boost_temperature"] == 23
    assert data["hysteresis"] == 0.2

    # With the preset command there is no boost.
    result = await rooms.async_init((entry.entry_id, SUBENTRY_ROOM), context={"source": SOURCE_USER})
    result = await rooms.async_configure(result["flow_id"], {"name": "Hall", "source": "climate"})
    result = await rooms.async_configure(
        result["flow_id"], {"climates": ["climate.hall"], "command_mode": "preset"}
    )
    assert "trv_boost" not in _keys(result)


async def test_frost_hysteresis_for_trvs_with_a_room_sensor(hass: HomeAssistant) -> None:
    """A TRV reporting hvac_action, with a room sensor: the hysteresis is asked for frost."""
    hass.states.async_set(
        "climate.trv", "heat", {"hvac_modes": ["heat", "off"], "hvac_action": "idle"}
    )
    entry = _house_with_rooms(hass)
    rooms = hass.config_entries.subentries
    result = await rooms.async_init((entry.entry_id, SUBENTRY_ROOM), context={"source": SOURCE_USER})
    result = await rooms.async_configure(result["flow_id"], {"name": "Office", "source": "climate"})
    result = await rooms.async_configure(
        result["flow_id"], {"climates": ["climate.trv"], "command_mode": "temperature"}
    )
    # hvac_action is reported: no hysteresis on the thermostat step.
    assert "hysteresis" not in _keys(result)
    result = await rooms.async_configure(result["flow_id"], {"learn_tolerance": 0.0})
    result = await _until(hass, result, rooms, stop={"sensors"})
    result = await rooms.async_configure(result["flow_id"], {"temperature_sensors": ["sensor.office"]})
    assert result["step_id"] == "sensors_details"
    assert "hysteresis" in _keys(result)
    result = await rooms.async_configure(result["flow_id"], {"hysteresis": 0.5})
    result = await _until(hass, result, rooms, stop=set())
    assert result["type"] is FlowResultType.CREATE_ENTRY
    data = next(sub for sub in entry.subentries.values() if sub.title == "Office").data
    assert data["hysteresis"] == 0.5
