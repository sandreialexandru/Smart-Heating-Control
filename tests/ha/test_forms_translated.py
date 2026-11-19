"""Every field of every form has a name and an explanation in every language.

The forms are walked as a user would fill them, in the combinations that show
the most fields; each form shown is checked against the translations (field
names, explanations, the options of its lists and its errors), and the limits
of its number fields against ``NUMBER_LIMITS``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.advanced_climate.const import DOMAIN, SUBENTRY_ROOM

# The limits of every number field, by (step, field): (min, max, step, unit).
# A field added to a form is added here too; the guide and the configurator
# show the same limits.
NUMBER_LIMITS: dict[tuple[str, str], tuple[Any, ...]] = {
    ("alerts", "alert_no_effect_hours"): (0.0, 12.0, 0.5, "h"),
    ("alerts", "alert_silent_hours"): (0.0, 48.0, 0.5, "h"),
    ("alerts", "alert_unavailable_minutes"): (1.0, 720.0, 1.0, "min"),
    ("alerts", "alert_window_minutes"): (1.0, 720.0, 1.0, "min"),
    ("alerts", "battery_threshold"): (1.0, 100.0, 1.0, "%"),
    ("alerts", "pause_remind_hours"): (0.0, 168.0, 1.0, "h"),
    ("alerts", "room_diff_alert"): (0.0, 10.0, 0.5, "°C"),
    ("behavior", "auto_vacation_hours"): (0.0, 720.0, 1.0, "h"),
    ("behavior", "frost_temp"): (3.0, 15.0, 0.5, "°C"),
    ("behavior", "max_temp"): (15.0, 35.0, 0.5, "°C"),
    ("behavior", "reevaluation_minutes"): (1.0, 60.0, 1.0, "min"),
    ("behavior", "vacation_preheat_hours"): (0.0, 48.0, 0.5, "h"),
    ("behavior_details", "override_hours"): (0.25, 72.0, 0.25, "h"),
    ("boiler_details", "boiler_idle_temp"): (3.0, 30.0, 0.5, "°C"),
    ("boiler_details", "boiler_min_off"): (0.0, 60.0, 1.0, "min"),
    ("boiler_details", "boiler_min_on"): (0.0, 60.0, 1.0, "min"),
    ("boiler_details", "boiler_min_rooms"): (1.0, 1.0, 1.0, None),
    ("boiler_source", "source_cold_below"): (-30.0, 20.0, 0.5, "°C"),
    ("boiler_source", "source_switch_minutes"): (0.0, 240.0, 1.0, "min"),
    ("control_boost", "hysteresis"): (0.1, 3.0, 0.1, "°C"),
    ("control_boost", "trv_boost_temperature"): (7.0, 25.0, 0.5, "°C"),
    ("control_on_off", "hysteresis"): (0.1, 3.0, 0.1, "°C"),
    ("control_on_off", "min_off_minutes"): (0.0, 60.0, 1.0, "min"),
    ("control_on_off", "min_on_minutes"): (0.0, 60.0, 1.0, "min"),
    ("control_thermostat", "hysteresis"): (0.1, 3.0, 0.1, "°C"),
    ("energy_details", "price_high"): (-1000.0, 1000.0, 0.001, None),
    ("energy_details", "price_high_offset"): (-3.0, 3.0, 0.1, "°C"),
    ("energy_details", "price_low"): (-1000.0, 1000.0, 0.001, None),
    ("energy_details", "price_low_offset"): (-3.0, 3.0, 0.1, "°C"),
    ("energy_details", "pv_offset"): (-3.0, 3.0, 0.1, "°C"),
    ("energy_details", "pv_threshold"): (0.0, 100000.0, 10.0, "W"),
    ("extras", "solar_offset"): (-3.0, 0.0, 0.1, "°C"),
    ("heating_boost", "hysteresis"): (0.1, 3.0, 0.1, "°C"),
    ("heating_boost", "trv_boost_temperature"): (7.0, 25.0, 0.5, "°C"),
    ("heating_on_off", "hysteresis"): (0.1, 3.0, 0.1, "°C"),
    ("heating_on_off", "min_off_minutes"): (0.0, 60.0, 1.0, "min"),
    ("heating_on_off", "min_on_minutes"): (0.0, 60.0, 1.0, "min"),
    ("heating_thermostat", "hysteresis"): (0.1, 3.0, 0.1, "°C"),
    ("levels", "temp_activity"): (7.0, 25.0, 0.5, "°C"),
    ("levels", "temp_away"): (7.0, 25.0, 0.5, "°C"),
    ("levels", "temp_comfort"): (7.0, 25.0, 0.5, "°C"),
    ("levels", "temp_eco"): (7.0, 25.0, 0.5, "°C"),
    ("levels", "temp_home"): (7.0, 25.0, 0.5, "°C"),
    ("levels", "temp_sleep"): (7.0, 25.0, 0.5, "°C"),
    ("levels_nearby", "nearby_temp"): (7.0, 25.0, 0.5, "°C"),
    ("presence", "arrival_delay"): (0.0, 240.0, 1.0, "min"),
    ("presence", "departure_delay"): (0.0, 240.0, 1.0, "min"),
    ("presence", "guest_expire_hours"): (0.0, 720.0, 1.0, "h"),
    ("presence_details", "arrival_distance"): (0.0, 500.0, 0.5, "km"),
    ("presence_details", "arrival_minutes"): (0.0, 240.0, 1.0, "min"),
    ("schedule_optimal", "optimal_start_max_minutes"): (10.0, 1440.0, 5.0, "min"),
    ("schedule_optimal", "optimal_stop_minutes"): (5.0, 1440.0, 5.0, "min"),
    ("schedule_optimal", "stop_tolerance"): (0.0, 2.0, 0.1, "°C"),
    ("sensors_details", "hysteresis"): (0.1, 3.0, 0.1, "°C"),
    ("sensors_details", "occupancy_minutes"): (1.0, 720.0, 1.0, "min"),
    ("sensors_details", "occupancy_return_minutes"): (0.0, 60.0, 1.0, "min"),
    ("weather", "window_ignore_above"): (0.0, 40.0, 0.5, "°C"),
    ("weather_details", "compensation_below"): (-30.0, 15.0, 0.5, "°C"),
    ("weather_details", "compensation_offset"): (-3.0, 3.0, 0.1, "°C"),
    ("weather_details", "cutoff_avg_hours"): (1.0, 48.0, 1.0, "h"),
    ("weather_details", "cutoff_hysteresis"): (0.0, 5.0, 0.1, "°C"),
    ("weather_details", "cutoff_temp"): (5.0, 30.0, 0.5, "°C"),
    ("weather_details", "forecast_hours"): (1.0, 24.0, 1.0, "h"),
    ("weather_details", "season_days"): (1.0, 14.0, 1.0, "d"),
    ("weather_details", "season_temp"): (0.0, 25.0, 0.5, "°C"),
    ("windows_details", "window_close_delay"): (0.0, 3600.0, 5.0, "s"),
    ("windows_details", "window_drop_degrees"): (0.2, 5.0, 0.1, "°C"),
    ("windows_details", "window_drop_minutes"): (1.0, 30.0, 1.0, "min"),
    ("windows_details", "window_open_delay"): (0.0, 3600.0, 5.0, "s"),
}

LANGS = ("en", "ro", "de", "nl", "fr", "it", "es")
TRANSLATIONS = {
    lang: json.loads(
        (
            Path(__file__).resolve().parents[2]
            / "custom_components"
            / "advanced_climate"
            / "translations"
            / f"{lang}.json"
        ).read_text()
    )
    for lang in LANGS
}


# Every number field seen, by (step, field): (min, max, step, unit).
SEEN_NUMBERS: dict[tuple[str, str], tuple[Any, ...]] = {}


def _numbers(result: dict) -> None:
    """Record the limits of the number fields of the form of ``result``."""
    for marker, field in result["data_schema"].schema.items():
        config = getattr(field, "config", None)
        if type(field).__name__ != "NumberSelector" or not isinstance(config, dict):
            continue
        key = str(getattr(marker, "schema", marker))
        limits = (
            config.get("min"),
            config.get("max"),
            config.get("step"),
            config.get("unit_of_measurement"),
        )
        SEEN_NUMBERS[(result["step_id"], key)] = limits
        if os.environ.get("SHC_DUMP_NUMBERS"):
            print("NUMBER", repr((result["step_id"], key)), repr(limits))
        expected = NUMBER_LIMITS.get((result["step_id"], key))
        assert expected is not None, (
            "a number field missing in NUMBER_LIMITS",
            result["step_id"],
            key,
            limits,
        )
        assert limits == expected, (result["step_id"], key, limits, expected)


def _check(result: dict, path: tuple[str, ...], seen: set[str]) -> None:
    """The form of ``result`` is translated in every language."""
    if result["type"] is FlowResultType.MENU:
        for lang in LANGS:
            node: Any = TRANSLATIONS[lang]
            for part in path:
                node = node[part]
            options = node["step"][result["step_id"]]["menu_options"]
            assert set(result["menu_options"]) <= set(options), (lang, result["step_id"])
        return
    if result["type"] is not FlowResultType.FORM:
        return
    step = result["step_id"]
    seen.add(step)
    _numbers(result)
    for lang in LANGS:
        node = TRANSLATIONS[lang]
        for part in path:
            node = node[part]
        texts = node["step"][step]
        assert texts.get("title"), (lang, step)
        for marker, field in result["data_schema"].schema.items():
            key = str(getattr(marker, "schema", marker))
            if step == "profiles":
                continue  # the rooms of a scenario, by their names
            assert texts.get("data", {}).get(key), (lang, step, key, "name")
            assert texts.get("data_description", {}).get(key), (lang, step, key, "explanation")
            config = getattr(field, "config", None)
            if isinstance(config, dict) and config.get("translation_key"):
                labels = TRANSLATIONS[lang]["selector"][config["translation_key"]]["options"]
                for option in config.get("options", []):
                    value = option if isinstance(option, str) else option["value"]
                    assert labels.get(value), (lang, step, key, value)
        for error in (result.get("errors") or {}).values():
            assert node["error"].get(error), (lang, step, error)


async def _walk(
    hass: HomeAssistant,
    manager: Any,
    result: dict,
    path: tuple[str, ...],
    inputs: dict[str, dict],
    seen: set[str],
    limit: int = 25,
) -> dict:
    """Fill the forms with ``inputs`` (by step, else nothing) until the end."""
    for _ in range(limit):
        _check(result, path, seen)
        if result["type"] not in (FlowResultType.FORM, FlowResultType.MENU):
            return result
        step = result["step_id"]
        data = inputs.get(step, {})
        result = await manager.async_configure(result["flow_id"], data)
        if result["type"] is FlowResultType.FORM and result["step_id"] == step and data:
            _check(result, path, seen)
            assert not result.get("errors"), (step, result.get("errors"))
    raise AssertionError(f"the flow did not end: {result.get('step_id')}")


def _house(hass: HomeAssistant, options: dict) -> MockConfigEntry:
    for sensor in ("room", "bath", "a", "b", "outdoor"):
        hass.states.async_set(
            f"sensor.{sensor}", "20", {"device_class": "temperature", "unit_of_measurement": "°C"}
        )
    hass.states.async_set(
        "sensor.h", "50", {"device_class": "humidity", "unit_of_measurement": "%"}
    )
    entry = MockConfigEntry(domain=DOMAIN, title="Home", options=options)
    entry.add_to_hass(hass)
    return entry


HOUSE = {
    "persons": ["person.andrei"],
    "nearby_zones": [],
    "outdoor_sensor": "sensor.outdoor",
    "weather": "weather.home",
    "price_sensor": "sensor.price",
    "price_low": 0.1,
    "pv_sensor": "sensor.pv",
    "boiler_entity": "climate.boiler",
}


async def test_every_option_form(hass: HomeAssistant) -> None:
    hass.states.async_set("climate.trv", "heat", {"hvac_modes": ["heat", "off"]})
    entry = _house(hass, HOUSE)
    options = hass.config_entries.options
    seen: set[str] = set()
    pages = {
        "heating": {"source": "climate"},
        "heating_devices": {
            "climates": ["climate.trv"],
            "command_mode": "temperature",
            "trv_boost": True,
        },
        "presence": {
            "persons": ["person.andrei"],
            "presence_sensors": ["binary_sensor.x"],
            "proximity_distance": "sensor.distance",
            "travel_time": ["sensor.travel"],
        },
        "calendar": {"workday_sensor": "binary_sensor.workday", "calendar": "calendar.home"},
        "weather": {
            "outdoor_sensor": "sensor.outdoor",
            "weather": "weather.home",
            "cutoff_enabled": True,
            "season_mode": "auto",
            "compensation_enabled": True,
            "forecast_enabled": True,
        },
        "energy": {"price_sensor": "sensor.price", "pv_sensor": "sensor.pv"},
        "energy_details": {"price_low": 0.1},
        "boiler": {"boiler_entity": "climate.boiler", "secondary_source": "switch.pump"},
        "heating_boost": {"temperature_sensors": ["sensor.room"]},
        "boiler_details": {"source_criterion": "cold"},
        "behavior": {"override_mode": "fixed"},
    }
    for menu in pages_in_menu():
        result = await options.async_init(entry.entry_id)
        _check(result, ("options",), seen)
        result = await options.async_configure(result["flow_id"], {"next_step_id": menu})
        await _walk(hass, options, result, ("options",), pages, seen)
    # The other criteria: the entity, and the switching time alone.
    for criterion in ("entity", "pv_surplus", "cheap_power", "none"):
        result = await options.async_init(entry.entry_id)
        result = await options.async_configure(result["flow_id"], {"next_step_id": "boiler"})
        await _walk(
            hass,
            options,
            result,
            ("options",),
            {
                **pages,
                "boiler_details": {"source_criterion": criterion},
                "boiler_source": {"source_criterion_entity": "binary_sensor.cheap"}
                if criterion == "entity"
                else {},
            },
            seen,
        )
    assert {
        "heating",
        "heating_devices",
        "heating_boost",
        "presence",
        "presence_details",
        "calendar",
        "weather",
        "weather_details",
        "energy",
        "energy_details",
        "boiler",
        "boiler_details",
        "boiler_source",
        "behavior",
        "behavior_details",
        "alerts",
    } <= seen, seen


def pages_in_menu() -> list[str]:
    return [
        "heating",
        "presence",
        "calendar",
        "weather",
        "energy",
        "boiler",
        "behavior",
        "alerts",
    ]


async def test_the_thermostat_forms_of_the_whole_house(hass: HomeAssistant) -> None:
    """Other thermostats without the boost; relays; the first setup."""
    seen: set[str] = set()
    _house(hass, {})
    flow = hass.config_entries.flow
    result = await flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    await _walk(
        hass,
        flow,
        result,
        ("config",),
        {
            "user": {"name": "Home", "persons": [], "nearby_zones": [], "home_rule": "any"},
            "heating": {"source": "climate"},
            "heating_devices": {
                "climates": ["climate.trv"],
                "command_mode": "temperature",
                "trv_boost": False,
            },
        },
        seen,
    )
    entry = _house(hass, {})
    options = hass.config_entries.options
    for source, devices, on_off in (
        ("switch", {"switches": ["switch.heater"]}, {"temperature_sensors": ["sensor.room"]}),
        ("climate", {"climates": ["climate.trv2"], "command_mode": "hvac_mode"}, {}),
        ("climate", {"climates": ["climate.trv3"], "command_mode": "preset"}, {}),
    ):
        result = await options.async_init(entry.entry_id)
        result = await options.async_configure(result["flow_id"], {"next_step_id": "heating"})
        await _walk(
            hass,
            options,
            result,
            ("options",),
            {
                "heating": {"source": source},
                "heating_devices": devices,
                "heating_on_off": on_off,
            },
            seen,
        )
    assert {"user", "heating", "heating_devices", "heating_thermostat", "heating_on_off"} <= seen


async def test_every_room_form(hass: HomeAssistant) -> None:
    hass.states.async_set(
        "climate.office",
        "heat",
        {"hvac_modes": ["heat", "off"], "hvac_action": "idle", "preset_modes": ["comfort", "eco"]},
    )
    hass.states.async_set("zone.near", "0", {"latitude": 0, "longitude": 0, "radius": 100})
    entry = _house(hass, {**HOUSE, "circuits": ["switch.floor"], "nearby_zones": ["zone.near"]})
    flow = hass.config_entries.subentries
    seen: set[str] = set()
    for source, devices, extra in (
        (
            "climate",
            {"climates": ["climate.bedroom"], "command_mode": "temperature", "trv_boost": True},
            {
                "schedule": {
                    "schedule_source": "helper",
                    "optimal_start": True,
                    "optimal_stop": True,
                },
                "windows": {"window_sensors": ["binary_sensor.window"], "window_drop_detect": True},
                "levels": {"nearby_mode": "temperature"},
            },
        ),
        (
            "switch",
            {"switches": ["switch.bath"], "use_house_source": True},
            {"schedule": {"schedule_source": "internal", "optimal_start": True}},
        ),
        (
            "climate",
            {"climates": ["climate.office"], "command_mode": "preset"},
            {"schedule": {"schedule_source": "internal", "optimal_stop": True}},
        ),
    ):
        result = await flow.async_init(
            (entry.entry_id, SUBENTRY_ROOM), context={"source": SOURCE_USER}
        )
        await _walk(
            hass,
            flow,
            result,
            ("config_subentries", "room"),
            {
                "basics": {"name": f"Room {source} {len(seen)}", "source": source},
                "devices": devices,
                "sensors": {
                    "temperature_sensors": ["sensor.a", "sensor.b"],
                    "humidity_sensor": "sensor.h",
                    "occupancy_sensors": ["binary_sensor.motion"],
                },
                "windows": {"window_sensors": ["binary_sensor.window"]},
                "schedule_helper": {"schedule_helper": "schedule.bedroom"},
                **extra,
            },
            seen,
            limit=40,
        )
    assert {
        "basics",
        "devices",
        "house_source",
        "control_boost",
        "control_on_off",
        "levels",
        "sensors",
        "sensors_details",
        "windows",
        "windows_details",
        "schedule",
        "schedule_helper",
        "schedule_internal",
        "extras",
        "levels_nearby",
    } <= seen, seen
    # With several rooms the alerts compare them with each other.
    options = hass.config_entries.options
    result = await options.async_init(entry.entry_id)
    result = await options.async_configure(result["flow_id"], {"next_step_id": "alerts"})
    await _walk(hass, options, result, ("options",), {}, seen)
    assert ("alerts", "room_diff_alert") in SEEN_NUMBERS


async def test_the_circuit_forms_without_a_heat_source(hass: HomeAssistant) -> None:
    """Zone valves wired to the boiler: the circuits page and the room's circuit."""
    entry = _house(hass, {"persons": ["person.andrei"], "nearby_zones": []})
    seen: set[str] = set()
    options = hass.config_entries.options
    result = await options.async_init(entry.entry_id)
    result = await options.async_configure(result["flow_id"], {"next_step_id": "boiler"})
    await _walk(
        hass,
        options,
        result,
        ("options",),
        {
            "boiler": {},
            "boiler_circuits": {"circuits": ["switch.upstairs", "switch.downstairs"]},
        },
        seen,
    )
    assert {"boiler", "boiler_circuits"} <= seen, seen
    assert entry.options["circuits"] == ["switch.upstairs", "switch.downstairs"]
    flow = hass.config_entries.subentries
    result = await flow.async_init((entry.entry_id, SUBENTRY_ROOM), context={"source": SOURCE_USER})
    await _walk(
        hass,
        flow,
        result,
        ("config_subentries", "room"),
        {
            "basics": {"name": "Bedroom", "source": "climate"},
            "devices": {"climates": ["climate.bedroom"], "command_mode": "temperature"},
            "room_circuit": {"circuit": "switch.upstairs"},
            "sensors": {"temperature_sensors": ["sensor.a"]},
        },
        seen,
        limit=40,
    )
    assert {"devices", "room_circuit"} <= seen, seen
    assert "house_source" not in seen
    room = next(iter(entry.subentries.values()))
    assert room.data["circuit"] == "switch.upstairs"
