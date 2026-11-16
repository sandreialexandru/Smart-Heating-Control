// The SHC panel: the house on top, the rooms on the side, the chosen room in the middle.
const ROOMS = [
  { id: "r1", name: "Bedroom", humidity: 62, wall: 84.4, alerts: [{ code: "mold_risk", params: { surface: 84, humidity: 62 }, room: "r1", message: "m" }] },
  { id: "r2", name: "Office", learned: false, source: "climate", climates: ["climate.office"],
    override: { temperature: 23, until: new Date(Date.now() + 2 * 3600e3).toISOString(), origin: "card", preset: null, applied: true }, state: "manual_override" },
  { id: "r3", name: "Living", window: true, state: "window_open", reasonKey: "window_open", demand: false, heating: false },
  { id: "r4", name: "Kid", current: null, dropAttrs: ["plan", "next_estimate", "levels", "offsets", "alerts", "humidity"], learned: false },
];
const openPanel = async (p, hass, opts) => {
  await p.evaluate(([h, o]) => mountPanel(h, o), [hass, opts || {}]);
  await p.waitForTimeout(250);
};
const inPanel = (p, fn, arg) => p.evaluate(([f, a]) => new Function("sr", "a", `return (${f})(sr, a)`)(panel.shadowRoot, a), [fn.toString(), arg]);
const clickIn = (p, sel) => inPanel(p, (sr, s) => { const el = sr.querySelector(s); if (!el) throw new Error("no " + s); el.click(); }, sel);
const shown = (p, sel) => inPanel(p, (sr, s) => { const el = sr.querySelector(s); return !!el && el.offsetParent !== null && !el.closest("[hidden]"); }, sel);

// Every text and every control of a part of the card or the panel.
const contents = (root) => {
  const texts = new Set();
  const walk = (node) => {
    for (const n of node.childNodes) {
      if (n.nodeType === 3) {
        const t = n.textContent.replace(/\s+/g, " ").trim();
        if (t) texts.add(t);
      } else if (n.nodeType === 1) walk(n);
    }
  };
  walk(root);
  const controls = new Set(
    [...root.querySelectorAll("[data-action]")].map((el) =>
      ["action", "entity", "option", "room", "key", "preset", "profile", "series", "zoom", "house"].map((k) => el.dataset[k] || "").join("|")
    )
  );
  return { texts: [...texts], controls: [...controls] };
};

test("the house on top, every room on the side, the first room open", async (p) => {
  await openPanel(p, { rooms: ROOMS });
  const r = await inPanel(p, (sr) => ({
    house: !!sr.querySelector(".phouse .block.house"),
    rows: [...sr.querySelectorAll(".pside .block.room.folded .name")].map((n) => n.innerText),
    open: sr.querySelector(".pmain .block.room .room-title, .pmain .block.room .name")?.innerText,
    chosen: [...sr.querySelectorAll(".pside .chosen .name")].map((n) => n.innerText),
    title: sr.querySelector(".ptop h1").innerText,
  }));
  ok(r.house, "house block");
  eq(r.rows, ["Bedroom", "Kid", "Living", "Office"], "rooms by name");
  ok(r.open.includes("Bedroom"), "first room open: " + r.open);
  eq(r.chosen, ["Bedroom"], "the open room marked");
  eq(r.title, "SHC", "title");
});

test("a room row opens that room; the address and the browser keep it", async (p) => {
  await openPanel(p, { rooms: ROOMS });
  await clickIn(p, '.pside [data-action="fold"][data-key="room-r2"]'); await p.waitForTimeout(150);
  const r = await inPanel(p, (sr) => ({ open: sr.querySelector(".pmain .block.room").innerText.includes("Office"), hash: location.hash, kept: localStorage.getItem("shc-panel-room") }));
  eq(r, { open: true, hash: "#r2", kept: "r2" }, "chosen");
  // A new panel (the page opened again) opens the same room.
  await p.evaluate(() => { history.replaceState(null, "", location.pathname); });
  await openPanel(p, { rooms: ROOMS });
  ok(await inPanel(p, (sr) => sr.querySelector(".pmain .block.room").innerText.includes("Office")), "kept in the browser");
  // The address wins.
  await p.evaluate(() => { location.hash = "#r3"; }); await p.waitForTimeout(150);
  ok(await inPanel(p, (sr) => sr.querySelector(".pmain .block.room").innerText.includes("Living")), "from the address");
  await p.evaluate(() => { localStorage.removeItem("shc-panel-room"); history.replaceState(null, "", location.pathname); });
});

