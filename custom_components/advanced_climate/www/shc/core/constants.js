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

// From warm to cold, by what each level is for; none of them the colour of the
// heat (the flame, --ac-hot) nor of the alerts (amber, red).
export const PRESET_COLORS = {
  comfort: "#c2255c",
  home: "#f2a900",
  activity: "#74b816",
  eco: "#2f9e8f",
  sleep: "#5f6fd1",
  away: "#8a96a3",
  frost: "#74a9cf",
};

export const DEFAULTS = {
  show_title: true,
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

// A request of the card or the panel that has not answered after this long (the
// time its data is kept) is asked again: a connection that died without a word
// would otherwise keep it waiting for good.
export const ANSWER_WAIT_MS = 5 * 60e3;

/** A cached answer to ask for again: none yet, older than ``ms``, or still waiting after ANSWER_WAIT_MS. */
export function stale(entry, ms) {
  if (!entry) return true;
  return Date.now() - entry.at > (entry.loading ? ANSWER_WAIT_MS : ms);
}
