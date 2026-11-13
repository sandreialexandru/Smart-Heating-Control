"""Room controller: decides and commands one heating zone."""

from __future__ import annotations

import logging
from collections import deque
from collections.abc import Callable
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigSubentry
from homeassistant.const import (
    ATTR_TEMPERATURE,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import Event, EventStateChangedData, State, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import (
    area_registry as ar,
)
from homeassistant.helpers import (
    entity_registry as er,
)
from homeassistant.helpers.event import async_call_later, async_track_state_change_event
from homeassistant.util import dt as dt_util

from .const import (
    COMMAND_HVAC,
    COMMAND_PRESET,
    COMMAND_TEMPERATURE,
    CONF_AREA,
    CONF_BOILER_ENTITY,
    CONF_CIRCUIT,
    CONF_CLIMATES,
    CONF_COMMAND_MODE,
    CONF_FROST_TEMP,
    CONF_HELPER_OFF_PRESET,
    CONF_HELPER_ON_PRESET,
    CONF_HYSTERESIS,
    CONF_LEVELS,
    CONF_LINKED_WINDOW_SENSORS,
    CONF_MAX_TEMP,
    CONF_NEARBY_LIMIT,
    CONF_NEARBY_MODE,
    CONF_NEARBY_TEMP,
    CONF_OCCUPANCY_MINUTES,
    CONF_OCCUPANCY_RETURN_MINUTES,
    CONF_OCCUPANCY_SENSORS,
    CONF_OPTIMAL_START,
    CONF_OPTIMAL_START_MAX,
    CONF_OPTIMAL_STOP,
    CONF_OPTIMAL_STOP_MINUTES,
    CONF_PRESET_MAP,
    CONF_PRESET_NAMES,
    CONF_PROFILE_DAYS,
    CONF_SCHEDULE,
    CONF_SCHEDULE_HELPER,
    CONF_SCHEDULE_SOURCE,
    CONF_SOLAR_OFFSET,
    CONF_SOURCE,
    CONF_STARTS_HOUSE_SOURCE,
    CONF_SWITCHES,
    CONF_TEMP_AGGREGATION,
    CONF_TEMP_SENSORS,
    CONF_TOP_UP,
    CONF_TRV_BOOST,
    CONF_USE_HOUSE_SOURCE,
    CONF_VALVE_DAY,
    CONF_VALVE_EXERCISE,
    CONF_VALVE_TIME,
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
    MODE_AUTO,
    MODE_AWAY,
    MODE_OFF,
    MODE_SUMMER,
    MODE_VACATION,
    OCCUPANCY_RETURN_MAX,
    PRESET_FROST,
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
    SCHEDULE_HELPER,
    SOURCE_CLIMATE,
    SOURCE_GT,
    SOURCE_SWITCH,
    VALVE_EXERCISE_SECONDS,
    WEEKDAYS,
)
from .device_echo import DeviceLimits, SentValues
from .engine import (
    KIND_NONE,
    KIND_OFF,
    KIND_PRESET,
    KIND_TEMPERATURE,
    Decision,
    RoomInputs,
    Target,
    decide,
    optimal_schedule,
    optimal_stop_state,
)
from .learning import ThermalLearner
from .room_alerts import RoomAlerts
from .room_common import (
    DEVICE_LIMIT_KEEP,
    SENT_RECENT,
    SENT_STABLE,
)
from .room_devices import RoomDevices
from .room_optimal import RoomOptimal
from .room_override import RoomOverride
from .room_status import RoomStatus
from .schedule import (
    Schedule,
    ScheduleError,
    ScheduleState,
    Slot,
    overlap,
    parse_schedule,
)
from .trend import TemperatureTrend
from .util import (
    aggregate,
    as_list,
    climate_temp,
    finite,
    from_iso,
    iso,
    parse_clock,
    system_unit,
    temp_state,
    to_celsius,
    valid,
)
from .window import TemperatureDrop, WindowState

if TYPE_CHECKING:
    from .house import House

_LOGGER = logging.getLogger(__name__)


class Room(RoomDevices, RoomOverride, RoomOptimal, RoomAlerts, RoomStatus):
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
            # A name that is the key of another level (e.g. Eco named "home", or a
            # device preset "comfort" used for home) never takes that key over:
            # the schedule keeps the keys, so it would read the wrong level.
            if name.lower() in PRESETS or name.lower() == PRESET_FROST:
                continue
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
        # The thermal model of the room (heating, heat loss and inertia).
        self.learner = ThermalLearner.from_dict(stored.get("thermal"))
        self.runtime_s = float(stored.get("runtime_s", 0.0))
        self.observed_temps: dict[str, float] = {
            str(k): float(v) for k, v in (stored.get("observed_temps") or {}).items()
        }
        self.decisions: deque[dict[str, Any]] = deque(
            stored.get("decisions", []), maxlen=MAX_DECISION_LOG
        )
        self.last_exercise: str | None = stored.get("last_exercise")
        # The profile chosen last from its select (shown while it is on).
        self.chosen_profile: str | None = stored.get("chosen_profile")

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
        # The window state after the delays, and a quick drop of the temperature.
        self.window = WindowState()
        self.temp_drop = TemperatureDrop()
        # Warming or cooling now (the arrow of the card).
        self.trend = TemperatureTrend()
        self._window_timer: Callable[[], None] | None = None
        self._last_occupied: datetime | None = None
        # Since when someone is present in a room that is in eco for no occupancy.
        self._present_since: datetime | None = None
        self._occupancy_wakeup: datetime | None = None
        self._started_at = dt_util.utcnow()
        self._exercise_until: datetime | None = None
        self._relay_on: bool | None = None
        # An on / off TRV turned on only to be kept open for the heat source.
        self._relay_held = False
        # Just topped up (the heat source stopped before the target): a TRV
        # still heating inside the hysteresis does not ask for heat (it would
        # start the boiler again at once), until the room leaves the band.
        self._top_up_settle = False
        # Kept over a restart: the minimum on / off time of the relay holds.
        self._relay_changed: datetime | None = from_iso(stored.get("relay_changed"))
        self._heating_since: datetime | None = None
        self._unsubs: list[Callable[[], None]] = []
        self._verify_unsub: Callable[[], None] | None = None
        self._stopped = False
        self._verify_attempts = 0
        self._unavailable_since: dict[str, datetime] = {}
        # Temperature sensors told as silent (no report for long).
        self._silent: set[str] = set()
        # Heating without effect: the heating watched now (start, temperature,
        # the model then), and the temperature when it was told.
        self._no_effect_run: dict[str, Any] | None = None
        self._no_effect_told: float | None = None
        # Mold risk: since when the wall surface is humid enough, and its humidity now.
        self._mold_since: datetime | None = None
        self.humidity: float | None = None
        self.surface_humidity: float | None = None
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
        # Stopped early by the learned inertia: the temperature it still reaches (°C).
        self.inertia_stop: float | None = None
        self._inertia_peak: float | None = None
        # When the minimum on / off time of the relay ends (while it waits).
        self._relay_wait_until: datetime | None = None
        # The values sent to each device: a device that reports them later (a
        # sleepy Zigbee TRV), or reports an older one once more, is not a person.
        self.sent = SentValues(SENT_RECENT, SENT_STABLE)
        # Limits a thermostat applies on the device itself, below its entity range
        # (e.g. "Max temperature" 25 on a Tuya TRV whose entity goes to 35).
        self.limits = DeviceLimits(DEVICE_LIMIT_KEEP)

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------
    def apply_schedule(self, text: str, profile_days: dict | None = None) -> None:
        """Use a new schedule (and the days of its profiles) without reloading."""
        self.config[CONF_SCHEDULE] = text
        self.config[CONF_PROFILE_DAYS] = profile_days
        self.schedule_error = None
        self.schedule = self._build_schedule(text)

    async def async_activate_profile(self, name: str) -> None:
        """Turn a profile on, as in the card: the active ones of the same days go off."""
        if name not in self.schedule.profile_names:
            raise HomeAssistantError(f"Unknown profile {name}")
        self.activate_profiles([name])

    def activate_profiles(self, names: list[str]) -> None:
        """Turn profiles on (see ``_activate_profiles``); one profile is noted as chosen.

        The profile select shows the one chosen while it stays on, also on the
        days it does not cover; several (a scenario) leave it to today's profile.
        """
        self.chosen_profile = names[0] if len(names) == 1 else None
        self.house.async_save()
        self._activate_profiles(names)

    def _activate_profiles(self, names: list[str]) -> None:
        """Turn profiles on; the active ones sharing days with them go off.

        Saved in the room like the days chosen in the card (the update listener
        applies them without a reload). The profiles must not share days among
        themselves (the scenarios check it).
        """
        days = {n: dict(item) for n, item in self.schedule.profile_days.items()}
        for name in names:
            chosen = days[name]["days"]
            for other, item in days.items():
                if other not in names and item["enabled"] and overlap(chosen, item["days"]):
                    item["enabled"] = False
            days[name]["enabled"] = True
        if days == self.schedule.profile_days:
            self.house.async_notify_listeners()
            return
        entry = self.house.entry
        subentry = entry.subentries[self.id]
        self.hass.config_entries.async_update_subentry(
            entry, subentry, data={**subentry.data, CONF_PROFILE_DAYS: days}
        )

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
        # A command still being sent does not plan new timers afterwards.
        self._stopped = True
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
            "thermal": self.learner.as_dict(),
            "runtime_s": round(self.runtime_s, 1),
            "observed_temps": self.observed_temps,
            "decisions": list(self.decisions),
            "last_exercise": self.last_exercise,
            "chosen_profile": self.chosen_profile,
            "relay_changed": iso(self._relay_changed),
        }

    # ------------------------------------------------------------------
    # Properties used by entities
    # ------------------------------------------------------------------
    @property
    def window_open(self) -> bool:
        """The window counts as open (after the delays)."""
        return self.window.open

    @window_open.setter
    def window_open(self, value: bool) -> None:
        self.window.open = value

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
        """Highest temperature the thermostats accept (valve exercise, boost).

        Their entity range, or the lower maximum a device showed it applies.
        """
        values = [
            v
            for entity_id in self.climates
            if (v := climate_temp(self.hass, self.hass.states.get(entity_id), "max_temp"))
            is not None
        ]
        learned = self._learned_max()
        if learned is not None:
            values.append(learned)
        return min(values) if values else None

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------
    def _device_changed(self, entity_id: str, new: State | None) -> None:
        """A device changed, not by the integration: a manual change, except in a pause.

        In a pause something else controls the heating (a heat pump making hot
        water, an automation, a person by hand): what it leaves on the devices
        is no choice for after the pause. Its values are not ours any more, so
        the decision is sent again when the pause ends.
        """
        if self.house.paused:
            self.sent.forget(entity_id)
            return
        self._handle_manual_change(entity_id, new)

    @callback
    def _async_entity_changed(self, event: Event[EventStateChangedData]) -> None:
        """A room entity changed: detect manual changes and evaluate again."""
        entity_id = event.data["entity_id"]
        old: State | None = event.data["old_state"]
        new: State | None = event.data["new_state"]
        now = dt_util.utcnow()
        if entity_id in self.climates:
            self._remember_preset_temp(new)
            if self._check_device_limit(entity_id, old, new):
                pass  # its own limit, not a person
            elif self._is_manual_change(event, old, new):
                self._device_changed(entity_id, new)
            else:
                self.sent.confirm(entity_id, new, now)
        elif entity_id in self.switches:
            if (
                old is not None
                and new is not None
                and valid(old)
                and valid(new)
                and old.state != new.state
                and not self.house.is_own_context(event.context)
                and not self.sent.is_echo(entity_id, old, new, now)
            ):
                self._device_changed(entity_id, new)
        if entity_id in as_list(self.config.get(CONF_TEMP_SENSORS)) or entity_id in self.climates:
            self._update_temperature(now)
        self._update_window(now)
        self.house.async_request_evaluate()

    def reset_learning(self) -> None:
        """Forget the learned thermal model (it is learned again from now)."""
        self.learner.reset()
        self.house.async_save()

    # ------------------------------------------------------------------
    # Inputs
    # ------------------------------------------------------------------
    def _update_temperature(self, now: datetime) -> None:
        """Room temperature from the sensors, else from the thermostats."""
        sensors = as_list(self.config.get(CONF_TEMP_SENSORS))
        values = []
        reporting = []
        for entity_id in sensors:
            # A sensor told silent (no report for long) holds an old value: it is
            # left out until it reports again, like an unavailable one.
            if self._left_out(entity_id, now):
                continue
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
        needs_temp = self.source == SOURCE_SWITCH or self.command_mode == COMMAND_HVAC or self.boost
        self.sensor_failed = self.current_temp is None and (bool(sensors) or needs_temp)
        # A quick drop of the temperature counts as an open window (a change of
        # the sensors that give it is not a drop).
        sources = tuple(reporting) if external is not None else ("device", *device_reporting)
        self.temp_drop.update(
            now,
            sources,
            self.current_temp,
            enabled=bool(self.config[CONF_WINDOW_DROP_DETECT]),
            minutes=float(self.config[CONF_WINDOW_DROP_MINUTES]),
            degrees=float(self.config[CONF_WINDOW_DROP_DEGREES]),
        )
        self.trend.update(now, sources, self.current_temp)

    def external_temperature(self) -> float | None:
        """Aggregated external sensors only."""
        values = [
            v
            for entity_id in as_list(self.config.get(CONF_TEMP_SENSORS))
            if not self._left_out(entity_id, dt_util.utcnow())
            and (v := temp_state(self.hass, entity_id, self.house.unit)) is not None
        ]
        return aggregate(values, self.config[CONF_TEMP_AGGREGATION])

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
        return self.temp_drop.active(now)

    def _update_window(self, now: datetime) -> None:
        """Debounce the window state with the open / close delays."""
        raw = self._window_raw(now)
        due, closed = self.window.update(
            now,
            raw,
            timedelta(seconds=float(self.config[CONF_WINDOW_OPEN_DELAY])),
            timedelta(seconds=float(self.config[CONF_WINDOW_CLOSE_DELAY])),
        )
        if closed:
            self.house.clear_alert(f"window_{self.id}")
        until = self.temp_drop.until
        if until is not None and now < until:
            due = min(due, until) if due else until
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

            if not self._stopped:
                self._window_timer = async_call_later(self.hass, delay, _recheck)

    def _room_unoccupied(self, now: datetime) -> bool:
        """True when the room counts as empty (eco for no occupancy).

        Empty after the occupancy sensors were off for *Eco after no occupancy
        for*; occupied again after someone was present without a break for
        *Back from eco after presence of* (0 = at once). A presence that ends
        sooner leaves the room in eco and the count starts again.
        """
        self._occupancy_wakeup = None
        sensors = as_list(self.config.get(CONF_OCCUPANCY_SENSORS))
        if not sensors:
            self._present_since = None
            return False
        since = self._last_occupied or self._started_at
        empty = now - since >= timedelta(minutes=float(self.config[CONF_OCCUPANCY_MINUTES]))
        present = any(
            (st := self.hass.states.get(eid)) is not None and st.state == STATE_ON
            for eid in sensors
        )
        if not present:
            self._present_since = None
            if not empty:
                self._occupancy_wakeup = since + timedelta(
                    minutes=float(self.config[CONF_OCCUPANCY_MINUTES])
                )
            return empty
        back = timedelta(
            minutes=min(
                float(self.config.get(CONF_OCCUPANCY_RETURN_MINUTES, 0) or 0),
                OCCUPANCY_RETURN_MAX,
            )
        )
        if empty and back > timedelta(0):
            self._present_since = self._present_since or now
            if now - self._present_since < back:
                self._occupancy_wakeup = self._present_since + back
                return True
        self._present_since = None
        self._last_occupied = now
        return False

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
        """Decide and apply.

        The steps, in order: read the room, follow the schedule (with the
        optimal start / stop), decide, command the devices, learn, check the
        alerts and plan the next look.
        """
        self._update_temperature(now)
        self._update_window(now)
        self._account_runtime(now)

        state = self._schedule_lookup(now)
        self.schedule_state = state
        preset, schedule_rule = self._schedule_preset(now, state)
        inputs = self._inputs(now, state, preset, schedule_rule)
        decision = decide(inputs)
        self._note_decision(decision)
        self._record(decision, now)
        topped = self.topped_up
        self.decision = decision
        if topped and not self.topped_up:
            self._top_up_settle = True
        # Kept open for the heat source: the target of the room stays the one
        # of its rule (the TRVs only are opened further).
        self.target_temperature = (
            decision.params.get("temperature")
            if self.opened_for_source
            else self._resolve_temperature(decision.target)
        )

        await self._async_apply(decision.target)
        await self._async_calibrate(now)
        self._update_demand()
        self._learn(now)
        self._check_alerts(now)
        self.next_wakeup = self._next_wakeup(now, state)

    def _schedule_preset(
        self, now: datetime, state: ScheduleState | None
    ) -> tuple[str | None, str]:
        """The level the schedule (or the calendar) asks for now, and its rule.

        The optimal start / stop may take the next level early; what they work
        out is kept in ``next_estimate`` for the card and the next wakeup.
        """
        house = self.house
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
        return preset, schedule_rule

    def _inputs(
        self, now: datetime, state: ScheduleState | None, preset: str | None, schedule_rule: str
    ) -> RoomInputs:
        """What the decision needs: the house, the room and the schedule now.

        Also notes what the decision depends on (``signature``): a manual change
        lasts until it changes (see ``_check_override``).
        """
        house = self.house
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

        return RoomInputs(
            now=now,
            # Guests win over the vacation and away modes: the rooms follow the schedule.
            mode=MODE_AUTO
            if house.mode in (MODE_VACATION, MODE_AWAY) and house.guest
            else house.mode,
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
            keep_open=house.keep_open_room == self.id,
            keep_open_temp=self._keep_open_temp(),
            top_up=self.id in house.top_up_rooms,
        )

    @property
    def kept_open(self) -> bool:
        """The TRVs are kept open for the heat source (the last room that asked for heat)."""
        return self.decision is not None and self.decision.key == "keep_open"

    @property
    def topped_up(self) -> bool:
        """Heating up to its target while the heat source runs for other rooms."""
        return self.decision is not None and self.decision.key == "top_up"

    @property
    def opened_for_source(self) -> bool:
        """The TRVs or relay are on for the heat source of the house, not for the
        room itself (kept open, or topped up): the room asks for no heat."""
        return self.kept_open or self.topped_up

    @property
    def can_top_up(self) -> bool:
        """The room may be topped up: TRVs or a relay on the heat source of the
        house, with the option on."""
        return (
            bool(self.config.get(CONF_TOP_UP))
            and self.source in (SOURCE_CLIMATE, SOURCE_SWITCH)
            and self.uses_house_source
            and bool(self.house.options.get(CONF_BOILER_ENTITY))
        )

    def _in_top_up_band(self) -> bool:
        """A little below the target: inside the hysteresis, not asking yet."""
        current, target = self.current_temp, self.target_temperature
        if current is None or target is None:
            return False
        return target - float(self.config[CONF_HYSTERESIS]) < current < target

    def top_up_wanted(self, active: bool) -> bool:
        """While the heat source runs: a little below the target (inside the
        hysteresis, so not asking yet), up to the target. Its circuit, if any,
        must be open already (a pump is not started for a few tenths)."""
        # The room kept open now is not topped up; one just released (another
        # room asks) goes on at once, its TRVs not closed in between.
        if not self.can_top_up or self.house.keep_open_room == self.id:
            return False
        if not active and self.heat_demand and not self.kept_open:
            return False
        if self.circuit is not None and self.house.circuit_on(self.circuit) is not True:
            return False
        return self._in_top_up_band()

    @property
    def can_keep_open(self) -> bool:
        """A room with TRVs that heats from the heat source of the house."""
        return self.source == SOURCE_CLIMATE and self.uses_house_source

    @property
    def keep_open_needs_heat(self) -> bool:
        """Kept open, but the room itself is cold enough to ask for heat again."""
        return (
            self.current_temp is not None
            and self.target_temperature is not None
            and self.current_temp <= self.target_temperature - float(self.config[CONF_HYSTERESIS])
        )

    def _keep_open_temp(self) -> float:
        """What the TRVs get while kept open: the maximum of the room, within theirs."""
        value = self.max_temp()
        device_max = self.device_max_temp()
        return value if device_max is None else min(value, device_max)

    def _note_decision(self, decision: Decision) -> None:
        """What a decision means for a manual change and the optimal stop."""
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

    def _learn(self, now: datetime) -> None:
        """Learn how fast the room heats and cools (in the cold season only)."""
        house = self.house
        # Not in mode Off or Summer, nor outside the heating season.
        if house.season_active and house.mode not in (MODE_OFF, MODE_SUMMER):
            outdoor = house.outdoor_now
            # An episode is not used with a window open, when the outdoor
            # temperature of a house that has one became unknown, when the
            # state of the heat source is unknown, or during the valve exercise.
            # Nor while the TRVs are kept open for the heat source (the leftover
            # heat would look like a room that cools slowly).
            disturbed = (
                self._window_sensor_open()
                or (house.outdoor_configured and outdoor is None)
                or self.source_unknown
                or self._exercise_until is not None
                or self.opened_for_source
            )
            self.learner.observe(
                now,
                self.heating,
                self.current_temp,
                outdoor,
                disturbed,
                house.outdoor_configured,
                house.sun_now,
            )
        else:
            self.learner.cancel()

    def _next_wakeup(self, now: datetime, state: ScheduleState | None) -> datetime | None:
        """When to look again: the next change of the schedule, an end, a start."""
        wakeups = []
        if state and state.next_change:
            wakeups.append(state.next_change)
        if self.override and self.override.get("until"):
            wakeups.append(self.override["until"])
        if self._exercise_until:
            wakeups.append(self._exercise_until)
        # The room becomes empty, or occupied again after the presence time.
        if self._occupancy_wakeup is not None and self._occupancy_wakeup > now:
            wakeups.append(self._occupancy_wakeup)
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
        return min(wakeups) if wakeups else None

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

    @property
    def uses_house_source(self) -> bool:
        """True when the room heats from the heat source of the house (the default)."""
        # The default is never used (the config has every key): not mutated.
        return bool(self.config.get(CONF_USE_HOUSE_SOURCE, True))  # pragma: no mutate

    @property
    def circuit(self) -> str | None:
        """The relay of the heating circuit of the room (a circuit of the house), if any."""
        circuit = self.config.get(CONF_CIRCUIT)
        if not circuit or not self.uses_house_source:
            return None
        return circuit if circuit in self.house.circuits else None

    @property
    def starts_house_source(self) -> bool:
        """A room of the heat source that may start it (off: a secondary room).

        Secondary only in a house with a heat source (the form asks only then)
        and never the whole-house zone (the only room of the house).
        """
        if not self.uses_house_source:
            return False
        secondary = (
            not self.config.get(CONF_STARTS_HOUSE_SOURCE, True)  # pragma: no mutate
            and bool(self.house.options.get(CONF_BOILER_ENTITY))
            and not self.is_whole_house
        )
        return not secondary

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
        if self._exercise_until is not None or self.opened_for_source:
            # The valves are exercised, or kept open or topped up for the heat
            # source: no heat is asked for.
            pass
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
            if self._top_up_settle:
                if self._in_top_up_band():
                    demand = False
                else:
                    self._top_up_settle = False
            # Frost protection from the room sensor (the TRVs are boosted for it).
            demand = demand or self._boost_demand
        self.heat_demand = demand
        # The room heats only while its heat source runs: its own device (GT,
        # relay, on / off thermostat) and, when one is set, the heat source of
        # the house (the boiler that TRVs and zone valves wait for).
        configured, source_on = self.house.heat_source_state()
        configured = configured and self.uses_house_source
        self.source_unknown = configured and source_on is None
        heating = demand and (not configured or bool(source_on))
        # On a circuit: only while its relay is on too (the pump or valve).
        if heating and self.circuit is not None:
            heating = self.house.circuit_on(self.circuit) is True
        now = dt_util.utcnow()
        # The two checks below overlap with _account_runtime (each evaluation): their
        # mutants change nothing visible.
        if heating and self._heating_since is None:  # pragma: no mutate
            self._heating_since = now
        if not heating and self._heating_since is not None:  # pragma: no mutate
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

    @property
    def domain(self) -> str:
        """Integration domain."""
        return DOMAIN
