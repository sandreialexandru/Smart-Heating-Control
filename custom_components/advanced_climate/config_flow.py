"""Config flow for Smart Heating Control: the house entry and room subentries."""

from __future__ import annotations

import math
from types import MappingProxyType
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentry,
    ConfigSubentryFlow,
    OptionsFlow,
    SubentryFlowResult,
)
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import selector

from .const import (
    AGG_MEAN,
    AGG_MEDIAN,
    AGG_MIN,
    CALIBRATION_EXTERNAL,
    CALIBRATION_OFF,
    CALIBRATION_OFFSET,
    COMMAND_HVAC,
    COMMAND_PRESET,
    COMMAND_TEMPERATURE,
    CONF_ALERT_UNAVAILABLE_MINUTES,
    CONF_ALERT_WINDOW_MINUTES,
    CONF_AREA,
    CONF_ARRIVAL_DELAY,
    CONF_ARRIVAL_DISTANCE,
    CONF_ARRIVAL_MINUTES,
    CONF_AUTO_VACATION_HOURS,
    CONF_BATTERY_THRESHOLD,
    CONF_BOILER_ENTITY,
    CONF_BOILER_MIN_OFF,
    CONF_BOILER_MIN_ON,
    CONF_BOILER_MIN_ROOMS,
    CONF_CALENDAR,
    CONF_CALIBRATION_ENTITIES,
    CONF_CALIBRATION_MODE,
    CONF_CLIMATES,
    CONF_COMMAND_MODE,
    CONF_COMP_BELOW,
    CONF_COMP_ENABLED,
    CONF_COMP_OFFSET,
    CONF_CUTOFF_AVG_HOURS,
    CONF_CUTOFF_ENABLED,
    CONF_CUTOFF_HYSTERESIS,
    CONF_CUTOFF_TEMP,
    CONF_DAY_BOUNDARY,
    CONF_DEPARTURE_DELAY,
    CONF_FORECAST_ENABLED,
    CONF_FORECAST_HOURS,
    CONF_FROST_TEMP,
    CONF_GUEST_EXPIRE_HOURS,
    CONF_HELPER_OFF_PRESET,
    CONF_HELPER_ON_PRESET,
    CONF_HOME_RULE,
    CONF_HYSTERESIS,
    CONF_LEARN_TOLERANCE,
    CONF_LEVELS,
    CONF_LINKED_WINDOW_SENSORS,
    CONF_MAX_TEMP,
    CONF_MIN_OFF,
    CONF_MIN_ON,
    CONF_NEARBY_GEOMETRIC,
    CONF_NEARBY_LIMIT,
    CONF_NEARBY_MODE,
    CONF_NEARBY_TEMP,
    CONF_NEARBY_ZONES,
    CONF_NOTIFY_SERVICE,
    CONF_OCCUPANCY_MINUTES,
    CONF_OCCUPANCY_SENSORS,
    CONF_OPTIMAL_START,
    CONF_OPTIMAL_START_MAX,
    CONF_OPTIMAL_STOP,
    CONF_OPTIMAL_STOP_MINUTES,
    CONF_OUTDOOR_SENSOR,
    CONF_OVERRIDE_HOURS,
    CONF_OVERRIDE_MODE,
    CONF_OVERRIDE_SCOPE,
    CONF_PERSONS,
    CONF_PRESENCE_SENSORS,
    CONF_PRESET_MAP,
    CONF_PRESET_NAMES,
    CONF_PRICE_HIGH,
    CONF_PRICE_HIGH_OFFSET,
    CONF_PRICE_LOW,
    CONF_PRICE_LOW_OFFSET,
    CONF_PRICE_SENSOR,
    CONF_PROXIMITY_DIRECTION,
    CONF_PROXIMITY_DISTANCE,
    CONF_PV_OFFSET,
    CONF_PV_SENSOR,
    CONF_PV_THRESHOLD,
    CONF_REEVAL_MINUTES,
    CONF_REFERENCE_ROOM,
    CONF_ROOM_DIFF_ALERT,
    CONF_SCHEDULE,
    CONF_SCHEDULE_HELPER,
    CONF_SCHEDULE_SOURCE,
    CONF_SEASON_DAYS,
    CONF_SEASON_END,
    CONF_SEASON_MODE,
    CONF_SEASON_START,
    CONF_SEASON_TEMP,
    CONF_SOLAR_OFFSET,
    CONF_SOURCE,
    CONF_STOP_TOLERANCE,
    CONF_SWITCHES,
    CONF_TEMP_AGGREGATION,
    CONF_TEMP_SENSORS,
    CONF_TEMP_UNIT,
    CONF_TRAVEL_TIME,
    CONF_TRV_BOOST,
    CONF_TRV_BOOST_TEMP,
    CONF_VACATION_PREHEAT,
    CONF_VALVE_DAY,
    CONF_VALVE_EXERCISE,
    CONF_VALVE_TIME,
    CONF_VERIFY_COMMANDS,
    CONF_WEATHER,
    CONF_WINDOW_ACTION,
    CONF_WINDOW_CLOSE_DELAY,
    CONF_WINDOW_DROP_DEGREES,
    CONF_WINDOW_DROP_DETECT,
    CONF_WINDOW_DROP_MINUTES,
    CONF_WINDOW_IGNORE_ABOVE,
    CONF_WINDOW_OPEN_DELAY,
    CONF_WINDOW_SENSORS,
    CONF_WORKDAY_SENSOR,
    DEFAULT_LEVEL_TEMPS,
    DOMAIN,
    GT_DOMAIN,
    HOME_RULE_ALL,
    HOME_RULE_ANY,
    HOUSE_DEFAULTS,
    NEARBY_PRESET,
    NEARBY_TEMPERATURE,
    OVERRIDE_FIXED,
    OVERRIDE_HOURS_MAX,
    OVERRIDE_HOURS_MIN,
    OVERRIDE_NEXT,
    OVERRIDE_SCOPE_HOUSE,
    OVERRIDE_SCOPE_ROOM,
    PRESETS,
    ROOM_DEFAULTS,
    SCHEDULE_HELPER,
    SCHEDULE_INTERNAL,
    SEASON_ALWAYS,
    SEASON_AUTO,
    SEASON_DATES,
    SOURCE_CLIMATE,
    SOURCE_GT,
    SOURCE_SWITCH,
    SUBENTRY_ROOM,
    WEEKDAYS,
    WINDOW_ACTION_FROST,
    WINDOW_ACTION_OFF,
)
from .outdoor import parse_month_day
from .schedule import NAME_RE, ScheduleError, parse_schedule
from .util import (
    as_list,
    delta_from_celsius,
    delta_to_celsius,
    from_celsius,
    is_fahrenheit,
    system_unit,
    to_celsius,
)

CONF_NAME = "name"

# ---------------------------------------------------------------------------
# Selector helpers
# ---------------------------------------------------------------------------


def _entity(
    domain: str | list[str], *, multiple: bool = False, **kwargs: Any
) -> selector.EntitySelector:
    """Entity picker for one or more domains."""
    return selector.EntitySelector(
        selector.EntitySelectorConfig(domain=domain, multiple=multiple, **kwargs)
    )


def _number(
    minimum: float, maximum: float, step: float = 1, unit: str | None = None
) -> selector.NumberSelector:
    """Number box with limits, step and unit."""
    config = selector.NumberSelectorConfig(
        min=minimum, max=maximum, step=step, mode=selector.NumberSelectorMode.BOX
    )
    if unit:
        config["unit_of_measurement"] = unit
    return selector.NumberSelector(config)


def _select(options: list[str], key: str) -> selector.SelectSelector:
    """Drop-down list whose labels come from the translations (``key``)."""
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=options, translation_key=key, mode=selector.SelectSelectorMode.DROPDOWN
        )
    )


def _bool() -> selector.BooleanSelector:
    """On / off switch."""
    return selector.BooleanSelector()


def _text(multiline: bool = False) -> selector.TextSelector:
    """Text field, on one or more lines."""
    return selector.TextSelector(selector.TextSelectorConfig(multiline=multiline))


def _opt(key: str, values: dict[str, Any]) -> vol.Optional:
    """Optional field pre-filled with the current value (can be cleared)."""
    return vol.Optional(key, description={"suggested_value": values.get(key)})


def _req(key: str, values: dict[str, Any], defaults: dict[str, Any]) -> vol.Required:
    """Required field with the current value, else the default."""
    return vol.Required(key, default=values.get(key, defaults.get(key)))


def _merge(
    current: dict[str, Any], schema: vol.Schema, user_input: dict[str, Any]
) -> dict[str, Any]:
    """Merge a step into the stored values; cleared optional fields are removed."""
    result = dict(current)
    for marker in schema.schema:
        key = str(getattr(marker, "schema", marker))
        if key in user_input:
            result[key] = user_input[key]
        else:
            result.pop(key, None)
    return result


# ---------------------------------------------------------------------------
# Temperature unit of the house. Values are stored in °C; the forms show them
# in the unit of the house and convert what the user enters back to °C.
# ---------------------------------------------------------------------------
UNIT_CELSIUS = "celsius"
UNIT_FAHRENHEIT = "fahrenheit"

