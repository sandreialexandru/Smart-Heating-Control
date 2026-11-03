// Configurations and room states.
const ROOMS = [
  { id: "r1", name: "Bedroom", humidity: 62, wall: 84.4, alerts: [{ code: "mold_risk", params: { surface: 84, humidity: 62 }, room: "r1", message: "m" }] },
  { id: "r2", name: "Office", learned: false, source: "climate", climates: ["climate.office"],
    override: { temperature: 23, until: new Date(Date.now() + 2 * 3600e3).toISOString(), origin: "card", preset: null, applied: true }, state: "manual_override" },
  { id: "r3", name: "Living", window: true, state: "window_open", reasonKey: "window_open", demand: false, heating: false },
  { id: "r4", name: "Kid", current: null, dropAttrs: ["plan", "next_estimate", "levels", "offsets", "alerts", "humidity"], learned: false },
];
const mount = async (p, config, hass) => { await p.evaluate(([c, h]) => mount(c, h), [config, hass]); await p.waitForTimeout(250); };
const text = (p) => p.evaluate(() => [...card.shadowRoot.children].map((n) => n.innerText || "").join(" ").replace(/\s+/g, " "));
const count = (p, sel) => p.evaluate((s) => card.shadowRoot.querySelectorAll(s).length, sel);

test("default config, 4 rooms with different states, no JS errors", async (p) => {
  await mount(p, {}, { rooms: ROOMS });
  const t = await text(p);
  for (const n of ["Bedroom", "Office", "Living", "Kid", "Home"]) ok(t.includes(n), `missing ${n}`);
  eq(await count(p, '[data-key^="chart-"]'), 4, "chart buttons");
});

test("collapsed rows show the drop only for the room with the mold alert", async (p) => {
  await mount(p, { collapsed: true }, { rooms: ROOMS });
  eq(await count(p, 'ha-icon[icon="mdi:water-alert-outline"]'), 1, "drops");
});

test("compact mode renders all rooms with icons", async (p) => {
  await mount(p, { compact: true }, { rooms: ROOMS });
  eq(await count(p, 'ha-icon[icon="mdi:water-alert-outline"]'), 1, "drops");
  ok((await text(p)).includes("Kid"), "Kid tile");
});

test("show_timeline false hides the chart button", async (p) => {
  await mount(p, { show_timeline: false }, { rooms: ROOMS });
  eq(await count(p, '[data-key^="chart-"]'), 0, "chart buttons");
});

test("show_details false hides details", async (p) => {
  await mount(p, { show_details: false }, { rooms: ROOMS });
  eq(await count(p, '[data-key^="details-"]'), 0, "details buttons");
});

test("rooms list limits the rooms and keeps the order", async (p) => {
  await mount(p, { rooms: ["sensor.office_decision", "sensor.bedroom_decision"] }, { rooms: ROOMS });
  const names = await p.evaluate(() => [...card.shadowRoot.querySelectorAll('[data-key^="room-"]')].map((b) => b.dataset.key));
  eq(names, ["room-r2", "room-r1"], "order");
});

test("Romanian texts in details", async (p) => {
  await mount(p, {}, { rooms: [ROOMS[0]], lang: "ro" });
  await p.evaluate(() => card.shadowRoot.querySelector('[data-key="details-r1"]').click()); await p.waitForTimeout(150);
  const t = await text(p);
  for (const s of ["Umiditate", "aer 62%", "peretele cel mai rece 84%", "risc de mucegai", "Curba de temperatură", "învățat"]) ok(t.includes(s), `missing ${s}`);
});

test("°F house: details and chart in °F, prediction converted", async (p) => {
  await mount(p, {}, { rooms: [ROOMS[0]], unit: "°F" });
  await p.evaluate(() => card.shadowRoot.querySelector('[data-key="details-r1"]').click()); await p.waitForTimeout(150);
  const t = await text(p);
  ok(t.includes("°F/h for each °F colder"), "curve in °F");
  ok(t.includes("±0.22 °F/h"), "error in °F");
  await p.evaluate(() => card.shadowRoot.querySelector('[data-key="chart-r1"]').click()); await p.waitForTimeout(300);
  const pr = await p.evaluate(() => { const d = card._charts.r1; return { first: d.pred[0][1], max: Math.max(...d.pred.map((x) => x[1])), min: Math.min(...d.pred.map((x) => x[1])) }; });
  ok(pr.first > 60 && pr.max < 80 && pr.min > 55, "prediction in °F range: " + JSON.stringify(pr));
});