test("nothing of the card is missing: every text and control of the house and of each room", async (p) => {
  // One clock for the card and the panel (times like "Sleep at 20:24" would differ across a minute).
  await p.clock.setFixedTime(new Date());
  for (const room of ROOMS) {
    const hass = { rooms: [room], source: { state: "auto", options: ["auto", "primary", "secondary"], active: "primary" }, scenarios: ["Home office"], scenario: "Home office" };
    await p.evaluate(([c, h]) => mount(c, h), [{}, hass]); await p.waitForTimeout(250);
    const card = await p.evaluate(`(${contents.toString()})(card.shadowRoot.querySelector("ha-card"))`);
    await openPanel(p, hass);
    const panel = await p.evaluate(`(${contents.toString()})(panel.shadowRoot)`);
    const missingTexts = card.texts.filter((t) => t !== "Heating" && !panel.texts.includes(t));
    const missingControls = card.controls.filter((c) => !panel.controls.includes(c));
    eq(missingTexts, [], `${room.name}: texts`);
    eq(missingControls, [], `${room.name}: controls`);
  }
});

test("the sections of the open room work as in the card (details, chart window)", async (p) => {
  await openPanel(p, { rooms: ROOMS });
  await clickIn(p, '.pmain [data-key="details-r1"]'); await p.waitForTimeout(150);
  ok(await inPanel(p, (sr) => sr.querySelector(".pmain").innerText.includes("Humidity")), "details open");
  await clickIn(p, '.pmain [data-key="chart-r1"]'); await p.waitForTimeout(400);
  eq(await inPanel(p, (sr) => { const d = sr.querySelector("dialog.chartpop"); return d && d.matches(":modal"); }), true, "modal chart window");
  await clickIn(p, '[data-action="closechart"]'); await p.waitForTimeout(150);
  eq(await inPanel(p, (sr) => !!sr.querySelector("dialog.chartpop")), false, "closed");
});

test("the title of the open room does not fold it", async (p) => {
  await openPanel(p, { rooms: ROOMS });
  await clickIn(p, '.pmain [data-action="fold"][data-key="room-r1"]'); await p.waitForTimeout(150);
  ok(await inPanel(p, (sr) => !sr.querySelector(".pmain .block.room.folded") && !!sr.querySelector(".pmain .block.room")), "still open");
});

test("the panel sends what the card sends (mode, a room for a while)", async (p) => {
  await openPanel(p, { rooms: [ROOMS[0]] });
  await clickIn(p, '.phouse [data-action="mode"][data-option="away"]'); await p.waitForTimeout(100);
  await clickIn(p, '.pmain [data-key="quick-r1"]'); await p.waitForTimeout(100);
  await clickIn(p, '.pmain [data-action="quick-preset"][data-preset="eco"]'); await p.waitForTimeout(100);
  const s = await p.evaluate(() => calls.service.map((c) => [c.domain, c.service, c.data.option || c.data.preset]));
  eq(s[0], ["select", "select_option", "away"], "mode");
  eq(s.at(-1), ["advanced_climate", "set_override", "eco"], "for a while");
});

test("phone: the house and the list, a room on the whole screen, Back to the list", async (p) => {
  await openPanel(p, { rooms: ROOMS }, { narrow: true });
  ok((await shown(p, ".phouse")) && (await shown(p, ".pside")) && !(await shown(p, ".pmain")), "list first");
  await clickIn(p, '.pside [data-action="fold"][data-key="room-r3"]'); await p.waitForTimeout(150);
  ok(!(await shown(p, ".phouse")) && !(await shown(p, ".pside")) && (await shown(p, ".pmain")), "the room alone");
  eq(await inPanel(p, (sr) => [sr.querySelector(".ptop h1").innerText, sr.querySelector(".pback").hidden]), ["Living", false], "Back and the name");
  await clickIn(p, ".pback"); await p.waitForTimeout(150);
  ok((await shown(p, ".pside")) && !(await shown(p, ".pmain")), "back to the list");
  eq(await p.evaluate(() => location.hash), "", "address without a room");
  const overflow = await p.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  ok(overflow <= 0, "no sideways scroll: " + overflow);
  await p.evaluate(() => localStorage.removeItem("shc-panel-room"));
}, { viewport: { width: 390, height: 844 }, touch: true });

test("no houses yet: says so", async (p) => {
  await p.evaluate(() => { const h = makeHass({ rooms: [] }); for (const id of Object.keys(h.states)) delete h.states[id]; mountPanel({}); panel.hass = h; });
  await p.waitForTimeout(200);
  ok(await inPanel(p, (sr) => sr.querySelector(".phouse").innerText.includes("No")), "empty message");
});

