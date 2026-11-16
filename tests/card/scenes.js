// The states of the card that compare.js photographs and replays.
//
// A scene mounts the card with a configuration and a fake Home Assistant
// (fixtures.js), then may act on it (open a section, drag a time, hover the
// chart). compare.js photographs it and records the services and the
// websocket messages it sent. Times are relative to the frozen clock of
// compare.js, so every run draws the same.
const H = 3600e3;
const NOW = Date.parse("2026-01-14T10:17:00+02:00");
const at = (ms) => new Date(NOW + ms).toISOString();

const MOLD = { code: "mold_risk", params: { surface: 84, humidity: 62 }, room: "r1", message: "m" };
const UNAVAILABLE = { code: "device_unavailable", params: { entity: "climate.trv", minutes: 15 }, room: "r1", message: "m" };
const OVERRIDE = { temperature: 23, until: at(2 * H), origin: "card", preset: null, applied: true };
const ROOMS = [
  { id: "r1", name: "Bedroom", humidity: 62, wall: 84.4, alerts: [MOLD] },
  { id: "r2", name: "Office", learned: false, source: "climate", climates: ["climate.office"], override: OVERRIDE, state: "manual_override" },
  { id: "r3", name: "Living", window: true, state: "window_open", reasonKey: "window_open", demand: false, heating: false },
  { id: "r4", name: "Kid", current: null, dropAttrs: ["plan", "next_estimate", "levels", "offsets", "alerts", "humidity"], learned: false },
];
const R1 = [{ id: "r1", name: "Bedroom", humidity: 62, wall: 84.4 }];
const DEVICES = {
  devices: ["climate.trv", "switch.valve"],
  extra: [
    ["climate.trv", "heat", { friendly_name: "TRV", temperature: 21, current_temperature: 20.5, hvac_action: "heating", battery: 64 }],
    ["switch.valve", "unavailable", { friendly_name: "Valve" }],
  ],
};
const OPTIMAL = { kind: "optimal_start", at: at(5 * H), preset: "comfort", minutes: 90, starts_at: at(3.5 * H), started_at: null,
  outdoor: 5, outdoor_source: "now", learned: true, sent_as: "temperature", temperature: 22 };

// Actions, run in the page with the card under test.
const click = (sel) => async (p) => {
  await p.evaluate((s) => { const el = card.shadowRoot.querySelector(s); if (!el) throw new Error("no " + s); el.click(); }, sel);
  await p.waitForTimeout(150);
};
const steps = (...fns) => async (p) => { for (const f of fns) await f(p); };
const hoverChart = (fx, fy) => async (p) => {
  const pt = await p.evaluate(([x, y]) => { const r = card.shadowRoot.querySelector(".hchart").getBoundingClientRect(); return [r.left + r.width * x, r.top + r.height * y]; }, [fx, fy]);
  await p.mouse.move(pt[0], pt[1]); await p.waitForTimeout(200);
};
const dragHandle = (index, dx) => async (p) => {
  const pt = await p.evaluate((i) => { const h = card.shadowRoot.querySelectorAll(".handle")[i]; h.scrollIntoView({ block: "center" }); const r = h.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }, index);
  await p.mouse.move(pt[0], pt[1]); await p.mouse.down();
  for (let i = 1; i <= 5; i++) await p.mouse.move(pt[0] + (dx * i) / 5, pt[1]);
  await p.mouse.up(); await p.waitForTimeout(150);
};
const input = (sel, value) => async (p) => {
  await p.evaluate(([s, v]) => { const i = card.shadowRoot.querySelector(s); i.value = v; i.dispatchEvent(new Event("change", { bubbles: true })); }, [sel, value]);
  await p.waitForTimeout(100);
};
const openChart = (room = "r1") => steps(click(`[data-key="chart-${room}"]`), async (p) => p.waitForTimeout(300));
const editSchedule = steps(click('[data-key="sched-r1"]'), click('[data-action="edit"][data-room="r1"]'));

// The form of the card editor in the language of the user, with its labels,
// and the configuration of a new card: kept with the calls, so compared too.
const editorForm = async (p) => {
  await p.evaluate(() => {
    const ha = document.createElement("home-assistant");
    ha.hass = card.hass;
    document.body.appendChild(ha);
    const C = customElements.get("smart-heating-control-card");
    const form = C.getConfigForm();
    window.calls.form = { stub: C.getStubConfig(), schema: form.schema, labels: form.schema.map((f) => form.computeLabel(f)) };
    ha.remove();
  });
};

