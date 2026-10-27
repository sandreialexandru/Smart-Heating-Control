"""Sensors for Smart Heating Control."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import AdvancedClimateConfigEntry
from .const import (
    CONF_CUTOFF_ENABLED,
    CONF_CUTOFF_HYSTERESIS,
    CONF_CUTOFF_TEMP,
    CONF_FORECAST_ENABLED,
    CONF_FORECAST_HOURS,
    DOMAIN,
    PRESENCE_STATES,
    PRESETS,
    RULE_OPTIMAL_START,
    RULE_OPTIMAL_STOP,
    RULE_SCHEDULE,
    RULE_UNOCCUPIED,
    RULES,
)
from .entity import HOUSE_ENTITY_KEYS, ROOM_ENTITY_KEYS, HouseEntity, RoomEntity, entity_map
from .house import House
from .learning import LARGE_EPISODE, start_gap
from .room import Room
from .schedule import profiles_to_dict
from .util import delta_from_celsius, from_celsius, iso


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AdvancedClimateConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensors."""
    house = entry.runtime_data
    async_add_entities(
        [
            PresenceSensor(house),
            OutdoorAverageSensor(house),
            HouseRuntimeSensor(house),
        ]
    )
    for room in house.rooms.values():
        async_add_entities(
            [
                DecisionSensor(room),
                TargetTemperatureSensor(room),
                CurrentTemperatureSensor(room),
                NextChangeSensor(room),
                HeatingRateSensor(room),
                CoolingRateSensor(room),
                RoomRuntimeSensor(room),
            ],
            config_subentry_id=room.id,
        )


class PresenceSensor(HouseEntity, SensorEntity):
    """House presence: home / nearby / far."""

    _attr_device_class = SensorDeviceClass.ENUM
    _unrecorded_attributes = frozenset(
        {"advanced_climate_house", "entry_id", "house_name", "house_entities"}
    )

    def __init__(self, house: House) -> None:
        """Initialize."""
        super().__init__(house, "presence")
        self._attr_options = list(PRESENCE_STATES)

    @property
    def native_value(self) -> str | None:
        """Return the presence."""
        return self.house.presence_state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Details."""
        return {
            "persons": self.house.person_classes,
            "arriving": self.house.arriving,
            "guest_mode": self.house.guest,
            "vacation_active": self.house.vacation_active(),
            "vacation_preheating": self.house.vacation_preheating(),
            "pending": self.house.presence.pending,
            "pending_since": iso(self.house.presence.pending_since),
            "advanced_climate_house": True,
            "temperature_unit": self.house.unit,
            "entry_id": self.house.entry.entry_id,
            "house_name": self.house.entry.title,
            "house_entities": entity_map(
                self.hass, self.house.entry.entry_id, HOUSE_ENTITY_KEYS
            ),
        }


def _t(value: float | None, unit: str, digits: int = 2) -> float | None:
    """A temperature kept in °C in the unit of the house."""
    value = from_celsius(value, unit)
    return None if value is None else round(value, digits)


def _d(value: float | None, unit: str, digits: int = 2) -> float | None:
    """A temperature difference kept in °C in the unit of the house."""
    value = delta_from_celsius(value, unit)
    return None if value is None else round(value, digits)


class _HouseUnitTemperature(SensorEntity):
    """Temperature sensor shown in the unit chosen for the house."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    house: House

    @property
    def native_unit_of_measurement(self) -> str:
        """The unit of the house."""
        return self.house.unit

    async def async_added_to_hass(self) -> None:
        """Show the value in the unit of the house, not the one of Home Assistant.

        The unit is set when the sensor is new or the unit of the house changes; a
        display unit chosen later in the entity settings is kept.
        """
        await super().async_added_to_hass()
        registry = er.async_get(self.hass)
        entry = registry.async_get(self.entity_id)
        if entry is None:
            return
        applied = (entry.options.get(DOMAIN) or {}).get("unit")
        if applied == self.house.unit:
            return
        registry.async_update_entity_options(
            self.entity_id,
            "sensor",
            {**(entry.options.get("sensor") or {}), "unit_of_measurement": self.house.unit},
        )
        registry.async_update_entity_options(
            self.entity_id, DOMAIN, {**(entry.options.get(DOMAIN) or {}), "unit": self.house.unit}
        )