test("hover lights the whole row of a room, not a box inside it; a click on its margin opens it", async (p) => {
  await openPanel(p, { rooms: ROOMS });
  const at = await inPanel(p, (sr) => { const b = sr.querySelector('.pside [data-key="room-r2"]').closest(".block"); b.scrollIntoView({ block: "center" }); const r = b.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2, r.left + 4, r.top + r.height / 2]; });
  const look = () => inPanel(p, (sr) => { const b = sr.querySelector('.pside [data-key="room-r2"]'); return { row: getComputedStyle(b.closest(".block")).backgroundColor, button: getComputedStyle(b).backgroundColor }; });
  const before = await look();
  await p.mouse.move(at[0], at[1]); await p.waitForTimeout(150);
  const hover = await look();
  ok(hover.row !== before.row, "the row is lit: " + JSON.stringify([before, hover]));
  eq(hover.button, "rgba(0, 0, 0, 0)", "no box inside the row");
  await p.mouse.click(at[2], at[3]); await p.waitForTimeout(150);
  ok(await inPanel(p, (sr) => sr.querySelector(".pmain .block.room").innerText.includes("Office")), "opened from the margin");
  await p.evaluate(() => { localStorage.removeItem("shc-panel-room"); history.replaceState(null, "", location.pathname); });
});

test("two houses: both on top, the rooms under the name of their house", async (p) => {
  await p.evaluate(() => {
    const a = makeHass({ rooms: [{ id: "r1", name: "Bedroom" }] });
    const b = makeHass({ entry: "e2", houseName: "Cabin", prefix: "cabin", rooms: [{ id: "c1", name: "Loft", prefix: "loft" }] });
    Object.assign(a.states, b.states);
    const host = document.getElementById("host"); host.innerHTML = ""; host.style.maxWidth = "none";
    window.panel = document.createElement("shc-panel"); panel.hass = a; host.appendChild(panel);
  });
  await p.waitForTimeout(250);
  const r = await inPanel(p, (sr) => ({
    houses: sr.querySelectorAll(".phouse .block.house").length,
    list: [...sr.querySelectorAll(".pside .hname, .pside .block.room .name")].map((n) => n.innerText),
  }));
  eq(r.houses, 2, "two houses");
  eq(r.list, ["Home", "Bedroom", "Cabin", "Loft"], "rooms under their house, the houses as in the card");
});

test("a room that is gone (kept in the browser): the first room opens", async (p) => {
  await p.evaluate(() => localStorage.setItem("shc-panel-room", "gone"));
  await openPanel(p, { rooms: ROOMS });
  ok(await inPanel(p, (sr) => sr.querySelector(".pmain .block.room").innerText.includes("Bedroom")), "first room");
  await p.evaluate(() => localStorage.removeItem("shc-panel-room"));
});

test("phone: a room unknown in the address shows the list", async (p) => {
  await p.evaluate(() => { history.replaceState(null, "", location.pathname + "#nope"); });
  await openPanel(p, { rooms: ROOMS }, { narrow: true });
  ok((await shown(p, ".pside")) && !(await shown(p, ".pmain")), "the list");
  await p.evaluate(() => { history.replaceState(null, "", location.pathname); });
}, { viewport: { width: 390, height: 844 } });

test("from wide to narrow (a window made smaller): the open room stays, with Back", async (p) => {
  await openPanel(p, { rooms: ROOMS });
  await clickIn(p, '.pside [data-key="room-r3"]'); await p.waitForTimeout(150);
  await p.evaluate(() => { panel.narrow = true; }); await p.waitForTimeout(150);
  ok((await shown(p, ".pmain")) && !(await shown(p, ".pside")), "the room");
  eq(await inPanel(p, (sr) => sr.querySelector(".ptop h1").innerText), "Living", "its name");
  await p.evaluate(() => { panel.narrow = false; }); await p.waitForTimeout(150);
  ok((await shown(p, ".pmain")) && (await shown(p, ".pside")) && (await shown(p, ".phouse")), "all again");
  await p.evaluate(() => { localStorage.removeItem("shc-panel-room"); history.replaceState(null, "", location.pathname); });
});

