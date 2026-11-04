// The values the card shows and the services its buttons call.
const mount = async (p, config, hass) => { await p.evaluate(([c, h]) => mount(c, h), [config, hass]); await p.waitForTimeout(200); };
const click = (p, sel) => p.evaluate((s) => { const el = card.shadowRoot.querySelector(s); if (!el) throw new Error("no " + s); el.click(); }, sel);
const services = (p) => p.evaluate(() => calls.service);
const last = async (p) => (await services(p)).at(-1);
const openChart = async (p) => { await click(p, '[data-key="chart-r1"]'); await p.waitForTimeout(400); };
const R = [{ id: "r1", name: "Bedroom" }];
const H = 3600e3;

test("chart data: the measured temperature and the heating from the history", async (p) => {
  await mount(p, {}, { rooms: R }); await openChart(p);
  const r = await p.evaluate(() => {
    const d = card._charts.r1;
    // The fake history: 19.5 + 1.5 × sin(2π × hours / 24), every 15 minutes.
    const expected = (t) => 19.5 + 1.5 * Math.sin((t / 3600e3 / 24) * 2 * Math.PI);
    const past = d.temp.filter(([t]) => t < d.now);
    const worst = Math.max(...past.map(([t, v]) => Math.abs(v - expected(t))));
    // Heating on for the first hour of every 3 hours.
    const periods = d.heat.slice(1, -1).map(([s, e]) => [(e - s) / 60000, s]);
    const gaps = periods.slice(1).map(([, s], i) => (s - periods[i][1]) / 3600e3);
    return { worst, count: past.length, last: d.temp.at(-1)[1], lengths: [...new Set(periods.map(([m]) => Math.round(m)))], gaps: [...new Set(gaps.map((g) => Math.round(g * 100) / 100))] };
  });
  ok(r.count > 600 && r.worst < 1e-9, JSON.stringify(r));
  eq(r.last, 20.2, "the current temperature closes the line");
  eq(r.lengths, [60], "every heating period 60 minutes");
  eq(r.gaps, [3], "every 3 hours");
});

test("prediction: warms to the target, falls to the sleep level and holds it, warms again", async (p) => {
  // Learned room (fixtures): h 2 °C/h, curve 0.05, loss 0.05/h, inertia 30 min, 30 % of the
  // heat on its way; 20.2 °C now, home (21 °C) for 3 h, sleep (18.5 °C) until 10 h, then home.
  await mount(p, {}, { rooms: R }); await openChart(p);
  const r = await p.evaluate(() => {
    const d = card._charts.r1;
    const at = (h) => { const t = d.now + h * 3600e3; let v = null; for (const [pt, x] of d.pred) { if (pt <= t) v = x; else break; } return v; };
    return { first: d.pred[0][1], h1: at(1), h2: at(2), h5: at(5), h9: at(9), h99: at(9.9), h12: at(12), heat: d.predHeat.map(([s, e]) => [(s - d.now) / 3600e3, (e - d.now) / 3600e3]) };
  });
  eq(r.first, 20.2, "starts at the room temperature");
  ok(r.h1 > 20.5 && Math.abs(r.h2 - 21) < 0.2, "warms to 21: " + JSON.stringify(r));
  ok(r.h5 < 20 && Math.abs(r.h9 - 18.5) < 0.15, "falls to 18.5 and holds it: " + JSON.stringify(r));
  ok(r.h12 > r.h99 + 1, "warms again for home: " + JSON.stringify(r));
  ok(r.heat[0][0] === 0 && r.heat[0][1] > 1 && r.heat[0][1] < 2, "heats from now for 1–2 h: " + JSON.stringify(r.heat));
  ok(r.heat.at(-1)[1] > 11, "heats for home at the end: " + JSON.stringify(r.heat));
});

