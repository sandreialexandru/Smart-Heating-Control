// The devices of a room in its Details.
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