// name, config of the card, options of the fake Home Assistant, action.
const SCENES = [
  // The house.
  ["house-auto", {}, { rooms: ROOMS }, editorForm],
  ["house-away", {}, { rooms: R1, mode: "away", presence: "away" }],
  ["house-vacation", {}, { rooms: R1, mode: "vacation" }],
  ["house-off", {}, { rooms: R1, mode: "off" }],
  ["house-summer", {}, { rooms: R1, mode: "summer" }],
  ["house-pause", {}, { rooms: R1, pause: true }],
  ["house-guests", {}, { rooms: R1, guest: true }],
  ["house-guests-away", {}, { rooms: R1, guest: true, mode: "away" }],
  ["house-pause-guests-override", {}, { rooms: [{ id: "r1", name: "Bedroom", override: OVERRIDE }], pause: true, guest: true }],
  ["house-source-auto", {}, { rooms: R1, source: { state: "auto", options: ["auto", "primary", "secondary"], active: "primary", switch_at: at(10 * 60e3) } }],
  ["house-source-secondary", {}, { rooms: R1, source: { state: "secondary", options: ["primary", "secondary"], active: "secondary" } }],
  ["house-scenarios", {}, { rooms: R1, scenarios: ["Home office", "Holidays"], scenario: "Holidays" }],
  ["house-alerts", {}, { rooms: [{ id: "r1", name: "Bedroom", alerts: [UNAVAILABLE, MOLD] }, { id: "r2", name: "Office", alerts: [MOLD] }, { id: "r3", name: "Kid" }] }],
  ["house-no-outdoor", {}, { rooms: R1, noOutdoor: true }],
  ["house-fahrenheit", {}, { rooms: ROOMS, unit: "°F" }],
  ["house-vacation-form", {}, { rooms: R1 }, click('[data-key="vac-e1"]')],
  ["house-runtime-week", {}, { rooms: R1 }, click('[data-action="period"]')],
  // Layouts of the rooms.
  ["rooms-collapsed", { collapsed: true }, { rooms: ROOMS }],
  ["rooms-compact", { compact: true }, { rooms: ROOMS }],
  ["rooms-compact-house-open", { compact: true }, { rooms: ROOMS }, click('.house-row')],
  ["rooms-compact-room-open", { compact: true }, { rooms: ROOMS }, click('[data-action="fold"][data-key="room-r1"]')],
  ["rooms-collapsed-room-open", { collapsed: true }, { rooms: ROOMS }, click('[data-action="fold"][data-key="room-r2"]')],
  ["rooms-compact-heating", { compact: true }, { rooms: [{ id: "r1", name: "Bedroom", heating: true }, { id: "r2", name: "Office", heating: false }] }],
  ["rooms-only-some", { rooms: ["sensor.office_decision", "sensor.bedroom_decision"] }, { rooms: ROOMS }],
  ["rooms-no-sections", { show_timeline: false, show_details: false, show_quick_override: false, show_schedule_editor: false, show_levels: false }, { rooms: R1 }],
  ["rooms-no-house", { show_house: false }, { rooms: R1 }],
  // A room.
  ["room-trend-up", {}, { rooms: [{ id: "r1", name: "Bedroom", trend: 1 }] }],
  ["room-trend-down", {}, { rooms: [{ id: "r1", name: "Bedroom", trend: -1, demand: false, heating: false }] }],
  ["room-near-target", { collapsed: true }, { rooms: [{ id: "r1", name: "Bedroom", current: 20.8, target: 21 }, { id: "r2", name: "Office", current: 20.5, target: 21 }] }],
  ["room-held-at-min", {}, { rooms: [{ id: "r1", name: "Living", preset: "away", target: 12, heldAt: 16 }] }],
  ["room-keep-open", {}, { rooms: [{ id: "r1", name: "Bedroom", reasonKey: "keep_open", reasonParams: { preset: "home", temperature: 21 } }] }],
  ["room-top-up", {}, { rooms: [{ id: "r1", name: "Bedroom", reasonKey: "top_up", reasonParams: { preset: "home", temperature: 21 } }] }],
  ["room-optimal-start", {}, { rooms: [{ id: "r1", name: "Bedroom", estimate: OPTIMAL, current: 18.5 }] }],
  ["room-details", {}, { rooms: R1 }, click('[data-key="details-r1"]')],
  ["room-details-not-learned", {}, { rooms: [ROOMS[1]] }, click('[data-key="details-r2"]')],
  ["room-details-inertia", {}, { rooms: [{ id: "r1", name: "Bedroom", band: [0.3, 0.3], tau: 60, inertia: true, sunGain: 1.2 }] }, click('[data-key="details-r1"]')],
  ["room-details-devices", {}, { rooms: [{ id: "r1", name: "Bedroom", source: "climate", ...DEVICES }], extra: DEVICES.extra }, click('[data-key="details-r1"]')],
  ["room-details-negative-curve", {}, { rooms: [{ id: "r1", name: "Bedroom", curve: -0.04 }] }, click('[data-key="details-r1"]')],
  ["room-levels", {}, { rooms: R1 }, click('[data-key="levels-r1"]')],
  ["room-quick", {}, { rooms: R1 }, click('[data-key="quick-r1"]')],
  ["room-quick-override", {}, { rooms: [{ id: "r1", name: "Bedroom", override: OVERRIDE }] }, click('[data-key="quick-r1"]')],
  ["room-reset-confirm", {}, { rooms: R1 }, steps(click('[data-key="details-r1"]'), click('[data-action="reset-learning"]'))],
  // The schedule.
  ["schedule-view", {}, { rooms: R1 }, click('[data-key="sched-r1"]')],
  ["schedule-edit", {}, { rooms: R1 }, editSchedule],
  ["schedule-drag", {}, { rooms: R1 }, steps(editSchedule, dragHandle(1, 40))],
  ["schedule-add-slot", {}, { rooms: R1 }, steps(editSchedule, click('[data-action="add-slot"][data-profile="workday"]'))],
  ["schedule-profile-confirm", {}, { rooms: R1 }, steps(click('[data-key="sched-r1"]'), click('[data-action="profile-toggle"][data-profile="weekend"]'))],
  // The chart.
  ["chart", {}, { rooms: R1 }, openChart()],
  ["chart-zoom-6h", {}, { rooms: R1 }, steps(openChart(), click('[data-action="zoom"][data-zoom="6h"]'))],
  ["chart-hover-past", {}, { rooms: R1 }, steps(openChart(), hoverChart(0.3, 0.4))],
  ["chart-hover-future", {}, { rooms: R1 }, steps(openChart(), hoverChart(0.85, 0.4))],
  ["chart-legend-off", {}, { rooms: R1 }, steps(openChart(), click('[data-action="series"][data-series="temp"]'))],
  ["chart-sun", {}, { rooms: [{ id: "r1", name: "Bedroom", sunGain: 1.5 }], sun: 0.4 }, openChart()],
  ["chart-optimal-start", {}, { rooms: [{ id: "r1", name: "Bedroom", estimate: OPTIMAL, current: 18.5 }] }, openChart()],
  ["chart-band", {}, { rooms: [{ id: "r1", name: "Bedroom", current: 21, target: 21, band: [0.3, 0.3], tau: 60 }] }, openChart()],
  ["chart-zoom-1h-pan", {}, { rooms: R1 }, steps(openChart(), click('[data-action="zoom"][data-zoom="1h"]'), async (p) => {
    const pt = await p.evaluate(() => { const r = card.shadowRoot.querySelector(".hchart").getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; });
    await p.mouse.move(pt[0], pt[1]); await p.mouse.wheel(-300, 0); await p.waitForTimeout(250);
  })],
  ["chart-empty-history", {}, { rooms: R1, emptyHistory: true }, openChart()],
];