TEMP_ABSOLUTE_KEYS = {
    CONF_CUTOFF_TEMP,
    CONF_SEASON_TEMP,
    CONF_COMP_BELOW,
    CONF_WINDOW_IGNORE_ABOVE,
    CONF_FROST_TEMP,
    CONF_MAX_TEMP,
    CONF_NEARBY_TEMP,
    CONF_TRV_BOOST_TEMP,
    *(f"temp_{p}" for p in PRESETS),
}
TEMP_DELTA_KEYS = {
    CONF_CUTOFF_HYSTERESIS,
    CONF_COMP_OFFSET,
    CONF_PRICE_HIGH_OFFSET,
    CONF_PRICE_LOW_OFFSET,
    CONF_PV_OFFSET,
    CONF_ROOM_DIFF_ALERT,
    CONF_HYSTERESIS,
    CONF_LEARN_TOLERANCE,
    CONF_STOP_TOLERANCE,
    CONF_WINDOW_DROP_DEGREES,
    CONF_SOLAR_OFFSET,
}


def _fahrenheit(unit: str | None) -> bool:
    """True when the forms are in °F."""
    return is_fahrenheit(unit)


def _shown(values: dict[str, Any], unit: str | None) -> dict[str, Any]:
    """Stored values (°C) as the form shows them."""
    if not _fahrenheit(unit):
        return dict(values)
    out = dict(values)
    for key, value in values.items():
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            continue
        if key in TEMP_ABSOLUTE_KEYS:
            out[key] = round(float(from_celsius(value, unit)), 1)
        elif key in TEMP_DELTA_KEYS:
            out[key] = round(float(delta_from_celsius(value, unit)), 2)
    return out


def _kept(user_input: dict[str, Any] | None, unit: str | None) -> dict[str, Any]:
    """What the user entered, converted back to °C for storage."""
    values = dict(user_input or {})
    if not _fahrenheit(unit):
        return values
    for key, value in list(values.items()):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            continue
        if key in TEMP_ABSOLUTE_KEYS:
            values[key] = round(float(to_celsius(value, unit)), 3)
        elif key in TEMP_DELTA_KEYS:
            values[key] = round(float(delta_to_celsius(value, unit)), 3)
    return values


def _unitize(schema: vol.Schema, unit: str | None) -> vol.Schema:
    """Number fields of temperatures in the unit of the house."""
    if not _fahrenheit(unit):
        return schema
    fields: dict[Any, Any] = {}
    for marker, field in schema.schema.items():
        key = str(getattr(marker, "schema", marker))
        absolute = key in TEMP_ABSOLUTE_KEYS
        if (absolute or key in TEMP_DELTA_KEYS) and isinstance(field, selector.NumberSelector):
            config = dict(field.config)
            for bound, rounding in (("min", math.floor), ("max", math.ceil)):
                if config.get(bound) is not None:
                    value = float(config[bound])
                    converted = value * 1.8 + 32 if absolute else value * 1.8
                    # Rounded outwards to a tenth, so a converted value at the limit
                    # is accepted and a small minimum (e.g. 0.1 °C) does not become 0.
                    config[bound] = rounding(round(converted * 10, 6)) / 10
            config["unit_of_measurement"] = "°F"
            field = selector.NumberSelector(selector.NumberSelectorConfig(**config))
        fields[marker] = field
    return vol.Schema(fields)


class _UnitForms:
    """Forms shown in the unit of the house."""

    def _unit(self) -> str:
        """Unit the forms of this flow use."""
        return UNIT_CELSIUS

    def async_show_form(
        self, *, step_id: str, data_schema: vol.Schema | None = None, **kwargs: Any
    ) -> Any:
        """Show a form with its temperature fields in the unit of the house."""
        if data_schema is not None:
            data_schema = _unitize(data_schema, self._unit())
        return super().async_show_form(  # type: ignore[misc]
            step_id=step_id, data_schema=data_schema, **kwargs
        )


def _unit_select() -> selector.SelectSelector:
    """Choice between °C and °F."""
    return _select([UNIT_CELSIUS, UNIT_FAHRENHEIT], "temperature_unit")


# ---------------------------------------------------------------------------
# House schemas (used by the options flow). Each group has a first form with
# the choices and the sensors, and a second form only with the values that
# apply to what was chosen (skipped when nothing applies).
# ---------------------------------------------------------------------------


def _presence_schema(v: dict[str, Any]) -> vol.Schema:
    """People, home rule, nearby zones and what presence information is used."""
    d = HOUSE_DEFAULTS
    return vol.Schema(
        {
            _req(CONF_PERSONS, v, d): _entity("person", multiple=True),
            _req(CONF_HOME_RULE, v, d): _select([HOME_RULE_ANY, HOME_RULE_ALL], "home_rule"),
            _req(CONF_NEARBY_ZONES, v, d): _entity("zone", multiple=True),
            _req(CONF_NEARBY_GEOMETRIC, v, d): _bool(),
            _req(CONF_DEPARTURE_DELAY, v, d): _number(0, 240, 1, "min"),
            _req(CONF_ARRIVAL_DELAY, v, d): _number(0, 240, 1, "min"),
            _req(CONF_PRESENCE_SENSORS, v, d): _entity(
                ["binary_sensor", "input_boolean", "switch"], multiple=True
            ),
            _req(CONF_GUEST_EXPIRE_HOURS, v, d): _number(0, 720, 1, "h"),
            _opt(CONF_PROXIMITY_DISTANCE, v): _entity("sensor"),
            _opt(CONF_PROXIMITY_DIRECTION, v): _entity("sensor"),
            _opt(CONF_TRAVEL_TIME, v): _entity("sensor"),
        }
    )


def _presence_details(v: dict[str, Any]) -> vol.Schema:
    """Values that apply to the presence choices (delays, distances, guests)."""
    d = HOUSE_DEFAULTS
    fields: dict[Any, Any] = {}
    if v.get(CONF_PROXIMITY_DISTANCE):
        fields[_req(CONF_ARRIVAL_DISTANCE, v, d)] = _number(0, 500, 0.5, "km")
    if v.get(CONF_TRAVEL_TIME):
        fields[_req(CONF_ARRIVAL_MINUTES, v, d)] = _number(0, 240, 1, "min")
    return vol.Schema(fields)


def _calendar_schema(v: dict[str, Any]) -> vol.Schema:
    """Calendar and Workday sensor that choose the schedule profile."""
    d = HOUSE_DEFAULTS
    return vol.Schema(
        {
            _opt(CONF_WORKDAY_SENSOR, v): _entity("binary_sensor"),
            _opt(CONF_CALENDAR, v): _entity("calendar"),
            _req(CONF_DAY_BOUNDARY, v, d): selector.TimeSelector(),
        }
    )


def _weather_schema(v: dict[str, Any]) -> vol.Schema:
    """Outdoor source and which weather features are used."""
    d = HOUSE_DEFAULTS
    return vol.Schema(
        {
            _opt(CONF_OUTDOOR_SENSOR, v): _entity("sensor", device_class="temperature"),
            _opt(CONF_WEATHER, v): _entity("weather"),
            _req(CONF_CUTOFF_ENABLED, v, d): _bool(),
            _req(CONF_FORECAST_ENABLED, v, d): _bool(),
            _req(CONF_SEASON_MODE, v, d): _select(
                [SEASON_ALWAYS, SEASON_DATES, SEASON_AUTO], "season_mode"
            ),
            _req(CONF_COMP_ENABLED, v, d): _bool(),
            _opt(CONF_WINDOW_IGNORE_ABOVE, v): _number(0, 40, 0.5, "°C"),
        }
    )


def _weather_details(v: dict[str, Any]) -> vol.Schema:
    """Values of the chosen weather features (cutoff, season, compensation, forecast)."""
    d = HOUSE_DEFAULTS
    fields: dict[Any, Any] = {}
    if v.get(CONF_CUTOFF_ENABLED) or v.get(CONF_FORECAST_ENABLED):
        fields[_req(CONF_CUTOFF_TEMP, v, d)] = _number(5, 30, 0.5, "°C")
    if v.get(CONF_CUTOFF_ENABLED):
        fields[_req(CONF_CUTOFF_HYSTERESIS, v, d)] = _number(0, 5, 0.1, "°C")
        fields[_req(CONF_CUTOFF_AVG_HOURS, v, d)] = _number(1, 48, 1, "h")
    if v.get(CONF_FORECAST_ENABLED):
        fields[_req(CONF_FORECAST_HOURS, v, d)] = _number(1, 24, 1, "h")
    if v.get(CONF_SEASON_MODE) == SEASON_DATES:
        fields[_req(CONF_SEASON_START, v, d)] = _text()
        fields[_req(CONF_SEASON_END, v, d)] = _text()
    if v.get(CONF_SEASON_MODE) == SEASON_AUTO:
        fields[_req(CONF_SEASON_DAYS, v, d)] = _number(1, 14, 1, "d")
        fields[_req(CONF_SEASON_TEMP, v, d)] = _number(0, 25, 0.5, "°C")
    if v.get(CONF_COMP_ENABLED):
        fields[_req(CONF_COMP_BELOW, v, d)] = _number(-30, 15, 0.5, "°C")
        fields[_req(CONF_COMP_OFFSET, v, d)] = _number(-3, 3, 0.1, "°C")
    return vol.Schema(fields)