test("updates while the chart window is open: the same window, still modal; the open room kept", async (p) => {
  await openPanel(p, { rooms: ROOMS });
  await clickIn(p, '.pside [data-key="room-r2"]'); await p.waitForTimeout(150);
  await clickIn(p, '.pmain [data-key="chart-r2"]'); await p.waitForTimeout(400);
  const same = await p.evaluate(async (rooms) => {
    const d1 = panel.shadowRoot.querySelector("dialog.chartpop");
    for (let i = 1; i <= 10; i++) { panel.hass = makeHass({ rooms: rooms.map((r) => ({ ...r, current: 20 + i / 10 })), tick: i }); await sleep(30); }
    const d2 = panel.shadowRoot.querySelector("dialog.chartpop");
    return { same: d1 === d2, modal: d2.matches(":modal"), room: panel.shadowRoot.querySelector(".pmain .block.room").innerText.includes("Office") };
  }, ROOMS);
  eq(same, { same: true, modal: true, room: true }, "kept");
  await p.evaluate(() => { localStorage.removeItem("shc-panel-room"); history.replaceState(null, "", location.pathname); });
});

test("dark theme: the panel and its rows follow the theme", async (p) => {
  await p.evaluate(() => { const b = document.body.style; b.setProperty("--primary-background-color", "#111"); b.setProperty("--card-background-color", "#1c1c1c"); b.setProperty("--primary-text-color", "#e1e1e1"); });
  await openPanel(p, { rooms: ROOMS, dark: true });
  const c = await inPanel(p, (sr) => ({ page: getComputedStyle(sr.host).backgroundColor, text: getComputedStyle(sr.querySelector(".pside .name")).color }));
  eq(c, { page: "rgb(17, 17, 17)", text: "rgb(225, 225, 225)" }, "theme colours");
}, { dark: true });

// ---------------------------------------------------------------- statistics and history
const R4 = [{ id: "r1", name: "Bedroom" }, { id: "r2", name: "Kid", preset: "sleep" }, { id: "r3", name: "Living" }];
const tab = async (p, t) => { await clickIn(p, `[data-action="panel-tab"][data-option="${t}"]`); await p.waitForTimeout(300); };
const extraText = (p) => inPanel(p, (sr) => sr.querySelector(".pextra").innerText);

test("statistics: the house by day, the rooms by their time, the starts asked; weeks and months", async (p) => {
  await openPanel(p, { rooms: R4 });
  await tab(p, "stats");
  const r = await inPanel(p, (sr) => ({
    bars: sr.querySelectorAll(".ps-cols")[0].querySelectorAll(".ps-col").length,
    rooms: [...sr.querySelectorAll(".ps-row .ps-name")].map((n) => n.innerText),
    pct: [...sr.querySelectorAll(".ps-row .ps-pct")].map((n) => parseInt(n.innerText, 10)),
    hidden: ["phouse", "pside", "pmain"].map((c) => getComputedStyle(sr.querySelector(`.${c}`)).display),
  }));
  eq(r.bars, 14, "14 days");
  eq(r.rooms.length, 3, "every room");
  ok(Math.abs(r.pct.reduce((a, b) => a + b, 0) - 100) <= 2, "shares add up: " + r.pct);
  eq(r.hidden, ["none", "none", "none"], "the rooms tab hidden");
  const t = await extraText(p);
  ok(t.includes("Heating time of the house") && t.includes("last 14 days") && t.includes("Times the heat source was asked to start"), t.slice(0, 200));
  const ask = await p.evaluate(() => calls.ws.filter((m) => m.type === "recorder/statistics_during_period").at(-1));
  eq([ask.period, ask.types, ask.statistic_ids.length, !!ask.end_time], ["day", ["change", "mean", "min", "max"], 11, true], "the statistics asked: heating times and temperatures, in one call");
  ok(["sensor.home_outdoor_average", "sensor.kid_room_temperature", "sensor.kid_target_temperature"].every((id) => ask.statistic_ids.includes(id)), "the temperatures");
  ok(ask.statistic_ids.includes("sensor.home_heating_runtime") && ask.statistic_ids.includes("sensor.kid_heating_runtime"), "house and rooms");
  await clickIn(p, '[data-action="stats-period"][data-option="month"]'); await p.waitForTimeout(300);
  eq(await inPanel(p, (sr) => sr.querySelectorAll(".ps-cols").length), 1, "no starts by month (only by day)");
  ok((await extraText(p)).includes("last 12 months"), "months");
  eq((await p.evaluate(() => calls.ws.filter((m) => m.type === "recorder/statistics_during_period").at(-1))).period, "month", "asked by month");
  await p.evaluate(() => localStorage.removeItem("shc-panel-tab"));
});

test("statistics: the tab is kept in the browser; the rows sorted by time", async (p) => {
  await openPanel(p, { rooms: R4 });
  await tab(p, "stats");
  await openPanel(p, { rooms: R4 });
  await p.waitForTimeout(300);
  ok(await inPanel(p, (sr) => getComputedStyle(sr.querySelector(".pextra")).display !== "none"), "statistics again");
  const hours = await inPanel(p, (sr) => [...sr.querySelectorAll(".ps-row .ps-fill")].map((f) => parseFloat(f.style.width)));
  eq([...hours].sort((a, b) => b - a), hours, "longest first");
  await p.evaluate(() => localStorage.removeItem("shc-panel-tab"));
});

