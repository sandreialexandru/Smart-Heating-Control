"""Constants for the Smart Heating Control integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "advanced_climate"
SUBENTRY_ROOM: Final = "room"

STORAGE_VERSION: Final = 1
SIGNAL_UPDATE: Final = f"{DOMAIN}_update_{{}}"
EVENT_DECISION_CHANGED: Final = f"{DOMAIN}_decision_changed"

CARD_URL: Final = f"/{DOMAIN}/smart-heating-control-card.js"
# The card URL before the rename: not served; a dashboard resource with it is
# moved to CARD_URL.
LEGACY_CARD_URL: Final = f"/{DOMAIN}/advanced-climate-card.js"

# ---------------------------------------------------------------------------
# Presets (same names as Generic Thermostat)
# ---------------------------------------------------------------------------
PRESET_HOME: Final = "home"
PRESET_SLEEP: Final = "sleep"
PRESET_ECO: Final = "eco"
PRESET_AWAY: Final = "away"
PRESET_COMFORT: Final = "comfort"
PRESET_ACTIVITY: Final = "activity"
PRESET_NONE: Final = "none"
# Not a level of the device: the schedule has no active profile for the day,
# so the room keeps its frost protection.
PRESET_FROST: Final = "frost"

PRESETS: Final = (
    PRESET_HOME,
    PRESET_SLEEP,
    PRESET_ECO,
    PRESET_AWAY,
    PRESET_COMFORT,
    PRESET_ACTIVITY,
)

DEFAULT_LEVEL_TEMPS: Final = {
    PRESET_HOME: 21.0,
    PRESET_SLEEP: 18.0,
    PRESET_ECO: 17.0,
    PRESET_AWAY: 12.0,
    PRESET_COMFORT: 22.0,
    PRESET_ACTIVITY: 20.0,
}

# ---------------------------------------------------------------------------
# Presence
# ---------------------------------------------------------------------------
PRESENCE_HOME: Final = "home"
PRESENCE_NEARBY: Final = "nearby"
PRESENCE_FAR: Final = "far"
PRESENCE_STATES: Final = (PRESENCE_HOME, PRESENCE_NEARBY, PRESENCE_FAR)

HOME_RULE_ANY: Final = "any"
HOME_RULE_ALL: Final = "all"

# ---------------------------------------------------------------------------
# Global modes
# ---------------------------------------------------------------------------
MODE_AUTO: Final = "auto"
MODE_VACATION: Final = "vacation"
MODE_OFF: Final = "off"
MODE_SUMMER: Final = "summer"
MODES: Final = (MODE_AUTO, MODE_VACATION, MODE_OFF, MODE_SUMMER)

# ---------------------------------------------------------------------------
# Decision rules (state of the decision sensor)
# ---------------------------------------------------------------------------
RULE_STARTING: Final = "starting"
RULE_SAFETY: Final = "frost_protection"
RULE_MAX: Final = "maximum_temperature"
RULE_PAUSE: Final = "pause"
RULE_MODE_OFF: Final = "mode_off"
RULE_SUMMER: Final = "summer"
RULE_OUT_OF_SEASON: Final = "out_of_season"
RULE_VALVE_EXERCISE: Final = "valve_exercise"
RULE_WINDOW: Final = "window_open"
RULE_OVERRIDE: Final = "manual_override"
RULE_VACATION: Final = "vacation"
RULE_FAR: Final = "presence_far"
RULE_NEARBY: Final = "presence_nearby"
RULE_UNOCCUPIED: Final = "room_unoccupied"
RULE_SENSOR_FALLBACK: Final = "sensor_fallback"
RULE_SCHEDULE: Final = "schedule"
RULE_OPTIMAL_START: Final = "optimal_start"
RULE_OPTIMAL_STOP: Final = "optimal_stop"
RULE_CUTOFF: Final = "outdoor_cutoff"

RULES: Final = (
    RULE_STARTING,
    RULE_SAFETY,
    RULE_MAX,
    RULE_PAUSE,
    RULE_MODE_OFF,
    RULE_SUMMER,
    RULE_OUT_OF_SEASON,
    RULE_VALVE_EXERCISE,
    RULE_WINDOW,
    RULE_OVERRIDE,
    RULE_VACATION,
    RULE_FAR,
    RULE_NEARBY,
    RULE_UNOCCUPIED,
    RULE_SENSOR_FALLBACK,
    RULE_SCHEDULE,
    RULE_OPTIMAL_START,
    RULE_OPTIMAL_STOP,
    RULE_CUTOFF,
)

# ---------------------------------------------------------------------------
# House (main config entry) options
# ---------------------------------------------------------------------------
CONF_PERSONS: Final = "persons"
CONF_HOME_RULE: Final = "home_rule"
CONF_NEARBY_ZONES: Final = "nearby_zones"
CONF_NEARBY_GEOMETRIC: Final = "nearby_geometric"
CONF_DEPARTURE_DELAY: Final = "departure_delay"
CONF_ARRIVAL_DELAY: Final = "arrival_delay"
CONF_PRESENCE_SENSORS: Final = "presence_sensors"
CONF_GUEST_EXPIRE_HOURS: Final = "guest_expire_hours"
CONF_PROXIMITY_DISTANCE: Final = "proximity_distance"
CONF_PROXIMITY_DIRECTION: Final = "proximity_direction"
CONF_TRAVEL_TIME: Final = "travel_time"
CONF_ARRIVAL_DISTANCE: Final = "arrival_distance"
CONF_ARRIVAL_MINUTES: Final = "arrival_minutes"

CONF_WORKDAY_SENSOR: Final = "workday_sensor"
CONF_CALENDAR: Final = "calendar"
CONF_DAY_BOUNDARY: Final = "day_boundary"

CONF_OUTDOOR_SENSOR: Final = "outdoor_sensor"
CONF_WEATHER: Final = "weather"
CONF_CUTOFF_ENABLED: Final = "cutoff_enabled"
CONF_CUTOFF_TEMP: Final = "cutoff_temp"
CONF_CUTOFF_HYSTERESIS: Final = "cutoff_hysteresis"
CONF_CUTOFF_AVG_HOURS: Final = "cutoff_avg_hours"
CONF_SEASON_MODE: Final = "season_mode"
CONF_SEASON_START: Final = "season_start"
CONF_SEASON_END: Final = "season_end"
CONF_SEASON_DAYS: Final = "season_days"
CONF_SEASON_TEMP: Final = "season_temp"
CONF_COMP_ENABLED: Final = "compensation_enabled"
CONF_COMP_BELOW: Final = "compensation_below"
CONF_COMP_OFFSET: Final = "compensation_offset"
CONF_FORECAST_ENABLED: Final = "forecast_enabled"
CONF_FORECAST_HOURS: Final = "forecast_hours"
CONF_WINDOW_IGNORE_ABOVE: Final = "window_ignore_above"

CONF_PRICE_SENSOR: Final = "price_sensor"
CONF_PRICE_HIGH: Final = "price_high"
CONF_PRICE_HIGH_OFFSET: Final = "price_high_offset"
CONF_PRICE_LOW: Final = "price_low"
CONF_PRICE_LOW_OFFSET: Final = "price_low_offset"
CONF_PV_SENSOR: Final = "pv_sensor"
CONF_PV_THRESHOLD: Final = "pv_threshold"
CONF_PV_OFFSET: Final = "pv_offset"

CONF_BOILER_ENTITY: Final = "boiler_entity"
CONF_BOILER_MIN_ROOMS: Final = "boiler_min_rooms"
CONF_REFERENCE_ROOM: Final = "reference_room"
CONF_BOILER_MIN_ON: Final = "boiler_min_on"
CONF_BOILER_MIN_OFF: Final = "boiler_min_off"
CONF_ROOM_DIFF_ALERT: Final = "room_diff_alert"

CONF_OVERRIDE_MODE: Final = "override_mode"
CONF_OVERRIDE_HOURS: Final = "override_hours"
# Limits of a fixed duration of a manual change (form and services), hours.
OVERRIDE_HOURS_MIN: Final = 0.25
OVERRIDE_HOURS_MAX: Final = 72.0
CONF_OVERRIDE_SCOPE: Final = "override_scope"
CONF_REEVAL_MINUTES: Final = "reevaluation_minutes"
CONF_VACATION_PREHEAT: Final = "vacation_preheat_hours"
CONF_AUTO_VACATION_HOURS: Final = "auto_vacation_hours"

CONF_NOTIFY_SERVICE: Final = "notify_service"
CONF_ALERT_WINDOW_MINUTES: Final = "alert_window_minutes"
CONF_ALERT_UNAVAILABLE_MINUTES: Final = "alert_unavailable_minutes"
CONF_BATTERY_THRESHOLD: Final = "battery_threshold"
CONF_VERIFY_COMMANDS: Final = "verify_commands"

CONF_FROST_TEMP: Final = "frost_temp"
CONF_MAX_TEMP: Final = "max_temp"

OVERRIDE_FIXED: Final = "fixed"
OVERRIDE_NEXT: Final = "until_next_reevaluation"
OVERRIDE_SCOPE_ROOM: Final = "room"
OVERRIDE_SCOPE_HOUSE: Final = "house"

SEASON_ALWAYS: Final = "always"
SEASON_DATES: Final = "dates"
SEASON_AUTO: Final = "auto"

HOUSE_DEFAULTS: Final = {
    CONF_PERSONS: [],
    CONF_HOME_RULE: HOME_RULE_ANY,
    CONF_NEARBY_ZONES: [],
    CONF_NEARBY_GEOMETRIC: True,
    CONF_DEPARTURE_DELAY: 10,
    CONF_ARRIVAL_DELAY: 0,
    CONF_PRESENCE_SENSORS: [],
    CONF_GUEST_EXPIRE_HOURS: 0,
    CONF_ARRIVAL_DISTANCE: 10.0,
    CONF_ARRIVAL_MINUTES: 20,
    CONF_DAY_BOUNDARY: "00:00:00",
    CONF_CUTOFF_ENABLED: False,
    CONF_CUTOFF_TEMP: 18.0,
    CONF_CUTOFF_HYSTERESIS: 1.0,
    CONF_CUTOFF_AVG_HOURS: 6,
    CONF_SEASON_MODE: SEASON_ALWAYS,
    CONF_SEASON_START: "10-15",
    CONF_SEASON_END: "04-15",
    CONF_SEASON_DAYS: 3,
    CONF_SEASON_TEMP: 15.0,
    CONF_COMP_ENABLED: False,
    CONF_COMP_BELOW: -5.0,
    CONF_COMP_OFFSET: 0.5,
    CONF_FORECAST_ENABLED: False,
    CONF_FORECAST_HOURS: 3,
    CONF_PRICE_HIGH_OFFSET: -1.0,
    CONF_PRICE_LOW_OFFSET: 0.5,
    CONF_PV_THRESHOLD: 1000.0,
    CONF_PV_OFFSET: 0.5,
    CONF_BOILER_MIN_ROOMS: 1,
    CONF_BOILER_MIN_ON: 5,
    CONF_BOILER_MIN_OFF: 5,
    CONF_ROOM_DIFF_ALERT: 0.0,
    CONF_OVERRIDE_MODE: OVERRIDE_FIXED,
    CONF_OVERRIDE_HOURS: 2.0,
    CONF_OVERRIDE_SCOPE: OVERRIDE_SCOPE_ROOM,
    CONF_REEVAL_MINUTES: 5,
    CONF_VACATION_PREHEAT: 4.0,
    CONF_AUTO_VACATION_HOURS: 0.0,
    CONF_ALERT_WINDOW_MINUTES: 30,
    CONF_ALERT_UNAVAILABLE_MINUTES: 15,
    CONF_BATTERY_THRESHOLD: 20,
    CONF_VERIFY_COMMANDS: True,
    CONF_FROST_TEMP: 7.0,
    CONF_MAX_TEMP: 25.0,
}

# ---------------------------------------------------------------------------
# Room (subentry) data
# ---------------------------------------------------------------------------
CONF_AREA: Final = "area"
CONF_SOURCE: Final = "source"
CONF_CLIMATES: Final = "climates"
CONF_SWITCHES: Final = "switches"
CONF_COMMAND_MODE: Final = "command_mode"
CONF_PRESET_NAMES: Final = "preset_names"
CONF_TEMP_UNIT: Final = "temperature_unit"  # house: °C or °F (values are stored in °C)
CONF_PRESET_MAP: Final = "preset_map"  # level role -> device preset (climate + preset command)
CONF_LEVELS: Final = "levels"  # level temperatures chosen in the room flow
CONF_NEARBY_MODE: Final = "nearby_mode"
CONF_NEARBY_TEMP: Final = "nearby_temp"
# Nearby never above the schedule: the lower of the two applies.
CONF_NEARBY_LIMIT: Final = "nearby_not_above_schedule"
CONF_TEMP_SENSORS: Final = "temperature_sensors"
CONF_TEMP_AGGREGATION: Final = "temperature_aggregation"
CONF_CALIBRATION_MODE: Final = "calibration_mode"
CONF_CALIBRATION_ENTITIES: Final = "calibration_entities"
CONF_HYSTERESIS: Final = "hysteresis"
CONF_LEARN_TOLERANCE: Final = "learn_tolerance"  # thermostat tolerance (other thermostats)
# Temperature command: the TRVs get a higher temperature while the room asks for
# heat (decided from the room sensor with the hysteresis), the target otherwise.
CONF_TRV_BOOST: Final = "trv_boost"
CONF_TRV_BOOST_TEMP: Final = "trv_boost_temperature"  # °C; empty = maximum of the house
CONF_STOP_TOLERANCE: Final = "stop_tolerance"  # comfort kept by optimal stop (other thermostats)
CONF_MIN_ON: Final = "min_on_minutes"
CONF_MIN_OFF: Final = "min_off_minutes"
CONF_OCCUPANCY_SENSORS: Final = "occupancy_sensors"
CONF_OCCUPANCY_MINUTES: Final = "occupancy_minutes"
CONF_WINDOW_SENSORS: Final = "window_sensors"
CONF_LINKED_WINDOW_SENSORS: Final = "linked_window_sensors"
CONF_WINDOW_OPEN_DELAY: Final = "window_open_delay"
CONF_WINDOW_CLOSE_DELAY: Final = "window_close_delay"
CONF_WINDOW_ACTION: Final = "window_action"
CONF_WINDOW_DROP_DETECT: Final = "window_drop_detect"
CONF_WINDOW_DROP_DEGREES: Final = "window_drop_degrees"
CONF_WINDOW_DROP_MINUTES: Final = "window_drop_minutes"
CONF_SCHEDULE_SOURCE: Final = "schedule_source"
CONF_SCHEDULE: Final = "schedule"
# Days and on / off of each profile: {name: {"days": ..., "enabled": bool}}.
CONF_PROFILE_DAYS: Final = "profile_days"
DAYS_ALL: Final = "all"
DAYS_WORKDAY: Final = "workday"
DAYS_WEEKEND: Final = "weekend"
CONF_SCHEDULE_HELPER: Final = "schedule_helper"
CONF_HELPER_ON_PRESET: Final = "helper_on_preset"
CONF_HELPER_OFF_PRESET: Final = "helper_off_preset"
CONF_OPTIMAL_START: Final = "optimal_start"
CONF_OPTIMAL_START_MAX: Final = "optimal_start_max_minutes"
CONF_OPTIMAL_STOP: Final = "optimal_stop"
CONF_OPTIMAL_STOP_MINUTES: Final = "optimal_stop_minutes"
CONF_SOLAR_OFFSET: Final = "solar_offset"
CONF_VALVE_EXERCISE: Final = "valve_exercise"
CONF_VALVE_DAY: Final = "valve_exercise_day"
CONF_VALVE_TIME: Final = "valve_exercise_time"

SOURCE_GT: Final = "generic_thermostat"
SOURCE_CLIMATE: Final = "climate"
SOURCE_SWITCH: Final = "switch"

COMMAND_PRESET: Final = "preset"
COMMAND_TEMPERATURE: Final = "temperature"
COMMAND_HVAC: Final = "hvac_mode"

NEARBY_PRESET: Final = "preset"
NEARBY_TEMPERATURE: Final = "temperature"

AGG_MEAN: Final = "mean"
AGG_MIN: Final = "min"
AGG_MEDIAN: Final = "median"

CALIBRATION_OFF: Final = "off"
CALIBRATION_OFFSET: Final = "offset"
CALIBRATION_EXTERNAL: Final = "external"

WINDOW_ACTION_FROST: Final = "frost"
WINDOW_ACTION_OFF: Final = "off"

SCHEDULE_INTERNAL: Final = "internal"
SCHEDULE_HELPER: Final = "helper"

WEEKDAYS: Final = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")

DEFAULT_SCHEDULE: Final = (
    "workday: 00:00 sleep, 06:00 home, 22:00 sleep\nweekend: 00:00 sleep, 08:00 home, 23:00 sleep"
)

ROOM_DEFAULTS: Final = {
    CONF_SOURCE: SOURCE_GT,
    CONF_CLIMATES: [],
    CONF_SWITCHES: [],
    CONF_COMMAND_MODE: COMMAND_PRESET,
    CONF_PRESET_NAMES: {},
    CONF_NEARBY_MODE: NEARBY_PRESET,
    CONF_NEARBY_TEMP: 17.0,
    CONF_NEARBY_LIMIT: False,
    CONF_TEMP_SENSORS: [],
    CONF_TEMP_AGGREGATION: AGG_MEAN,
    CONF_CALIBRATION_MODE: CALIBRATION_OFF,
    CONF_CALIBRATION_ENTITIES: [],
    CONF_HYSTERESIS: 0.3,
    CONF_LEARN_TOLERANCE: 0.0,
    CONF_TRV_BOOST: False,
    CONF_STOP_TOLERANCE: 0.0,
    CONF_MIN_ON: 5,
    CONF_MIN_OFF: 5,
    CONF_OCCUPANCY_SENSORS: [],
    CONF_OCCUPANCY_MINUTES: 30,
    CONF_WINDOW_SENSORS: [],
    CONF_LINKED_WINDOW_SENSORS: [],
    CONF_WINDOW_OPEN_DELAY: 60,
    CONF_WINDOW_CLOSE_DELAY: 30,
    CONF_WINDOW_ACTION: WINDOW_ACTION_FROST,
    CONF_WINDOW_DROP_DETECT: False,
    CONF_WINDOW_DROP_DEGREES: 1.0,
    CONF_WINDOW_DROP_MINUTES: 3,
    CONF_SCHEDULE_SOURCE: SCHEDULE_INTERNAL,
    CONF_SCHEDULE: DEFAULT_SCHEDULE,
    CONF_HELPER_ON_PRESET: PRESET_HOME,
    CONF_HELPER_OFF_PRESET: PRESET_SLEEP,
    CONF_OPTIMAL_START: False,
    CONF_OPTIMAL_START_MAX: 120,
    CONF_OPTIMAL_STOP: False,
    CONF_OPTIMAL_STOP_MINUTES: 30,
    CONF_SOLAR_OFFSET: 0.0,
    CONF_VALVE_EXERCISE: False,
    CONF_VALVE_DAY: "sun",
    CONF_VALVE_TIME: "10:00:00",
}

# Generic Thermostat option keys holding the preset temperatures.
GT_DOMAIN: Final = "generic_thermostat"
GT_PRESET_KEYS: Final = {preset: f"{preset}_temp" for preset in PRESETS}

# Timing
STARTUP_DELAY: Final = 10  # seconds after HA start before the first command
VERIFY_DELAY: Final = 120  # seconds before a command is verified
VALVE_EXERCISE_SECONDS: Final = 300
TEMP_DROP_HOLD_MINUTES: Final = 15
# How long a value sent to a thermostat may still come back late as its report.
SENT_RECENT_MINUTES: Final = 5
# How long the device must show the last value sent before the older ones are forgotten.
SENT_STABLE_SECONDS: Final = 60
# How long a limit learned from a thermostat is kept (then it is tried again).
DEVICE_LIMIT_HOURS: Final = 24
MAX_DECISION_LOG: Final = 100
