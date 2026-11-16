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