def _weather_choice_errors(user_input: dict[str, Any]) -> dict[str, str]:
    """Weather functions that need an outdoor temperature or a weather entity."""
    errors: dict[str, str] = {}
    outdoor = bool(user_input.get(CONF_OUTDOOR_SENSOR) or user_input.get(CONF_WEATHER))
    if not outdoor:
        if user_input.get(CONF_CUTOFF_ENABLED):
            errors[CONF_CUTOFF_ENABLED] = "outdoor_required"
        if user_input.get(CONF_SEASON_MODE) == SEASON_AUTO:
            errors[CONF_SEASON_MODE] = "outdoor_required"
        if user_input.get(CONF_COMP_ENABLED):
            errors[CONF_COMP_ENABLED] = "outdoor_required"
        if user_input.get(CONF_WINDOW_IGNORE_ABOVE) not in (None, ""):
            errors[CONF_WINDOW_IGNORE_ABOVE] = "outdoor_required"
    if user_input.get(CONF_FORECAST_ENABLED):
        if not user_input.get(CONF_WEATHER):
            errors[CONF_FORECAST_ENABLED] = "weather_required"
        elif not user_input.get(CONF_CUTOFF_ENABLED):
            errors[CONF_FORECAST_ENABLED] = "cutoff_required"
    return errors


def _weather_errors(user_input: dict[str, Any]) -> dict[str, str]:
    """Check the heating season dates (MM-DD)."""
    errors: dict[str, str] = {}
    for key in (CONF_SEASON_START, CONF_SEASON_END):
        if key in user_input:
            try:
                parse_month_day(str(user_input.get(key, "")))
            except ValueError:
                errors[key] = "invalid_month_day"
    return errors


def _energy_schema(v: dict[str, Any]) -> vol.Schema:
    """Tariff and PV sensors."""
    return vol.Schema(
        {
            _opt(CONF_PRICE_SENSOR, v): _entity("sensor"),
            _opt(CONF_PV_SENSOR, v): _entity("sensor"),
        }
    )


def _energy_details(v: dict[str, Any]) -> vol.Schema:
    """Price limits and adjustments for the chosen energy sensors."""
    d = HOUSE_DEFAULTS
    fields: dict[Any, Any] = {}
    if v.get(CONF_PRICE_SENSOR):
        fields[_opt(CONF_PRICE_HIGH, v)] = _number(-1000, 1000, 0.001)
        fields[_req(CONF_PRICE_HIGH_OFFSET, v, d)] = _number(-3, 3, 0.1, "°C")
        fields[_opt(CONF_PRICE_LOW, v)] = _number(-1000, 1000, 0.001)
        fields[_req(CONF_PRICE_LOW_OFFSET, v, d)] = _number(-3, 3, 0.1, "°C")
    if v.get(CONF_PV_SENSOR):
        fields[_req(CONF_PV_THRESHOLD, v, d)] = _number(0, 100000, 10, "W")
        fields[_req(CONF_PV_OFFSET, v, d)] = _number(-3, 3, 0.1, "°C")
    return vol.Schema(fields)


def _boiler_schema(v: dict[str, Any]) -> vol.Schema:
    """Boiler entity and room-difference alert."""
    d = HOUSE_DEFAULTS
    return vol.Schema(
        {
            _opt(CONF_BOILER_ENTITY, v): _entity(["switch", "climate", "input_boolean"]),
            _req(CONF_ROOM_DIFF_ALERT, v, d): _number(0, 10, 0.5, "°C"),
        }
    )


def _boiler_details(v: dict[str, Any], rooms: list[selector.SelectOptionDict]) -> vol.Schema:
    """Boiler timing and the rooms that decide it (reference room only with several rooms)."""
    d = HOUSE_DEFAULTS
    fields: dict[Any, Any] = {}
    if v.get(CONF_BOILER_ENTITY):
        # At most as many rooms as the house has now (at least 1).
        most = max(1, len(rooms))
        shown = {
            **v,
            CONF_BOILER_MIN_ROOMS: min(
                int(v.get(CONF_BOILER_MIN_ROOMS, d[CONF_BOILER_MIN_ROOMS])), most
            ),
        }
        fields[_req(CONF_BOILER_MIN_ROOMS, shown, d)] = _number(1, most, 1)
        fields[_req(CONF_BOILER_MIN_ON, v, d)] = _number(0, 60, 1, "min")
        fields[_req(CONF_BOILER_MIN_OFF, v, d)] = _number(0, 60, 1, "min")
        if len(rooms) > 1:
            fields[_opt(CONF_REFERENCE_ROOM, v)] = selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=rooms, mode=selector.SelectSelectorMode.DROPDOWN
                )
            )
    return vol.Schema(fields)


def _behavior_schema(v: dict[str, Any]) -> vol.Schema:
    """Manual changes, vacation and safety choices."""
    d = HOUSE_DEFAULTS
    return vol.Schema(
        {
            _req(CONF_OVERRIDE_MODE, v, d): _select(
                [OVERRIDE_FIXED, OVERRIDE_NEXT], "override_mode"
            ),
            _req(CONF_OVERRIDE_SCOPE, v, d): _select(
                [OVERRIDE_SCOPE_ROOM, OVERRIDE_SCOPE_HOUSE], "override_scope"
            ),
            _req(CONF_VACATION_PREHEAT, v, d): _number(0, 48, 0.5, "h"),
            _req(CONF_AUTO_VACATION_HOURS, v, d): _number(0, 720, 1, "h"),
            _req(CONF_FROST_TEMP, v, d): _number(3, 15, 0.5, "°C"),
            _req(CONF_MAX_TEMP, v, d): _number(15, 35, 0.5, "°C"),
            _req(CONF_REEVAL_MINUTES, v, d): _number(1, 60, 1, "min"),
        }
    )


def _behavior_details(v: dict[str, Any]) -> vol.Schema:
    """Values that apply to the behavior choices."""
    d = HOUSE_DEFAULTS
    if v.get(CONF_OVERRIDE_MODE) == OVERRIDE_FIXED:
        return vol.Schema(
            {
                _req(CONF_OVERRIDE_HOURS, v, d): _number(
                    OVERRIDE_HOURS_MIN, OVERRIDE_HOURS_MAX, 0.25, "h"
                )
            }
        )
    return vol.Schema({})


def _alerts_schema(v: dict[str, Any]) -> vol.Schema:
    """Notifications: service, unavailable devices, batteries, windows."""
    d = HOUSE_DEFAULTS
    return vol.Schema(
        {
            _opt(CONF_NOTIFY_SERVICE, v): _text(),
            _req(CONF_ALERT_WINDOW_MINUTES, v, d): _number(1, 720, 1, "min"),
            _req(CONF_ALERT_UNAVAILABLE_MINUTES, v, d): _number(1, 720, 1, "min"),
            _req(CONF_BATTERY_THRESHOLD, v, d): _number(1, 100, 1, "%"),
            _req(CONF_VERIFY_COMMANDS, v, d): _bool(),
        }
    )


# ---------------------------------------------------------------------------
# Shared room schemas (rooms and the whole-house zone)
# ---------------------------------------------------------------------------


def _devices_schema(d: dict[str, Any]) -> vol.Schema:
    """The devices of the chosen source (and the command for other thermostats)."""
    source = d[CONF_SOURCE]
    if source == SOURCE_GT:
        return vol.Schema(
            {
                vol.Required(CONF_CLIMATES, default=d.get(CONF_CLIMATES) or []): _entity(
                    "climate", multiple=True, integration=GT_DOMAIN
                )
            }
        )
    if source == SOURCE_CLIMATE:
        return vol.Schema(
            {
                vol.Required(CONF_CLIMATES, default=d.get(CONF_CLIMATES) or []): _entity(
                    "climate", multiple=True
                ),
                vol.Required(CONF_COMMAND_MODE, default=d[CONF_COMMAND_MODE]): _select(
                    [COMMAND_TEMPERATURE, COMMAND_PRESET, COMMAND_HVAC], "command_mode"
                ),
                vol.Required(
                    CONF_TRV_BOOST, default=bool(d.get(CONF_TRV_BOOST, False))
                ): _bool(),
            }
        )
    return vol.Schema(
        {
            vol.Required(CONF_SWITCHES, default=d.get(CONF_SWITCHES) or []): _entity(
                ["switch", "input_boolean"], multiple=True
            )
        }
    )


Skip = tuple[str | None, str | None]


def _gt_heaters(hass: Any) -> dict[str, str]:
    """Generic Thermostat climate entity -> its heater (from the GT entries)."""
    heaters: dict[str, str] = {}
    registry = er.async_get(hass)
    for gt_entry in hass.config_entries.async_entries(GT_DOMAIN):
        heater = {**gt_entry.data, **gt_entry.options}.get("heater")
        if heater:
            for item in er.async_entries_for_config_entry(registry, gt_entry.entry_id):
                if item.domain == "climate":
                    heaters[item.entity_id] = heater
    return heaters


def _entity_owners(hass: Any, skip: Skip = (None, None)) -> dict[str, tuple[str, str]]:
    """Who controls an entity already, in every house: entity -> (kind, where).

    Kinds: ``room`` (a thermostat or relay of a room), ``source`` (the heat
    source of a house), ``gt_heater`` (the relay of a Generic Thermostat used by
    a room). ``skip`` is (entry id, subentry id or "boiler") of what is being
    edited, so it does not count against itself.
    """
    heaters = _gt_heaters(hass)
    owners: dict[str, tuple[str, str]] = {}
    for entry in hass.config_entries.async_entries(DOMAIN):
        boiler = {**entry.data, **entry.options}.get(CONF_BOILER_ENTITY)
        if boiler and skip != (entry.entry_id, "boiler"):
            owners[boiler] = ("source", entry.title)
        for sub in entry.subentries.values():
            if skip == (entry.entry_id, sub.subentry_id):
                continue
            where = f"{entry.title} → {sub.title}"
            devices = [*(sub.data.get(CONF_CLIMATES) or []), *(sub.data.get(CONF_SWITCHES) or [])]
            for entity_id in devices:
                owners[entity_id] = ("room", where)
                if (heater := heaters.get(entity_id)) is not None:
                    owners.setdefault(heater, ("gt_heater", where))
    return owners