test("statistics: days without history kept have no bar; statistics that fail say so", async (p) => {
  await openPanel(p, { rooms: R4, emptyHistory: true });
  await tab(p, "stats");
  const starts = await inPanel(p, (sr) => { const c = sr.querySelectorAll(".ps-cols")[1]; return [...c.querySelectorAll(".ps-bar")].map((b) => parseFloat(b.style.height)); });
  eq(starts.filter((h) => h > 0).length, 0, "no bars");
  ok((await inPanel(p, (sr) => sr.querySelectorAll(".ps-cols")[1].querySelector(".ps-col").title)).endsWith("–"), "a dash, not 0");
  await openPanel(p, { rooms: R4, statsFail: true });
  await p.waitForTimeout(300);
  ok((await extraText(p)).includes("The statistics could not be read"), "failure");
  await p.evaluate(() => localStorage.removeItem("shc-panel-tab"));
});

test("history: newest first by day; decisions and alerts with start, end and the restart", async (p) => {
  await openPanel(p, { rooms: R4 });
  await tab(p, "history");
  const r = await inPanel(p, (sr) => ({
    days: sr.querySelectorAll(".ph-day").length,
    first: sr.querySelector(".ph-list li").innerText.replace(/\s+/g, " "),
    lines: [...sr.querySelectorAll(".ph-list li")].map((li) => li.innerText.replace(/\s+/g, " ")),
  }));
  eq(r.days, 3, "three days");
  ok(r.first.includes("Schedule: Home"), "newest first: " + r.first);
  const mold = r.lines.find((l) => l.includes("Mold risk"));
  ok(mold && mold.includes("still applies") && !mold.includes("Mold risk: Mold risk"), "mold once, still: " + mold);
  const dev = r.lines.find((l) => l.includes("Device unavailable"));
  ok(dev && dev.includes("(45 min)"), "how long: " + dev);
  const out = r.lines.find((l) => l.includes("Whole house"));
  ok(out && out.includes("Home Assistant restarted"), "the restart: " + out);
  eq(await p.evaluate(() => calls.ws.filter((m) => m.type === "advanced_climate/history").length), 1, "asked once");
  await p.evaluate(() => localStorage.removeItem("shc-panel-tab"));
});

test("history: only decisions, only alerts, one room (with the alerts of the whole house)", async (p) => {
  await openPanel(p, { rooms: R4 });
  await tab(p, "history");
  const lines = () => inPanel(p, (sr) => [...sr.querySelectorAll(".ph-list li")].map((li) => [li.className, li.innerText.replace(/\s+/g, " ")]));
  await clickIn(p, '[data-action="history-kind"][data-option="decision"]'); await p.waitForTimeout(150);
  ok((await lines()).every(([c]) => c === "ph-decision"), "decisions only");
  await clickIn(p, '[data-action="history-kind"][data-option="alert"]'); await p.waitForTimeout(150);
  eq((await lines()).length, 3, "the three alerts");
  await clickIn(p, '[data-action="history-kind"][data-option="all"]'); await p.waitForTimeout(150);
  await inPanel(p, (sr) => { const s = sr.querySelector(".ph-room"); s.value = "r2"; s.dispatchEvent(new Event("change", { bubbles: true })); });
  await p.waitForTimeout(150);
  const kid = await lines();
  ok(kid.every(([, t]) => t.includes("Kid") || t.includes("Whole house")), "Kid and the whole house: " + JSON.stringify(kid));
  ok(kid.some(([, t]) => t.includes("Whole house")) && !kid.some(([, t]) => t.includes("Bedroom")), "not the alerts of Bedroom");
  await p.evaluate(() => localStorage.removeItem("shc-panel-tab"));
});

test("history that fails says so; Romanian texts", async (p) => {
  await openPanel(p, { rooms: R4, historyLogFails: true });
  await tab(p, "history");
  ok((await extraText(p)).includes("The history could not be read"), "failure");
  await openPanel(p, { rooms: R4, lang: "ro" });
  await p.waitForTimeout(300);
  const t = await extraText(p);
  ok(t.includes("Decizii") && t.includes("Toate camerele") && t.includes("Toată casa") && t.includes("Home Assistant a repornit"), t.slice(0, 300));
  eq(await inPanel(p, (sr) => [...sr.querySelectorAll('[data-action="panel-tab"]')].map((b) => b.innerText)), ["Camere", "Program", "Statistici", "Istoric"], "tabs");
  await p.evaluate(() => localStorage.removeItem("shc-panel-tab"));
});

