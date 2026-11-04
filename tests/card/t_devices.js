// The devices of a room in its Details, and which rooms start the heat source.
const mount = async (p, config, hass) => { await p.evaluate(([c, h]) => mount(c, h), [config, hass]); await p.waitForTimeout(200); };
const click = (p, sel) => p.evaluate((s) => { const el = card.shadowRoot.querySelector(s); if (!el) throw new Error("no " + s); el.click(); }, sel);
const text = (p, sel) => p.evaluate((s) => [...card.shadowRoot.querySelectorAll(s)].map((el) => el.innerText.replace(/\s+/g, " ").trim()), sel);

const DEVICES = [
  ["climate.trv", "thermostat"], ["switch.heater", "switch"], ["sensor.temp", "temperature"],
  ["sensor.hum", "humidity"], ["binary_sensor.win", "window"], ["binary_sensor.motion", "occupancy"],
  ["sensor.gone", "temperature"],
];
const EXTRA = [
  ["climate.trv", "heat", { friendly_name: "TRV Bedroom", current_temperature: 20.4, temperature: 21, hvac_action: "heating" }],
  ["switch.heater", "on", { friendly_name: "Heater" }],
  ["sensor.temp", "20.6", { friendly_name: "Bedroom temperature", unit_of_measurement: "°C" }],
  ["sensor.hum", "unavailable", { friendly_name: "Bedroom humidity" }],
  ["binary_sensor.win", "on", { friendly_name: "Bedroom window" }],
  ["binary_sensor.motion", "off", { friendly_name: "Bedroom motion" }],
];

test("details: every device of the room with its state, the unavailable ones marked", async (p) => {
  await mount(p, {}, { rooms: [{ id: "r1", name: "Bedroom", devices: DEVICES }], extra: EXTRA });
  await click(p, '[data-key="details-r1"]'); await p.waitForTimeout(150);
  const rows = await text(p, ".details.devices .dev");
  eq(rows, [
    "TRV Bedroom Thermostat 20.4° → 21.0° heating",
    "Heater Switch On",
    "Bedroom temperature Temperature 20.6 °C",
    "Bedroom humidity Humidity unavailable",
    "Bedroom window Window open",
    "Bedroom motion Occupancy nobody",
    "sensor.gone Temperature not found",
  ], "the rows");
  const bad = await p.evaluate(() => [...card.shadowRoot.querySelectorAll(".details.devices .dev.bad")].length);
  eq(bad, 2, "the unavailable and the missing one stand out");
  // A row opens the dialog of its entity.
  const opened = await p.evaluate(() => {
    let id = null;
    card.addEventListener("hass-more-info", (ev) => { id = ev.detail.entityId; }, { once: true });
    card.shadowRoot.querySelectorAll(".details.devices .dev")[4].click();
    return id;
  });
  eq(opened, "binary_sensor.win", "more-info of the window");
});

test("details: no devices group without devices; Romanian labels", async (p) => {
  await mount(p, {}, { rooms: [{ id: "r1", name: "Bedroom" }] });
  await click(p, '[data-key="details-r1"]'); await p.waitForTimeout(150);
  eq(await text(p, ".details.devices"), [], "no group");
  await mount(p, {}, { lang: "ro", rooms: [{ id: "r1", name: "Bedroom", devices: DEVICES.slice(4, 6) }], extra: EXTRA });
  await click(p, '[data-key="details-r1"]'); await p.waitForTimeout(150);
  eq(await text(p, ".details.devices .dev"), ["Bedroom window Fereastră deschisă", "Bedroom motion Ocupare nimeni"], "in Romanian");
});

test("heat source: the rooms that ask, the rooms still needed, the minimum time", async (p) => {
  const R = [{ id: "r1", name: "Bedroom" }];
  const line = () => text(p, ".demandline");
  await mount(p, {}, { rooms: R, demand: { rooms: ["Living", "Bathroom"], frost_rooms: [], own_heat_rooms: [], needed: 1, reference_room: null, source_configured: true, waiting: null } });
  eq(await line(), ["Heat: asked by Living, Bathroom"], "two rooms");
  await mount(p, {}, { rooms: R, houseDemand: false, demand: { rooms: ["Living"], frost_rooms: [], own_heat_rooms: ["Office"], needed: 2, reference_room: null, source_configured: true, waiting: "min_off" } });
  eq(await line(), ["Heat: asked by Living · 1 of 2 rooms needed to start the heat source · with their own heating: Office · the heat source waits for its minimum time off"], "fewer rooms than needed");
  await mount(p, {}, { rooms: R, demand: { rooms: ["Living"], frost_rooms: ["Office"], own_heat_rooms: [], needed: null, reference_room: "Bathroom", source_configured: true, waiting: null } });
  eq(await line(), ["Heat: the heat source follows Bathroom · Bathroom does not ask for heat · frost protection: Office"], "reference room");
  // Nothing asks and nothing waits: no line.
  await mount(p, {}, { rooms: R, houseDemand: false, demand: { rooms: [], frost_rooms: [], own_heat_rooms: [], needed: 1, reference_room: null, source_configured: true, waiting: null } });
  eq(await line(), [], "no line");
  // Without a heat source the number of rooms is not told.
  await mount(p, {}, { rooms: R, demand: { rooms: ["Living"], frost_rooms: [], own_heat_rooms: [], needed: 2, reference_room: null, source_configured: false, waiting: null } });
  eq(await line(), ["Heat: asked by Living"], "no heat source");
});