def _in_use_error(
    hass: Any, entities: list[str], skip: Skip, placeholders: dict[str, str]
) -> str | None:
    """Error key when one of ``entities`` is controlled somewhere else (fills placeholders)."""
    owners = _entity_owners(hass, skip)
    heaters = _gt_heaters(hass)
    # The relay of a chosen Generic Thermostat must not be commanded elsewhere either.
    checked = [*entities, *(heaters[e] for e in entities if e in heaters)]
    for entity_id in checked:
        if entity_id in owners:
            kind, where = owners[entity_id]
            placeholders.update({"entity": entity_id, "owner": where})
            return {"room": "entity_in_room", "source": "entity_is_source"}.get(
                kind, "entity_is_gt_heater"
            )
    return None


def _outdoor_error(hass: Any, sensors: list[str], placeholders: dict[str, str]) -> str | None:
    """Error key when a room temperature sensor is the outdoor sensor of a house."""
    for entry in hass.config_entries.async_entries(DOMAIN):
        outdoor = {**entry.data, **entry.options}.get(CONF_OUTDOOR_SENSOR)
        if outdoor and outdoor in sensors:
            placeholders.update({"entity": outdoor, "owner": entry.title})
            return "room_sensor_is_outdoor"
    return None


def _room_sensor_owner(hass: Any, sensor: str) -> str | None:
    """The room (house → room) that uses ``sensor`` as a temperature sensor."""
    for entry in hass.config_entries.async_entries(DOMAIN):
        for sub in entry.subentries.values():
            if sensor in (sub.data.get(CONF_TEMP_SENSORS) or []):
                return f"{entry.title} → {sub.title}"
    return None


def _devices_done(d: dict[str, Any], user_input: dict[str, Any]) -> dict[str, str]:
    """Store the devices of the source (the others are cleared); errors if none."""
    source = d[CONF_SOURCE]
    key = CONF_SWITCHES if source == SOURCE_SWITCH else CONF_CLIMATES
    if not user_input.get(key):
        return {key: "no_devices"}
    boost = source == SOURCE_CLIMATE and bool(user_input.get(CONF_TRV_BOOST, False))
    if boost and user_input.get(CONF_COMMAND_MODE) != COMMAND_TEMPERATURE:
        return {CONF_TRV_BOOST: "boost_temperature_only"}
    other = CONF_CLIMATES if source == SOURCE_SWITCH else CONF_SWITCHES
    d[key] = list(user_input[key])
    d[other] = []
    if source == SOURCE_CLIMATE:
        d[CONF_COMMAND_MODE] = user_input[CONF_COMMAND_MODE]
        d[CONF_TRV_BOOST] = boost
    return {}


def _is_on_off(d: dict[str, Any]) -> bool:
    """Relays, or thermostats switched on and off by the integration."""
    return d[CONF_SOURCE] == SOURCE_SWITCH or (
        d[CONF_SOURCE] == SOURCE_CLIMATE and d.get(CONF_COMMAND_MODE) == COMMAND_HVAC
    )


def _on_off_schema(d: dict[str, Any], with_sensors: bool) -> vol.Schema:
    """Relay control: hysteresis and minimum on / off times (and sensors when needed)."""
    fields: dict[Any, Any] = {}
    if with_sensors:
        fields[_req(CONF_TEMP_SENSORS, d, ROOM_DEFAULTS)] = _entity(
            "sensor", multiple=True, device_class="temperature"
        )
    fields[_req(CONF_HYSTERESIS, d, ROOM_DEFAULTS)] = _number(0.1, 3, 0.1, "°C")
    fields[_req(CONF_MIN_ON, d, ROOM_DEFAULTS)] = _number(0, 60, 1, "min")
    fields[_req(CONF_MIN_OFF, d, ROOM_DEFAULTS)] = _number(0, 60, 1, "min")
    return vol.Schema(fields)


def _no_hvac_action(hass: Any, d: dict[str, Any]) -> bool:
    """A chosen thermostat may not report whether it heats (no hvac_action).

    Also True when a thermostat is unavailable now: it cannot be checked, so the
    hysteresis is asked for instead of assumed.
    """
    for entity_id in d.get(CONF_CLIMATES) or []:
        state = hass.states.get(entity_id)
        if (
            state is None
            or state.state in ("unknown", "unavailable")
            or "hvac_action" not in state.attributes
        ):
            return True
    return False


def _thermostat_schema(d: dict[str, Any], hass: Any) -> vol.Schema:
    """Thermostat tolerance, and the hysteresis for thermostats that may not report hvac_action."""
    fields: dict[Any, Any] = {
        _req(CONF_LEARN_TOLERANCE, d, ROOM_DEFAULTS): _number(0, 2, 0.1, "°C")
    }
    # Without hvac_action the heat demand is decided with the hysteresis.
    if _no_hvac_action(hass, d):
        fields[_req(CONF_HYSTERESIS, d, ROOM_DEFAULTS)] = _number(0.1, 3, 0.1, "°C")
    return vol.Schema(fields)


def _boost_possible(d: dict[str, Any]) -> bool:
    """The TRV boost exists for thermostats commanded with a temperature."""
    return d[CONF_SOURCE] == SOURCE_CLIMATE and d.get(CONF_COMMAND_MODE) == COMMAND_TEMPERATURE


def _boost_on(d: dict[str, Any]) -> bool:
    """The TRV boost is chosen."""
    return _boost_possible(d) and bool(d.get(CONF_TRV_BOOST, False))


def _boost_schema(
    d: dict[str, Any], low: float, high: float, with_sensors: bool
) -> vol.Schema:
    """The boost temperature (empty = maximum of the house), the hysteresis and the sensors.

    ``d`` holds the values as the form shows them; ``low`` / ``high`` (°C) are the
    frost protection and the maximum of the house.
    """
    fields: dict[Any, Any] = {}
    if with_sensors:
        fields[_req(CONF_TEMP_SENSORS, d, ROOM_DEFAULTS)] = _entity(
            "sensor", multiple=True, device_class="temperature"
        )
    fields[_opt(CONF_TRV_BOOST_TEMP, d)] = _number(low, high, 0.5, "°C")
    fields[_req(CONF_HYSTERESIS, d, ROOM_DEFAULTS)] = _number(0.1, 3, 0.1, "°C")
    return vol.Schema(fields)


# ---------------------------------------------------------------------------
# Whole-house heating (a zone created together with the house)
# ---------------------------------------------------------------------------
HOUSE_ZONE_ID = "whole_house"
HOUSE_ZONE_TITLE = "Whole house"
SOURCE_NONE = "none"