test("phone: the tabs over the list, none over an open room; statistics without sideways scroll", async (p) => {
  await openPanel(p, { rooms: R4 }, { narrow: true });
  ok(await shown(p, ".ptabs"), "tabs over the list");
  await clickIn(p, '.pside [data-key="room-r1"]'); await p.waitForTimeout(150);
  ok(!(await shown(p, ".ptabs")), "no tabs over a room");
  await clickIn(p, ".pback"); await p.waitForTimeout(150);
  await tab(p, "stats");
  const over = await p.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  ok(over <= 0, "no sideways scroll: " + over);
  eq(await inPanel(p, (sr) => getComputedStyle(sr.querySelector(".ps-val")).display), "none", "no values over the bars");
  await p.evaluate(() => { localStorage.removeItem("shc-panel-tab"); localStorage.removeItem("shc-panel-room"); history.replaceState(null, "", location.pathname); });
}, { viewport: { width: 390, height: 844 }, touch: true });

test("statistics: a tap on a bar shows its period (the house, the rooms, the starts); again or ✕ the whole range", async (p) => {
  await openPanel(p, { rooms: R4 });
  await tab(p, "stats");
  const pick = (i, chart = 0) => inPanel(p, (sr, a) => sr.querySelectorAll(".ps-cols")[a[1]].querySelectorAll(".ps-col")[a[0]].click(), [i, chart]);
  const look = () => inPanel(p, (sr) => ({
    detail: sr.querySelector(".ps-detail")?.innerText.replace(/\s+/g, " ") || null,
    rooms: sr.querySelectorAll(".ps-title")[1].innerText,
    picked: [...sr.querySelectorAll(".ps-col.picked")].length,
    dim: [...sr.querySelectorAll(".ps-col.dim")].length,
    hours: [...sr.querySelectorAll(".ps-row")].map((r) => r.querySelector(".ps-h").innerText),
  }));
  const whole = await look();
  await pick(9); await p.waitForTimeout(150);
  const one = await look();
  ok(one.detail && /\d+ starts asked/.test(one.detail), "detail: " + one.detail);
  ok(!one.rooms.includes("last 14 days") && one.rooms.startsWith("Heating time by room"), "rooms of that day: " + one.rooms);
  eq([one.picked, one.dim], [2, 26], "the day marked in both charts");
  ok(JSON.stringify(one.hours) !== JSON.stringify(whole.hours), "the rooms of that day only");
  // The day of the starts chart chooses the same day.
  await pick(9, 1); await p.waitForTimeout(150);
  eq((await look()).detail, null, "the same day again: the whole range");
  await pick(3, 1); await p.waitForTimeout(150);
  eq((await look()).picked, 2, "from the starts chart");
  await clickIn(p, ".ps-unpick"); await p.waitForTimeout(150);
  eq(await look(), whole, "✕: the whole range");
  await pick(2); await p.waitForTimeout(150);
  await clickIn(p, '[data-action="stats-period"][data-option="week"]'); await p.waitForTimeout(300);
  eq((await look()).detail, null, "another period: the whole range");
  await pick(11); await p.waitForTimeout(150);
  ok(/ – /.test((await look()).detail), "a week from its first to its last day");
  await p.evaluate(() => localStorage.removeItem("shc-panel-tab"));
});

