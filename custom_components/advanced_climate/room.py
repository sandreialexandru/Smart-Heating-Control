"""Room controller: decides and commands one heating zone."""

from __future__ import annotations

import logging
import math
from collections import deque
from collections.abc import Callable
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigSubentry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_TEMPERATURE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import Event, EventStateChangedData, State, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import (
    area_registry as ar,
)
from homeassistant.helpers import (
    device_registry as dr,
)
from homeassistant.helpers import (
    entity_registry as er,
)
from homeassistant.helpers.event import async_call_later, async_track_state_change_event
from homeassistant.util import dt as dt_util

from .const import (
    CALIBRATION_EXTERNAL,
    CALIBRATION_OFFSET,
    COMMAND_HVAC,
    COMMAND_PRESET,
    COMMAND_TEMPERATURE,
    CONF_ALERT_WINDOW_MINUTES,
    CONF_AREA,
    CONF_BATTERY_THRESHOLD,
    CONF_BOILER_MIN_ROOMS,
    CONF_CALIBRATION_ENTITIES,
    CONF_CALIBRATION_MODE,
    CONF_CLIMATES,
    CONF_COMMAND_MODE,
    CONF_FROST_TEMP,
    CONF_HELPER_OFF_PRESET,
    CONF_HELPER_ON_PRESET,
    CONF_HYSTERESIS,
    CONF_LEARN_TOLERANCE,
    CONF_LEVELS,
    CONF_LINKED_WINDOW_SENSORS,
    CONF_MAX_TEMP,
    CONF_MIN_OFF,
    CONF_MIN_ON,
    CONF_NEARBY_LIMIT,
    CONF_NEARBY_MODE,
    CONF_NEARBY_TEMP,
    CONF_OCCUPANCY_MINUTES,
    CONF_OCCUPANCY_SENSORS,
    CONF_OPTIMAL_START,
    CONF_OPTIMAL_START_MAX,
    CONF_OPTIMAL_STOP,
    CONF_OPTIMAL_STOP_MINUTES,
    CONF_OVERRIDE_HOURS,
    CONF_OVERRIDE_MODE,
    CONF_PRESET_MAP,
    CONF_PRESET_NAMES,
    CONF_PROFILE_DAYS,
    CONF_REFERENCE_ROOM,
    CONF_SCHEDULE,
    CONF_SCHEDULE_HELPER,
    CONF_SCHEDULE_SOURCE,
    CONF_SOLAR_OFFSET,
    CONF_SOURCE,
    CONF_STOP_TOLERANCE,
    CONF_SWITCHES,
    CONF_TEMP_AGGREGATION,
    CONF_TEMP_SENSORS,
    CONF_TRV_BOOST,
    CONF_TRV_BOOST_TEMP,
    CONF_VALVE_DAY,
    CONF_VALVE_EXERCISE,
    CONF_VALVE_TIME,
    CONF_VERIFY_COMMANDS,
    CONF_WINDOW_ACTION,
    CONF_WINDOW_CLOSE_DELAY,
    CONF_WINDOW_DROP_DEGREES,
    CONF_WINDOW_DROP_DETECT,
    CONF_WINDOW_DROP_MINUTES,
    CONF_WINDOW_OPEN_DELAY,
    CONF_WINDOW_SENSORS,
    DEFAULT_LEVEL_TEMPS,
    DEFAULT_SCHEDULE,
    DOMAIN,
    EVENT_DECISION_CHANGED,
    GT_DOMAIN,
    GT_PRESET_KEYS,
    MAX_DECISION_LOG,
    MODE_OFF,
    MODE_SUMMER,
    OVERRIDE_FIXED,
    OVERRIDE_NEXT,
    PRESET_FROST,
    PRESET_NONE,
    PRESETS,
    ROOM_DEFAULTS,
    RULE_MAX,
    RULE_OPTIMAL_START,
    RULE_OPTIMAL_STOP,
    RULE_OVERRIDE,
    RULE_PAUSE,
    RULE_SAFETY,
    RULE_SCHEDULE,
    RULE_STARTING,
    RULE_VACATION,
    SCHEDULE_HELPER,
    SENT_RECENT_MINUTES,
    SOURCE_CLIMATE,
    SOURCE_GT,
    SOURCE_SWITCH,
    TEMP_DROP_HOLD_MINUTES,
    VALVE_EXERCISE_SECONDS,
    VERIFY_DELAY,
    WEEKDAYS,
)
from .engine import (
    KIND_NONE,
    KIND_OFF,
    KIND_PRESET,
    KIND_TEMPERATURE,
    Decision,
    RoomInputs,
    Target,
    decide,
    optimal_period,
    optimal_schedule,
    optimal_stop_state,
)
from .learning import CoolingLearner, HeatingRateLearner
from .schedule import (
    Schedule,
    ScheduleError,
    ScheduleState,
    Slot,
    parse_schedule,
    uncovered_days,
)
from .util import (
    aggregate,
    as_list,
    climate_temp,
    delta_from_celsius,
    delta_to_celsius,
    finite,
    float_attr,
    from_celsius,
    from_iso,
    heat_mode,
    iso,
    parse_clock,
    system_unit,
    temp_state,
    to_celsius,
    valid,
)

if TYPE_CHECKING:
    from .house import House

_LOGGER = logging.getLogger(__name__)
SENT_RECENT = timedelta(minutes=SENT_RECENT_MINUTES)


def device_values(state: State) -> dict[str, Any]:
    """What a person set on a device: mode (or on / off), preset and temperature."""
    values: dict[str, Any] = {"state": state.state}
    if state.domain == "climate":
        values["preset_mode"] = state.attributes.get("preset_mode")
        values["temperature"] = state.attributes.get(ATTR_TEMPERATURE)
    return values