class OutdoorAverageSensor(HouseEntity, _HouseUnitTemperature):
    """Average outdoor temperature used by the cutoff."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_suggested_display_precision = 1
    _unrecorded_attributes = frozenset({"forecast"})

    def __init__(self, house: House) -> None:
        """Initialize."""
        super().__init__(house, "outdoor_average")

    @property
    def native_value(self) -> float | None:
        """Average outdoor temperature."""
        return _t(self.house.outdoor_average, self.house.unit)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Details."""
        opts = self.house.options
        unit = self.house.unit
        return {
            "latest": _t(self.house.outdoor_now, self.house.unit),
            "average_hours": self.house.average_hours,
            "cutoff_active": self.house.cutoff_active,
            "forecast_cutoff": self.house.forecast_cutoff,
            "cutoff_reason": self.house.cutoff_reason,
            "forecast_mean": _t(self.house.forecast_mean, unit, 1),
            "forecast_hours": float(opts[CONF_FORECAST_HOURS]),
            "heating_season": self.house.season_active,
            # The cutoff for the card: on at the threshold, off again below it
            # by the hysteresis.
            "cutoff_enabled": bool(opts[CONF_CUTOFF_ENABLED]),
            "cutoff_temperature": _t(float(opts[CONF_CUTOFF_TEMP]), unit, 1),
            "cutoff_resume_temperature": _t(
                float(opts[CONF_CUTOFF_TEMP]) - float(opts[CONF_CUTOFF_HYSTERESIS]), unit, 1
            ),
            "forecast_enabled": bool(opts[CONF_FORECAST_ENABLED]),
            "forecast": [[iso(t), _t(v, unit, 1)] for t, v in self.house.forecast_ahead()],
        }


class HouseRuntimeSensor(HouseEntity, SensorEntity):
    """Total time the house asked for heat."""

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_suggested_display_precision = 2

    def __init__(self, house: House) -> None:
        """Initialize."""
        super().__init__(house, "heating_runtime")

    @property
    def native_value(self) -> float:
        """Hours."""
        return round(self.house.boiler_runtime_s / 3600, 3)


class DecisionSensor(RoomEntity, SensorEntity):
    """The rule that decides the room right now, with the reason."""

    _attr_device_class = SensorDeviceClass.ENUM
    _unrecorded_attributes = frozenset(
        {
            "schedule",
            "presets",
            "preset_names",
            "levels",
            "climate_entities",
            "current_temperature",
            "day_boundary",
            "schedule_editable",
            "entry_id",
            "room_id",
            "entities",
            "house_entities",
            "house_name",
            "source",
            "custom_levels",
            "device_levels",
            "plan",
            "next_estimate",
            "alerts",
        }
    )

    def __init__(self, room: Room) -> None:
        """Initialize."""
        super().__init__(room, "decision")
        self._attr_options = list(RULES)

    @property
    def native_value(self) -> str:
        """Winning rule."""
        return self.room.rule

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Everything the card and automations need."""
        room = self.room
        decision = room.decision
        state = room.schedule_state
        unit = room.house.unit
        return {
            "room_id": room.id,
            "entry_id": room.house.entry.entry_id,
            "room_name": room.name,
            "reason": decision.description if decision else None,
            # The reason for the card, in its language (temperatures in the house unit).
            "reason_key": decision.key if decision else None,
            "reason_params": _reason_params(decision.params, unit) if decision else {},
            "target_kind": decision.target.kind if decision else None,
            "preset": decision.target.preset if decision else None,
            "temperature_unit": unit,
            "target_temperature": _t(room.target_temperature, unit),
            "current_temperature": _t(room.current_temp, unit),
            "offsets": [[label, _d(delta, unit)] for label, delta in decision.offsets]
            if decision
            else [],
            "presence": room.house.presence_state,
            "window_open": room.window_open,
            "override": _override(room, unit),
            "profile": state.profile if state else None,
            "next_change": iso(state.next_change) if state else None,
            "next_preset": state.next_preset if state else None,
            "plan": room.plan(dt_util.utcnow()),
            "schedule": profiles_to_dict(room.schedule.profiles),
            "profile_days": room.schedule.profile_days,
            "schedule_error": room.schedule_error,
            "schedule_editable": room.config.get("schedule_source", "internal") == "internal",
            "presets": list(PRESETS),
            "preset_names": room.preset_names,
            "levels": {p: _t(room.level_temp(p), unit, 1) for p in PRESETS},
            "min_temperature": _t(room.frost_temp(), unit, 1),
            "max_temperature": _t(room.max_temp(), unit, 1),
            "climate_entities": room.climates,
            "device_preset": room.device_preset(),
            "trv_boost": _boost(room, unit),
            "device_level": room.level_of_device_preset(room.device_preset()),
            "time_to_target": room.time_to_target(room.house.outdoor_now),
            "stop_forecast": _forecast(room, unit),
            "next_estimate": _estimate(room, unit),
            "no_heat_reason": room.no_heat_reason(),
            "hold_until": iso(room.hold_until(dt_util.utcnow())),
            "alerts": room.house.alerts_for(room),
            "optimal_stop_cancelled": room.stop_cancelled,
            "rate_learned": bool(room.learner.episodes),
            "device_levels": room.device_levels,
            "heat_demand": room.heat_demand,
            "heating": room.heating,
            "day_boundary": room.house.day_boundary_minutes,
            "source": room.source,
            "custom_levels": room.uses_custom_levels,
            "house_name": room.house.entry.title,
            "entities": entity_map(self.hass, room.id, ROOM_ENTITY_KEYS),
            "house_entities": entity_map(
                self.hass, room.house.entry.entry_id, HOUSE_ENTITY_KEYS
            ),
        }


class TargetTemperatureSensor(RoomEntity, _HouseUnitTemperature):
    """The target temperature decided for the room."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1

    def __init__(self, room: Room) -> None:
        """Initialize."""
        super().__init__(room, "target_temperature")

    @property
    def native_value(self) -> float | None:
        """Target."""
        return _t(self.room.target_temperature, self.house.unit)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Preset."""
        decision = self.room.decision
        return {"preset": decision.target.preset if decision else None}


class CurrentTemperatureSensor(RoomEntity, _HouseUnitTemperature):
    """The room temperature used by the integration."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, room: Room) -> None:
        """Initialize."""
        super().__init__(room, "room_temperature")

    @property
    def native_value(self) -> float | None:
        """Room temperature."""
        return _t(self.room.current_temp, self.house.unit)