class _HouseHeatingSteps:
    """Heating of the whole house: source, devices, then the command settings."""

    _zone: dict[str, Any]

    def _zone_base(self) -> dict[str, Any]:
        """Current data of the whole-house zone (empty for a new one)."""
        return {}

    def _zone_title(self) -> str:
        """Title of the whole-house zone."""
        return HOUSE_ZONE_TITLE

    def _owner_skip(self) -> Skip:
        """(entry, subentry) of the zone being edited, not counted as another owner."""
        return (None, None)

    def _house_limits(self) -> tuple[float, float]:
        """Frost protection and maximum of the house (°C)."""
        return float(HOUSE_DEFAULTS[CONF_FROST_TEMP]), float(HOUSE_DEFAULTS[CONF_MAX_TEMP])

    async def _async_heating_done(self, data: dict[str, Any] | None) -> Any:
        """Save the zone (None = no heating devices)."""
        raise NotImplementedError

    async def async_step_heating(self, user_input: dict[str, Any] | None = None) -> Any:
        """What heats the whole house."""
        base = self._zone_base()
        if user_input is not None:
            if user_input[CONF_SOURCE] == SOURCE_NONE:
                return await self._async_heating_done(None)
            self._zone = {**ROOM_DEFAULTS, **base, CONF_SOURCE: user_input[CONF_SOURCE]}
            return await self.async_step_heating_devices()
        schema = vol.Schema(
            {
                vol.Required(CONF_SOURCE, default=base.get(CONF_SOURCE, SOURCE_GT)): _select(
                    [SOURCE_GT, SOURCE_CLIMATE, SOURCE_SWITCH, SOURCE_NONE], "house_source"
                )
            }
        )
        return self.async_show_form(  # type: ignore[attr-defined]
            step_id="heating",
            data_schema=schema,
            description_placeholders={"zone": self._zone_title()},
        )

    async def async_step_heating_devices(self, user_input: dict[str, Any] | None = None) -> Any:
        """The devices (and the command for other thermostats)."""
        z = self._zone
        schema = _devices_schema(z)
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {"entity": "", "owner": ""}
        if user_input is not None:
            errors = _devices_done(z, user_input)
            key = CONF_SWITCHES if z[CONF_SOURCE] == SOURCE_SWITCH else CONF_CLIMATES
            if not errors and (
                error := _in_use_error(
                    self.hass,  # type: ignore[attr-defined]
                    list(user_input.get(key) or []),
                    self._owner_skip(),
                    placeholders,
                )
            ):
                errors = {key: error}
            if not errors:
                if z[CONF_SOURCE] == SOURCE_GT:
                    return await self._async_heating_done(z)
                if _is_on_off(z):
                    return await self.async_step_heating_on_off()
                if _boost_on(z):
                    return await self.async_step_heating_boost()
                return await self.async_step_heating_thermostat()
        return self.async_show_form(  # type: ignore[attr-defined]
            step_id="heating_devices",
            data_schema=schema,
            errors=errors,
            description_placeholders=placeholders,
        )

    async def async_step_heating_on_off(self, user_input: dict[str, Any] | None = None) -> Any:
        """On / off settings (relays need a temperature sensor)."""
        z = self._zone
        relay = z[CONF_SOURCE] == SOURCE_SWITCH
        schema = _on_off_schema(_shown(z, self._unit()), relay)  # type: ignore[attr-defined]
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {"entity": "", "owner": ""}
        if user_input is not None:
            if relay and not user_input.get(CONF_TEMP_SENSORS):
                errors[CONF_TEMP_SENSORS] = "sensor_required"
            elif error := _outdoor_error(
                self.hass,  # type: ignore[attr-defined]
                list(user_input.get(CONF_TEMP_SENSORS) or []),
                placeholders,
            ):
                errors[CONF_TEMP_SENSORS] = error
            else:
                self._zone = _merge(z, schema, _kept(user_input, self._unit()))  # type: ignore[attr-defined]
                return await self._async_heating_done(self._zone)
        return self.async_show_form(  # type: ignore[attr-defined]
            step_id="heating_on_off",
            data_schema=schema,
            errors=errors,
            description_placeholders=placeholders,
        )

    async def async_step_heating_thermostat(self, user_input: dict[str, Any] | None = None) -> Any:
        """Thermostat tolerance."""
        schema = _thermostat_schema(_shown(self._zone, self._unit()), self.hass)  # type: ignore[attr-defined]
        if user_input is not None:
            self._zone = _merge(self._zone, schema, _kept(user_input, self._unit()))  # type: ignore[attr-defined]
            return await self._async_heating_done(self._zone)
        return self.async_show_form(  # type: ignore[attr-defined]
            step_id="heating_thermostat", data_schema=schema
        )

    async def async_step_heating_boost(self, user_input: dict[str, Any] | None = None) -> Any:
        """TRV boost: its temperature, the hysteresis and the room sensors it needs."""
        low, high = self._house_limits()
        shown = _shown(self._zone, self._unit())  # type: ignore[attr-defined]
        if shown.get(CONF_TRV_BOOST_TEMP) is not None:
            value = float(self._zone[CONF_TRV_BOOST_TEMP])
            shown = {
                **shown,
                **_shown({CONF_TRV_BOOST_TEMP: min(max(value, low), high)}, self._unit()),  # type: ignore[attr-defined]
            }
        schema = _boost_schema(shown, low, high, True)
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {"entity": "", "owner": ""}
        if user_input is not None:
            sensors = list(user_input.get(CONF_TEMP_SENSORS) or [])
            if not sensors:
                errors[CONF_TEMP_SENSORS] = "boost_sensor_required"
            elif error := _outdoor_error(self.hass, sensors, placeholders):  # type: ignore[attr-defined]
                errors[CONF_TEMP_SENSORS] = error
            else:
                self._zone = _merge(self._zone, schema, _kept(user_input, self._unit()))  # type: ignore[attr-defined]
                return await self._async_heating_done(self._zone)
        return self.async_show_form(  # type: ignore[attr-defined]
            step_id="heating_boost",
            data_schema=schema,
            errors=errors,
            description_placeholders=placeholders,
        )


# ---------------------------------------------------------------------------
# Main config flow
# ---------------------------------------------------------------------------