class Room:
    """Controller for one room (config subentry)."""

    def __init__(self, house: House, subentry: ConfigSubentry, stored: dict[str, Any]) -> None:
        """Initialize."""
        self.house = house
        self.hass = house.hass
        self.id = subentry.subentry_id
        self.name = subentry.title
        self.unique_id = subentry.unique_id
        self.config: dict[str, Any] = {**ROOM_DEFAULTS, **subentry.data}
        self.source: str = self.config[CONF_SOURCE]
        self.climates = as_list(self.config.get(CONF_CLIMATES))
        self.switches = as_list(self.config.get(CONF_SWITCHES))
        self.command_mode: str = (
            COMMAND_PRESET if self.source == SOURCE_GT else self.config[CONF_COMMAND_MODE]
        )
        # TRV boost: the heat demand comes from the room sensor (hysteresis) and
        # the TRVs get the boost temperature while it lasts, the target otherwise.
        self.boost = (
            self.source == SOURCE_CLIMATE
            and self.command_mode == COMMAND_TEMPERATURE
            and bool(self.config.get(CONF_TRV_BOOST, False))
        )
        self._boost_demand = False  # the room asks for heat (boost rooms)
        self._boosted = False  # the TRVs hold the boost temperature we sent
        self._boost_base: float | None = None  # the target under the boost (°C)

        # Custom level names (when not using Generic Thermostat).
        names = dict(self.config.get(CONF_PRESET_NAMES) or {})
        self.preset_names: dict[str, str] = {
            p: (str(names.get(p)).strip() or p) if names.get(p) else p for p in PRESETS
        }
        # Climate devices commanded with presets: which device preset each level uses.
        # Levels without a device preset are reached with a temperature.
        self.preset_map: dict[str, str] | None = None
        self._legacy_map = False
        if self.source == SOURCE_CLIMATE and self.command_mode == COMMAND_PRESET:
            raw = self.config.get(CONF_PRESET_MAP)
            if raw is None:
                # No preset map saved: the level name (or the role) is the device preset.
                self._legacy_map = True
                raw = dict(self.preset_names)
            self.preset_map = {
                p: str(v).strip()
                for p, v in dict(raw).items()
                if p in PRESETS and v and str(v).strip()
            }
            if not self._legacy_map:
                self.preset_names = {p: self.preset_map.get(p, p) for p in PRESETS}
        self.aliases: dict[str, str] = {p: p for p in PRESETS}
        for role, name in self.preset_names.items():
            self.aliases[name.lower()] = role

        # Schedule
        self.schedule_error: str | None = None
        self.schedule = self._build_schedule(self.config.get(CONF_SCHEDULE) or DEFAULT_SCHEDULE)
        self.schedule_state: ScheduleState | None = None

        # Persisted state
        self.levels: dict[str, float] = {
            p: float(stored.get("levels", {}).get(p, DEFAULT_LEVEL_TEMPS[p])) for p in PRESETS
        }
        configured = self.config.get(CONF_LEVELS) or None
        if configured and configured != stored.get("levels_config"):
            # New temperatures chosen in the room settings win over older edits.
            for preset, value in configured.items():
                if preset in PRESETS and value is not None:
                    self.levels[preset] = float(value)
        self.levels_config: dict[str, float] | None = configured
        self.nearby_temp: float = float(
            stored.get("nearby_temp", self.config.get(CONF_NEARBY_TEMP) or 17.0)
        )
        self.override: dict[str, Any] | None = stored.get("override")
        if self.override is not None:
            self.override["until"] = from_iso(self.override.get("until"))
            self.override["since"] = from_iso(self.override.get("since"))
        self.child_lock = bool(stored.get("child_lock", False))
        self.learner = HeatingRateLearner.from_dict(stored.get("learner"))
        self.cooling = CoolingLearner.from_dict(stored.get("cooling"))
        self.runtime_s = float(stored.get("runtime_s", 0.0))
        self.observed_temps: dict[str, float] = {
            str(k): float(v) for k, v in (stored.get("observed_temps") or {}).items()
        }
        self.decisions: deque[dict[str, Any]] = deque(
            stored.get("decisions", []), maxlen=MAX_DECISION_LOG
        )
        self.last_exercise: str | None = stored.get("last_exercise")

        # Runtime state
        self.decision: Decision | None = None
        self.current_temp: float | None = None
        self.target_temperature: float | None = None
        self.heat_demand = False
        # The heat source runs for this room (see _update_demand); the learning
        # and the heating time count only then.
        self.heating = False
        self.source_unknown = False
        self.next_wakeup: datetime | None = None
        self.window_open = False
        self._window_raw_since: datetime | None = None
        self._window_closed_since: datetime | None = None
        self._window_opened_at: datetime | None = None
        self._window_timer: Callable[[], None] | None = None
        # Room temperature readings as runs of the same value: [first seen, last seen, value].
        # Kept by time (the drop window plus 15 minutes), not by count, so a busy
        # house that reads the temperature often does not shorten the window.
        self._temp_samples: list[list] = []
        # Which sensors gave the room temperature (a change of them is not a drop).
        self._temp_sources: tuple | None = None
        self._drop_until: datetime | None = None
        self._last_occupied: datetime | None = None
        self._started_at = dt_util.utcnow()
        self._exercise_until: datetime | None = None
        self._relay_on: bool | None = None
        # Kept over a restart: the minimum on / off time of the relay holds.
        self._relay_changed: datetime | None = from_iso(stored.get("relay_changed"))
        self._heating_since: datetime | None = None
        self._unsubs: list[Callable[[], None]] = []
        self._verify_unsub: Callable[[], None] | None = None
        self._verify_attempts = 0
        self._unavailable_since: dict[str, datetime] = {}
        self._calibration_written: dict[str, datetime] = {}
        self.sensor_failed = False
        self.external_failed = False
        self.signature: tuple | None = None
        # The schedule change an optimal start / stop already began for.
        self._optimal_for: datetime | None = None
        self._optimal_rule: str | None = None
        # The change whose optimal stop was cancelled (the room got too cold).
        self._stop_cancelled_for: datetime | None = None
        self.stop_cancelled = False
        # Optimal start / stop expected for the next scheduled change.
        self.next_estimate: dict[str, Any] | None = None
        # A relay that should switch but waits for its minimum on / off time.
        self.relay_waiting: str | None = None
        # When the minimum on / off time of the relay ends (while it waits).
        self._relay_wait_until: datetime | None = None
        # Values of the last commands, per device: a device that reports them
        # later (e.g. a sleepy Zigbee TRV) is not a manual change.
        self._sent: dict[str, dict[str, Any]] = {}
        # Every value sent to a thermostat in the last minutes: a TRV may report
        # an older command after a newer one was sent (e.g. 21 °C, then 12 °C for
        # away, and only then the 21 °C); that is not a manual change either.
        self._sent_recent: dict[str, list[tuple[datetime, str, Any]]] = {}

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------
    def apply_schedule(self, text: str, profile_days: dict | None = None) -> None:
        """Use a new schedule (and the days of its profiles) without reloading."""
        self.config[CONF_SCHEDULE] = text
        self.config[CONF_PROFILE_DAYS] = profile_days
        self.schedule_error = None
        self.schedule = self._build_schedule(text)

    def _build_schedule(self, text: str) -> Schedule:
        """Parse the schedule text; the default schedule is used when it is invalid."""
        valid_names = list(PRESETS) + [n for n in self.preset_names.values() if n not in PRESETS]
        try:
            profiles = parse_schedule(text, valid_names)
        except ScheduleError as err:
            self.schedule_error = str(err)
            _LOGGER.error("Room %s: invalid schedule (%s); using the default", self.name, err)
            profiles = parse_schedule(DEFAULT_SCHEDULE, PRESETS)
        normalized = {
            name: [Slot(s.minute, self.aliases.get(s.preset.lower(), s.preset)) for s in slots]
            for name, slots in profiles.items()
        }
        days = self.config.get(CONF_PROFILE_DAYS) if not self.schedule_error else None
        return Schedule(normalized, self.house.day_boundary_minutes, days)

    @callback
    def async_start(self) -> None:
        """Start tracking the room entities."""
        cfg = self.config
        tracked = set(self.climates) | set(self.switches)
        tracked |= set(as_list(cfg.get(CONF_TEMP_SENSORS)))
        tracked |= set(as_list(cfg.get(CONF_WINDOW_SENSORS)))
        tracked |= set(as_list(cfg.get(CONF_LINKED_WINDOW_SENSORS)))
        tracked |= set(as_list(cfg.get(CONF_OCCUPANCY_SENSORS)))
        if cfg.get(CONF_SCHEDULE_SOURCE) == SCHEDULE_HELPER and cfg.get(CONF_SCHEDULE_HELPER):
            tracked.add(cfg[CONF_SCHEDULE_HELPER])
        if tracked:
            self._unsubs.append(
                async_track_state_change_event(
                    self.hass, sorted(tracked), self._async_entity_changed
                )
            )
        self._update_temperature(dt_util.utcnow())
        self._update_window(dt_util.utcnow())

    @callback
    def async_stop(self) -> None:
        """Stop all listeners and timers."""
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        for attr in ("_window_timer", "_verify_unsub"):
            unsub = getattr(self, attr)
            if unsub:
                unsub()
                setattr(self, attr, None)

    def as_dict(self) -> dict[str, Any]:
        """Data persisted between restarts."""
        override = None
        if self.override:
            override = {
                **self.override,
                "until": iso(self.override.get("until")),
                "since": iso(self.override.get("since")),
            }
        return {
            "levels": self.levels,
            "levels_config": self.levels_config,
            "nearby_temp": self.nearby_temp,
            "override": override,
            "child_lock": self.child_lock,
            "learner": self.learner.as_dict(),
            "cooling": self.cooling.as_dict(),
            "runtime_s": round(self.runtime_s, 1),
            "observed_temps": self.observed_temps,
            "decisions": list(self.decisions),
            "last_exercise": self.last_exercise,
            "relay_changed": iso(self._relay_changed),
        }

    # ------------------------------------------------------------------
    # Properties used by entities
    # ------------------------------------------------------------------
    @property
    def is_whole_house(self) -> bool:
        """True for the zone created with the house."""
        return self.unique_id == "whole_house"

    @property
    def area_name(self) -> str | None:
        """Name of the configured area."""
        area_id = self.config.get(CONF_AREA)
        if not area_id:
            return None
        area = ar.async_get(self.hass).async_get_area(area_id)
        return area.name if area else None

    @property
    def uses_custom_levels(self) -> bool:
        """True when the temperatures of the levels are set by this integration."""
        return self.source != SOURCE_GT

    @property
    def device_levels(self) -> list[str]:
        """Levels whose temperature is kept by the thermostat itself."""
        if self.source == SOURCE_GT:
            return list(PRESETS)
        if self.preset_map is None:
            return []
        if self._legacy_map:
            available = self.device_presets()
            return [p for p in PRESETS if self._device_preset(p, available) is not None]
        return [p for p in PRESETS if p in self.preset_map]

    @property
    def editable_levels(self) -> list[str]:
        """Levels whose temperature is set in this integration."""
        if self.source == SOURCE_GT:
            return []
        if self._legacy_map:
            # Without a saved preset map every level stays editable.
            return list(PRESETS)
        return [p for p in PRESETS if p not in self.device_levels]

    def level_of_device_preset(self, name: str | None) -> str | None:
        """Level that uses the given device preset."""
        if not name:
            return None
        if self.source == SOURCE_GT:
            return name if name in PRESETS else None
        if self.preset_map is not None:
            for preset, device in self.preset_map.items():
                if device == name:
                    return preset
            if self._legacy_map and name in PRESETS:
                return name
        return None

    @property
    def supports_valve_exercise(self) -> bool:
        """Valve exercise only makes sense for climate devices (TRVs)."""
        return self.source == SOURCE_CLIMATE and self.command_mode != COMMAND_HVAC

    @property
    def rule(self) -> str:
        """The current decision rule."""
        return self.decision.rule if self.decision else RULE_STARTING

    @property
    def override_active(self) -> bool:
        """Return True if a manual override is active."""
        return self.override is not None

    def display_name(self, preset: str | None) -> str | None:
        """Return the user facing name of a level."""
        if preset is None:
            return None
        return self.preset_names.get(preset, preset)

    # ------------------------------------------------------------------
    # Temperatures of the levels
    # ------------------------------------------------------------------
    def _gt_options(self) -> dict[str, Any]:
        """Options of the Generic Thermostat config entry, if any."""
        if self.source != SOURCE_GT or not self.climates:
            return {}
        registry = er.async_get(self.hass)
        entry = registry.async_get(self.climates[0])
        if entry is None or entry.config_entry_id is None:
            return {}
        config_entry = self.hass.config_entries.async_get_entry(entry.config_entry_id)
        if config_entry is None or config_entry.domain != GT_DOMAIN:
            return {}
        return dict(config_entry.options)

    def level_temp(self, preset: str) -> float | None:
        """Return the temperature of a level, if known."""
        if preset == PRESET_FROST:
            return self.frost_temp()  # a day without an active profile
        if preset not in PRESETS:
            return None
        if self.source != SOURCE_GT:
            if preset in self.device_levels and preset in self.observed_temps:
                # The thermostat keeps this preset; show what it really uses.
                return self.observed_temps[preset]
            return self.levels.get(preset)
        value = self._gt_options().get(GT_PRESET_KEYS[preset])
        if (number := finite(value)) is not None:
            return float(to_celsius(number, system_unit(self.hass)))
        return self.observed_temps.get(preset)

    def device_presets(self) -> list[str]:
        """Presets supported by the first available climate entity."""
        for entity_id in self.climates:
            state = self.hass.states.get(entity_id)
            if valid(state):
                return list(state.attributes.get("preset_modes") or [])  # type: ignore[union-attr]
        return []

    def device_preset(self) -> str | None:
        """Preset currently active on the first available thermostat."""
        for entity_id in self.climates:
            state = self.hass.states.get(entity_id)
            if valid(state):
                return state.attributes.get("preset_mode")  # type: ignore[union-attr]
        return None

    def frost_temp(self) -> float:
        """Frost protection temperature."""
        if self.source == SOURCE_GT:
            for entity_id in self.climates:
                value = climate_temp(self.hass, self.hass.states.get(entity_id), "min_temp")
                if value is not None:
                    return value
            gt_min = self._gt_options().get("min_temp")
            if gt_min is not None:
                return float(to_celsius(float(gt_min), system_unit(self.hass)))
        return float(self.house.options[CONF_FROST_TEMP])

    def max_temp(self) -> float:
        """Maximum allowed temperature."""
        maximum = float(self.house.options[CONF_MAX_TEMP])
        for entity_id in self.climates:
            value = climate_temp(self.hass, self.hass.states.get(entity_id), "max_temp")
            if value is not None:
                maximum = min(maximum, value) if self.source != SOURCE_GT else maximum
        return maximum

    def device_max_temp(self) -> float | None:
        """Highest temperature the thermostats accept (valve exercise)."""
        values = [
            v
            for entity_id in self.climates
            if (v := climate_temp(self.hass, self.hass.states.get(entity_id), "max_temp"))
            is not None
        ]
        return min(values) if values else None

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------
    @callback
    def _async_entity_changed(self, event: Event[EventStateChangedData]) -> None:
        """A room entity changed: detect manual changes and evaluate again."""
        entity_id = event.data["entity_id"]
        old: State | None = event.data["old_state"]
        new: State | None = event.data["new_state"]
        now = dt_util.utcnow()
        if entity_id in self.climates:
            self._remember_preset_temp(new)
            if self._is_manual_change(event, old, new):
                self._handle_manual_change(entity_id, new)
        elif entity_id in self.switches:
            if (
                old is not None
                and new is not None
                and valid(old)
                and valid(new)
                and old.state != new.state
                and not self.house.is_own_context(event.context)
                and not self._is_echo(entity_id, old, new)
            ):
                self._handle_manual_change(entity_id, new)
        if entity_id in as_list(self.config.get(CONF_TEMP_SENSORS)) or entity_id in self.climates:
            self._update_temperature(now)
        self._update_window(now)
        self.house.async_request_evaluate()

    def _remember_preset_temp(self, state: State | None) -> None:
        """Learn the temperatures of the thermostat presets from the climate state."""
        if not valid(state):
            return
        preset = self.level_of_device_preset(state.attributes.get("preset_mode"))  # type: ignore[union-attr]
        temperature = climate_temp(self.hass, state, ATTR_TEMPERATURE)
        if preset is not None and temperature is not None:
            self.observed_temps[preset] = temperature

    def _is_manual_change(self, event: Event, old: State | None, new: State | None) -> bool:
        """True when a person changed the thermostat (not the integration, nor a late confirmation)."""
        if old is None or new is None or not valid(old) or not valid(new):
            return False
        if self.house.is_own_context(event.context):
            return False
        if not self.house.started:
            return False
        if self._is_echo(event.data["entity_id"], old, new):
            return False
        if old.state != new.state:
            return True
        for attr in ("preset_mode", ATTR_TEMPERATURE):
            if old.attributes.get(attr) != new.attributes.get(attr):
                return True
        return False

    def _is_echo(self, entity_id: str, old: State, new: State) -> bool:
        """True when a device only reports the values the integration sent it.

        Devices that confirm a command late get a new context, so the context
        alone cannot tell them apart from a person. Every changed value we sent
        must match it, and at least one must have been sent.
        """
        sent = self._sent.get(entity_id) or {}
        now = dt_util.utcnow()
        recent = [
            (key, value)
            for at, key, value in self._sent_recent.get(entity_id, [])
            if now - at <= SENT_RECENT
        ]
        if not sent and not recent:
            return False
        changed: dict[str, Any] = {}
        if old.state != new.state:
            changed["state"] = new.state
        for attr in ("preset_mode", ATTR_TEMPERATURE):
            if old.attributes.get(attr) != new.attributes.get(attr):
                changed[attr] = new.attributes.get(attr)
        matched = False
        for key, value in changed.items():
            candidates = ([sent[key]] if key in sent else []) + [v for k, v in recent if k == key]
            if not candidates:
                continue
            if key == ATTR_TEMPERATURE:
                # The device may round to its own step.
                step = float_attr(new, "target_temp_step")
                margin = step / 2 + 0.01 if step else 0.05

                def close(sent_value: Any) -> bool:
                    try:
                        return abs(float(value) - float(sent_value)) < margin
                    except (TypeError, ValueError):
                        return False

                same = any(close(c) for c in candidates)
            else:
                same = value in candidates
            if not same:
                return False
            matched = True
        return matched

    def _handle_manual_change(self, entity_id: str, new: State | None) -> None:
        """Respect a manual change (or revert it with the child lock)."""
        # From now on the device shows a person's values, not ours: if the person
        # later sets the value we sent before, that is a manual change too.
        self._sent.pop(entity_id, None)
        self._sent_recent.pop(entity_id, None)
        self._boosted = False  # the person's value replaced the boost
        # In a pause the change is kept (it applies after the pause); the child
        # lock does not undo it then, since a pause sends nothing.
        if self.child_lock and self.decision is not None and not self.house.paused:
            _LOGGER.debug("Room %s: child lock reverts a manual change", self.name)
            self.hass.async_create_task(self._async_apply(self.decision.target, force=True))
            return
        description = "manual change"
        if new is not None:
            if new.state == STATE_OFF:
                description = "turned off"
            elif new.attributes.get("preset_mode") not in (None, PRESET_NONE):
                description = f"preset {new.attributes.get('preset_mode')}"
            elif (value := climate_temp(self.hass, new, ATTR_TEMPERATURE)) is not None:
                unit = self.house.unit
                description = f"{from_celsius(value, unit):.1f} {unit}"
            elif entity_id in self.switches:
                description = f"switch {new.state}"
        # What the person set is kept, to set it again after an interruption
        # (a window opened, frost protection).
        devices = {entity_id: device_values(new)} if new is not None else None
        if self.house.override_scope_house:
            for room in self.house.rooms.values():
                room.set_override(
                    description, source=self.name, devices=devices if room is self else None
                )
        else:
            self.set_override(description, devices=devices)

    def set_override(
        self,
        description: str,
        *,
        source: str | None = None,
        hours: float | None = None,
        target: Target | None = None,
        devices: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        """Start a manual override.

        ``target`` is a level or temperature set by the card or a service: it is
        sent while the manual change applies. ``devices`` are the values a
        person set on the devices: they are only set again after an
        interruption (a higher rule changed the devices meanwhile).
        """
        now = dt_util.utcnow()
        kept: dict[str, dict[str, Any]] = {}
        if target is None and self.override and not self.override.get("target"):
            # Another device of the room changed by hand: keep the earlier ones too.
            kept = dict(self.override.get("devices") or {})
        kept.update(devices or {})
        mode = self.house.options[CONF_OVERRIDE_MODE]
        if hours is None and mode == OVERRIDE_FIXED:
            hours = float(self.house.options[CONF_OVERRIDE_HOURS])
        until = now + timedelta(hours=hours) if hours else None
        self.override = {
            "description": description if source is None else f"{description} ({source})",
            "since": now,
            "until": until,
            "mode": OVERRIDE_FIXED if until else OVERRIDE_NEXT,
            "signature": list(self.signature) if self.signature else None,
            "target": target.as_dict() if target else None,
            "devices": kept if target is None else {},
            "interrupted": False,
            # A change made on a device is already there; one from the card or
            # a service is sent when the manual change applies.
            "applied": target is None,
        }
        self.house.async_save()

    def clear_override(self) -> None:
        """Clear the manual override."""
        self.override = None
        self.house.async_save()

    def reset_heating_learning(self) -> None:
        """Forget the learned heating (episodes and the one in progress)."""
        self.learner = HeatingRateLearner()
        self.house.async_save()

    def reset_cooling_learning(self) -> None:
        """Forget the learned cooling (episodes and the one in progress)."""
        self.cooling = CoolingLearner()
        self.house.async_save()

    def _check_override(self, now: datetime, signature: tuple) -> None:
        """End the manual change when its time is over or something relevant changed."""
        if self.override is None:
            return
        until = self.override.get("until")
        if until is not None:
            if now >= until:
                self.override = None
            return
        stored = self.override.get("signature")
        if stored is None:
            self.override["signature"] = list(signature)
        elif tuple(stored) != tuple(signature):
            # Something relevant changed: the override ends.
            self.override = None

    # ------------------------------------------------------------------
    # Inputs
    # ------------------------------------------------------------------
    def _update_temperature(self, now: datetime) -> None:
        """Room temperature from the sensors, else from the thermostats."""
        sensors = as_list(self.config.get(CONF_TEMP_SENSORS))
        values = []
        reporting = []
        for entity_id in sensors:
            value = temp_state(self.hass, entity_id, self.house.unit)
            if value is not None:
                values.append(value)
                reporting.append(entity_id)
        external = aggregate(values, self.config[CONF_TEMP_AGGREGATION])
        self.external_failed = bool(sensors) and external is None
        device = None
        device_reporting = []
        device_values = []
        for eid in self.climates:
            v = climate_temp(self.hass, self.hass.states.get(eid), "current_temperature")
            if v is not None:
                device_values.append(v)
                device_reporting.append(eid)
        if device_values:
            device = round(sum(device_values) / len(device_values), 2)
        self.current_temp = external if external is not None else device
        # Without any temperature a relay cannot be regulated.
        needs_temp = (
            self.source == SOURCE_SWITCH or self.command_mode == COMMAND_HVAC or self.boost
        )
        self.sensor_failed = self.current_temp is None and (bool(sensors) or needs_temp)
        # When a sensor stops or comes back, or the room falls back to the device
        # sensor, the value jumps: the quick drop (open window) starts again from
        # the new value instead of taking the jump for an open window.
        sources = tuple(reporting) if external is not None else ("device", *device_reporting)
        if sources != self._temp_sources:
            self._temp_sources = sources
            self._temp_samples.clear()
        if self.current_temp is not None:
            samples = self._temp_samples
            if samples and samples[-1][2] == self.current_temp:
                samples[-1][1] = now  # the same value read again
            else:
                samples.append([now, now, self.current_temp])
            keep = timedelta(minutes=float(self.config[CONF_WINDOW_DROP_MINUTES]) + 15)
            while len(samples) > 1 and now - samples[0][1] > keep:
                samples.pop(0)
            self._check_temp_drop(now)

    def external_temperature(self) -> float | None:
        """Aggregated external sensors only."""
        values = [
            v
            for entity_id in as_list(self.config.get(CONF_TEMP_SENSORS))
            if (v := temp_state(self.hass, entity_id, self.house.unit)) is not None
        ]
        return aggregate(values, self.config[CONF_TEMP_AGGREGATION])

    def _check_temp_drop(self, now: datetime) -> None:
        """Count a quick temperature drop as an open window."""
        if not self.config[CONF_WINDOW_DROP_DETECT] or self.current_temp is None:
            return
        if self._drop_until is not None and now < self._drop_until:
            return  # already holding
        window = timedelta(minutes=float(self.config[CONF_WINDOW_DROP_MINUTES]))
        # Every value read inside the window (a run that lasted into it counts:
        # it was the value at the start of the window).
        recent = [v for _first, last, v in self._temp_samples if now - last <= window]
        # The value valid just before the window, if it was read at most 15 minutes
        # before it (sensors report on change; an older value may be stale).
        before = [(last, v) for _first, last, v in self._temp_samples if now - last > window]
        if before and now - before[-1][0] <= window + timedelta(minutes=15):
            recent.append(before[-1][1])
        if recent and max(recent) - self.current_temp >= float(
            self.config[CONF_WINDOW_DROP_DEGREES]
        ):
            self._drop_until = now + timedelta(minutes=TEMP_DROP_HOLD_MINUTES)

    def learn_tolerance(self) -> float:
        """How far below the target the thermostat lets the room fall before heating."""
        if self.source == SOURCE_GT:
            value = self._gt_options().get("cold_tolerance")
            try:
                return (
                    float(delta_to_celsius(float(value), system_unit(self.hass)))
                    if value is not None
                    else 0.0
                )
            except (TypeError, ValueError):
                return 0.0
        if self.source == SOURCE_SWITCH or self.command_mode == COMMAND_HVAC or self.boost:
            return float(self.config[CONF_HYSTERESIS])
        return float(self.config.get(CONF_LEARN_TOLERANCE, 0.0))

    def stop_tolerance(self) -> float:
        """How far below a level the room may fall during an optimal stop (its comfort)."""
        if self.source == SOURCE_GT:
            return self.learn_tolerance()  # the cold tolerance of Generic Thermostat
        if (
            self.source == SOURCE_SWITCH
            or self.command_mode == COMMAND_HVAC
            or self.boost
            or self.lacks_hvac_action()
        ):
            return float(self.config[CONF_HYSTERESIS])
        return float(self.config.get(CONF_STOP_TOLERANCE, 0.0))

    def lacks_hvac_action(self) -> bool:
        """A thermostat of the room does not report hvac_action (or cannot be checked now).

        Such thermostats are handled like relays: their heat demand and the
        comfort of the optimal stop use the hysteresis.
        """
        return any(
            not valid(state := self.hass.states.get(entity_id))
            or "hvac_action" not in state.attributes  # type: ignore[union-attr]
            for entity_id in self.climates
        )

    def comfort_floor(self, preset: str) -> float | None:
        """Lowest temperature still in the comfort of ``preset`` (optimal stop)."""
        level = self.level_temp(preset)
        return None if level is None else level - max(0.0, self.stop_tolerance())

    def stop_needed(self, preset: str, outdoor: float | None) -> float | None:
        """Minutes the room can cool and stay in the comfort of ``preset``.

        None before any cooling is learned (the longest optimal stop is used).
        """
        floor = self.comfort_floor(preset)
        if floor is None or self.current_temp is None:
            return None
        return self.cooling.minutes_to_fall(self.current_temp, floor, outdoor)

    def optimal_estimate(
        self, now: datetime, state: ScheduleState, outdoor_known: bool, stop_allowed: bool
    ) -> dict[str, Any] | None:
        """When the optimal start / stop for the next change begins, and with what.

        The outdoor temperature is the one expected while it runs (hourly
        forecast), else the one of now. The period depends on that temperature,
        so it is worked out again a few times from the period found before.
        """
        change, next_preset = state.next_change, state.next_preset
        if change is None or next_preset is None or change <= now or self.current_temp is None:
            return None
        now_temp = self.level_temp(state.preset)
        next_temp = self.level_temp(next_preset)
        if now_temp is None or next_temp is None:
            return None
        house = self.house
        if next_temp > now_temp and self.config[CONF_OPTIMAL_START]:
            kind = RULE_OPTIMAL_START
            limit = float(self.config[CONF_OPTIMAL_START_MAX])
        elif (
            next_temp < now_temp
            and self.config[CONF_OPTIMAL_STOP]
            and outdoor_known
            and stop_allowed
        ):
            kind = RULE_OPTIMAL_STOP
            limit = float(self.config[CONF_OPTIMAL_STOP_MINUTES])
        else:
            return None
        gap = next_temp - self.current_temp
        floor = self.comfort_floor(state.preset)

        def minutes_for(outdoor: float | None) -> float | None:
            if kind == RULE_OPTIMAL_START:
                return self.learner.minutes(gap, outdoor, now) if gap > 0 else 0.0
            if floor is None:
                return None
            return self.cooling.minutes_to_fall(self.current_temp, floor, outdoor)

        minutes, outdoor, source = optimal_period(
            limit,
            minutes_for,
            lambda length: house.outdoor_between(change - timedelta(minutes=length), change),
            house.outdoor_now,
        )
        needed = minutes_for(outdoor)
        return {
            "kind": kind,
            "change": change,
            "preset": next_preset,
            "minutes": minutes,
            "needed": needed,
            "outdoor": outdoor,
            "outdoor_source": source,
            "learned": bool(
                self.learner.episodes if kind == RULE_OPTIMAL_START else self.cooling.episodes
            ),
        }

    def stop_forecast(self, now: datetime) -> dict[str, Any] | None:
        """During an optimal stop: the expected temperature at the scheduled change."""
        state = self.schedule_state
        if (
            self.decision is None
            or self.decision.rule != RULE_OPTIMAL_STOP
            or state is None
            or state.next_change is None
            or self.current_temp is None
        ):
            return None
        minutes = max(0.0, (state.next_change - now).total_seconds() / 60)
        outdoor, _ = self.house.outdoor_between(now, state.next_change)
        value = self.cooling.temperature_after(self.current_temp, outdoor, minutes)
        if value is None:
            return None
        return {"at": state.next_change.isoformat(), "temperature": value}

    def _start_needed(
        self, preset: str | None, outdoor: float | None, now: datetime
    ) -> float | None:
        """Minutes the room needs to heat up to the level of ``preset`` (learned)."""
        if preset is None or self.current_temp is None:
            return None
        level = self.level_temp(preset)
        if level is None or level <= self.current_temp:
            return None
        return self.learner.minutes(level - self.current_temp, outdoor, now)

    def time_to_target(self, outdoor: float | None) -> int | None:
        """Minutes until the target is reached, as learned (None when not heating up)."""
        if self.current_temp is None or self.target_temperature is None:
            return None
        if self.decision is None or self.decision.target.kind == KIND_OFF or self.window_open:
            return None
        gap = self.target_temperature - self.current_temp
        if gap <= 0:
            return None
        return max(1, round(self.learner.minutes(gap, outdoor, dt_util.utcnow())))

    def _window_sensor_open(self) -> bool:
        """A window or door sensor of the room (or a linked one) is open right now."""
        sensors = as_list(self.config.get(CONF_WINDOW_SENSORS)) + as_list(
            self.config.get(CONF_LINKED_WINDOW_SENSORS)
        )
        return any(
            (st := self.hass.states.get(eid)) is not None and st.state == STATE_ON
            for eid in sensors
        )

    def _window_raw(self, now: datetime) -> bool:
        """Window state before the delays (sensors or a quick drop)."""
        if self.house.windows_ignored:
            return False
        sensors = as_list(self.config.get(CONF_WINDOW_SENSORS)) + as_list(
            self.config.get(CONF_LINKED_WINDOW_SENSORS)
        )
        if any(
            (st := self.hass.states.get(eid)) is not None and st.state == STATE_ON
            for eid in sensors
        ):
            return True
        return self._drop_until is not None and now < self._drop_until

    def _update_window(self, now: datetime) -> None:
        """Debounce the window state with the open / close delays."""
        raw = self._window_raw(now)
        open_delay = timedelta(seconds=float(self.config[CONF_WINDOW_OPEN_DELAY]))
        close_delay = timedelta(seconds=float(self.config[CONF_WINDOW_CLOSE_DELAY]))
        due: datetime | None = None
        if raw:
            self._window_closed_since = None
            if not self.window_open:
                if self._window_raw_since is None:
                    self._window_raw_since = now
                if now - self._window_raw_since >= open_delay:
                    self.window_open = True
                    self._window_opened_at = now
                else:
                    due = self._window_raw_since + open_delay
        else:
            self._window_raw_since = None
            if self.window_open:
                if self._window_closed_since is None:
                    self._window_closed_since = now
                if now - self._window_closed_since >= close_delay:
                    self.window_open = False
                    self._window_opened_at = None
                    self._window_closed_since = None
                    self.house.clear_alert(f"window_{self.id}")
                else:
                    due = self._window_closed_since + close_delay
        if self._drop_until is not None and now < self._drop_until:
            due = min(due, self._drop_until) if due else self._drop_until
        if self._window_timer:
            self._window_timer()
            self._window_timer = None
        if due is not None:
            delay = max((due - now).total_seconds(), 0) + 0.5

            @callback
            def _recheck(_now: datetime) -> None:
                """Check the window again when a delay ends."""
                self._window_timer = None
                self._update_window(dt_util.utcnow())
                self.house.async_request_evaluate(0)

            self._window_timer = async_call_later(self.hass, delay, _recheck)

    def _room_unoccupied(self, now: datetime) -> bool:
        """True when the occupancy sensors have been off for the configured time."""
        sensors = as_list(self.config.get(CONF_OCCUPANCY_SENSORS))
        if not sensors:
            return False
        if any(
            (st := self.hass.states.get(eid)) is not None and st.state == STATE_ON
            for eid in sensors
        ):
            self._last_occupied = now
            return False
        since = self._last_occupied or self._started_at
        return now - since >= timedelta(minutes=float(self.config[CONF_OCCUPANCY_MINUTES]))

    def _day_info(self, day: date) -> tuple[bool, str | None]:
        """Whether a day is a workday, and a profile forced by the calendar.

        An event titled with a profile name selects it for the whole schedule
        day it covers part of (read from the start of today for the next days,
        every hour and when the calendar changes). Today the active event also
        counts, in case the events cannot be read.
        """
        forced = None
        today = self.schedule.schedule_day(dt_util.now())  # local
        if day >= today:
            forced = self.house.calendar_profile(day, self.schedule.profiles)
        if forced is None and day == today and self.house.calendar_message:
            message = self.house.calendar_message.lower()
            if message in self.schedule.profiles:
                forced = message
        return self.house.is_workday(day), forced

    def _schedule_lookup(self, now: datetime) -> ScheduleState | None:
        """Current level and next change, from the internal schedule or a Schedule helper."""
        cfg = self.config
        if cfg.get(CONF_SCHEDULE_SOURCE) == SCHEDULE_HELPER and cfg.get(CONF_SCHEDULE_HELPER):
            state = self.hass.states.get(cfg[CONF_SCHEDULE_HELPER])
            if not valid(state):
                return None
            on = state.state == STATE_ON  # type: ignore[union-attr]
            preset = cfg[CONF_HELPER_ON_PRESET] if on else cfg[CONF_HELPER_OFF_PRESET]
            data_preset = state.attributes.get("preset")  # type: ignore[union-attr]
            if on and data_preset:
                preset = self.aliases.get(str(data_preset).lower(), preset)
            next_event = from_iso(state.attributes.get("next_event"))  # type: ignore[union-attr]
            next_preset = cfg[CONF_HELPER_OFF_PRESET] if on else cfg[CONF_HELPER_ON_PRESET]
            return ScheduleState(
                preset=preset,
                profile="helper",
                slot_start=state.last_changed,  # type: ignore[union-attr]
                next_change=next_event,
                next_preset=next_preset if next_event else None,
            )
        return self.schedule.lookup(dt_util.as_local(now), self._day_info)

    def plan(self, now: datetime, hours: float = 12) -> list[dict[str, Any]]:
        """Schedule levels for the next hours (shown by the card)."""
        state = self.schedule_state
        if state is None:
            return []
        result = [{"at": now.isoformat(), "preset": state.preset}]
        cfg = self.config
        if cfg.get(CONF_SCHEDULE_SOURCE) == SCHEDULE_HELPER and cfg.get(CONF_SCHEDULE_HELPER):
            if state.next_change and state.next_preset:
                result.append({"at": state.next_change.isoformat(), "preset": state.next_preset})
            return result
        try:
            changes = self.schedule.upcoming(
                dt_util.as_local(now), self._day_info, timedelta(hours=hours)
            )
        except Exception:  # noqa: BLE001 - the plan is only informative
            return result
        result += [{"at": moment.isoformat(), "preset": preset} for moment, preset in changes]
        return result

    def _calendar_preset(self) -> str | None:
        """Level named by the current calendar event."""
        message = self.house.calendar_message
        if not message:
            return None
        return self.aliases.get(message.lower())

    def _offsets(self) -> list[tuple[str, float]]:
        """Adjustments of the target: house ones and the solar gain of the room."""
        offsets = self.house.house_offsets()
        solar = float(self.config.get(CONF_SOLAR_OFFSET) or 0)
        if solar and self.house.sunny():
            offsets.append(("solar_gain", solar))
        return offsets

    def _valve_exercise_due(self, now: datetime) -> bool:
        """True during the weekly valve exercise."""
        if not self.config[CONF_VALVE_EXERCISE] or not self.supports_valve_exercise:
            return False
        if self._exercise_until is not None:
            if now < self._exercise_until:
                return True
            self._exercise_until = None
            return False
        local = dt_util.as_local(now)  # the day and time of the exercise are local
        if WEEKDAYS[local.weekday()] != self.config[CONF_VALVE_DAY]:
            return False
        if self.house.paused or self.window_open or self.override_active:
            # Postponed: it starts when the pause or the manual change ends, or
            # the window closes.
            return False
        start = parse_clock(self.config[CONF_VALVE_TIME])
        start_dt = local.replace(hour=start.hour, minute=start.minute, second=0, microsecond=0)
        today = local.date().isoformat()
        # From the set time until the end of that day (a pause or an open window
        # postpones it, but only to the same day).
        if start_dt <= local and self.last_exercise != today:
            self.last_exercise = today
            self._exercise_until = now + timedelta(seconds=VALVE_EXERCISE_SECONDS)
            return True
        return False

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------
    async def async_evaluate(self, now: datetime) -> None:
        """Decide and apply."""
        house = self.house
        self._update_temperature(now)
        self._update_window(now)
        self._account_runtime(now)

        state = self._schedule_lookup(now)
        self.schedule_state = state
        preset = state.preset if state else None
        schedule_rule = "schedule"
        calendar_preset = self._calendar_preset()
        previous_estimate, self.next_estimate = self.next_estimate, None
        if calendar_preset is not None:
            preset = calendar_preset
            self._optimal_for = None
        elif state is not None:
            same = self._optimal_for is not None and self._optimal_for == state.next_change
            started = same and self._optimal_rule == RULE_OPTIMAL_START
            stop_allowed, stop_started, self.stop_cancelled = optimal_stop_state(
                same and self._optimal_rule == RULE_OPTIMAL_STOP,
                self._stop_cancelled_for is not None
                and self._stop_cancelled_for == state.next_change,
                self.current_temp,
                self.comfort_floor(state.preset),
            )
            self._stop_cancelled_for = state.next_change if self.stop_cancelled else None
            # The optimal stop needs the outdoor temperature (sensor or weather).
            outdoor_known = house.outdoor_configured and house.outdoor_now is not None
            estimate = self.optimal_estimate(now, state, outdoor_known, stop_allowed)
            start_needed = (
                estimate["needed"]
                if estimate and estimate["kind"] == RULE_OPTIMAL_START
                else self._start_needed(state.next_preset, house.outdoor_now, now)
            )
            stop_needed = (
                estimate["needed"]
                if estimate and estimate["kind"] == RULE_OPTIMAL_STOP
                else self.stop_needed(state.preset, house.outdoor_now)
            )
            preset, schedule_rule = optimal_schedule(
                now,
                state.preset,
                state.next_change,
                state.next_preset,
                self.current_temp,
                self.level_temp,
                start_needed,
                bool(self.config[CONF_OPTIMAL_START]),
                float(self.config[CONF_OPTIMAL_START_MAX]),
                bool(self.config[CONF_OPTIMAL_STOP]) and stop_allowed and outdoor_known,
                float(self.config[CONF_OPTIMAL_STOP_MINUTES]),
                started,
                stop_needed,
                stop_started,
            )
            optimal = schedule_rule in (RULE_OPTIMAL_START, RULE_OPTIMAL_STOP)
            self._optimal_for = state.next_change if optimal else None
            self._optimal_rule = schedule_rule if optimal else None
            if (
                optimal
                and previous_estimate is not None
                and previous_estimate.get("started_at") is not None
                and previous_estimate["change"] == state.next_change
                and previous_estimate["kind"] == schedule_rule
            ):
                # Running: what it started with is kept.
                estimate = previous_estimate
            elif estimate is not None:
                estimate["started_at"] = (
                    now if optimal and estimate["kind"] == schedule_rule else None
                )
            self.next_estimate = estimate

        vacation = house.vacation_active(now)
        preheat = not vacation and house.vacation_preheating(now)
        signature = (
            house.mode,
            house.presence_state,
            house.arriving,
            vacation,
            preheat,
            preset,
            state.profile if state else None,
            self.window_open,
            house.cutoff_active,
            house.season_active,
        )
        self.signature = signature
        self._check_override(now, signature)
        valve = self._valve_exercise_due(now)

        inputs = RoomInputs(
            now=now,
            mode=house.mode,
            paused=house.paused,
            season_active=house.season_active,
            cutoff_active=house.cutoff_active,
            valve_exercise=valve,
            window_open=self.window_open,
            window_action=self.config[CONF_WINDOW_ACTION],
            override_active=self.override_active,
            vacation_active=vacation,
            presence=house.presence_state or "home",
            arriving=house.arriving,
            room_unoccupied=self._room_unoccupied(now),
            sensor_failed=self.sensor_failed,
            schedule_preset=preset,
            schedule_rule=schedule_rule,
            current_temp=self.current_temp,
            frost_temp=self.frost_temp(),
            max_temp=self.max_temp(),
            exercise_temp=self.device_max_temp(),
            nearby_mode=self.config[CONF_NEARBY_MODE],
            nearby_limit=bool(self.config.get(CONF_NEARBY_LIMIT, False)),
            nearby_temp=self.nearby_temp,
            level_temp=self.level_temp,
            offsets=self._offsets(),
            supports_off=self._supports_off(),
            unit=self.house.unit,
            vacation_preheat=preheat,
            frost_holding=self._frost_holding(),
            device_setpoint=self._device_setpoint(),
            on_off=self.source == SOURCE_SWITCH or self.command_mode == COMMAND_HVAC,
        )
        decision = decide(inputs)
        if self.override is not None and decision.rule == RULE_OVERRIDE:
            self.override["applied"] = True
        if self.override is not None and decision.rule not in (RULE_OVERRIDE, RULE_PAUSE, RULE_MAX):
            # A higher rule changes the devices while the manual change lasts:
            # what the person set is set again afterwards. (Pause sends nothing;
            # the maximum limits the manual value for good.)
            self.override["interrupted"] = True
        if self.stop_cancelled and decision.rule == RULE_SCHEDULE:
            decision.description += " (optimal stop cancelled: the room got colder than expected)"
            decision.params = {**decision.params, "stop_cancelled": True}
        self._record(decision, now)
        self.decision = decision
        self.target_temperature = self._resolve_temperature(decision.target)

        await self._async_apply(decision.target)
        await self._async_calibrate(now)
        self._update_demand()
        # The heating and the cooling are learned in the cold season only (not in
        # mode Off or Summer, nor outside the heating season).
        if house.season_active and house.mode not in (MODE_OFF, MODE_SUMMER):
            outdoor = house.outdoor_now
            # An episode is not used with a window open, when the outdoor
            # temperature of a house that has one became unknown, when the
            # state of the heat source is unknown, or during the valve exercise.
            disturbed = (
                self._window_sensor_open()
                or (house.outdoor_configured and outdoor is None)
                or self.source_unknown
                or self._exercise_until is not None
            )
            self.learner.observe(
                now,
                self.heating,
                self.current_temp,
                self.target_temperature,
                outdoor,
                disturbed,
                self.learn_tolerance(),
            )
            self.cooling.observe(now, self.heating, self.current_temp, outdoor, disturbed)
        else:
            self.learner.cancel()
            self.cooling.cancel()
        self._check_alerts(now)

        # When should we look again?
        wakeups = []
        if state and state.next_change:
            wakeups.append(state.next_change)
        if self.override and self.override.get("until"):
            wakeups.append(self.override["until"])
        if self._exercise_until:
            wakeups.append(self._exercise_until)
        # The end of the minimum on / off time the relay waits for.
        if self.relay_waiting and self._relay_wait_until is not None:
            wakeups.append(self._relay_wait_until)
        # The moment the next optimal start / stop is expected to begin (worked
        # out again at every evaluation, so the wakeup moves with it).
        estimate = self.next_estimate
        if estimate and estimate.get("started_at") is None and estimate.get("minutes"):
            begin = estimate["change"] - timedelta(minutes=float(estimate["minutes"]))
            if begin > now:
                wakeups.append(begin)
        self.next_wakeup = min(wakeups) if wakeups else None

    def _device_setpoint(self) -> float | None:
        """Highest temperature set on the thermostats (not for on / off control)."""
        if self.source == SOURCE_SWITCH or self.command_mode == COMMAND_HVAC:
            return None
        values = [
            v
            for entity_id in self.climates
            if (v := climate_temp(self.hass, self.hass.states.get(entity_id), ATTR_TEMPERATURE))
            is not None
        ]
        return max(values) if values else None

    def _frost_holding(self) -> bool:
        """Frost protection started (heating off otherwise) and the device still heats."""
        previous = self.decision
        return (
            previous is not None
            and previous.rule == RULE_SAFETY
            and previous.target.kind == KIND_TEMPERATURE
            and previous.target.preset is None
            and self.heat_demand
        )

    def _supports_off(self) -> bool:
        """True when the devices can be turned off (else the frost temperature is used)."""
        if self.source == SOURCE_SWITCH or self.command_mode == COMMAND_HVAC:
            return True
        for entity_id in self.climates:
            state = self.hass.states.get(entity_id)
            if valid(state):
                return STATE_OFF in (state.attributes.get("hvac_modes") or [])  # type: ignore[union-attr]
        return True

    def _override_target(self) -> Target | None:
        """Level or temperature of a manual change set by the card or a service."""
        stored = (self.override or {}).get("target")
        if not isinstance(stored, dict) or stored.get("kind") not in (
            KIND_TEMPERATURE,
            KIND_PRESET,
        ):
            return None
        return Target(
            stored["kind"], preset=stored.get("preset"), temperature=stored.get("temperature")
        )

    def _resolve_temperature(self, target: Target) -> float | None:
        """Temperature a target stands for (level, manual temperature or the thermostat)."""
        if target.kind == KIND_TEMPERATURE:
            return target.temperature
        if target.kind == KIND_PRESET and target.preset:
            return self.level_temp(target.preset)
        if target.kind == KIND_NONE and (stored := self._override_target()) is not None:
            return self._resolve_temperature(stored)
        if target.kind == KIND_NONE:
            for entity_id in self.climates:
                value = climate_temp(self.hass, self.hass.states.get(entity_id), ATTR_TEMPERATURE)
                if value is not None:
                    return value
        return None

    def _record(self, decision: Decision, now: datetime) -> None:
        """Keep the decision history and fire an event when the decision changes."""
        previous = self.decision
        if (
            previous is not None
            and previous.rule == decision.rule
            and previous.target == decision.target
        ):
            return
        entry = {
            "time": now.isoformat(),
            "rule": decision.rule,
            "target": decision.target.as_dict(),
            "description": decision.description,
        }
        self.decisions.append(entry)
        self.hass.bus.async_fire(
            EVENT_DECISION_CHANGED,
            {
                "room": self.name,
                "room_id": self.id,
                "old_rule": previous.rule if previous else None,
                "old_target": previous.target.as_dict() if previous else None,
                "rule": decision.rule,
                "target": decision.target.as_dict(),
                "reason": decision.description,
            },
        )

    def _account_runtime(self, now: datetime) -> None:
        """Add the heating time since the last evaluation."""
        if self._heating_since is not None:
            self.runtime_s += (now - self._heating_since).total_seconds()
            self._heating_since = now if self.heating else None

    def _update_demand(self) -> None:
        """Whether the room asks for heat (hvac_action, else the hysteresis; relays: on)."""
        demand = False
        if self._exercise_until is not None:
            pass  # the valves are exercised: no heat is asked for
        elif self.source == SOURCE_SWITCH or self.command_mode == COMMAND_HVAC:
            demand = bool(self._relay_on)
        elif self.boost:
            demand = self._boost_demand  # from the room sensor, with the hysteresis
        else:
            hysteresis = float(self.config[CONF_HYSTERESIS])
            for entity_id in self.climates:
                state = self.hass.states.get(entity_id)
                if not valid(state):
                    continue
                action = state.attributes.get("hvac_action")  # type: ignore[union-attr]
                if action is not None:
                    demand = demand or action == "heating"
                    continue
                # No hvac_action: heating is decided with the hysteresis, like a relay.
                current = climate_temp(self.hass, state, "current_temperature")
                target = climate_temp(self.hass, state, ATTR_TEMPERATURE)
                if state.state == STATE_OFF or current is None or target is None:  # type: ignore[union-attr]
                    continue
                if current <= target - hysteresis:
                    demand = True
                elif current < target + hysteresis and self.heat_demand:
                    demand = True  # between the limits: keep heating
            # Frost protection from the room sensor (the TRVs are boosted for it).
            demand = demand or self._boost_demand
        self.heat_demand = demand
        # The room heats only while its heat source runs: its own device (GT,
        # relay, on / off thermostat) and, when one is set, the heat source of
        # the house (the boiler that TRVs and zone valves wait for).
        configured, source_on = self.house.heat_source_state()
        self.source_unknown = configured and source_on is None
        heating = demand and (not configured or bool(source_on))
        now = dt_util.utcnow()
        if heating and self._heating_since is None:
            self._heating_since = now
        if not heating and self._heating_since is not None:
            self._account_runtime(now)
            self._heating_since = None
        self.heating = heating

    @property
    def frost_demand(self) -> bool:
        """The room asks for heat to stay at the frost protection temperature."""
        if not self.heat_demand or self.target_temperature is None:
            return False
        return self.target_temperature <= self.frost_temp()

    def temperature_gap(self) -> float | None:
        """Degrees below the target (negative when above)."""
        if self.current_temp is None or self.target_temperature is None:
            return None
        if self.decision is None or self.decision.target.kind == KIND_OFF:
            return None
        return round(self.target_temperature - self.current_temp, 2)

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------
    async def _call(self, domain: str, service: str, data: dict[str, Any]) -> bool:
        """Call a service with the context of the integration; False when it fails."""
        try:
            await self.hass.services.async_call(
                domain, service, data, blocking=True, context=self.house.new_context()
            )
        except (HomeAssistantError, ValueError) as err:
            _LOGGER.warning("Room %s: %s.%s failed: %s", self.name, domain, service, err)
            return False
        return True

    async def _async_apply(self, target: Target, *, force: bool = False) -> None:
        """Send the commands needed to reach ``target``."""
        on_off = self.source == SOURCE_SWITCH or self.command_mode == COMMAND_HVAC
        if target.kind == KIND_NONE:
            # Nothing is sent (pause, no schedule) unless a manual change applies.
            self.relay_waiting = None
            self._relay_wait_until = None
            if self.decision is None or self.decision.rule != RULE_OVERRIDE or not self.override:
                await self._async_boost_without_target(target)
                return
            stored = self._override_target()
            if stored is None:
                await self._async_boost_without_target(target)
                # Changed on the device: set again only after an interruption.
                if self.override.get("interrupted"):
                    self.override["interrupted"] = False
                    for entity_id, values in (self.override.get("devices") or {}).items():
                        if not await self._async_restore_device(entity_id, values):
                            # The minimum on / off time runs: set again when it ends.
                            self.override["interrupted"] = True
                return
            # Set by the card or a service: kept on the devices (relays regulate around it).
            self.override["interrupted"] = False
            target = stored
        if self._boost_capable:
            # The demand first, so the TRVs get the right temperature now.
            heat = target.kind != KIND_OFF and self._exercise_until is None
            temperature = self._resolve_temperature(target)
            if self.boost:
                self._boost_demand = heat and self._boost_wanted(temperature)
            elif (
                self._frost_boost_possible()
                and temperature is not None
                and temperature <= self.frost_temp() + 1e-9
            ):
                self._boost_demand = heat and self._frost_wanted(temperature)
            else:
                self._boost_demand = False
        sent = False
        if on_off:
            sent = await self._async_apply_relay(target)
        else:
            for entity_id in self.climates:
                sent |= await self._async_apply_climate(entity_id, target, force)
        if self._boost_capable:
            self._boosted = self._boost_demand
            self._boost_base = (
                None if target.kind == KIND_OFF else self._target_temperature_of(target)
            )
        if sent and self.house.options[CONF_VERIFY_COMMANDS]:
            self._schedule_verify(target)

    @property
    def boost_active(self) -> bool:
        """The TRVs hold the boost temperature now (the TRV boost or frost protection)."""
        return self._boost_capable and self._boosted

    @property
    def _boost_capable(self) -> bool:
        """TRVs commanded with a temperature or a preset can be boosted."""
        return self.source == SOURCE_CLIMATE and self.command_mode != COMMAND_HVAC

    def _frost_boost_possible(self) -> bool:
        """A TRV room without the boost, with its own room sensor (frost protection).

        The TRV next to the radiator reads warmer than the room: at the frost
        protection temperature it would not open, so it is boosted like the TRV
        boost while the room sensor is below the frost protection.
        """
        return (
            not self.boost
            and self._boost_capable
            and bool(as_list(self.config.get(CONF_TEMP_SENSORS)))
            and not self.external_failed
        )

    def _frost_wanted(self, frost: float) -> bool:
        """Frost protection demand from the room sensor: below it, until it + hysteresis."""
        if self.current_temp is None:
            return False
        if self.current_temp < frost:
            return True
        if self.current_temp >= frost + float(self.config[CONF_HYSTERESIS]):
            return False
        return self._boost_demand  # between the limits: as it was

    def _boost_wanted(self, temperature: float | None) -> bool:
        """The room asks for heat (boost rooms): the room sensor with the hysteresis."""
        if temperature is None or self.current_temp is None:
            return False
        hysteresis = float(self.config[CONF_HYSTERESIS])
        if self.current_temp <= temperature - hysteresis:
            return True
        if self.current_temp >= temperature + hysteresis:
            return False
        return self._boost_demand  # between the limits: as it was

    def boost_temperature(self, temperature: float) -> float:
        """Temperature the TRVs get while the room asks for heat (°C).

        The boost temperature of the room (the maximum of the house when empty),
        never below the target, never above the maximum of the house nor of the TRVs.
        """
        chosen = self.config.get(CONF_TRV_BOOST_TEMP) if self.boost else None
        value = float(chosen) if chosen not in (None, "") else self.max_temp()
        value = min(value, self.max_temp())
        device_max = self.device_max_temp()
        if device_max is not None:
            value = min(value, device_max)
        return max(value, temperature)

    def _target_temperature_of(self, target: Target) -> float | None:
        """Temperature of a target, before the boost."""
        if target.kind == KIND_TEMPERATURE:
            return target.temperature
        if target.kind == KIND_PRESET:
            return self.level_temp(target.preset or "")
        return None

    def _climate_temperature(self, target: Target) -> float | None:
        """Temperature a thermostat gets for ``target`` (with the TRV boost)."""
        temperature = self._target_temperature_of(target)
        if temperature is not None and self._boost_capable and self._boost_demand:
            return self.boost_temperature(temperature)
        return temperature

    async def _async_boost_without_target(self, target: Target) -> None:
        """Boost rooms when nothing is sent (pause, no schedule, a change on the TRV).

        A boost we left on the TRVs is taken back to the target, so a TRV never
        keeps the boost temperature while nobody regulates it; the heat demand
        follows the room sensor against what the TRV is set to.
        """
        if not self._boost_capable:
            return
        # Until the TRVs report it, the temperature they hold is the one taken back.
        temperature = self._resolve_temperature(target)
        if self._boosted and self._boost_base is not None:
            temperature = self._boost_base
            for entity_id in self.climates:
                state = self.hass.states.get(entity_id)
                if valid(state):
                    assert state is not None
                    await self._send(
                        entity_id,
                        "set_temperature",
                        ATTR_TEMPERATURE,
                        self._device_value(state, self._boost_base),
                    )
        self._boosted = False
        heat = self._exercise_until is None
        # Without the TRV boost the demand comes from the TRVs again.
        self._boost_demand = self.boost and heat and self._boost_wanted(temperature)

    async def _async_restore_device(self, entity_id: str, values: dict[str, Any]) -> bool:
        """Set again what a person set on a device (after an interruption).

        False while the minimum on / off time of a relay (or on / off thermostat)
        runs: it is set again when that time ends.
        """
        state = self.hass.states.get(entity_id)
        if not valid(state) or not values:
            return True
        assert state is not None
        domain = entity_id.split(".", 1)[0]
        wanted = values.get("state")
        on_off = self.source == SOURCE_SWITCH or self.command_mode == COMMAND_HVAC
        if on_off and wanted and state.state != wanted:
            actual = self._relay_actual()
            now = dt_util.utcnow()
            if actual is not None:
                self._note_relay_state(actual, now)
                if (wanted != STATE_OFF) != actual and self._relay_must_wait(actual, now):
                    return False
        if domain != "climate":
            if (
                wanted in (STATE_ON, STATE_OFF)
                and state.state != wanted
                and await self._call(
                    domain,
                    SERVICE_TURN_ON if wanted == STATE_ON else SERVICE_TURN_OFF,
                    {ATTR_ENTITY_ID: entity_id},
                )
            ):
                self._sent[entity_id] = {"state": wanted}
                if entity_id in self.switches:
                    self._relay_on = wanted == STATE_ON
                    self._relay_changed = dt_util.utcnow()
            return True
        if (
            wanted
            and state.state != wanted
            and await self._send(entity_id, "set_hvac_mode", "hvac_mode", wanted, "state")
            and on_off
        ):
            self._relay_on = wanted != STATE_OFF
            self._relay_changed = dt_util.utcnow()
        if wanted == STATE_OFF:
            return True
        preset = values.get("preset_mode")
        if preset not in (None, PRESET_NONE):
            if state.attributes.get("preset_mode") != preset:
                await self._send(entity_id, "set_preset_mode", "preset_mode", preset)
            return True
        temperature = values.get("temperature")
        if temperature is not None and float_attr(state, ATTR_TEMPERATURE) != temperature:
            await self._send(entity_id, "set_temperature", ATTR_TEMPERATURE, temperature)
        return True

    def sends_preset(self, preset: str) -> bool:
        """The level is sent to the device as a preset (else as a temperature)."""
        if self.source not in (SOURCE_GT, SOURCE_CLIMATE) or self.command_mode != COMMAND_PRESET:
            return False
        for entity_id in self.climates:
            state = self.hass.states.get(entity_id)
            if valid(state):
                available = list(state.attributes.get("preset_modes") or [])  # type: ignore[union-attr]
                return self._device_preset(preset, available) is not None
        return self.source == SOURCE_GT

    def _device_preset(self, preset: str, available: list[str]) -> str | None:
        """Map a level to the device preset name."""
        if self.source == SOURCE_GT:
            return preset if preset in available else None
        if self.preset_map is None:
            return None
        candidates = [self.preset_map.get(preset)]
        if self._legacy_map:
            candidates.append(preset)
        for candidate in candidates:
            if candidate and candidate in available:
                return candidate
        return None

    def _matches(self, state: State, target: Target) -> bool:
        """Return True if the climate state already matches the target."""
        if target.kind == KIND_OFF:
            if STATE_OFF in (state.attributes.get("hvac_modes") or []):
                return state.state == STATE_OFF
            return float_attr(state, ATTR_TEMPERATURE) == float_attr(state, "min_temp")
        if state.state == STATE_OFF:
            return False
        if target.kind == KIND_PRESET and self.command_mode == COMMAND_PRESET:
            name = self._device_preset(
                target.preset or "", list(state.attributes.get("preset_modes") or [])
            )
            if name is not None:
                return state.attributes.get("preset_mode") == name
        temperature = self._climate_temperature(target)
        if temperature is None:
            return True
        # Compared in the unit of the thermostat, as sent.
        current = float_attr(state, ATTR_TEMPERATURE)
        wanted = self._device_value(state, temperature)
        return current is not None and abs(current - wanted) < 0.05

    async def _async_apply_climate(self, entity_id: str, target: Target, force: bool) -> bool:
        """Bring one thermostat to the target (mode, preset or temperature)."""
        state = self.hass.states.get(entity_id)
        if not valid(state):
            return False
        assert state is not None
        if not force and self._matches(state, target):
            return False
        self._sent[entity_id] = {}
        modes = list(state.attributes.get("hvac_modes") or [])
        # Turned on only with a mode that heats (no guess when there is none).
        on_mode = heat_mode(modes) if {"heat", "auto"} & set(modes) else None

        if target.kind == KIND_OFF:
            if STATE_OFF in modes:
                return await self._send(entity_id, "set_hvac_mode", "hvac_mode", STATE_OFF, "state")
            minimum = float_attr(state, "min_temp")
            if minimum is None:
                return False
            return await self._send(entity_id, "set_temperature", ATTR_TEMPERATURE, minimum)

        if state.state == STATE_OFF and on_mode:
            await self._send(entity_id, "set_hvac_mode", "hvac_mode", on_mode, "state")

        if target.kind == KIND_PRESET and self.command_mode == COMMAND_PRESET:
            available = list(state.attributes.get("preset_modes") or [])
            name = self._device_preset(target.preset or "", available)
            if name is not None:
                self.house.clear_alert(f"preset_{self.id}_{target.preset}")
                return await self._send(entity_id, "set_preset_mode", "preset_mode", name)
        temperature = self._climate_temperature(target)
        if temperature is None:
            self.house.notify(
                f"preset_{self.id}_{target.preset}",
                f"{self.name}: the level '{self.display_name(target.preset)}' is not "
                f"available on {entity_id} and its temperature is unknown. "
                "Configure this preset in the thermostat.",
                code="preset_missing",
                params={"level": self.display_name(target.preset), "entity": entity_id},
                room=self.id,
            )
            return False
        return await self._send(
            entity_id, "set_temperature", ATTR_TEMPERATURE, self._device_value(state, temperature)
        )

    def _device_value(self, state: State, temperature: float) -> float:
        """Temperature to send, in the unit of the thermostat.

        A thermostat rounds to its own step; where that would take a value
        within the maximum of the house above it, the value is rounded down to
        the step instead, so the thermostat never holds more than the maximum.
        A value meant to be above the maximum (the valve exercise) is sent as
        it is.
        """
        unit = system_unit(self.hass)
        value = round(float(from_celsius(temperature, unit)), 1)
        step = float_attr(state, "target_temp_step")
        if step:
            maximum = float(from_celsius(self.max_temp(), unit))
            if value <= maximum + 1e-9 < round(value / step) * step:
                value = round(math.floor(maximum / step + 1e-9) * step, 2)
        return value

    async def _send(
        self, entity_id: str, service: str, key: str, value: Any, field: str | None = None
    ) -> bool:
        """Send one climate command and remember the value it sets."""
        ok = await self._call("climate", service, {ATTR_ENTITY_ID: entity_id, key: value})
        if ok:
            self._sent.setdefault(entity_id, {})[field or key] = value
            now = dt_util.utcnow()
            recent = [r for r in self._sent_recent.get(entity_id, []) if now - r[0] <= SENT_RECENT]
            recent.append((now, field or key, value))
            self._sent_recent[entity_id] = recent
        return ok

    async def _async_apply_relay(self, target: Target) -> bool:
        """On/off control for switches or climates in hvac_mode command mode."""
        now = dt_util.utcnow()
        self.relay_waiting = None
        self._relay_wait_until = None
        # The real state first: inside the hysteresis band it stays as it is
        # (also when a person switched it by hand).
        actual = self._relay_actual()
        if actual is None:
            return False
        self._note_relay_state(actual, now)
        if target.kind == KIND_OFF:
            want = False
        else:
            temperature = self._resolve_temperature(target)
            if temperature is None or self.current_temp is None:
                want = False
            else:
                hysteresis = float(self.config[CONF_HYSTERESIS])
                if self.current_temp <= temperature - hysteresis:
                    want = True
                elif self.current_temp >= temperature + hysteresis:
                    want = False
                else:
                    want = actual
        if want == actual:
            return False
        if self._relay_must_wait(actual, now):
            return False
        ok = True
        if self.source == SOURCE_SWITCH:
            for entity_id in self.switches:
                sent = await self._call(
                    entity_id.split(".", 1)[0],
                    SERVICE_TURN_ON if want else SERVICE_TURN_OFF,
                    {ATTR_ENTITY_ID: entity_id},
                )
                if sent:
                    self._sent[entity_id] = {"state": STATE_ON if want else STATE_OFF}
                ok &= sent
        else:
            for entity_id in self.climates:
                state = self.hass.states.get(entity_id)
                on_mode = heat_mode(state.attributes.get("hvac_modes") if valid(state) else None)  # type: ignore[union-attr]
                self._sent[entity_id] = {}
                ok &= await self._send(
                    entity_id, "set_hvac_mode", "hvac_mode", on_mode if want else STATE_OFF, "state"
                )
        if ok:
            self._relay_on = want
            self._relay_changed = now
        return ok

    def _note_relay_state(self, actual: bool, now: datetime) -> None:
        """Remember the real relay state; a switch from outside starts the minimum time."""
        if self._relay_on is not None and actual != self._relay_on:
            self._relay_changed = now
        self._relay_on = actual

    def _relay_must_wait(self, actual: bool, now: datetime) -> bool:
        """True while the minimum on / off time of the relay runs (and note until when)."""
        if self._relay_changed is None:
            return False
        minimum = timedelta(
            minutes=float(self.config[CONF_MIN_ON] if actual else self.config[CONF_MIN_OFF])
        )
        if now - self._relay_changed < minimum:
            self.relay_waiting = "min_on" if actual else "min_off"
            self._relay_wait_until = self._relay_changed + minimum
            return True
        return False

    def _relay_actual(self) -> bool | None:
        """True when a relay (or on / off thermostat) is on now."""
        entities = self.switches if self.source == SOURCE_SWITCH else self.climates
        states = [self.hass.states.get(eid) for eid in entities]
        usable = [s for s in states if valid(s)]
        if not usable:
            return None
        return any(s.state not in (STATE_OFF,) for s in usable)  # type: ignore[union-attr]

    def _schedule_verify(self, target: Target) -> None:
        """Check later that the devices accepted the command; retry once, then alert."""
        if self._verify_unsub:
            self._verify_unsub()
        expected = target

        async def _verify(_now: datetime) -> None:
            """Compare the devices with the command sent."""
            self._verify_unsub = None
            # A manual change set by the card or a service has no target in the
            # decision (it is "respected"); its stored target is checked instead.
            current = (
                self._override_target()
                if self.decision is not None and self.decision.rule == RULE_OVERRIDE
                else self.decision.target
                if self.decision is not None
                else None
            )
            if current != expected:
                self._verify_attempts = 0
                return
            if self.source == SOURCE_SWITCH or self.command_mode == COMMAND_HVAC:
                self._verify_attempts = 0
                return
            mismatched = [
                eid
                for eid in self.climates
                if valid(state := self.hass.states.get(eid)) and not self._matches(state, expected)  # type: ignore[arg-type]
            ]
            if not mismatched:
                self._verify_attempts = 0
                self.house.clear_alert(f"verify_{self.id}")
                return
            self._verify_attempts += 1
            if self._verify_attempts == 1:
                await self._async_apply(expected, force=True)
            else:
                self._verify_attempts = 0
                self.house.notify(
                    f"verify_{self.id}",
                    f"{self.name}: {', '.join(mismatched)} did not accept "
                    f"{expected.describe(self.house.unit)}.",
                    repeat=timedelta(hours=6),
                    code="not_accepted",
                    params={"entities": mismatched, "target": expected.describe(self.house.unit)},
                    room=self.id,
                )

        self._verify_unsub = async_call_later(self.hass, VERIFY_DELAY, _verify)

    async def async_apply_manual(self, target: Target, hours: float | None) -> None:
        """Service: set a manual target and keep it as an override.

        A temperature is kept between the frost protection and the maximum.
        The new manual change ends the earlier one (and what it kept).
        """
        if target.kind == KIND_TEMPERATURE and target.temperature is not None:
            limited = min(max(target.temperature, self.frost_temp()), self.max_temp())
            target = Target(KIND_TEMPERATURE, preset=target.preset, temperature=limited)
        # Sent by the decision that follows, only when the manual change applies
        # (not in a pause, with a window open, in mode Off...).
        self.set_override(
            f"set by service: {target.describe(self.house.unit)}", hours=hours, target=target
        )

    # ------------------------------------------------------------------
    # Calibration
    # ------------------------------------------------------------------
    async def _async_calibrate(self, now: datetime) -> None:
        """Write the external temperature (or the offset) to the TRV calibration entities."""
        mode = self.config[CONF_CALIBRATION_MODE]
        if mode not in (CALIBRATION_OFFSET, CALIBRATION_EXTERNAL) or self.house.paused:
            return
        external = self.external_temperature()
        if external is None:
            return
        entity_reg = er.async_get(self.hass)
        for number_id in as_list(self.config.get(CONF_CALIBRATION_ENTITIES)):
            number = self.hass.states.get(number_id)
            if not valid(number):
                continue
            assert number is not None
            last = self._calibration_written.get(number_id)
            interval = timedelta(minutes=10 if mode == CALIBRATION_OFFSET else 5)
            if last is not None and now - last < interval:
                continue
            step = float_attr(number, "step") or 0.1
            minimum = float_attr(number, "min")
            maximum = float_attr(number, "max")
            if (current := finite(number.state)) is None:
                continue  # not a number: this entity is skipped
            # The TRV number has its own unit (usually °C).
            number_unit = number.attributes.get("unit_of_measurement") or system_unit(self.hass)
            if mode == CALIBRATION_EXTERNAL:
                value = float(from_celsius(external, number_unit))
            else:
                climate_id = self._climate_on_same_device(entity_reg, number_id)
                device_temp = (
                    climate_temp(self.hass, self.hass.states.get(climate_id), "current_temperature")
                    if climate_id
                    else None
                )
                if device_temp is None:
                    continue
                value = current + float(delta_from_celsius(external - device_temp, number_unit))
            value = round(round(value / step) * step, 2)
            if minimum is not None:
                value = max(minimum, value)
            if maximum is not None:
                value = min(maximum, value)
            if abs(value - current) < max(step, 0.1):
                continue
            if await self._call("number", "set_value", {ATTR_ENTITY_ID: number_id, "value": value}):
                self._calibration_written[number_id] = now

    def _climate_on_same_device(self, registry: er.EntityRegistry, entity_id: str) -> str | None:
        """Thermostat on the same device as a calibration entity."""
        entry = registry.async_get(entity_id)
        if entry is None or entry.device_id is None:
            return self.climates[0] if len(self.climates) == 1 else None
        for climate_id in self.climates:
            climate_entry = registry.async_get(climate_id)
            if climate_entry is not None and climate_entry.device_id == entry.device_id:
                return climate_id
        return None

    # ------------------------------------------------------------------
    # Alerts
    # ------------------------------------------------------------------
    def _check_alerts(self, now: datetime) -> None:
        """Alerts for long open windows, unavailable devices, failed sensors and schedule errors."""
        house = self.house
        # Window open for too long while heating matters.
        if self.window_open and self._window_opened_at is not None:
            minutes = float(house.options[CONF_ALERT_WINDOW_MINUTES])
            heating_relevant = house.mode not in (MODE_OFF, MODE_SUMMER) and house.season_active
            if heating_relevant and now - self._window_opened_at >= timedelta(minutes=minutes):
                house.notify(
                    f"window_{self.id}",
                    f"{self.name}: a window has been open for more than {minutes:.0f} minutes.",
                    code="window_long",
                    params={"minutes": round(minutes)},
                    room=self.id,
                )
        # Unavailable devices.
        limit = timedelta(minutes=house.alert_unavailable_minutes)
        for entity_id in self.climates + self.switches:
            state = self.hass.states.get(entity_id)
            if valid(state):
                if self._unavailable_since.pop(entity_id, None) is not None:
                    house.clear_alert(f"unavailable_{entity_id}")
                continue
            since = self._unavailable_since.setdefault(entity_id, now)
            if now - since >= limit:
                house.notify(
                    f"unavailable_{entity_id}",
                    f"{self.name}: {entity_id} has been unavailable for more than "
                    f"{limit.total_seconds() / 60:.0f} minutes.",
                    code="device_unavailable",
                    params={"entity": entity_id, "minutes": round(limit.total_seconds() / 60)},
                    room=self.id,
                )
        # External sensors.
        if self.external_failed:
            fallback = "the device sensor" if not self.sensor_failed else "eco"
            house.notify(
                f"sensor_{self.id}",
                f"{self.name}: the temperature sensors are unavailable; using {fallback}.",
                code="sensor_unavailable",
                params={"fallback": "eco" if self.sensor_failed else "device"},
                room=self.id,
            )
        else:
            house.clear_alert(f"sensor_{self.id}")
        # Schedule errors.
        if self.schedule_error:
            house.notify(
                f"schedule_{self.id}",
                f"{self.name}: the schedule is invalid ({self.schedule_error}); "
                "the default schedule is used.",
                code="schedule_invalid",
                params={"error": self.schedule_error},
                room=self.id,
            )
        else:
            house.clear_alert(f"schedule_{self.id}")
        # Days without an active profile (frost protection on those days).
        gaps = (
            uncovered_days(self.schedule.profile_days)
            if not (
                self.config.get(CONF_SCHEDULE_SOURCE) == SCHEDULE_HELPER
                and self.config.get(CONF_SCHEDULE_HELPER)
            )
            else {"days": [], "free_days": False, "workdays": False}
        )
        if gaps["days"] or gaps["free_days"] or gaps["workdays"]:
            house.notify(
                f"schedule_gap_{self.id}",
                f"{self.name}: no active schedule profile on "
                + ", ".join(
                    [
                        *gaps["days"],
                        *(["free days"] if gaps["free_days"] else []),
                        *(["workdays on the weekend"] if gaps["workdays"] else []),
                    ]
                )
                + "; the room keeps its frost protection on those days.",
                code="schedule_gap",
                params=dict(gaps),
                room=self.id,
            )
        else:
            house.clear_alert(f"schedule_gap_{self.id}")

    @callback
    def check_batteries(self) -> None:
        """Alert about low batteries of the room devices."""
        threshold = float(self.house.options[CONF_BATTERY_THRESHOLD])
        entity_reg = er.async_get(self.hass)
        device_reg = dr.async_get(self.hass)
        devices: set[str] = set()
        related = (
            self.climates
            + self.switches
            + as_list(self.config.get(CONF_TEMP_SENSORS))
            + as_list(self.config.get(CONF_WINDOW_SENSORS))
            + as_list(self.config.get(CONF_OCCUPANCY_SENSORS))
        )
        for entity_id in related:
            entry = entity_reg.async_get(entity_id)
            if entry is not None and entry.device_id:
                devices.add(entry.device_id)
        for device_id in devices:
            device = device_reg.async_get(device_id)
            for entry in er.async_entries_for_device(entity_reg, device_id):
                if entry.domain != "sensor":
                    continue
                if (entry.device_class or entry.original_device_class) != "battery":
                    continue
                state = self.hass.states.get(entry.entity_id)
                if not valid(state):
                    continue
                level = finite(state.state)  # type: ignore[union-attr]
                if level is None:
                    continue
                key = f"battery_{entry.entity_id}"
                if level < threshold:
                    name = (device.name_by_user or device.name) if device else entry.entity_id
                    self.house.notify(
                        key,
                        f"{self.name}: low battery on {name} ({level:.0f}%).",
                        repeat=timedelta(days=1),
                        code="battery_low",
                        params={"device": name, "level": round(level)},
                        room=self.id,
                    )
                else:
                    self.house.clear_alert(key)

    # ------------------------------------------------------------------
    # Setters used by entities and services
    # ------------------------------------------------------------------
    async def async_set_level(self, preset: str, value: float) -> None:
        """Set the temperature of a custom level."""
        if preset == "nearby":
            self.nearby_temp = value
        else:
            self.levels[preset] = value
        await self.house.async_evaluate_or_notify()

    async def async_set_child_lock(self, on: bool) -> None:
        """Enable or disable the child lock."""
        self.child_lock = on
        await self.house.async_evaluate_or_notify()

    # ------------------------------------------------------------------
    # Diagnostics / attributes
    # ------------------------------------------------------------------
    def override_info(self) -> dict[str, Any] | None:
        """Override details for attributes."""
        if not self.override:
            return None
        return {
            "description": self.override.get("description"),
            "since": iso(self.override.get("since")),
            "until": iso(self.override.get("until")),
            "mode": self.override.get("mode"),
            # Set by the card / a service, or on the device itself.
            "origin": "card" if self.override.get("target") else "device",
            "devices": list((self.override.get("devices") or {}).keys()),
            # A higher rule changed the devices: the manual value comes back after it.
            "interrupted": bool(self.override.get("interrupted")),
            # False while a higher rule has kept it from the devices so far.
            "applied": bool(self.override.get("applied", True)),
            # What the manual change holds (°C), also while a higher rule interrupts it.
            **self._override_level(),
        }

    def _override_level(self) -> dict[str, Any]:
        """Level and temperature (°C) a manual change holds, when known."""
        stored = self._override_target()
        if stored is not None:
            return {"preset": stored.preset, "temperature": self._resolve_temperature(stored)}
        for values in (self.override or {}).get("devices", {}).values():
            if values.get("state") == STATE_OFF:
                return {"preset": None, "temperature": None}
            level = self.level_of_device_preset(values.get("preset_mode"))
            if level is not None:
                return {"preset": level, "temperature": self.level_temp(level)}
            if values.get("temperature") is not None:
                try:
                    value = to_celsius(float(values["temperature"]), system_unit(self.hass))
                except (TypeError, ValueError):
                    continue
                return {"preset": None, "temperature": value}
        return {"preset": None, "temperature": None}

    def hold_until(self, now: datetime) -> datetime | None:
        """Until when the current level holds before the schedule applies, when known.

        A planned vacation ends when its preheating starts; a calendar event
        at its end. (The card plans the rest from the decision and the schedule.)
        """
        rule = self.decision.rule if self.decision else None
        if rule == RULE_VACATION:
            return self.house.vacation_until(now)
        end = self.house.calendar_end
        if self._calendar_preset() is not None and end is not None and end > now:
            return end
        return None

    def no_heat_reason(self) -> dict[str, Any] | None:
        """Why the room does not heat although it is below its target."""
        decision = self.decision
        if (
            decision is None
            or decision.target.kind == KIND_OFF
            or decision.rule == RULE_PAUSE
            or self.current_temp is None
            or self.target_temperature is None
            or self.current_temp >= self.target_temperature
            or self.heating
            or self._exercise_until is not None
        ):
            return None
        house = self.house
        configured, source_on = house.heat_source_state()
        if self.heat_demand:
            if configured and source_on is None:
                return {"code": "source_unknown"}
            if house.source_waiting:
                return {"code": f"source_{house.source_waiting}"}
            reference = house.options.get(CONF_REFERENCE_ROOM)
            if (
                reference
                and reference in house.rooms
                and reference != self.id
                and not house.rooms[reference].heat_demand
            ):
                return {"code": "reference_room", "room": house.rooms[reference].name}
            needed = max(1, int(house.options[CONF_BOILER_MIN_ROOMS]))
            count = sum(1 for room in house.rooms.values() if room.heat_demand)
            if not reference and count < needed:
                return {"code": "rooms_needed", "count": count, "needed": needed}
            return {"code": "source_off"}
        if self.source == SOURCE_SWITCH or self.command_mode == COMMAND_HVAC or self.boost:
            if self.relay_waiting:
                return {"code": f"relay_{self.relay_waiting}"}
            return {
                "code": "hysteresis",
                "value": round(
                    delta_from_celsius(float(self.config[CONF_HYSTERESIS]), house.unit), 2
                ),
            }
        states = [st for eid in self.climates if valid(st := self.hass.states.get(eid))]
        if states and all(st.state == STATE_OFF for st in states):  # type: ignore[union-attr]
            return {"code": "device_off"}
        return {"code": "tolerance"}

    def diagnostics(self) -> dict[str, Any]:
        """Diagnostics for this room."""
        return {
            "id": self.id,
            "config": self.config,
            "rule": self.rule,
            "decision": self.decision.as_dict() if self.decision else None,
            "current_temperature": self.current_temp,
            "target_temperature": self.target_temperature,
            "heat_demand": self.heat_demand,
            "window_open": self.window_open,
            "override": self.override_info(),
            "schedule_error": self.schedule_error,
            "schedule_state": (
                {
                    "preset": self.schedule_state.preset,
                    "profile": self.schedule_state.profile,
                    "next_change": iso(self.schedule_state.next_change),
                    "next_preset": self.schedule_state.next_preset,
                }
                if self.schedule_state
                else None
            ),
            "levels": {p: self.level_temp(p) for p in PRESETS},
            "learned_heating": {
                "fixed_minutes": self.learner.model.fixed,
                "minutes_per_degree_at_0": self.learner.model.per_degree,
                "per_outdoor_degree": self.learner.model.per_outdoor,
                "uses_fixed": self.learner.model.uses_fixed,
                "uses_outdoor": self.learner.model.uses_outdoor,
                "episodes": len(self.learner.episodes),
            },
            "cooling_coefficient": self.cooling.coefficient,
            "runtime_hours": round(self.runtime_s / 3600, 2),
            "decisions": list(self.decisions),
        }

    @property
    def domain(self) -> str:
        """Integration domain."""
        return DOMAIN