test("statistics: the outdoor temperature under each period and in its detail; the temperature and target of each room", async (p) => {
  await openPanel(p, { rooms: R4 });
  await tab(p, "stats");
  const look = () => inPanel(p, (sr) => ({
    title: sr.querySelector(".ps-title").innerText,
    outs: [...sr.querySelectorAll(".ps-cols")[0].querySelectorAll(".ps-out")].map((o) => o.innerText),
    startsOut: sr.querySelectorAll(".ps-cols")[1].querySelectorAll(".ps-out").length,
    temps: [...sr.querySelectorAll(".ps-row .ps-temp")].map((t) => t.innerText),
    tip: sr.querySelector(".ps-row").title,
    detail: sr.querySelector(".ps-detail")?.innerText.replace(/\s+/g, " ") || null,
  }));
  const whole = await look();
  eq(whole.outs.length, 14, "one outdoor mean a day");
  ok(whole.outs.every((o) => /^\d+\.\d°$/.test(o)), "outdoor means: " + whole.outs);
  eq(whole.startsOut, 0, "none under the starts");
  ok(/outdoor 4\.\d° \(1\.0° … 8\.0°\)/.test(whole.title), "the range of the whole interval in the title: " + whole.title);
  eq(whole.temps.length, 3, "every room");
  ok(whole.temps.every((t) => /^2\d\.\d° \(target 2\d\.\d°\)$/.test(t)), "room temperatures: " + whole.temps);
  ok(/^2\d\.\d° \(1\d\.\d° … 2\d\.\d°\)$/.test(whole.tip), "minimum and maximum of the room on hover: " + whole.tip);
  await inPanel(p, (sr) => sr.querySelectorAll(".ps-cols")[0].querySelectorAll(".ps-col")[9].click()); await p.waitForTimeout(150);
  const one = await look();
  ok(/outdoor \d+\.\d° \(\d\.0° … \d\.0°\)/.test(one.detail), "the outdoor of that day in the detail: " + one.detail);
  ok(JSON.stringify(one.temps) !== JSON.stringify(whole.temps), "the rooms of that day only: " + one.temps);
  // Statistics without temperatures (a recorder that kept none): only the times.
  await openPanel(p, { rooms: R4, noTempStats: true });
  await p.waitForTimeout(300);
  const none = await look();
  eq([none.outs.length, none.title.includes("outdoor")], [0, false], "no outdoor line");
  ok(none.temps.every((t) => t === ""), "no room temperatures: " + none.temps);
  await p.evaluate(() => localStorage.removeItem("shc-panel-tab"));
});

test("statistics in °F and in Romanian", async (p) => {
  await openPanel(p, { rooms: R4, unit: "°F", lang: "ro" });
  await tab(p, "stats");
  const r = await inPanel(p, (sr) => ({ title: sr.querySelector(".ps-title").innerText, temp: sr.querySelector(".ps-row .ps-temp").innerText }));
  ok(/afară 4\d\.\d° \(33\.8° … 46\.4°\)/.test(r.title), "°F outdoor: " + r.title);
  ok(/^6\d\.\d° \(țintă [67]\d\.\d°\)$/.test(r.temp), "°F room: " + r.temp);
  await p.evaluate(() => localStorage.removeItem("shc-panel-tab"));
});

test("schedule tab: every room on today, another day, no active profile, an outside schedule; a tap opens the editor", async (p) => {
  const rooms = [
    { id: "r1", name: "Bedroom" },
    { id: "r2", name: "Office", profileDays: { workday: { days: "workday", enabled: false }, weekend: { days: "weekend", enabled: false } } },
    { id: "r3", name: "Living", scheduleEditable: false },
  ];
  await openPanel(p, { rooms });
  await clickIn(p, '[data-action="panel-tab"][data-option="week"]'); await p.waitForTimeout(100);
  const today = await p.evaluate(() => (new Date().getDay() + 6) % 7);
  const look = () => inPanel(p, (sr) => ({
    day: [...sr.querySelectorAll('[data-action="week-day"]')].findIndex((b) => b.classList.contains("active")),
    rows: [...sr.querySelectorAll(".pw-row")].map((r) => r.querySelector(".pw-name").innerText),
    profile: sr.querySelector('.pw-row[data-room="r1"] .pw-prof').innerText,
    segs: sr.querySelectorAll('.pw-row[data-room="r1"] .sseg').length,
    now: !!sr.querySelector('.pw-row[data-room="r1"] .pw-now'),
    gap: sr.querySelector('.pw-row[data-room="r2"] .pw-gap')?.innerText || null,
    outside: sr.querySelector(".pw-row .pw-ext")?.innerText || null,
    outsideButton: !!sr.querySelector('button.pw-row[data-room="r3"]'),
  }));
  const first = await look();
  eq([first.day, first.rows, first.now], [today, ["Bedroom", "Living", "Office"], true], "today, every room (in the order of the card), now on the bar");
  eq(first.profile, today < 5 ? "workday" : "weekend", "the profile of today");
  eq(first.segs, 3, "the slots of the profile");
  eq(first.gap, "No active profile: frost protection", "a room without an active profile");
  ok(/Schedule helper/.test(first.outside) && !first.outsideButton, "a room on a Schedule helper is not opened from here: " + first.outside);
  const other = today < 5 ? 5 : 0;
  await clickIn(p, `[data-action="week-day"][data-option="${other}"]`); await p.waitForTimeout(100);
  const second = await look();
  eq([second.day, second.profile, second.now], [other, other < 5 ? "workday" : "weekend", false], "another day: its profile, no now");
  // A tap on a room: the Rooms tab with that room and its schedule editor open.
  await clickIn(p, 'button.pw-row[data-room="r1"]'); await p.waitForTimeout(150);
  const opened = await inPanel(p, (sr) => ({
    tab: panel.getAttribute("tab"),
    room: sr.querySelector(".pmain .block.room")?.dataset.key || sr.querySelector(".pmain [data-key^='room-']")?.dataset.key,
    editor: !!sr.querySelector(".pmain .editor"),
  }));
  eq([opened.tab, opened.editor], ["rooms", true], "the editor of the room");
  ok(String(opened.room).includes("r1"), "that room: " + opened.room);
  await p.evaluate(() => localStorage.removeItem("shc-panel-tab"));
});

