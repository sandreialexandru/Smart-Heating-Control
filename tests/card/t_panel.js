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
  eq([ask.period, ask.types, ask.statistic_ids.length, !!ask.end_time], ["day", ["change"], 4, true], "the statistics asked");
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
  eq(await inPanel(p, (sr) => [...sr.querySelectorAll('[data-action="panel-tab"]')].map((b) => b.innerText)), ["Camere", "Statistici", "Istoric"], "tabs");
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