class NextChangeSensor(RoomEntity, SensorEntity):
    """Next scheduled change."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, room: Room) -> None:
        """Initialize."""
        super().__init__(room, "next_change")

    @property
    def native_value(self) -> datetime | None:
        """Moment of the next change."""
        state = self.room.schedule_state
        return state.next_change if state else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Next preset."""
        state = self.room.schedule_state
        return {
            "next_preset": state.next_preset if state else None,
            "profile": state.profile if state else None,
        }


class HeatingRateSensor(RoomEntity, SensorEntity):
    """Learned heating: minutes per degree now, the fixed part as an attribute."""

    _unrecorded_attributes = frozenset({"minutes_per_degree", "last_episodes"})

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_suggested_display_precision = 0

    def __init__(self, room: Room) -> None:
        """Initialize."""
        super().__init__(room, "heating_rate")

    @property
    def native_unit_of_measurement(self) -> str:
        """Minutes per degree of the house."""
        return f"min/{self.house.unit}"

    @property
    def native_value(self) -> float | None:
        """Minutes per degree at the current outdoor temperature."""
        return _per_degree(self.room.learner.minutes_per_degree(self.house.outdoor_now), self.house.unit)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """The learned model and the last episodes."""
        learner = self.room.learner
        model = learner.model
        unit = self.house.unit
        # Estimates at round outdoor temperatures of the unit of the house.
        points = (14, 32, 50, 68) if unit == "°F" else (-10, 0, 10, 20)
        per_outdoor = model.per_outdoor / 3.24 if unit == "°F" else model.per_outdoor
        return {
            "fixed_minutes": round(model.fixed, 1),
            "minutes_per_degree": (
                {
                    f"{t}{unit}": _per_degree(
                        learner.minutes_per_degree((t - 32) / 1.8 if unit == "°F" else t), unit
                    )
                    for t in points
                }
                if learner.episodes
                else {}
            ),
            "per_outdoor_degree": round(per_outdoor, 3),
            "uses_fixed": model.uses_fixed,
            "uses_outdoor": model.uses_outdoor,
            "episodes": len(learner.episodes),
            "large_episodes": sum(1 for e in learner.episodes if e[1] >= LARGE_EPISODE),
            "learning_starts_below_target": _d(start_gap(self.room.learn_tolerance()), unit),
            "last_episodes": [
                {"outdoor": _t(o, unit, 1), "rise": _d(g, unit, 2), "minutes": round(m), "at": at or None}
                for o, g, m, at in learner.episodes[-5:]
            ],
        }