test("statistics: what each room learned, or how far its learning is; a tap opens its Details", async (p) => {
  await openPanel(p, { rooms: ROOMS });
  await clickIn(p, '[data-action="panel-tab"][data-option="stats"]'); await p.waitForTimeout(150);
  const r = await inPanel(p, (sr) => [...sr.querySelectorAll(".pl-row")].map((row) => ({
    room: row.dataset.room,
    learning: row.classList.contains("pl-learning"),
    values: [...row.querySelectorAll(".pl-val")].map((v) => v.innerText.replace(/\s+/g, " ")),
    state: row.querySelector(".pl-state").innerText,
  })));
  eq(r.map((x) => [x.room, x.learning]), [["r1", false], ["r4", true], ["r3", false], ["r2", true]], "every room (in the order of the card), learned or not");
  eq(r[0].values, ["Heating 40 min/°C", "Inertia 30 min", "Heat loss 0.75 °C/h", "Weather curve +0.050 °C/h"], "the learned values");
  ok(/^learned/.test(r[0].state), "learned: " + r[0].state);
  eq(r[1].values, [], "no values while learning");
  ok(/^learning… with heating [\d.]+ of 4 h, without heating [\d.]+ of 4 h$/.test(r[1].state), "the progress: " + r[1].state);
  await clickIn(p, '.pl-row[data-room="r2"]'); await p.waitForTimeout(150);
  const opened = await inPanel(p, (sr) => ({ tab: panel.getAttribute("tab"), details: !!sr.querySelector('.pmain [data-section="details-r2"]') }));
  eq(opened, { tab: "rooms", details: true }, "the Details of that room");
  await p.evaluate(() => localStorage.removeItem("shc-panel-tab"));
});

test("history: the alerts on now on top, once each, with their room and since when; counted on the tab", async (p) => {
  const house = { key: "out", code: "outdoor_unavailable", params: {}, message: "m" };
  const rooms = [
    { id: "r1", name: "Bedroom", alerts: [{ key: "mold", code: "mold_risk", params: { surface: 84, humidity: 62 }, message: "m" }, house] },
    { id: "r2", name: "Office", alerts: [house] },
    { id: "r3", name: "Living", alerts: [house] },
  ];
  await openPanel(p, { rooms });
  const count = await inPanel(p, (sr) => sr.querySelector('[data-action="panel-tab"][data-option="history"] .tabcount')?.innerText);
  eq(count, "2", "two alerts on now, counted on the tab");
  await clickIn(p, '[data-action="panel-tab"][data-option="history"]'); await p.waitForTimeout(300);
  const r = await inPanel(p, (sr) => [...sr.querySelectorAll(".pa-list li")].map((li) => ({
    text: li.querySelector(".ph-text").innerText.replace(/\s+/g, " "),
    open: li.querySelector('[data-action="alert-room"]')?.dataset.room || null,
  })));
  eq(r.length, 2, "once each");
  ok(/^Bedroom Mold risk: .* · since /.test(r[0].text), "the room and since when (from the journal): " + r[0].text);
  eq(r[0].open, "r1", "its room opens");
  ok(/^Whole house Outdoor temperature unavailable/.test(r[1].text), "reported by every room: the house's: " + r[1].text);
  eq(r[1].open, null, "nothing to open for the house");
  await clickIn(p, '[data-action="alert-room"][data-room="r1"]'); await p.waitForTimeout(150);
  eq(await inPanel(p, () => panel.getAttribute("tab")), "rooms", "the room opens");
  // No alerts: said so, no count on the tab.
  await openPanel(p, { rooms: [{ id: "r1", name: "Bedroom" }] });
  await clickIn(p, '[data-action="panel-tab"][data-option="history"]'); await p.waitForTimeout(300);
  const none = await inPanel(p, (sr) => ({
    text: sr.querySelector(".pa-now p")?.innerText,
    count: !!sr.querySelector(".tabcount"),
  }));
  eq(none, { text: "No alerts now", count: false }, "no alerts");
  await p.evaluate(() => localStorage.removeItem("shc-panel-tab"));
});