test("tooltip: the values of the moment under the pointer", async (p) => {
  await mount(p, {}, { rooms: R }); await openChart(p);
  const hover = async (hours) => {
    const pos = await p.evaluate((h) => {
      const d = card._charts.r1; const b = card.shadowRoot.querySelector(".hchart").getBoundingClientRect();
      const f = (d.now + h * 3600e3 - d.v0) / (d.v1 - d.v0);
      return [b.left + b.width * f, b.top + 30];
    }, hours);
    await p.mouse.move(pos[0], pos[1]); await p.waitForTimeout(120);
    return p.evaluate((h) => {
      const d = card._charts.r1; const b = card.shadowRoot.querySelector(".hchart").getBoundingClientRect();
      const tip = card.shadowRoot.querySelector(".tip").innerText.replace(/\s+/g, " ");
      // The moment the pointer really is on (a pixel is about a minute).
      const t = d.now + h * 3600e3;
      let temp = null; for (const [pt, v] of d.temp) { if (pt <= t) temp = v; else break; }
      let pred = null; for (const [pt, v] of d.pred) { if (pt <= t) pred = v; else break; }
      const heating = d.heat.some(([s, e]) => s <= t && t <= e);
      return { tip, temp, pred, heating };
    }, hours);
  };
  const past = await hover(-6);
  ok(past.tip.includes(`${past.temp.toFixed(1)}°`) && past.tip.includes("21°") && !past.tip.includes("predicted"), JSON.stringify(past));
  ok(past.tip.includes("Heating") === past.heating, "heating word: " + JSON.stringify(past));
  const ahead = await hover(5);
  ok(ahead.tip.includes(`predicted ${ahead.pred.toFixed(1)}°`) && ahead.tip.includes("18.5°"), JSON.stringify(ahead));
  ok(ahead.tip.includes("Outdoor"), "outdoor forecast: " + ahead.tip);
});

test("house buttons: mode, pause, guests, reevaluate, clear the manual changes", async (p) => {
  await mount(p, {}, { rooms: R });
  await click(p, '[data-action="mode"][data-option="vacation"]'); await p.waitForTimeout(50);
  eq(await last(p), { domain: "select", service: "select_option", data: { entity_id: "select.home_mode", option: "vacation" } }, "mode");
  await click(p, '[data-action="toggle"][data-entity="switch.home_pause"]'); await p.waitForTimeout(50);
  eq(await last(p), { domain: "switch", service: "toggle", data: { entity_id: "switch.home_pause" } }, "pause");
  await click(p, '[data-action="toggle"][data-entity="switch.home_guest_mode"]'); await p.waitForTimeout(50);
  eq(await last(p), { domain: "switch", service: "toggle", data: { entity_id: "switch.home_guest_mode" } }, "guests");
  await click(p, '[data-action="press"][data-entity="button.home_reevaluate"]'); await p.waitForTimeout(50);
  eq(await last(p), { domain: "button", service: "press", data: { entity_id: "button.home_reevaluate" } }, "reevaluate");
  await click(p, '[data-action="press"][data-entity="button.home_clear_overrides"]'); await p.waitForTimeout(50);
  eq(await last(p), { domain: "button", service: "press", data: { entity_id: "button.home_clear_overrides" } }, "clear all");
});

test("room buttons: back to automatic, a temperature for a while, the child lock", async (p) => {
  const until = new Date(Date.now() + 2 * H).toISOString();
  await mount(p, {}, { rooms: [{ ...R[0], override: { temperature: 23, until, origin: "card", preset: null, applied: true } }] });
  await click(p, '[data-action="clear"][data-room="r1"]'); await p.waitForTimeout(50);
  eq(await last(p), { domain: "advanced_climate", service: "clear_override", data: { room: "r1" } }, "automatic");
  await click(p, '[data-key="quick-r1"]'); await p.waitForTimeout(100);
  await p.evaluate(() => {
    const set = (q, v) => { const i = card.shadowRoot.querySelector(q); i.value = v; i.dispatchEvent(new Event("change", { bubbles: true })); };
    set('input[data-quick="temp"][data-room="r1"]', "22.5");
    set('input[data-quick="hours"][data-room="r1"]', "1.5");
  });
  await click(p, '[data-action="quick-temp"][data-room="r1"]'); await p.waitForTimeout(50);
  eq(await last(p), { domain: "advanced_climate", service: "set_override", data: { room: "r1", temperature: 22.5, duration_hours: 1.5 } }, "temperature");
  await click(p, '[data-action="toggle"][data-entity="switch.bedroom_child_lock"]'); await p.waitForTimeout(50);
  eq(await last(p), { domain: "switch", service: "toggle", data: { entity_id: "switch.bedroom_child_lock" } }, "lock");
});

