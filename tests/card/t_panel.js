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
  // What a wide panel says on hover (its compact house bar).
  const titles = [...root.querySelectorAll("[title]")].map((el) => el.getAttribute("title"));
  const controls = new Set(
    [...root.querySelectorAll("[data-action]")].map((el) =>
      ["action", "entity", "option", "room", "key", "preset", "profile", "series", "zoom", "house"].map((k) => el.dataset[k] || "").join("|")
    )
  );
  return { texts: [...texts], controls: [...controls], titles };
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
  eq(r.title, "Home", "title: the name of the house");
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
    // Wide, the house is one bar: its values and names are said on hover; the
    // heating time names only the period shown; the chart is drawn beside the
    // room, so it has no button.
    const chart = await inPanel(p, (sr, id) => !!sr.querySelector(`.pmain .prw-chart [data-chartcard="${id}"]`), room.id);
    const said = (t) => panel.texts.includes(t) || panel.titles.some((x) => x.includes(t));
    const otherPeriod = (t) => /^Heating time · this (week|month)$/.test(t);
    const missingTexts = card.texts.filter((t) => t !== "Heating" && !said(t) && !otherPeriod(t) && !(t === "Chart" && chart));
    const missingControls = card.controls.filter((c) => !panel.controls.includes(c) && !(chart && c === `fold||||chart-${room.id}|||||`));
    eq(missingTexts, [], `${room.name}: texts`);
    eq(missingControls, [], `${room.name}: controls`);
  }
});

