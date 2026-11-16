// Constants of the card and the panel.

// Decisions that last only a while: the planned part of the chart shows the schedule.
export const TEMPORARY_RULES = ["window_open", "frost_protection", "valve_exercise"];

// Decisions that hold until something changes: the plan keeps them.
export const FLAT_RULES = [
  "mode_off", "summer", "out_of_season", "pause", "presence_far", "presence_nearby",
  "sensor_fallback", "outdoor_cutoff", "vacation", "house_away",
];

// A target that is only a temperature (no level): neutral.
export const TEMP_COLOR = "var(--ac-fixed)";

// Alerts that mean something does not work (red); the others are warnings (amber).
export const ALERT_ERRORS = [
  "source_unavailable",
  "circuit_unavailable",
  "device_unavailable",
  "sensor_unavailable",
  "not_accepted",
  "schedule_invalid",
  "outdoor_unavailable",
  "preset_missing",
];

export const PRESET_COLORS = {
  comfort: "#d9480f",
  home: "#f08c00",
  activity: "#e0a030",
  eco: "#2f9e8f",
  sleep: "#5f6fd1",
  away: "#8a96a3",
  frost: "#74a9cf",
};

export const DEFAULTS = {
  show_house: true,
  show_rooms: true,
  show_timeline: true,
  show_quick_override: true,
  show_levels: true,
  show_details: true,
  show_schedule_editor: true,
  collapsed: false,
  compact: false,
  runtime_period: "day",
};

export const RUNTIME_PERIODS = ["day", "week", "month"];
