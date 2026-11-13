"""Every field of every form has a name and an explanation in every language.

The forms are walked as a user would fill them, in the combinations that show
the most fields; each form shown is checked against the translations (field
names, explanations, the options of its lists and its errors).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.advanced_climate.const import DOMAIN, SUBENTRY_ROOM

LANGS = ("en", "ro", "de", "nl", "fr", "it")
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
    entry = _house(hass, {**HOUSE, "circuits": ["switch.floor"]})
    flow = hass.config_entries.subentries
    seen: set[str] = set()
    for source, devices, extra in (
        (
            "climate",
            {"climates": ["climate.bedroom"], "command_mode": "temperature", "trv_boost": True},
            {"schedule": {"schedule_source": "helper", "optimal_start": True}},
        ),
        (
            "switch",
            {"switches": ["switch.bath"], "use_house_source": True},
            {"schedule": {"schedule_source": "internal", "optimal_start": True}},
        ),
        (
            "climate",
            {"climates": ["climate.office"], "command_mode": "preset"},
            {},
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
    } <= seen, seen