test("heating time: a tap goes day → week → month → day", async (p) => {
  await mount(p, {}, { rooms: R });
  const label = () => p.evaluate(() => card.shadowRoot.querySelector('[data-action="period"]').innerText.replace(/\s+/g, " "));
  const seen = [await label()];
  for (let i = 0; i < 3; i++) { await click(p, '[data-action="period"]'); await p.waitForTimeout(150); seen.push(await label()); }
  ok(/today/i.test(seen[0]) && /week/i.test(seen[1]) && /month/i.test(seen[2]) && /today/i.test(seen[3]), JSON.stringify(seen));
});

test("schedule editor: add and delete a time, add a profile, save", async (p) => {
  await mount(p, {}, { rooms: R }); await click(p, '[data-key="sched-r1"]'); await p.waitForTimeout(100);
  await click(p, '[data-action="edit"][data-room="r1"]'); await p.waitForTimeout(100);
  // workday ends with 22:00: the new time is an hour later.
  await click(p, '[data-action="add-slot"][data-profile="workday"]'); await p.waitForTimeout(100);
  let draft = await p.evaluate(() => card._draft.workday.map((s) => s.time));
  eq(draft, ["00:00", "06:00", "22:00", "23:00"], "added");
  await p.evaluate(() => {
    const del = [...card.shadowRoot.querySelectorAll('[data-action="del-slot"][data-profile="workday"]')];
    del[del.length - 1].click();
  });
  await p.waitForTimeout(100);
  draft = await p.evaluate(() => card._draft.workday.map((s) => s.time));
  eq(draft, ["00:00", "06:00", "22:00"], "deleted");
  await p.evaluate(() => { card.shadowRoot.querySelector(".newprofile").value = "  Guest Room! "; });
  await click(p, '[data-action="add-profile"]'); await p.waitForTimeout(100);
  eq(await p.evaluate(() => card._draft.guest_room), [{ time: "00:00", preset: "home" }], "new profile, name cleaned");
  await click(p, '[data-action="save"][data-room="r1"]'); await p.waitForTimeout(150);
  const s = await last(p);
  eq(Object.keys(s.data.profiles), ["workday", "weekend", "guest_room"], "saved");
  eq(s.data.profile_days.guest_room.enabled, false, "a new profile starts off");
});

test("turning a profile off that leaves days without one asks first", async (p) => {
  await mount(p, {}, { rooms: R }); await click(p, '[data-key="sched-r1"]'); await p.waitForTimeout(100);
  const before = (await services(p)).length;
  await click(p, '[data-action="profile-toggle"][data-profile="weekend"]'); await p.waitForTimeout(100);
  eq((await services(p)).length, before, "nothing sent yet");
  await click(p, '[data-action="profile-cancel"]'); await p.waitForTimeout(100);
  eq((await services(p)).length, before, "cancelled");
  await click(p, '[data-action="profile-toggle"][data-profile="weekend"]'); await p.waitForTimeout(100);
  await click(p, '[data-action="profile-confirm"]'); await p.waitForTimeout(150);
  const s = await last(p);
  ok(s.service === "set_schedule" && s.data.profile_days.weekend.enabled === false, JSON.stringify(s));
});

test("vacation: the dates as typed, in the time zone of the card (Bucharest)", async (p) => {
  await mount(p, {}, { rooms: R });
  await click(p, '[data-key="vac-e1"]'); await p.waitForTimeout(100);
  await p.evaluate(() => {
    const set = (q, v) => { const i = card.shadowRoot.querySelector(q); i.value = v; i.dispatchEvent(new Event("change", { bubbles: true })); };
    set('input[data-vac="start"][data-house="e1"]', "2026-12-20T08:00");
    set('input[data-vac="end"][data-house="e1"]', "2026-12-27T18:30");
  });
  await click(p, '[data-action="vacation"][data-house="e1"]'); await p.waitForTimeout(100);
  const s = await last(p);
  eq(s.service, "set_vacation", "service");
  // 08:00 in Bucharest in December (UTC+2) is 06:00 UTC.
  eq([new Date(s.data.start).toISOString(), new Date(s.data.end).toISOString(), s.data.config_entry_id],
    ["2026-12-20T06:00:00.000Z", "2026-12-27T16:30:00.000Z", "e1"], "dates");
});