// Scenes that only send something: the services and messages are compared too.
const ACTIONS = [
  ["act-mode-away", {}, { rooms: R1 }, click('[data-action="mode"][data-option="away"]')],
  ["act-pause", {}, { rooms: R1 }, click('[data-action="toggle"][data-entity="switch.home_pause"]')],
  ["act-scenario", {}, { rooms: R1, scenarios: ["Home office", "Holidays"], scenario: "Holidays" }, click('.scen[data-option="Home office"]')],
  ["act-source", {}, { rooms: R1, source: { state: "auto", options: ["auto", "primary", "secondary"], active: "primary" } }, click('.sources .seg[data-option="secondary"]')],
  ["act-quick-preset", {}, { rooms: R1 }, steps(click('[data-key="quick-r1"]'), input('input[data-quick="hours"][data-room="r1"]', "2"), click('[data-action="quick-preset"][data-preset="eco"]'))],
  ["act-clear-override", {}, { rooms: [{ id: "r1", name: "Bedroom", override: OVERRIDE }] }, click('[data-action="clear"][data-room="r1"]')],
  ["act-reset-learning", {}, { rooms: R1 }, steps(click('[data-key="details-r1"]'), click('[data-action="reset-learning"]'), click('[data-action="reset-learning"]'))],
  ["act-schedule-drag-save", {}, { rooms: R1 }, steps(editSchedule, dragHandle(1, 40), click('[data-action="save"][data-room="r1"]'))],
  ["act-schedule-profile-off", {}, { rooms: R1 }, steps(click('[data-key="sched-r1"]'), click('[data-action="profile-toggle"][data-profile="weekend"]'), click('[data-action="profile-confirm"]'))],
  ["act-vacation", {}, { rooms: R1 }, steps(click('[data-key="vac-e1"]'), input('input[data-vac="start"][data-house="e1"]', "2026-12-20T08:00"),
    input('input[data-vac="end"][data-house="e1"]', "2026-12-27T18:30"), click('[data-action="vacation"][data-house="e1"]'))],
  ["act-level", {}, { rooms: R1 }, steps(click('[data-key="levels-r1"]'), input('input[data-action="number"]', "20.5"))],
];

module.exports = { SCENES, ACTIONS, NOW };