test("dark theme and transparent card background: tooltip and window opaque", async (p) => {
  await p.evaluate(() => { document.body.style.setProperty("--card-background-color", "rgba(20,20,20,0.3)"); document.body.style.setProperty("--ha-card-background", "rgba(20,20,20,0.3)"); document.body.style.setProperty("--primary-background-color", "#111"); document.body.style.setProperty("--primary-text-color", "#eee"); });
  await mount(p, {}, { rooms: [ROOMS[0]], dark: true });
  await p.evaluate(() => card.shadowRoot.querySelector('[data-key="chart-r1"]').click()); await p.waitForTimeout(300);
  const box = await p.evaluate(() => { const r = card.shadowRoot.querySelector(".hchart").getBoundingClientRect(); return [r.left + r.width * 0.3, r.top + 40]; });
  await p.mouse.move(box[0], box[1]); await p.waitForTimeout(200);
  const bg = await p.evaluate(() => ({ tip: getComputedStyle(card.shadowRoot.querySelector(".tip")).backgroundColor, dlg: getComputedStyle(card.shadowRoot.querySelector("dialog.chartpop")).backgroundColor }));
  ok(!/rgba\(.*,\s*0(\.\d+)?\)$/.test(bg.tip) && !bg.tip.startsWith("rgba"), "tip opaque: " + bg.tip);
  ok(!bg.dlg.startsWith("rgba"), "dialog opaque: " + bg.dlg);
}, { dark: true });

test("not learned room: progress, no prediction, default under it", async (p) => {
  await mount(p, {}, { rooms: [ROOMS[1]] });
  await p.evaluate(() => card.shadowRoot.querySelector('[data-key="details-r2"]').click()); await p.waitForTimeout(150);
  const t = await text(p);
  ok(t.includes("learning…") && t.includes("with heating 1.5 of 4 h") && t.includes("without heating 0.5 of 4 h"), "progress");
  const bars = await p.evaluate(() => [...card.shadowRoot.querySelectorAll(".lbar-track > span")].map((x) => x.style.width));
  eq(bars, ["38%", "13%"], "bars");
  ok(!t.includes("Weather curve"), "no curve row before learned");
  await p.evaluate(() => card.shadowRoot.querySelector('[data-key="chart-r2"]').click()); await p.waitForTimeout(300);
  eq(await p.evaluate(() => card._charts.r2.pred.length), 0, "no prediction");
  eq(await count(p, ".predline"), 0, "no predicted line");
  eq(await count(p, ".lg-pred"), 0, "no legend");
});

test("room with unavailable temperature and missing attributes does not break", async (p) => {
  await mount(p, {}, { rooms: [ROOMS[3]] });
  await p.evaluate(() => card.shadowRoot.querySelector('[data-key="details-r4"]').click());
  await p.evaluate(() => card.shadowRoot.querySelector('[data-key="chart-r4"]').click()); await p.waitForTimeout(300);
  ok(await p.evaluate(() => !!card.shadowRoot.querySelector("dialog.chartpop")), "chart window opens");
});

test("no humidity: no humidity row; air only: air only", async (p) => {
  await mount(p, {}, { rooms: [{ id: "r1", name: "Bedroom" }] });
  await p.evaluate(() => card.shadowRoot.querySelector('[data-key="details-r1"]').click()); await p.waitForTimeout(150);
  ok(!(await text(p)).includes("Humidity"), "no humidity row");
  await mount(p, {}, { rooms: [{ id: "r1", name: "Bedroom", humidity: 55 }] });
  await p.evaluate(() => card.shadowRoot.querySelector('[data-key="details-r1"]').click()); await p.waitForTimeout(150);
  const t = await text(p);
  ok(t.includes("Humidity air 55%") && !t.includes("coldest wall"), "air only: " + t.slice(t.indexOf("Humidity"), t.indexOf("Humidity") + 60));
  ok(!t.includes("mold risk"), "no risk mark");
});

test("wall below 80 %: no risk mark; curve zero shows none", async (p) => {
  await mount(p, {}, { rooms: [{ id: "r1", name: "Bedroom", humidity: 50, wall: 72, curve: 0 }] });
  await p.evaluate(() => card.shadowRoot.querySelector('[data-key="details-r1"]').click()); await p.waitForTimeout(150);
  const t = await text(p);
  ok(!t.includes("mold risk"), "no risk");
  ok(t.includes("Weather curve none the same at any outdoor temperature"), "curve none");
});

test("negative curve shown with a minus", async (p) => {
  await mount(p, {}, { rooms: [{ id: "r1", name: "Bedroom", curve: -0.03 }] });
  await p.evaluate(() => card.shadowRoot.querySelector('[data-key="details-r1"]').click()); await p.waitForTimeout(150);
  ok((await text(p)).includes("−0.030 °C/h for each °C colder"), "minus");
});

test("phone width: no horizontal overflow, chart window fits", async (p) => {
  await mount(p, {}, { rooms: ROOMS });
  const over = await p.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
  ok(!over, "page overflows sideways");
  await p.evaluate(() => card.shadowRoot.querySelector('[data-key="chart-r1"]').click()); await p.waitForTimeout(300);
  const r = await p.evaluate(() => { const d = card.shadowRoot.querySelector("dialog.chartpop").getBoundingClientRect(); return [d.left, d.right, window.innerWidth]; });
  ok(r[0] >= 0 && r[1] <= r[2], "dialog within screen: " + r);
}, { viewport: { width: 375, height: 740 }, touch: true });