class AdvancedClimateConfigFlow(_UnitForms, _HouseHeatingSteps, ConfigFlow, domain=DOMAIN):
    """Create the house."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize."""
        self._house: dict[str, Any] = {}
        self._zone = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """First step: name, people and nearby zones."""
        if user_input is not None:
            self._house = dict(user_input)
            return await self.async_step_heating()
        default_unit = UNIT_FAHRENHEIT if is_fahrenheit(system_unit(self.hass)) else UNIT_CELSIUS
        schema = vol.Schema(
            {
                vol.Required(CONF_TEMP_UNIT, default=default_unit): _unit_select(),
                vol.Required(CONF_NAME, default="Home"): _text(),
                vol.Required(CONF_PERSONS, default=[]): _entity("person", multiple=True),
                vol.Required(CONF_NEARBY_ZONES, default=[]): _entity("zone", multiple=True),
                vol.Required(CONF_HOME_RULE, default=HOME_RULE_ANY): _select(
                    [HOME_RULE_ANY, HOME_RULE_ALL], "home_rule"
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    def _unit(self) -> str:
        """Unit the forms of this flow use."""
        return str(self._house.get(CONF_TEMP_UNIT, UNIT_CELSIUS))

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change the temperature unit of the house (every value is shown converted)."""
        entry = self._get_reconfigure_entry()
        if user_input is not None:
            self.hass.config_entries.async_update_entry(
                entry, options={**entry.options, CONF_TEMP_UNIT: user_input[CONF_TEMP_UNIT]}
            )
            return self.async_abort(reason="reconfigure_successful")
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_TEMP_UNIT, default=entry.options.get(CONF_TEMP_UNIT, UNIT_CELSIUS)
                ): _unit_select()
            }
        )
        return self.async_show_form(step_id="reconfigure", data_schema=schema)

    async def _async_heating_done(self, data: dict[str, Any] | None) -> ConfigFlowResult:
        """Save the whole-house zone (None = no heating devices)."""
        options = dict(self._house)
        name = options.pop(CONF_NAME)
        subentries = []
        if data is not None:
            subentries.append(
                {
                    "data": dict(data),
                    "subentry_type": SUBENTRY_ROOM,
                    "title": HOUSE_ZONE_TITLE,
                    "unique_id": HOUSE_ZONE_ID,
                }
            )
        return self.async_create_entry(title=name, data={}, options=options, subentries=subentries)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Options flow."""
        return AdvancedClimateOptionsFlow()

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Rooms are subentries."""
        return {SUBENTRY_ROOM: RoomSubentryFlow}


class AdvancedClimateOptionsFlow(_UnitForms, _HouseHeatingSteps, OptionsFlow):
    """House options, grouped in a menu."""

    def __init__(self) -> None:
        """Initialize."""
        self._zone = {}
        self._pending: dict[str, Any] = {}

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Menu."""
        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "heating",
                "presence",
                "calendar",
                "weather",
                "energy",
                "boiler",
                "behavior",
                "alerts",
            ],
        )

    def _house_zone(self) -> ConfigSubentry | None:
        """The whole-house zone, or the only room if there is just one."""
        rooms = [
            sub
            for sub in self.config_entry.subentries.values()
            if sub.subentry_type == SUBENTRY_ROOM
        ]
        for sub in rooms:
            if sub.unique_id == HOUSE_ZONE_ID:
                return sub
        return rooms[0] if len(rooms) == 1 else None

    def _unit(self) -> str:
        """Unit the forms of this flow use."""
        return str(self.config_entry.options.get(CONF_TEMP_UNIT, UNIT_CELSIUS))

    def _house_limits(self) -> tuple[float, float]:
        """Frost protection and maximum of the house (°C)."""
        options = {**HOUSE_DEFAULTS, **self.config_entry.options}
        return float(options[CONF_FROST_TEMP]), float(options[CONF_MAX_TEMP])

    def _owner_skip(self) -> Skip:
        """The whole-house zone being edited does not count against itself."""
        zone = self._house_zone()
        return (self.config_entry.entry_id, zone.subentry_id if zone else None)

    def _zone_base(self) -> dict[str, Any]:
        """Current data of the whole-house zone (empty for a new one)."""
        zone = self._house_zone()
        return dict(zone.data) if zone else {}

    def _zone_title(self) -> str:
        """Title of the whole-house zone."""
        zone = self._house_zone()
        return zone.title if zone else HOUSE_ZONE_TITLE

    async def _async_heating_done(self, data: dict[str, Any] | None) -> ConfigFlowResult:
        """Save the whole-house zone (None = no heating devices)."""
        zone = self._house_zone()
        entries = self.hass.config_entries
        if data is None:
            if zone is not None and zone.unique_id == HOUSE_ZONE_ID:
                entries.async_remove_subentry(self.config_entry, zone.subentry_id)
        elif zone is None:
            entries.async_add_subentry(
                self.config_entry,
                ConfigSubentry(
                    data=MappingProxyType(dict(data)),
                    subentry_type=SUBENTRY_ROOM,
                    title=HOUSE_ZONE_TITLE,
                    unique_id=HOUSE_ZONE_ID,
                ),
            )
        else:
            entries.async_update_subentry(self.config_entry, zone, data=dict(data))
        return self.async_create_entry(data=dict(self.config_entry.options))

    @property
    def _values(self) -> dict[str, Any]:
        """Current options, as the forms show them."""
        return _shown({**HOUSE_DEFAULTS, **self.config_entry.options}, self._unit())

    def _save(self, schema: vol.Schema, user_input: dict[str, Any]) -> ConfigFlowResult:
        """Store one form of options and close the flow."""
        return self.async_create_entry(
            data=_merge(dict(self.config_entry.options), schema, _kept(user_input, self._unit()))
        )

    # -- two forms: the choices, then only the values that apply --------------
    def _first(self, schema: vol.Schema, user_input: dict[str, Any]) -> None:
        """Keep the first form (the choices) until the second one is filled."""
        self._pending = _merge(
            dict(self.config_entry.options), schema, _kept(user_input, self._unit())
        )

    def _second(
        self,
        step_id: str,
        schema: vol.Schema,
        user_input: dict[str, Any] | None,
        errors: dict[str, str] | None = None,
    ) -> ConfigFlowResult:
        """Second form with the values that apply; skipped when there are none."""
        if not schema.schema:
            return self.async_create_entry(data=self._pending)
        if user_input is not None and not errors:
            return self.async_create_entry(
                data=_merge(self._pending, schema, _kept(user_input, self._unit()))
            )
        return self.async_show_form(step_id=step_id, data_schema=schema, errors=errors or {})

    @property
    def _pending_values(self) -> dict[str, Any]:
        """Options with the first form applied, as the forms show them."""
        return _shown({**HOUSE_DEFAULTS, **self._pending}, self._unit())

    async def async_step_presence(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Presence options."""
        schema = _presence_schema(self._values)
        if user_input is not None:
            self._first(schema, user_input)
            return await self.async_step_presence_details()
        return self.async_show_form(step_id="presence", data_schema=schema)

    async def async_step_presence_details(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Preheat distances of the chosen sensors."""
        return self._second("presence_details", _presence_details(self._pending_values), user_input)

    async def async_step_calendar(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Workday and calendar options."""
        schema = _calendar_schema(self._values)
        if user_input is not None:
            return self._save(schema, user_input)
        return self.async_show_form(step_id="calendar", data_schema=schema)

    async def async_step_weather(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Weather and season options."""
        schema = _weather_schema(self._values)
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {"entity": "", "owner": ""}
        if user_input is not None:
            errors = _weather_choice_errors(user_input)
            outdoor = user_input.get(CONF_OUTDOOR_SENSOR)
            if outdoor and (room := _room_sensor_owner(self.hass, outdoor)):
                errors[CONF_OUTDOOR_SENSOR] = "outdoor_is_room_sensor"
                placeholders.update({"entity": outdoor, "owner": room})
            if not errors:
                self._first(schema, user_input)
                return await self.async_step_weather_details()
            # Show the form again with what was entered (an emptied field stays empty).
            shown = {**self._values, **user_input}
            for key in (CONF_OUTDOOR_SENSOR, CONF_WEATHER, CONF_WINDOW_IGNORE_ABOVE):
                if key not in user_input:
                    shown.pop(key, None)
            schema = _weather_schema(shown)
        return self.async_show_form(
            step_id="weather",
            data_schema=schema,
            errors=errors,
            description_placeholders=placeholders,
        )

    async def async_step_weather_details(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Values of the chosen weather functions."""
        values = {**self._pending_values, **(user_input or {})}
        errors = _weather_errors(user_input) if user_input is not None else None
        return self._second("weather_details", _weather_details(values), user_input, errors)

    async def async_step_energy(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Tariff and PV sensors."""
        schema = _energy_schema(self._values)
        if user_input is not None:
            self._first(schema, user_input)
            return await self.async_step_energy_details()
        return self.async_show_form(step_id="energy", data_schema=schema)

    async def async_step_energy_details(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Thresholds and adjustments of the chosen sensors."""
        return self._second("energy_details", _energy_details(self._pending_values), user_input)

    def _room_options(self) -> list[selector.SelectOptionDict]:
        """Rooms of the house, for the reference room choice."""
        return [
            selector.SelectOptionDict(value=sub.subentry_id, label=sub.title)
            for sub in self.config_entry.subentries.values()
            if sub.subentry_type == SUBENTRY_ROOM
        ]

    async def async_step_boiler(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Boiler and heat demand options."""
        schema = _boiler_schema(self._values)
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {"entity": "", "owner": ""}
        if user_input is not None:
            boiler = user_input.get(CONF_BOILER_ENTITY)
            skip = (self.config_entry.entry_id, "boiler")
            if boiler and (error := _in_use_error(self.hass, [boiler], skip, placeholders)):
                errors[CONF_BOILER_ENTITY] = error
            else:
                self._first(schema, user_input)
                return await self.async_step_boiler_details()
            schema = _boiler_schema({**self._values, **user_input})
        return self.async_show_form(
            step_id="boiler",
            data_schema=schema,
            errors=errors,
            description_placeholders=placeholders,
        )

    async def async_step_boiler_details(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Settings of the chosen boiler."""
        schema = _boiler_details(self._pending_values, self._room_options())
        return self._second("boiler_details", schema, user_input)

    async def async_step_behavior(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Overrides, vacation and limits."""
        schema = _behavior_schema(self._values)
        if user_input is not None:
            self._first(schema, user_input)
            return await self.async_step_behavior_details()
        return self.async_show_form(step_id="behavior", data_schema=schema)

    async def async_step_behavior_details(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Duration of manual changes (fixed duration only)."""
        return self._second("behavior_details", _behavior_details(self._pending_values), user_input)

    async def async_step_alerts(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Notifications."""
        schema = _alerts_schema(self._values)
        if user_input is not None:
            return self._save(schema, user_input)
        return self.async_show_form(step_id="alerts", data_schema=schema)


# ---------------------------------------------------------------------------
# Room subentry flow
# ---------------------------------------------------------------------------


class RoomSubentryFlow(_UnitForms, ConfigSubentryFlow):
    """Add or reconfigure a room."""

    def __init__(self) -> None:
        """Initialize."""
        self._data: dict[str, Any] = {}
        self._reconfigure = False
        self._subentry_id: str | None = None

    def _unit(self) -> str:
        """Unit the forms of this flow use."""
        return str(self._get_entry().options.get(CONF_TEMP_UNIT, UNIT_CELSIUS))

    def _shown(self) -> dict[str, Any]:
        """Room values as the forms show them (unit of the house)."""
        return _shown(self._data, self._unit())

    def _kept(self, user_input: dict[str, Any] | None) -> dict[str, Any]:
        """What the user entered, converted to °C for storage."""
        return _kept(user_input, self._unit())

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Start a new room."""
        self._data = dict(ROOM_DEFAULTS)
        return await self.async_step_basics(user_input)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Edit an existing room."""
        subentry = self._get_reconfigure_subentry()
        self._data = {**ROOM_DEFAULTS, **subentry.data, CONF_NAME: subentry.title}
        self._reconfigure = True
        self._subentry_id = subentry.subentry_id
        return await self.async_step_basics()

    async def async_step_basics(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Name, area and how the room is heated."""
        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=self._data.get(CONF_NAME, "")): _text(),
                _opt(CONF_AREA, self._data): selector.AreaSelector(),
                vol.Required(CONF_SOURCE, default=self._data[CONF_SOURCE]): _select(
                    [SOURCE_GT, SOURCE_CLIMATE, SOURCE_SWITCH], "source"
                ),
            }
        )
        if user_input is not None:
            self._data = _merge(self._data, schema, self._kept(user_input))
            return await self.async_step_devices()
        return self.async_show_form(step_id="basics", data_schema=schema)

    async def async_step_devices(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """The devices that heat the room (and the command for other thermostats)."""
        d = self._data
        schema = _devices_schema(d)
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {"entity": "", "owner": ""}
        if user_input is not None:
            errors = _devices_done(d, user_input)
            key = CONF_SWITCHES if d[CONF_SOURCE] == SOURCE_SWITCH else CONF_CLIMATES
            skip = (self._get_entry().entry_id, self._subentry_id)
            if not errors and (
                error := _in_use_error(
                    self.hass, list(user_input.get(key) or []), skip, placeholders
                )
            ):
                errors = {key: error}
            if not errors:
                if d[CONF_SOURCE] == SOURCE_GT:
                    return await self.async_step_levels()
                if _is_on_off(d):
                    return await self.async_step_control_on_off()
                if _boost_on(d):
                    return await self.async_step_control_boost()
                return await self.async_step_control_thermostat()
        return self.async_show_form(
            step_id="devices",
            data_schema=schema,
            errors=errors,
            description_placeholders=placeholders,
        )

    def _on_off(self) -> bool:
        """True when the room is controlled on / off (relays or hvac_mode)."""
        return _is_on_off(self._data)

    async def async_step_control_on_off(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Hysteresis and minimum times (relays and on / off)."""
        schema = _on_off_schema(self._shown(), False)
        if user_input is not None:
            self._data = _merge(self._data, schema, self._kept(user_input))
            return await self.async_step_levels()
        return self.async_show_form(step_id="control_on_off", data_schema=schema)

    async def async_step_control_thermostat(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Thermostat tolerance (temperature / preset command)."""
        schema = _thermostat_schema(self._shown(), self.hass)
        if user_input is not None:
            self._data = _merge(self._data, schema, self._kept(user_input))
            return await self.async_step_levels()
        return self.async_show_form(step_id="control_thermostat", data_schema=schema)

    async def async_step_control_boost(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """TRV boost: its temperature (empty = maximum of the house) and the hysteresis."""
        low, high = self._safety_limits()
        shown = self._shown()
        if self._data.get(CONF_TRV_BOOST_TEMP) is not None:
            value = float(self._data[CONF_TRV_BOOST_TEMP])
            shown = {
                **shown,
                **_shown({CONF_TRV_BOOST_TEMP: min(max(value, low), high)}, self._unit()),
            }
        schema = _boost_schema(shown, low, high, False)
        if user_input is not None:
            self._data = _merge(self._data, schema, self._kept(user_input))
            return await self.async_step_levels()
        return self.async_show_form(step_id="control_boost", data_schema=schema)

    def _safety_limits(self) -> tuple[float, float]:
        """Frost protection and maximum temperature of the house (°C), the limits of a level."""
        entry = self._get_entry()
        options = {**HOUSE_DEFAULTS, **entry.data, **entry.options}
        return float(options[CONF_FROST_TEMP]), float(options[CONF_MAX_TEMP])

    def _current_levels(self) -> dict[str, float]:
        """Level temperatures in use now (edited from the card or numbers included)."""
        levels = {p: float(v) for p, v in DEFAULT_LEVEL_TEMPS.items()}
        levels.update({p: float(v) for p, v in (self._data.get(CONF_LEVELS) or {}).items()})
        house = getattr(self._get_entry(), "runtime_data", None)
        room = house.rooms.get(self._subentry_id) if house and self._subentry_id else None
        if room is not None:
            levels.update(room.levels)
        return levels

    def _device_presets(self) -> list[str]:
        """Presets offered by the chosen thermostats."""
        found: list[str] = []
        for entity_id in self._data.get(CONF_CLIMATES) or []:
            state = self.hass.states.get(entity_id)
            if state is None:
                continue
            for name in state.attributes.get("preset_modes") or []:
                if name and name != "none" and name not in found:
                    found.append(str(name))
        return found

    async def async_step_levels(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Level names or thermostat presets, level temperatures and what 'nearby' means."""
        d = self._shown()
        source = d[CONF_SOURCE]
        uses_presets = source == SOURCE_CLIMATE and d.get(CONF_COMMAND_MODE) == COMMAND_PRESET
        names = dict(d.get(CONF_PRESET_NAMES) or {})
        device_presets = self._device_presets() if uses_presets else []
        preset_map = d.get(CONF_PRESET_MAP)
        if preset_map is None:
            # No choice saved yet: the thermostat preset with the same name.
            preset_map = {
                p: names.get(p) or p for p in PRESETS if (names.get(p) or p) in device_presets
            }
        low, high = self._safety_limits()
        levels = {
            p: _shown({f"temp_{p}": min(max(v, low), high)}, self._unit())[f"temp_{p}"]
            for p, v in self._current_levels().items()
        }

        fields: dict[Any, Any] = {
            vol.Required(CONF_NEARBY_MODE, default=d[CONF_NEARBY_MODE]): _select(
                [NEARBY_PRESET, NEARBY_TEMPERATURE], "nearby_mode"
            ),
            vol.Required(CONF_NEARBY_LIMIT, default=bool(d.get(CONF_NEARBY_LIMIT, False))): _bool(),
        }
        if source != SOURCE_GT:
            for preset in PRESETS:
                if uses_presets:
                    key = vol.Optional(
                        f"device_{preset}", description={"suggested_value": preset_map.get(preset)}
                    )
                    fields[key] = (
                        selector.SelectSelector(
                            selector.SelectSelectorConfig(
                                options=device_presets,
                                custom_value=True,
                                mode=selector.SelectSelectorMode.DROPDOWN,
                            )
                        )
                        if device_presets
                        else _text()
                    )
                else:
                    fields[vol.Optional(f"name_{preset}", default=names.get(preset, preset))] = (
                        _text()
                    )
                fields[vol.Required(f"temp_{preset}", default=levels[preset])] = _number(
                    low, high, 0.5, "°C"
                )
        schema = vol.Schema(fields)
        placeholders = {"presets": ", ".join(device_presets) or "-", "name": ""}
        if user_input is not None:
            if uses_presets:
                chosen = {p: str(user_input.get(f"device_{p}") or "").strip() for p in PRESETS}
                chosen = {p: v for p, v in chosen.items() if v and v != "none"}
                values = [v.lower() for v in chosen.values()]
                new_names: dict[str, str] = {}
            else:
                chosen = {}
                new_names = {
                    p: str(user_input.get(f"name_{p}", "")).strip() or p
                    for p in PRESETS
                    if source != SOURCE_GT
                }
                values = [n.lower() for n in new_names.values()]
                bad = next((n for n in new_names.values() if not NAME_RE.fullmatch(n)), None)
                if bad is not None:
                    return self.async_show_form(
                        step_id="levels",
                        data_schema=schema,
                        errors={"base": "invalid_level_name"},
                        description_placeholders={**placeholders, "name": bad},
                    )
            if len(set(values)) != len(values):
                return self.async_show_form(
                    step_id="levels",
                    data_schema=schema,
                    errors={"base": "duplicate_names"},
                    description_placeholders=placeholders,
                )
            self._data[CONF_PRESET_NAMES] = new_names
            if uses_presets:
                self._data[CONF_PRESET_MAP] = chosen
            else:
                self._data.pop(CONF_PRESET_MAP, None)
            if source != SOURCE_GT:
                kept = self._kept({f"temp_{p}": user_input[f"temp_{p}"] for p in PRESETS})
                self._data[CONF_LEVELS] = {p: float(kept[f"temp_{p}"]) for p in PRESETS}
            else:
                self._data.pop(CONF_LEVELS, None)
            self._data[CONF_NEARBY_MODE] = user_input[CONF_NEARBY_MODE]
            self._data[CONF_NEARBY_LIMIT] = bool(user_input.get(CONF_NEARBY_LIMIT, False))
            if user_input[CONF_NEARBY_MODE] == NEARBY_TEMPERATURE:
                return await self.async_step_levels_nearby()
            return await self.async_step_sensors()
        return self.async_show_form(
            step_id="levels", data_schema=schema, description_placeholders=placeholders
        )

    async def async_step_levels_nearby(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Fixed temperature when someone is nearby."""
        low, high = self._safety_limits()
        current = float(self._data.get(CONF_NEARBY_TEMP, ROOM_DEFAULTS[CONF_NEARBY_TEMP]))
        shown = _shown({CONF_NEARBY_TEMP: min(max(current, low), high)}, self._unit())
        schema = vol.Schema(
            {_req(CONF_NEARBY_TEMP, shown, ROOM_DEFAULTS): _number(low, high, 0.5, "°C")}
        )
        if user_input is not None:
            self._data = _merge(self._data, schema, self._kept(user_input))
            return await self.async_step_sensors()
        return self.async_show_form(step_id="levels_nearby", data_schema=schema)

    async def async_step_sensors(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Temperature, calibration (TRVs only) and occupancy sensors."""
        d = self._shown()
        trv = d[CONF_SOURCE] == SOURCE_CLIMATE
        relay = d[CONF_SOURCE] == SOURCE_SWITCH
        fields: dict[Any, Any] = {
            _req(CONF_TEMP_SENSORS, d, ROOM_DEFAULTS): _entity(
                "sensor", multiple=True, device_class="temperature"
            ),
        }
        if trv:
            fields[_req(CONF_CALIBRATION_MODE, d, ROOM_DEFAULTS)] = _select(
                [CALIBRATION_OFF, CALIBRATION_OFFSET, CALIBRATION_EXTERNAL], "calibration"
            )
        fields[_req(CONF_OCCUPANCY_SENSORS, d, ROOM_DEFAULTS)] = _entity(
            ["binary_sensor", "input_boolean"], multiple=True
        )
        schema = vol.Schema(fields)
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {"entity": "", "owner": ""}
        if user_input is not None:
            if relay and not user_input.get(CONF_TEMP_SENSORS):
                errors[CONF_TEMP_SENSORS] = "sensor_required"
            elif _boost_on(self._data) and not user_input.get(CONF_TEMP_SENSORS):
                errors[CONF_TEMP_SENSORS] = "boost_sensor_required"
            elif error := _outdoor_error(
                self.hass, list(user_input.get(CONF_TEMP_SENSORS) or []), placeholders
            ):
                errors[CONF_TEMP_SENSORS] = error
            else:
                self._data = _merge(self._data, schema, self._kept(user_input))
                if not trv:
                    self._data[CONF_CALIBRATION_MODE] = CALIBRATION_OFF
                return await self.async_step_sensors_details()
        return self.async_show_form(
            step_id="sensors",
            data_schema=schema,
            errors=errors,
            description_placeholders=placeholders,
        )

    async def async_step_sensors_details(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Only what the chosen sensors need."""
        d = self._shown()
        fields: dict[Any, Any] = {}
        if len(as_list(d.get(CONF_TEMP_SENSORS))) > 1:
            fields[_req(CONF_TEMP_AGGREGATION, d, ROOM_DEFAULTS)] = _select(
                [AGG_MEAN, AGG_MIN, AGG_MEDIAN], "aggregation"
            )
        if d.get(CONF_CALIBRATION_MODE, CALIBRATION_OFF) != CALIBRATION_OFF:
            fields[_req(CONF_CALIBRATION_ENTITIES, d, ROOM_DEFAULTS)] = _entity(
                "number", multiple=True
            )
        if as_list(d.get(CONF_OCCUPANCY_SENSORS)):
            fields[_req(CONF_OCCUPANCY_MINUTES, d, ROOM_DEFAULTS)] = _number(1, 720, 1, "min")
        # TRVs with a room sensor are boosted for frost protection until frost
        # protection + hysteresis; asked here when no earlier step asked for it.
        if (
            as_list(d.get(CONF_TEMP_SENSORS))
            and d[CONF_SOURCE] == SOURCE_CLIMATE
            and d.get(CONF_COMMAND_MODE) != COMMAND_HVAC
            and not _boost_on(d)
            and not _no_hvac_action(self.hass, d)
        ):
            fields[_req(CONF_HYSTERESIS, d, ROOM_DEFAULTS)] = _number(0.1, 3, 0.1, "°C")
        schema = vol.Schema(fields)
        if not fields:
            return await self.async_step_windows()
        if user_input is not None:
            self._data = _merge(self._data, schema, self._kept(user_input))
            return await self.async_step_windows()
        return self.async_show_form(step_id="sensors_details", data_schema=schema)

    async def async_step_windows(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Window and door sensors."""
        d = self._shown()
        schema = vol.Schema(
            {
                _req(CONF_WINDOW_SENSORS, d, ROOM_DEFAULTS): _entity(
                    ["binary_sensor", "input_boolean"], multiple=True
                ),
                _req(CONF_LINKED_WINDOW_SENSORS, d, ROOM_DEFAULTS): _entity(
                    ["binary_sensor", "input_boolean"], multiple=True
                ),
                _req(CONF_WINDOW_DROP_DETECT, d, ROOM_DEFAULTS): _bool(),
            }
        )
        if user_input is not None:
            self._data = _merge(self._data, schema, self._kept(user_input))
            return await self.async_step_windows_details()
        return self.async_show_form(step_id="windows", data_schema=schema)

    async def async_step_windows_details(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Delays and action, only with window sensors or the temperature drop detection."""
        d = self._shown()
        sensors = as_list(d.get(CONF_WINDOW_SENSORS)) + as_list(d.get(CONF_LINKED_WINDOW_SENSORS))
        drop = bool(d.get(CONF_WINDOW_DROP_DETECT))
        fields: dict[Any, Any] = {}
        if sensors or drop:
            fields[_req(CONF_WINDOW_OPEN_DELAY, d, ROOM_DEFAULTS)] = _number(0, 3600, 5, "s")
            fields[_req(CONF_WINDOW_CLOSE_DELAY, d, ROOM_DEFAULTS)] = _number(0, 3600, 5, "s")
            fields[_req(CONF_WINDOW_ACTION, d, ROOM_DEFAULTS)] = _select(
                [WINDOW_ACTION_FROST, WINDOW_ACTION_OFF], "window_action"
            )
        if drop:
            fields[_req(CONF_WINDOW_DROP_DEGREES, d, ROOM_DEFAULTS)] = _number(0.2, 5, 0.1, "°C")
            fields[_req(CONF_WINDOW_DROP_MINUTES, d, ROOM_DEFAULTS)] = _number(1, 30, 1, "min")
        schema = vol.Schema(fields)
        if not fields:
            return await self.async_step_schedule()
        if user_input is not None:
            self._data = _merge(self._data, schema, self._kept(user_input))
            return await self.async_step_schedule()
        return self.async_show_form(step_id="windows_details", data_schema=schema)

    async def async_step_schedule(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Where the schedule comes from, and optimal start / stop."""
        d = self._shown()
        entry = self._get_entry()
        house = {**entry.data, **entry.options}
        # The optimal stop needs the outdoor temperature (a sensor or weather).
        outdoor = bool(house.get(CONF_OUTDOOR_SENSOR) or house.get(CONF_WEATHER))
        fields: dict[Any, Any] = {
            _req(CONF_SCHEDULE_SOURCE, d, ROOM_DEFAULTS): _select(
                [SCHEDULE_INTERNAL, SCHEDULE_HELPER], "schedule_source"
            ),
            _req(CONF_OPTIMAL_START, d, ROOM_DEFAULTS): _bool(),
        }
        if outdoor:
            fields[_req(CONF_OPTIMAL_STOP, d, ROOM_DEFAULTS)] = _bool()
        schema = vol.Schema(fields)
        if user_input is not None:
            self._data = _merge(self._data, schema, self._kept(user_input))
            if not outdoor:
                self._data[CONF_OPTIMAL_STOP] = False
            if user_input[CONF_SCHEDULE_SOURCE] == SCHEDULE_HELPER:
                return await self.async_step_schedule_helper()
            return await self.async_step_schedule_internal()
        return self.async_show_form(step_id="schedule", data_schema=schema)

    async def async_step_schedule_internal(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """The schedule text."""
        d = {**self._data, **(user_input or {})}
        names = (
            list(PRESETS)
            + list((self._data.get(CONF_PRESET_NAMES) or {}).values())
            + list((self._data.get(CONF_PRESET_MAP) or {}).values())
        )
        schema = vol.Schema({_req(CONF_SCHEDULE, d, ROOM_DEFAULTS): _text(multiline=True)})
        errors: dict[str, str] = {}
        placeholders = {"error": ""}
        if user_input is not None:
            try:
                parse_schedule(user_input[CONF_SCHEDULE], names)
            except ScheduleError as err:
                errors[CONF_SCHEDULE] = "invalid_schedule"
                placeholders["error"] = str(err)
            if not errors:
                self._data = _merge(self._data, schema, self._kept(user_input))
                return await self.async_step_schedule_optimal()
        return self.async_show_form(
            step_id="schedule_internal",
            data_schema=schema,
            errors=errors,
            description_placeholders=placeholders,
        )

    async def async_step_schedule_helper(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """A Schedule helper and the levels for on / off."""
        d = {**self._data, **(user_input or {})}
        schema = vol.Schema(
            {
                _opt(CONF_SCHEDULE_HELPER, d): _entity("schedule"),
                _req(CONF_HELPER_ON_PRESET, d, ROOM_DEFAULTS): _select(list(PRESETS), "preset"),
                _req(CONF_HELPER_OFF_PRESET, d, ROOM_DEFAULTS): _select(list(PRESETS), "preset"),
            }
        )
        errors: dict[str, str] = {}
        if user_input is not None:
            if not user_input.get(CONF_SCHEDULE_HELPER):
                errors[CONF_SCHEDULE_HELPER] = "helper_required"
            else:
                self._data = _merge(self._data, schema, self._kept(user_input))
                return await self.async_step_schedule_optimal()
        return self.async_show_form(step_id="schedule_helper", data_schema=schema, errors=errors)

    async def async_step_schedule_optimal(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Limits of optimal start / stop (only those turned on)."""
        d = self._shown()
        fields: dict[Any, Any] = {}
        if d.get(CONF_OPTIMAL_START):
            fields[_req(CONF_OPTIMAL_START_MAX, d, ROOM_DEFAULTS)] = _number(10, 1440, 5, "min")
        if d.get(CONF_OPTIMAL_STOP):
            fields[_req(CONF_OPTIMAL_STOP_MINUTES, d, ROOM_DEFAULTS)] = _number(5, 1440, 5, "min")
            # Generic Thermostat uses its cold tolerance; relays and thermostats
            # without hvac_action use the hysteresis.
            if (
                d[CONF_SOURCE] == SOURCE_CLIMATE
                and not self._on_off()
                and not _boost_on(d)
                and not _no_hvac_action(self.hass, d)
            ):
                fields[_req(CONF_STOP_TOLERANCE, d, ROOM_DEFAULTS)] = _number(0, 2, 0.1, "°C")
        schema = vol.Schema(fields)
        if not fields:
            return await self.async_step_extras()
        if user_input is not None:
            self._data = _merge(self._data, schema, self._kept(user_input))
            return await self.async_step_extras()
        return self.async_show_form(step_id="schedule_optimal", data_schema=schema)

    async def async_step_extras(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Solar gain and valve exercise (TRVs without on / off only)."""
        d = self._shown()
        valves = d[CONF_SOURCE] == SOURCE_CLIMATE and not self._on_off()
        # Solar gain needs the weather entity of the house (sunny or not).
        entry = self._get_entry()
        solar = bool({**entry.data, **entry.options}.get(CONF_WEATHER))
        fields: dict[Any, Any] = {}
        if solar:
            fields[_req(CONF_SOLAR_OFFSET, d, ROOM_DEFAULTS)] = _number(-3, 0, 0.1, "°C")
        if valves:
            fields[_req(CONF_VALVE_EXERCISE, d, ROOM_DEFAULTS)] = _bool()
        schema = vol.Schema(fields)
        if not fields:
            user_input = {}
        if user_input is not None:
            self._data = _merge(self._data, schema, self._kept(user_input))
            if not solar:
                self._data[CONF_SOLAR_OFFSET] = 0.0
            if not valves:
                self._data[CONF_VALVE_EXERCISE] = False
            if self._data.get(CONF_VALVE_EXERCISE):
                return await self.async_step_extras_valves()
            return self._finish()
        return self.async_show_form(step_id="extras", data_schema=schema)

    async def async_step_extras_valves(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """When the valves are exercised."""
        d = self._shown()
        schema = vol.Schema(
            {
                _req(CONF_VALVE_DAY, d, ROOM_DEFAULTS): _select(list(WEEKDAYS), "weekday"),
                _req(CONF_VALVE_TIME, d, ROOM_DEFAULTS): selector.TimeSelector(),
            }
        )
        if user_input is not None:
            self._data = _merge(self._data, schema, self._kept(user_input))
            return self._finish()
        return self.async_show_form(step_id="extras_valves", data_schema=schema)

    def _finish(self) -> SubentryFlowResult:
        """Create or update the room with the collected values."""
        data = dict(self._data)
        title = str(data.pop(CONF_NAME, "Room")).strip() or "Room"
        if self._reconfigure:
            return self.async_update_and_abort(
                self._get_entry(), self._get_reconfigure_subentry(), title=title, data=data
            )
        return self.async_create_entry(title=title, data=data)