test("the sections of the open room work as in the card (details, chart window)", async (p) => {
  await openPanel(p, { rooms: ROOMS });
  await clickIn(p, '.pmain [data-key="details-r1"]'); await p.waitForTimeout(150);
  ok(await inPanel(p, (sr) => sr.querySelector(".pmain").innerText.includes("Humidity")), "details open");
  // Wide: the chart beside the room, the day and the levels under them, no chart button.
  const wide = await inPanel(p, (sr) => ({
    chart: !!sr.querySelector('.pmain .prw-chart [data-chartcard="r1"]'),
    button: !!sr.querySelector('.pmain [data-key="chart-r1"]'),
    today: !!sr.querySelector(".pmain .prw-below .today"),
    levels: [...sr.querySelectorAll(".pmain .prw-level")].map((l) => l.innerText.replace(/\s+/g, " ").trim()),
  }));
  eq([wide.chart, wide.button, wide.today], [true, false, true], "chart beside, no button, the day under");
  eq(wide.levels.slice(0, 2), ["Home 21°", "Eco 18°"], "the levels with their temperatures");
  // On a phone the chart opens in its window, as in the card.
  await p.evaluate(() => history.replaceState(null, "", "#r1"));
  await openPanel(p, { rooms: ROOMS }, { narrow: true });
  await clickIn(p, '.pmain [data-key="chart-r1"]'); await p.waitForTimeout(400);
  eq(await inPanel(p, (sr) => { const d = sr.querySelector("dialog.chartpop"); return d && d.matches(":modal"); }), true, "modal chart window");
  await clickIn(p, '[data-action="closechart"]'); await p.waitForTimeout(150);
  eq(await inPanel(p, (sr) => !!sr.querySelector("dialog.chartpop")), false, "closed");
  await p.evaluate(() => { localStorage.removeItem("shc-panel-room"); history.replaceState(null, "", location.pathname); });
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
  eq(await inPanel(p, (sr) => sr.querySelector(".ptop h1").innerText), "Smart Heating Control", "the title: the integration");
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
  // The chart window: a phone (wide, the chart is beside the room).
  await openPanel(p, { rooms: ROOMS }, { narrow: true });
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
  // The colour of the heating time, as the bars of the house: not the level of the
  // room now (a manual temperature has none, and the bar was grey on grey).
  const colors = await inPanel(p, (sr) => [...new Set([...sr.querySelectorAll(".ps-row .ps-fill")].map((f) => f.style.getPropertyValue("--c")))]);
  eq(colors, ["var(--ac-accent)"], "one colour");
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
  eq(await inPanel(p, (sr) => [...sr.querySelectorAll('[data-action="panel-tab"]')].map((b) => b.innerText)), ["Camere", "Ansamblu", "Program", "Statistici", "Istoric", "Dispozitive"], "tabs");
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

test("statistics: the outdoor temperature on the line over the periods and in their detail; the temperature and target of each room", async (p) => {
  await openPanel(p, { rooms: R4 });
  await tab(p, "stats");
  const look = () => inPanel(p, (sr) => ({
    title: sr.querySelector(".ps-title").innerText,
    outs: [...sr.querySelectorAll(".ps-cols")[0].querySelectorAll("circle.ps-hit")].map((o) => o.getAttribute("aria-label")),
    under: sr.querySelectorAll(".ps-cols .ps-out").length,
    startsOut: sr.querySelectorAll(".ps-cols")[1].querySelectorAll(".ps-out").length,
    temps: [...sr.querySelectorAll(".ps-row .ps-temp")].map((t) => t.innerText),
    tip: sr.querySelector(".ps-row").title,
    detail: sr.querySelector(".ps-detail")?.innerText.replace(/\s+/g, " ") || null,
  }));
  const whole = await look();
  eq([whole.outs.length, whole.under], [14, 0], "one point a day; no more numbers under the bars");
  ok(whole.outs.every((o) => /^\d+ \w{3}: \d+\.\d° \(\d\.0° … \d\.0°\)$/.test(o)), "each point: its day, mean, lowest and highest: " + whole.outs);
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

test("schedule tab: today and the next 6 days as the integration runs them; no active profile; an outside schedule; a tap opens the editor", async (p) => {
  const rooms = [
    { id: "r1", name: "Bedroom" },
    { id: "r2", name: "Office", profileDays: { workday: { days: "workday", enabled: false }, weekend: { days: "weekend", enabled: false } } },
    { id: "r3", name: "Living", scheduleEditable: false },
  ];
  await openPanel(p, { rooms });
  await clickIn(p, '[data-action="panel-tab"][data-option="week"]'); await p.waitForTimeout(200);
  const look = () => inPanel(p, (sr) => ({
    days: [...sr.querySelectorAll('[data-action="week-day"]')].map((b) => b.innerText.trim()),
    day: [...sr.querySelectorAll('[data-action="week-day"]')].findIndex((b) => b.classList.contains("active")),
    rows: [...sr.querySelectorAll(".pw-row")].map((r) => r.querySelector(".pw-name").innerText),
    profile: sr.querySelector('.pw-main[data-room="r1"] .pw-prof').innerText,
    segs: [...sr.querySelectorAll('.pw-main[data-room="r1"] .sseg')].map((x) => x.title),
    now: !!sr.querySelector('.pw-main[data-room="r1"] .pw-now'),
    gap: sr.querySelector('.pw-main[data-room="r2"] .pw-gap')?.innerText || null,
    outside: sr.querySelector(".pw-row .pw-ext")?.innerText || null,
    outsideButton: !!sr.querySelector('button.pw-main[data-room="r3"]'),
    asked: window.calls.ws.filter((c) => c.type === "advanced_climate/week").length,
  }));
  const first = await look();
  const weekday = await p.evaluate(() => (new Date().getDay() + 6) % 7);
  eq([first.days.length, first.day, first.rows, first.now], [7, 0, ["Bedroom", "Living", "Office"], true], "7 days from today, every room, now on today");
  ok(/^\w{3} \d{1,2}$/.test(first.days[0]), "a day with its date: " + first.days[0]);
  eq(first.profile, weekday < 5 ? "workday" : "weekend", "the profile of today");
  ok(first.segs.length >= 2 && /^Sleep 18\.5° 00:00–/.test(first.segs[0]), "the levels of the day from midnight: " + first.segs);
  eq(first.gap, "No active profile: frost protection", "a room without an active profile");
  ok(/Schedule helper/.test(first.outside) && !first.outsideButton, "a room on a Schedule helper is not opened from here: " + first.outside);
  eq(first.asked, 1, "asked once");
  await clickIn(p, '.pw-days .seg:nth-child(4)'); await p.waitForTimeout(100);
  const later = await look();
  eq([later.day, later.now], [3, false], "another day: no now");
  // A tap on a room: the Rooms tab with that room and its schedule editor open.
  await clickIn(p, 'button.pw-main[data-room="r1"]'); await p.waitForTimeout(150);
  const opened = await inPanel(p, (sr) => ({ tab: panel.getAttribute("tab"), editor: !!sr.querySelector(".pmain .editor") }));
  eq(opened, { tab: "rooms", editor: true }, "the editor of the room");
  await p.evaluate(() => localStorage.removeItem("shc-panel-tab"));
});

test("schedule tab: a holiday, a profile and a level from the calendar, the vacation", async (p) => {
  const week = {
    holiday: [1],
    forced: { day: 2, profile: "weekend" },
    levels: [{ day: 3, from: "10:00", to: "14:00", preset: "eco", summary: "Eco" }],
    vacation: { fromDay: 4, from: "08:00", toDay: 5, to: "20:00", resume: "18:00" },
  };
  await openPanel(p, { rooms: [{ id: "r1", name: "Bedroom" }], week });
  await clickIn(p, '[data-action="panel-tab"][data-option="week"]'); await p.waitForTimeout(200);
  const day = async (i) => {
    await clickIn(p, `.pw-days .seg:nth-child(${i + 1})`); await p.waitForTimeout(80);
    return inPanel(p, (sr) => ({
      notes: [...sr.querySelectorAll(".pw-notes li")].map((li) => li.innerText),
      profile: sr.querySelector('.pw-main[data-room="r1"] .pw-prof').innerText,
      over: [...sr.querySelectorAll('.pw-main[data-room="r1"] .pw-ov')].map((o) => ({ title: o.title, vac: o.classList.contains("pw-vac") })),
      first: sr.querySelector('.pw-main[data-room="r1"] .sseg')?.title || "",
    }));
  };
  const d1 = await day(1);
  ok(d1.notes.some((n) => /^Day off \(holiday\)/.test(n)), "the holiday: " + d1.notes);
  eq(d1.profile, "weekend", "the profile of weekend days");
  const d2 = await day(2);
  ok(d2.notes.includes("From the calendar: the profile weekend"), "a profile from the calendar: " + d2.notes);
  eq(d2.profile, "weekend · calendar", "marked in the row");
  const d3 = await day(3);
  ok(d3.notes.includes("From the calendar: Eco 10:00–14:00"), "a level from the calendar: " + d3.notes);
  eq(d3.over, [{ title: "calendar: Eco 10:00–14:00", vac: false }], "over the bar");
  const d4 = await day(4);
  ok(d4.notes.some((n) => /^Vacation from /.test(n)), "the vacation: " + d4.notes);
  eq(d4.over.map((o) => [o.vac, o.title]), [[true, "Vacation: Away 08:00–00:00"]], "from 08:00 to the end of the day");
  const d5 = await day(5);
  eq(d5.over.map((o) => o.title), ["Vacation: Away 00:00–18:00"], "until the heating starts again before its end");
  await p.evaluate(() => localStorage.removeItem("shc-panel-tab"));
});

test("schedule tab: the next days that cannot be read say so", async (p) => {
  await openPanel(p, { rooms: [{ id: "r1", name: "Bedroom" }], week: { fail: true } });
  await clickIn(p, '[data-action="panel-tab"][data-option="week"]'); await p.waitForTimeout(200);
  eq(await inPanel(p, (sr) => sr.querySelector(".pw-week p")?.innerText), "The next days could not be read.", "said so");
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

test("the menu button only where Home Assistant shows none: a phone, or the sidebar always hidden", async (p) => {
  const menu = () => inPanel(p, (sr) => !sr.querySelector(".pmenu").hidden);
  await openPanel(p, { rooms: ROOMS });
  eq(await menu(), false, "wide, sidebar docked: the sidebar has its own");
  await openPanel(p, { rooms: ROOMS, sidebar: "always_hidden" });
  eq(await menu(), true, "sidebar always hidden");
  await openPanel(p, { rooms: ROOMS }, { narrow: true });
  eq(await menu(), true, "a phone");
});

test("statistics: the time over a bar as 2h25, the same time as elsewhere", async (p) => {
  await openPanel(p, { rooms: ROOMS });
  const f = await inPanel(p, () => [0.5, 2 + 25 / 60, 3, 12.75, 150.2].map((h) => panel._shortHours(h)));
  eq(f, ["30min", "2h25", "3h", "12h45", "150h"], "short times");
  await clickIn(p, '[data-action="panel-tab"][data-option="stats"]'); await p.waitForTimeout(150);
  const r = await inPanel(p, (sr) => { const c = sr.querySelector(".ps-cols .ps-col"); return { short: c.querySelector(".ps-val").innerText, title: c.title }; });
  ok(/^\d+h(\d\d)?$/.test(r.short), "over the bar: " + r.short);
  await p.evaluate(() => localStorage.removeItem("shc-panel-tab"));
});

test("statistics: the period now has the heating time the card shows (with the minutes since the last full hour)", async (p) => {
  await openPanel(p, { rooms: ROOMS });
  await clickIn(p, '[data-action="panel-tab"][data-option="stats"]'); await p.waitForTimeout(200);
  const r = await inPanel(p, (sr) => {
    const cols = [...sr.querySelectorAll(".ps-cols")[0].querySelectorAll(".ps-col")];
    return { last: cols[cols.length - 1].title, count: cols.length };
  });
  eq(r.count, 14, "14 days");
  ok(/: 1 h 30 min$/.test(r.last), "today as the card asks for it (the fake answers 1.5 h): " + r.last);
  const asked = await p.evaluate(() => window.calls.ws.filter((c) => c.type === "recorder/statistic_during_period" && c.calendar?.period === "day").map((c) => c.statistic_id));
  ok(asked.includes("sensor.home_heating_runtime") && asked.includes("sensor.bedroom_heating_runtime"), "asked for the house and the rooms: " + asked);
  await p.evaluate(() => localStorage.removeItem("shc-panel-tab"));
});

test("devices: every entity of the rooms once, the unavailable first, with the battery of its device and how long ago", async (p) => {
  const rooms = [
    { id: "r1", name: "Bedroom", devices: [["climate.bed_trv", "thermostat"], ["binary_sensor.bed_window", "window"]] },
    { id: "r2", name: "Kid", devices: [["climate.kid_trv", "thermostat"], ["binary_sensor.bed_window", "window"]] },
  ];
  const extra = [
    ["climate.bed_trv", "heat", { friendly_name: "Bedroom TRV", current_temperature: 20.1, temperature: 21, hvac_action: "heating" }],
    ["binary_sensor.bed_window", "off", { friendly_name: "Bedroom window" }],
    ["climate.kid_trv", "unavailable", { friendly_name: "Kid TRV" }],
    ["sensor.bed_trv_battery", "64", { device_class: "battery", unit_of_measurement: "%" }],
    ["binary_sensor.bed_window_battery", "on", { device_class: "battery" }],
  ];
  const registry = { "climate.bed_trv": { device_id: "d1" }, "sensor.bed_trv_battery": { device_id: "d1" },
    "binary_sensor.bed_window": { device_id: "d2" }, "binary_sensor.bed_window_battery": { device_id: "d2" } };
  await openPanel(p, { rooms, extra, registry });
  await clickIn(p, '[data-action="panel-tab"][data-option="devices"]'); await p.waitForTimeout(150);
  const r = await inPanel(p, (sr) => ({
    title: sr.querySelector(".pd-devices .ps-title").innerText,
    rows: [...sr.querySelectorAll(".pd-row")].map((li) => ({
      id: li.dataset.entity,
      where: li.querySelector(".pd-name small").innerText,
      value: li.querySelector(".pd-val").innerText,
      battery: li.querySelector(".pd-bat").innerText.trim(),
      low: li.querySelector(".pd-bat").classList.contains("low"),
      bad: li.classList.contains("bad"),
      ago: li.querySelector(".pd-ago").innerText,
    })),
  }));
  ok(/^Devices of the rooms · 3 · 1 unavailable$/.test(r.title), "the count: " + r.title);
  eq(r.rows.map((x) => x.id), ["climate.kid_trv", "binary_sensor.bed_window", "climate.bed_trv"], "unavailable, then a low battery, then the rest");
  eq([r.rows[0].bad, r.rows[0].value], [true, "unavailable"], "unavailable");
  eq([r.rows[1].where, r.rows[1].battery, r.rows[1].low], ["Window · Bedroom, Kid", "low", true], "an entity of two rooms once; a low battery");
  eq([r.rows[2].value, r.rows[2].battery, r.rows[2].low], ["20.1° → 21.0° heating", "64%", false], "the battery in %");
  ok(r.rows.every((x) => x.ago === "now"), "how long ago: " + r.rows.map((x) => x.ago));
  await clickIn(p, '.pd-row[data-entity="climate.kid_trv"]');
  await p.evaluate(() => localStorage.removeItem("shc-panel-tab"));
});

test("schedule tab: the copy button opens the room with the rooms to copy its schedule to", async (p) => {
  await openPanel(p, { rooms: [{ id: "r1", name: "Bedroom" }, { id: "r2", name: "Kid" }] });
  await clickIn(p, '[data-action="panel-tab"][data-option="week"]'); await p.waitForTimeout(100);
  await clickIn(p, '[data-action="week-copy"][data-room="r2"]'); await p.waitForTimeout(150);
  const r = await inPanel(p, (sr) => ({
    tab: panel.getAttribute("tab"),
    box: !!sr.querySelector('.pmain [data-section="sched-r2"] .copybox'),
    rooms: [...sr.querySelectorAll(".pmain [data-copyto]")].map((c) => c.dataset.copyto),
  }));
  eq(r, { tab: "rooms", box: true, rooms: ["r1"] }, "the room, its copy box, the other room");
  await p.evaluate(() => localStorage.removeItem("shc-panel-tab"));
});

test("schedule tab: asked again at once when a schedule changes; the day kept by its date; ticks where the hours fall", async (p) => {
  await openPanel(p, { rooms: [{ id: "r1", name: "Bedroom" }] });
  await clickIn(p, '[data-action="panel-tab"][data-option="week"]'); await p.waitForTimeout(200);
  await clickIn(p, ".pw-days .seg:nth-child(3)"); await p.waitForTimeout(80);
  const chosen = await inPanel(p, (sr) => sr.querySelector(".pw-days .seg.active").dataset.option);
  const asked = () => p.evaluate(() => window.calls.ws.filter((c) => c.type === "advanced_climate/week").length);
  const before = await asked();
  // The schedule of the room changes (saved from the card, another device or a service).
  await p.evaluate(() => {
    const h = { ...panel._hass, states: { ...panel._hass.states } };
    const d = h.states["sensor.bedroom_decision"];
    h.states["sensor.bedroom_decision"] = { ...d, last_updated: new Date().toISOString(), attributes: { ...d.attributes, profile_days: { workday: { days: "all", enabled: true }, weekend: { days: "weekend", enabled: false } } } };
    panel.hass = h;
  });
  await p.waitForTimeout(200);
  eq(await asked(), before + 1, "asked again at once");
  const r = await inPanel(p, (sr) => ({
    active: sr.querySelector(".pw-days .seg.active").dataset.option,
    ticks: [...sr.querySelectorAll(".pw-tickline > span")].map((t) => [t.innerText, t.style.left]),
  }));
  eq(r.active, chosen, "the same date still chosen");
  eq(r.ticks.map((t) => t[0]), ["00:00", "06:00", "12:00", "18:00", "24:00"], "the hours");
  eq(r.ticks[0][1], "0%", "midnight at the start");
  eq(r.ticks[4][1], "100%", "the next midnight at the end");
  await p.evaluate(() => localStorage.removeItem("shc-panel-tab"));
});

test("schedule tab: a vacation held off by guest mode is told, not drawn; a room whose days failed says so", async (p) => {
  await openPanel(p, { rooms: [{ id: "r1", name: "Bedroom" }, { id: "r2", name: "Kid" }],
    week: { vacation: { fromDay: 0, from: "00:00", toDay: 2, to: "20:00", guests: true }, failedRoom: "r2" } });
  await clickIn(p, '[data-action="panel-tab"][data-option="week"]'); await p.waitForTimeout(200);
  const r = await inPanel(p, (sr) => ({
    notes: [...sr.querySelectorAll(".pw-notes li")].map((li) => li.innerText),
    over: sr.querySelectorAll('.pw-main[data-room="r1"] .pw-ov').length,
    failed: sr.querySelector(".pw-row .pw-ext")?.innerText || "",
    failedButton: !!sr.querySelector('button.pw-main[data-room="r2"]'),
  }));
  ok(r.notes.some((n) => /held off while guest mode is on$/.test(n)), "told: " + r.notes);
  eq(r.over, 0, "not drawn");
  eq([r.failed, r.failedButton], ["The next days of this room could not be computed.", false], "the room that failed");
  await p.evaluate(() => localStorage.removeItem("shc-panel-tab"));
});

test("rooms grouped by floor or by circuit, in the list, the schedule and the devices; kept in the browser", async (p) => {
  const rooms = [
    { id: "r1", name: "Bedroom", area: "bed", circuit: "switch.radiators", devices: [["climate.bed", "thermostat"]] },
    { id: "r2", name: "Kid", area: "kid", circuit: "switch.floor", devices: [["climate.kid", "thermostat"]] },
    { id: "r3", name: "Living", area: "living", circuit: "switch.floor", devices: [["climate.living", "thermostat"]] },
    { id: "r4", name: "Office", devices: [["climate.office", "thermostat"]] },
  ];
  const areas = { bed: { area_id: "bed", floor_id: "up" }, kid: { area_id: "kid", floor_id: "up" }, living: { area_id: "living", floor_id: "ground" } };
  const floors = { up: { floor_id: "up", name: "First floor", level: 1 }, ground: { floor_id: "ground", name: "Ground floor", level: 0 } };
  const extra = [["switch.radiators", "on", { friendly_name: "Radiators" }], ["switch.floor", "off", { friendly_name: "Floor heating" }]];
  await p.evaluate(() => localStorage.removeItem("shc-panel-group"));
  await openPanel(p, { rooms, areas, floors, extra });
  const list = () => inPanel(p, (sr) => [...sr.querySelectorAll(".pside > *")].map((n) => n.classList.contains("gname") ? `# ${n.innerText.trim()}` : n.__k.replace("row-", "")));
  const opts = await inPanel(p, (sr) => [...sr.querySelectorAll(".pgroup option")].map((o) => o.value));
  eq(opts, ["none", "floor", "circuit"], "the groupings there are");
  eq(await list(), ["r1", "r2", "r3", "r4"], "no groups at first");
  const pick = (v) => p.evaluate((v) => { const s = panel.shadowRoot.querySelector(".pgroup"); s.value = v; s.dispatchEvent(new Event("change", { bubbles: true, composed: true })); }, v);
  await pick("floor"); await p.waitForTimeout(100);
  eq((await list()).map((x) => x.toUpperCase()), ["# GROUND FLOOR", "R3", "# FIRST FLOOR", "R1", "R2", "# NO FLOOR", "R4"], "by the level of the floors; the rooms on none last");
  await pick("circuit"); await p.waitForTimeout(100);
  eq((await list()).map((x) => x.toUpperCase()), ["# FLOOR HEATING", "R2", "R3", "# RADIATORS", "R1", "# NO CIRCUIT", "R4"], "by circuit");
  eq(await p.evaluate(() => localStorage.getItem("shc-panel-group")), "circuit", "kept");
  await clickIn(p, '[data-action="panel-tab"][data-option="week"]'); await p.waitForTimeout(200);
  eq(await inPanel(p, (sr) => [...sr.querySelectorAll(".pw-group")].map((g) => g.innerText.toUpperCase())), ["FLOOR HEATING", "RADIATORS", "NO CIRCUIT"], "in the schedule");
  await clickIn(p, '[data-action="panel-tab"][data-option="devices"]'); await p.waitForTimeout(150);
  eq(await inPanel(p, (sr) => [...sr.querySelectorAll(".pd-devices .pd-list > li")].map((li) => li.classList.contains("pd-group") ? `# ${li.innerText.toUpperCase()}` : li.dataset.entity)),
    ["# FLOOR HEATING", "climate.kid", "climate.living", "# RADIATORS", "climate.bed", "# NO CIRCUIT", "climate.office"], "in the devices");
  // Rooms without floors or circuits: no choice.
  await openPanel(p, { rooms: [{ id: "r1", name: "Bedroom" }] });
  eq(await inPanel(p, (sr) => !!sr.querySelector(".pgroup")), false, "nothing to group by");
  await p.evaluate(() => { localStorage.removeItem("shc-panel-group"); localStorage.removeItem("shc-panel-tab"); });
});

test("humidity of every room: those at risk of mold first; a tap opens the Details", async (p) => {
  const rooms = [
    { id: "r1", name: "Bedroom", humidity: 48, wall: 62 },
    { id: "r2", name: "Bath", humidity: 70, wall: 86 },
    { id: "r3", name: "Kid", humidity: 55, wall: 70, alerts: [{ key: "mold", code: "mold_risk", params: { surface: 79, humidity: 55 }, message: "m" }] },
    { id: "r4", name: "Office" },
  ];
  await openPanel(p, { rooms });
  await clickIn(p, '[data-action="panel-tab"][data-option="devices"]'); await p.waitForTimeout(150);
  const r = await inPanel(p, (sr) => ({
    title: sr.querySelector(".pd-humidity .ps-title").innerText,
    rows: [...sr.querySelectorAll(".pd-humidity .ph-hum")].map((li) => [li.dataset.room, li.classList.contains("risk"), li.querySelector(".pd-val").innerText.replace(/\s+/g, " ").trim(), li.querySelector(".pd-bat").innerText.replace(/\s+/g, " ").trim()]),
  }));
  eq(r.title, "Humidity · 2 at risk of mold", "the count");
  eq(r.rows, [["r2", true, "air 70%", "coldest wall 86%"], ["r3", true, "air 55%", "coldest wall 70%"], ["r1", false, "air 48%", "coldest wall 62%"]], "the risk first (a mold alert, or 80% at the wall); a room without a sensor not shown");
  await clickIn(p, '.ph-hum[data-room="r2"]'); await p.waitForTimeout(150);
  eq(await inPanel(p, (sr) => ({ tab: panel.getAttribute("tab"), details: !!sr.querySelector('.pmain [data-section="details-r2"]') })), { tab: "rooms", details: true }, "its Details");
  // No humidity sensor anywhere: no section.
  await openPanel(p, { rooms: [{ id: "r1", name: "Bedroom" }] });
  await clickIn(p, '[data-action="panel-tab"][data-option="devices"]'); await p.waitForTimeout(150);
  eq(await inPanel(p, (sr) => !!sr.querySelector(".pd-humidity")), false, "no section");
  await p.evaluate(() => localStorage.removeItem("shc-panel-tab"));
});

test("chart: a history that could not be read is said, and asked for again when the chart opens again or the connection comes back", async (p) => {
  // Wide: said beside the room.
  await openPanel(p, { rooms: [{ id: "r1", name: "Bedroom" }], historyFails: true });
  await p.waitForTimeout(300);
  ok(/could not be read/.test(await inPanel(p, (sr) => sr.querySelector(".pmain .prw-chart").innerText)), "said beside the room");
  // On a phone, in the chart window.
  await p.evaluate(() => history.replaceState(null, "", "#r1"));
  await openPanel(p, { rooms: [{ id: "r1", name: "Bedroom" }], historyFails: true }, { narrow: true });
  const btn = '.pmain [data-action="fold"][data-key="chart-r1"]';
  const asked = () => p.evaluate(() => window.calls.ws.filter((c) => c.type === "history/history_during_period").length);
  await clickIn(p, btn); await p.waitForTimeout(300);
  ok(/could not be read/.test(await inPanel(p, (sr) => sr.querySelector("dialog.chartpop .popbody").innerText)), "said");
  const first = await asked();
  await p.keyboard.press("Escape"); await p.waitForTimeout(150);
  await clickIn(p, btn); await p.waitForTimeout(300);
  eq(await asked(), first + 1, "asked again when opened again");
  // The connection drops and comes back: asked again (the window still open).
  await p.evaluate(() => { panel.hass = { ...panel._hass, connected: false }; });
  await p.evaluate(() => { panel.hass = { ...panel._hass, connected: true }; });
  await p.waitForTimeout(300);
  eq(await asked(), first + 2, "asked again when the connection is back");
  await p.keyboard.press("Escape");
  await p.evaluate(() => { localStorage.removeItem("shc-panel-tab"); localStorage.removeItem("shc-panel-room"); history.replaceState(null, "", location.pathname); });
});

test("statistics: the outdoor mean as a line over the bars of the house, on its own scale", async (p) => {
  await openPanel(p, { rooms: ROOMS });
  await clickIn(p, '[data-action="panel-tab"][data-option="stats"]'); await p.waitForTimeout(200);
  const r = await inPanel(p, (sr) => {
    const svg = sr.querySelectorAll(".ps-cols")[0].querySelector("svg.ps-line");
    return {
      legend: sr.querySelector(".ps-legend")?.innerText.trim(),
      dots: [...svg.querySelectorAll("circle:not(.ps-hit)")].map((c) => c.getAttribute("cx")),
      lines: svg.querySelectorAll("line").length,
      scale: [...sr.querySelectorAll(".ps-chart")[0].querySelectorAll(".ps-axis span")].map((t) => t.textContent),
      inside: svg.querySelectorAll("text").length,
      starts: !!sr.querySelectorAll(".ps-cols")[1]?.querySelector("svg.ps-line"),
    };
  });
  eq(r.legend, "outdoor mean", "the legend");
  eq([r.dots.length, r.lines, r.dots[0], r.dots[13]], [14, 13, "3.571%", "96.429%"], "a point at the centre of each column");
  eq(r.scale, ["5.0°", "4.5°", "4.0°"], "its highest, middle and lowest, on a scale of its own");
  eq(r.inside, 0, "no value drawn over the bars");
  eq(r.starts, false, "not over the starts");
  await openPanel(p, { rooms: ROOMS, noTempStats: true });
  eq(await inPanel(p, (sr) => [!!sr.querySelector("svg.ps-line"), !!sr.querySelector(".ps-legend")]), [false, false], "no outdoor statistics: no line");
  await p.evaluate(() => localStorage.removeItem("shc-panel-tab"));
});

test("statistics: the heating by hour of every room, the mean of 7 days or one day", async (p) => {
  await openPanel(p, { rooms: [{ id: "r1", name: "Bedroom" }, { id: "r2", name: "Kid" }] });
  await clickIn(p, '[data-action="panel-tab"][data-option="stats"]'); await p.waitForTimeout(300);
  const look = () => inPanel(p, (sr) => ({
    chips: [...sr.querySelectorAll('[data-action="heat-day"]')].map((b) => b.innerText.trim()),
    active: sr.querySelector('[data-action="heat-day"].active')?.dataset.option,
    rows: [...sr.querySelectorAll(".hm-row:not(.hm-head)")].map((r) => r.querySelector(".hm-name").innerText),
    cells: sr.querySelectorAll(".hm-row:not(.hm-head)")[0].querySelectorAll(".hm-cell").length,
    full: [...sr.querySelectorAll(".hm-row:not(.hm-head)")[0].querySelectorAll(".hm-cell")].map((c) => c.style.getPropertyValue("--p")),
    title: [...sr.querySelectorAll(".hm-row:not(.hm-head)")[0].querySelectorAll(".hm-cell")].map((c) => c.title).find((t) => / 60 min/.test(t)) || "",
    // The heating by hour asks for every room at once (the chart of the room asks for its own).
    asked: window.calls.ws.filter((c) => c.type === "history/history_during_period" && c.entity_ids.includes("binary_sensor.bedroom_heat_demand") && c.entity_ids.includes("binary_sensor.kid_heat_demand")).length,
  }));
  const mean = await look();
  eq([mean.chips.length, mean.chips[0], mean.active], [8, "Mean", "mean"], "the mean and the 7 days");
  eq([mean.rows, mean.cells], [["Bedroom", "Kid"], 24], "a row of 24 hours for each room");
  ok(mean.full.filter((v) => v === "100%").length >= 6, "the hours heated every day: " + mean.full);
  ok(/^Bedroom \d\d:00–\d\d:00: heated 60 min a day on average$/.test(mean.title), "the minutes: " + mean.title);
  eq(mean.asked, 1, "one request for every room");
  await clickIn(p, '[data-action="heat-day"]:nth-child(8)'); await p.waitForTimeout(100);
  const today = await look();
  ok(today.active !== "mean" && today.full.some((v) => v === ""), "today: the hours to come empty");
  await p.evaluate(() => localStorage.removeItem("shc-panel-tab"));
});

test("statistics: a tap on a point of the outdoor line shows its mean, lowest and highest; again hides it", async (p) => {
  await openPanel(p, { rooms: ROOMS });
  await clickIn(p, '[data-action="panel-tab"][data-option="stats"]'); await p.waitForTimeout(200);
  const tip = () => inPanel(p, (sr) => sr.querySelector(".ps-tip")?.innerText.replace(/\s+/g, " ") || null);
  eq(await tip(), null, "none at first");
  await inPanel(p, (sr) => sr.querySelectorAll("circle.ps-hit")[2].dispatchEvent(new MouseEvent("click", { bubbles: true, composed: true })));
  await p.waitForTimeout(100);
  ok(/^\d\.\d° \(\d\.0° … \d\.0°\) \w+, \w+ \d+$/.test(await tip()), "shown, with its whole date: " + (await tip()));
  eq(await inPanel(p, (sr) => sr.querySelector(".ps-col.picked")), null, "the period is not chosen by it");
  await inPanel(p, (sr) => sr.querySelectorAll("circle.ps-hit")[2].dispatchEvent(new MouseEvent("click", { bubbles: true, composed: true })));
  await p.waitForTimeout(100);
  eq(await tip(), null, "hidden again");
  await p.evaluate(() => localStorage.removeItem("shc-panel-tab"));
});

test("statistics: a tap on an hour of the heating by hour shows its minutes; ✕ hides them", async (p) => {
  await openPanel(p, { rooms: [{ id: "r1", name: "Bedroom" }] });
  await clickIn(p, '[data-action="panel-tab"][data-option="stats"]'); await p.waitForTimeout(300);
  const detail = () => inPanel(p, (sr) => sr.querySelector(".hm-detail")?.innerText.trim() || null);
  eq(await detail(), null, "none at first");
  const cell = await inPanel(p, (sr) => { const c = [...sr.querySelectorAll("button.hm-cell")].find((b) => b.style.getPropertyValue("--p") === "100%"); c.click(); return c.dataset.cell; });
  await p.waitForTimeout(100);
  ok(/^Bedroom \d\d:00–\d\d:00: heated 60 min a day on average$/.test(await detail()), "its minutes: " + (await detail()));
  eq(await inPanel(p, (sr, c) => sr.querySelector(`button.hm-cell[data-cell="${c}"]`).classList.contains("picked"), cell), true, "marked");
  await clickIn(p, ".hm-detail .ps-unpick"); await p.waitForTimeout(100);
  eq(await detail(), null, "hidden");
  await p.evaluate(() => localStorage.removeItem("shc-panel-tab"));
});

// ---------------------------------------------------------------- the wide layout, the overview, the keyboard
test("wide: the house in one bar (its buttons as icons, named on hover); a phone keeps the card's house", async (p) => {
  await openPanel(p, { rooms: ROOMS });
  const wide = await inPanel(p, (sr) => ({
    bar: !!sr.querySelector(".phouse .pbar"),
    buttons: [...sr.querySelectorAll(".pbar .pb-actions .abtn")].map((b) => b.getAttribute("aria-label")),
    stats: sr.querySelectorAll(".pbar .pb-stat").length,
    height: sr.querySelector(".phouse").getBoundingClientRect().height,
  }));
  eq([wide.bar, wide.buttons.every(Boolean), wide.buttons.length, wide.stats], [true, true, 5, 4], "one bar, every button named");
  ok(wide.height < 170, "a short bar: " + wide.height);
  await openPanel(p, { rooms: ROOMS }, { narrow: true });
  eq(await inPanel(p, (sr) => [!!sr.querySelector(".phouse .pbar"), !!sr.querySelector(".phouse .hactions")]), [false, true], "the phone: as the card");
  await p.evaluate(() => localStorage.removeItem("shc-panel-room"));
});

test("overview: a tile per room with its temperature, target and last 24 hours; a tap opens the room", async (p) => {
  await openPanel(p, { rooms: ROOMS });
  await clickIn(p, '[data-action="panel-tab"][data-option="overview"]'); await p.waitForTimeout(400);
  const r = await inPanel(p, (sr) => [...sr.querySelectorAll(".ov-tile")].map((t) => ({
    name: t.querySelector(".ov-name").innerText,
    now: t.querySelector(".ov-now").innerText,
    spark: !!t.querySelector("svg.ov-spark polyline.t"),
  })));
  eq(r.map((t) => t.name).sort(), ["Bedroom", "Kid", "Living", "Office"], "a tile for every room");
  ok(r.find((t) => t.name === "Bedroom").spark, "the last 24 hours drawn");
  eq(r.find((t) => t.name === "Kid").now, "–", "no temperature: a dash");
  await clickIn(p, '.ov-tile[data-room="r2"]'); await p.waitForTimeout(200);
  eq(await inPanel(p, (sr) => [sr.host.getAttribute("tab"), sr.querySelector(".pmain .block.room .name").innerText]), ["rooms", "Office"], "opened");
  await p.evaluate(() => { localStorage.removeItem("shc-panel-tab"); localStorage.removeItem("shc-panel-room"); history.replaceState(null, "", location.pathname); });
});

test("keyboard: the arrows go from room to room and from tab to tab, the focus kept", async (p) => {
  await openPanel(p, { rooms: ROOMS });
  await inPanel(p, (sr) => sr.querySelector('.pside .frow[data-key="room-r1"]').focus());
  await p.keyboard.press("ArrowDown"); await p.waitForTimeout(150);
  const down = await inPanel(p, (sr) => [location.hash, sr.activeElement?.dataset.key]);
  const order = await inPanel(p, (sr) => [...sr.querySelectorAll(".pside .frow")].map((b) => b.dataset.key));
  eq(down, [`#${order[1].slice(5)}`, order[1]], "the next room chosen and focused");
  await p.keyboard.press("End"); await p.waitForTimeout(150);
  eq(await inPanel(p, (sr) => sr.activeElement?.dataset.key), order.at(-1), "End: the last");
  await inPanel(p, (sr) => sr.querySelector('[data-action="panel-tab"][data-option="rooms"]').focus());
  await p.keyboard.press("ArrowRight"); await p.waitForTimeout(150);
  eq(await inPanel(p, (sr) => [sr.host.getAttribute("tab"), sr.activeElement?.dataset.option]), ["overview", "overview"], "the next tab");
  await p.keyboard.press("ArrowLeft"); await p.keyboard.press("ArrowLeft"); await p.waitForTimeout(150);
  eq(await inPanel(p, (sr) => sr.host.getAttribute("tab")), "devices", "around to the last");
  await p.evaluate(() => { localStorage.removeItem("shc-panel-tab"); localStorage.removeItem("shc-panel-room"); history.replaceState(null, "", location.pathname); });
});

test("title: the name of the house; with several houses the name of the integration", async (p) => {
  await openPanel(p, { rooms: ROOMS, houseName: "Cabana" });
  eq(await inPanel(p, (sr) => sr.querySelector(".ptop h1").innerText), "Cabana", "one house");
});