test("learned sun gain: a Sun row with the gain now; none without it", async (p) => {
  await mount(p, {}, { rooms: [{ id: "r1", name: "Bedroom", sunGain: 1.5 }], sun: 0.4 });
  await p.evaluate(() => card.shadowRoot.querySelector('[data-key="details-r1"]').click()); await p.waitForTimeout(150);
  let t = await text(p);
  ok(t.includes("Sun +1.50 °C/h sun overhead, clear sky · now +0.60 °C/h"), t.slice(t.indexOf("Weather curve"), t.indexOf("Weather curve") + 160));
  await mount(p, {}, { rooms: [{ id: "r1", name: "Bedroom" }] });
  await p.evaluate(() => card.shadowRoot.querySelector('[data-key="details-r1"]').click()); await p.waitForTimeout(150);
  t = await text(p);
  ok(!t.includes("clear sky"), "no sun row");
});

test("learned room: one tile each for heating, inertia, curve and heat loss", async (p) => {
  await mount(p, {}, { rooms: [ROOMS[0]] });
  await p.evaluate(() => card.shadowRoot.querySelector('[data-key="details-r1"]').click()); await p.waitForTimeout(150);
  const tiles = await p.evaluate(() => [...card.shadowRoot.querySelectorAll(".ltile dt")].map((x) => x.innerText));
  eq(tiles, ["Heating", "Inertia", "Weather curve", "Heat loss"], "tiles");
  eq(await count(p, ".lbar"), 0, "no bars once learned");
});

test("house stats: two by two on a phone, one row on a wide card", async (p) => {
  await mount(p, {}, { rooms: [ROOMS[0]] });
  const rows = await p.evaluate(() => new Set([...card.shadowRoot.querySelectorAll(".stats > *")].map((x) => Math.round(x.getBoundingClientRect().top))).size);
  eq(rows, 2, "rows on a phone");
}, { viewport: { width: 375, height: 740 } });

test("house stats: one row on a wide card", async (p) => {
  await mount(p, {}, { rooms: [ROOMS[0]] });
  const rows = await p.evaluate(() => new Set([...card.shadowRoot.querySelectorAll(".stats > *")].map((x) => Math.round(x.getBoundingClientRect().top))).size);
  eq(rows, 1, "rows wide");
}, { viewport: { width: 900, height: 740 } });

test("short labels on the room buttons", async (p) => {
  await mount(p, {}, { rooms: [ROOMS[0]] });
  const labels = await p.evaluate(() => [...card.shadowRoot.querySelectorAll(".sbtn span")].map((x) => x.innerText));
  ok(labels.includes("For a while") && labels.includes("Levels") && !labels.includes("Set for a while"), JSON.stringify(labels));
  await mount(p, {}, { rooms: [ROOMS[0]], lang: "ro" });
  const ro = await p.evaluate(() => [...card.shadowRoot.querySelectorAll(".sbtn span")].map((x) => x.innerText));
  ok(ro.includes("Temporar") && ro.includes("Niveluri"), JSON.stringify(ro));
});

test("trend arrow: up, down, none when steady", async (p) => {
  await mount(p, {}, { rooms: [{ id: "r1", name: "Bedroom", trend: 1 }, { id: "r2", name: "Office", trend: -1 }, { id: "r3", name: "Living" }] });
  eq(await count(p, ".gtrend.up"), 1, "up");
  eq(await count(p, ".gtrend.down"), 1, "down");
  ok(await p.evaluate(() => card.shadowRoot.querySelector(".gauge").getAttribute("aria-label").includes("warming")), "label");
  await mount(p, { compact: true }, { rooms: [{ id: "r1", name: "Bedroom", trend: -1 }] });
  eq(await count(p, ".tile .gtrend.down"), 1, "compact");
});

test("manual change shows the time left; compact line: time to target while heating, else the next change", async (p) => {
  const until = new Date(Date.now() + 90 * 60e3 + 20e3).toISOString();
  await mount(p, {}, { rooms: [{ id: "r1", name: "Bedroom", override: { temperature: 23, until, origin: "card", preset: null, applied: true } }] });
  ok((await text(p)).includes("1 h 30 min left"), "left");
  await mount(p, {}, { rooms: [{ id: "r1", name: "Bedroom", override: { temperature: 23, until, origin: "card", preset: null, applied: true } }], lang: "ro" });
  ok((await text(p)).includes("încă 1 h 30 min"), "încă");
  await mount(p, { compact: true }, { rooms: [{ id: "r1", name: "Bedroom", heating: true }, { id: "r2", name: "Office", heating: false }] });
  const lines = await p.evaluate(() => [...card.shadowRoot.querySelectorAll(".tile")].map((x) => x.innerText.replace(/\s+/g, " ")));
  ok(lines[0].includes("~35 min"), lines[0]);
  ok(!lines[1].includes("~35 min") && /\d\d:\d\d/.test(lines[1]), lines[1]);
});