def _per_degree(value: float | None, unit: str) -> float | None:
    """Minutes per °C as minutes per degree of the house (a °F is smaller)."""
    if value is None:
        return None
    return round(value / 1.8 if unit == "°F" else value, 1)


def _boost(room: Room, unit: str) -> dict[str, Any] | None:
    """The TRV boost of the room: the temperature and whether it is on now."""
    if not room.boost:
        return None
    base = room.target_temperature
    temperature = room.boost_temperature(base) if base is not None else None
    return {"temperature": _t(temperature, unit, 1), "active": room.boost_active}


def _forecast(room: Room, unit: str) -> dict[str, Any] | None:
    """Expected temperature at the scheduled change during an optimal stop."""
    forecast = room.stop_forecast(dt_util.utcnow())
    if forecast is None:
        return None
    return {"at": forecast["at"], "temperature": _t(forecast["temperature"], unit, 1)}


def _reason_params(params: dict[str, Any], unit: str) -> dict[str, Any]:
    """Values of the reason, temperatures in the unit of the house."""
    temperatures = {"temperature", "limited", "max", "frost", "current", "value"}
    return {
        k: (_t(v, unit, 1) if k in temperatures and isinstance(v, (int, float)) else v)
        for k, v in params.items()
    }


def _override(room: Room, unit: str) -> dict[str, Any] | None:
    """The manual change, with its temperature in the unit of the house."""
    info = room.override_info()
    if info is None:
        return None
    return {**info, "temperature": _t(info.get("temperature"), unit, 1)}


def _estimate(room: Room, unit: str) -> dict[str, Any] | None:
    """The optimal start / stop expected for the next scheduled change."""
    estimate = room.next_estimate
    # Shown only while the room follows its schedule: a higher rule (vacation,
    # presence, window, mode, cutoff, pause...) would not let it happen.
    rule = room.decision.rule if room.decision else None
    if estimate is None or rule not in (
        RULE_SCHEDULE, RULE_OPTIMAL_START, RULE_OPTIMAL_STOP, RULE_UNOCCUPIED
    ):
        return None
    change = estimate["change"]
    started = estimate.get("started_at")
    return {
        "kind": estimate["kind"],
        "at": iso(change),
        "preset": estimate["preset"],
        "sent_as": "preset" if room.sends_preset(estimate["preset"]) else "temperature",
        "temperature": _t(room.level_temp(estimate["preset"]), unit, 1),
        "minutes": round(estimate["minutes"]),
        "starts_at": iso(change - timedelta(minutes=estimate["minutes"])),
        "started_at": iso(started) if started else None,
        "outdoor": _t(estimate["outdoor"], unit, 1),
        "outdoor_source": estimate["outdoor_source"],
        "learned": estimate["learned"],
    }


class CoolingRateSensor(RoomEntity, SensorEntity):
    """Learned cooling: how fast the room falls now without heating."""

    _unrecorded_attributes = frozenset({"last_episodes"})

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_suggested_display_precision = 2

    def __init__(self, room: Room) -> None:
        """Initialize."""
        super().__init__(room, "cooling_rate")

    @property
    def native_unit_of_measurement(self) -> str:
        """Degrees of the house per hour."""
        return f"{self.house.unit}/h"

    @property
    def native_value(self) -> float | None:
        """Fall per hour for the current room and outdoor temperatures."""
        rate = self.room.cooling.rate(self.room.current_temp, self.house.outdoor_now)
        return _d(rate, self.house.unit, 3)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Learned coefficient and the last episodes."""
        cooling = self.room.cooling
        unit = self.house.unit
        return {
            "coefficient_per_hour": cooling.coefficient,
            "episodes": len(cooling.episodes),
            "optimal_stop_tolerance": _d(self.room.stop_tolerance(), unit),
            "last_episodes": [
                {"outdoor": _t(o, unit, 1), "coefficient": k, "at": at or None}
                for o, k, at in cooling.episodes[-5:]
            ],
        }


class RoomRuntimeSensor(RoomEntity, SensorEntity):
    """Total time the room asked for heat."""

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_suggested_display_precision = 2

    def __init__(self, room: Room) -> None:
        """Initialize."""
        super().__init__(room, "heating_runtime")

    @property
    def native_value(self) -> float:
        """Hours."""
        return round(self.room.runtime_s / 3600, 3)
