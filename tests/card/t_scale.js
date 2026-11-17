// Bigger homes: one house with many rooms on three floors, and several houses
// (two of them with rooms of the same name). Every tab shows every room once,
// under its house; nothing runs wider than a phone; and the time each tab
// takes to draw is printed (not checked: it is there to compare runs).

const FLOORS = { f0: { floor_id: "f0", name: "Ground floor", level: 0 }, f1: { floor_id: "f1", name: "First floor", level: 1 }, f2: { floor_id: "f2", name: "Attic", level: 2 } };
const NAMES = ["Living", "Kitchen", "Dining", "Office", "Hall", "Bath", "Guest", "Laundry", "Bedroom", "Kid A", "Kid B", "Study",
  "Play", "Gym", "Library", "Studio", "Pantry", "Closet", "Den", "Loft", "Nursery", "Media", "Workshop", "Sauna"];
const CIRCUITS = ["switch.circuit_ground", "switch.circuit_first", "switch.circuit_attic", "switch.circuit_bath"];

// The big house: 24 rooms, 8 on each floor, each with a thermostat, a sensor and a window.
const BIG = NAMES.map((name, i) => {
  const p = `big${i}`;
  return {
    id: `b${i}`, name, prefix: p, area: `a${i}`, circuit: CIRCUITS[i % 4], humidity: 45 + (i % 9) * 3, wall: 60 + (i % 9) * 3,
    devices: [[`climate.${p}_trv`, "thermostat"], [`sensor.${p}_temp`, "temperature"], [`binary_sensor.${p}_window`, "window"]],
  };
});
const AREAS = Object.fromEntries(BIG.map((r, i) => [r.area, { area_id: r.area, name: r.name, floor_id: ["f0", "f1", "f2"][Math.floor(i / 8)] }]));
const EXTRA = BIG.flatMap((r) => [
  [`climate.${r.prefix}_trv`, "heat", { friendly_name: `${r.name} TRV`, current_temperature: 20.4, temperature: 21, hvac_action: "idle" }],
  [`sensor.${r.prefix}_temp`, "20.6", { friendly_name: `${r.name} temperature`, unit_of_measurement: "°C", device_class: "temperature" }],
  [`binary_sensor.${r.prefix}_window`, "off", { friendly_name: `${r.name} window`, device_class: "window" }],
]);

// Several houses in one Home Assistant: the states put together, each house answering for itself.
const SEVERAL = [
  { entry: "e1", houseName: "Home", prefix: "home", rooms: [{ id: "h1", name: "Bedroom", prefix: "h_bed", humidity: 55, wall: 70 }, { id: "h2", name: "Living", prefix: "h_liv" }] },
  { entry: "e2", houseName: "Cabin", prefix: "cabin", rooms: [{ id: "c1", name: "Bedroom", prefix: "c_bed", humidity: 66, wall: 83 }, { id: "c2", name: "Loft", prefix: "c_loft" }] },
  { entry: "e3", houseName: "Flat", prefix: "flat", rooms: [{ id: "f1", name: "Studio", prefix: "f_studio" }] },
];

/** Mounts the panel on one hass made of several (in the page). */
const openMany = (p, list, narrow, tab) =>
  p.evaluate(
    async ([houses, narrow, tab]) => {
      const all = houses.map((o) => makeHass(o));
      const a = all[0];
      for (const h of all.slice(1)) Object.assign(a.states, h.states);
      const one = a.callWS;
      a.callWS = async (msg) => {
        if (msg.type === "advanced_climate/week" || msg.type === "advanced_climate/history") {
          const res = await Promise.all(all.map((h, i) => (i ? h.callWS(msg) : one(msg))));
          return { houses: res.flatMap((r) => r.houses) };
        }
        return one(msg);
      };
      if (tab) localStorage.setItem("shc-panel-tab", tab);
      const host = document.getElementById("host"); host.innerHTML = ""; host.style.maxWidth = "none";
      window.panel = document.createElement("shc-panel"); panel.narrow = narrow; panel.hass = a; host.appendChild(panel);
      await sleep(400);
    },
    [list, !!narrow, tab || "rooms"]
  );

const openBig = (p, narrow, tab, group) =>
  p.evaluate(
    async ([o, narrow, tab, group]) => {
      localStorage.setItem("shc-panel-tab", tab);
      localStorage.setItem("shc-panel-group", group || "none");
      const host = document.getElementById("host"); host.innerHTML = ""; host.style.maxWidth = "none";
      window.panel = document.createElement("shc-panel"); panel.narrow = narrow;
      const t0 = performance.now();
      panel.hass = makeHass(o); host.appendChild(panel);
      const drawn = performance.now() - t0;
      await sleep(500);
      return drawn;
    },
    [{ rooms: BIG, areas: AREAS, floors: FLOORS, extra: EXTRA }, !!narrow, tab, group]
  );

const inPanel = (p, fn, arg) => p.evaluate(([f, a]) => new Function("sr", "a", `return (${f})(sr, a)`)(panel.shadowRoot, a), [fn.toString(), arg]);
const clean = (p) => p.evaluate(() => ["shc-panel-tab", "shc-panel-group", "shc-panel-room"].forEach((k) => localStorage.removeItem(k)));
// Wider than the screen: the page scrolls sideways (a phone must never).
const wide = (p) => p.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
// The time a change of the states takes to draw the tab again (median of 5).
const redraw = (p) =>
  p.evaluate(async () => {
    const times = [];
    for (let i = 0; i < 5; i++) {
      const h = { ...panel._hass, states: { ...panel._hass.states } };
      const id = Object.keys(h.states).find((k) => k.endsWith("_room_temperature"));
      h.states[id] = { ...h.states[id], state: String(19 + i / 10) };
      const t0 = performance.now();
      panel.hass = h;
      times.push(performance.now() - t0);
      await sleep(30);
    }
    return times.sort((a, b) => a - b)[2];
  });
const report = (what, ms) => console.log(`      ${what}: ${ms.toFixed(1)} ms`);

test("big house (24 rooms, 3 floors): every room once in every tab, by floor", async (p) => {
  const names = [...NAMES].sort();
  report("rooms tab, first draw", await openBig(p, false, "rooms", "floor"));
  report("rooms tab, redraw", await redraw(p));
  const rooms = await inPanel(p, (sr) => ({
    groups: [...sr.querySelectorAll(".pside .gname")].map((n) => n.innerText),
    rows: [...sr.querySelectorAll(".pside .block.room .name")].map((n) => n.innerText),
  }));
  eq(rooms.groups.map((g) => g.toLowerCase()), ["ground floor", "first floor", "attic"], "floors in the order of their level");
  eq([...rooms.rows].sort(), names, "every room once");
  eq(rooms.rows.slice(0, 8).sort(), NAMES.slice(0, 8).sort(), "the ground floor first");

  report("schedule tab", await openBig(p, false, "week", "floor"));
  await p.waitForTimeout(300);
  const week = await inPanel(p, (sr) => [...sr.querySelectorAll(".pw-row .pw-name")].map((n) => n.innerText.trim()));
  eq(week.length, 24, "a row for every room in the schedule");

  report("statistics tab", await openBig(p, false, "stats", "floor"));
  await p.waitForTimeout(600);
  const stats = await inPanel(p, (sr) => ({
    rooms: sr.querySelectorAll(".ps-rooms .ps-room, .ps-room-row, .ps-rooms li").length,
    heat: [...sr.querySelectorAll(".hm-row:not(.hm-head) .hm-name")].map((n) => n.innerText),
  }));
  eq([...stats.heat].sort(), names, "a row for every room in the heating by hour");

  report("devices tab", await openBig(p, false, "devices", "floor"));
  const dev = await inPanel(p, (sr) => ({
    devices: sr.querySelectorAll(".pd-devices .pd-row").length,
    humidity: sr.querySelectorAll(".pd-humidity .pd-row").length,
  }));
  eq(dev, { devices: 72, humidity: 24 }, "3 devices of each room, the humidity of each");

  report("history tab", await openBig(p, false, "history", "floor"));
  const opts = await inPanel(p, (sr) => [...sr.querySelectorAll("select option")].map((o) => o.textContent));
  for (const n of NAMES) ok(opts.includes(n), "the room in the filter of the history: " + n);
  await clean(p);
});

test("big house by circuit: the rooms under their circuit", async (p) => {
  await openBig(p, false, "rooms", "circuit");
  const groups = await inPanel(p, (sr) => [...sr.querySelectorAll(".pside .gname")].length);
  eq(groups, 4, "four circuits");
  const rows = await inPanel(p, (sr) => sr.querySelectorAll(".pside .block.room .name").length);
  eq(rows, 24, "every room");
  await clean(p);
});

test("big house on a phone: no tab is wider than the screen", async (p) => {
  for (const tab of ["rooms", "week", "stats", "history", "devices"]) {
    report(`${tab} on a phone`, await openBig(p, true, tab, "floor"));
    await p.waitForTimeout(400);
    eq(await wide(p), 0, `${tab}: wider than the phone by`);
  }
  // A room opened on the phone too.
  await p.evaluate(() => { location.hash = "#b12"; });
  await p.waitForTimeout(300);
  eq(await wide(p), 0, "an open room: wider than the phone by");
  await p.evaluate(() => history.replaceState(null, "", location.pathname));
  await clean(p);
}, { viewport: { width: 390, height: 844 } });

test("big house in the card: every room, the house once", async (p) => {
  const t = await p.evaluate(async (o) => {
    const t0 = performance.now();
    mount({}, o);
    const ms = performance.now() - t0;
    await sleep(300);
    return { ms, rooms: card.shadowRoot.querySelectorAll(".block.room").length, houses: card.shadowRoot.querySelectorAll(".block.house").length };
  }, { rooms: BIG, areas: AREAS, floors: FLOORS, extra: EXTRA });
  report("card, first draw", t.ms);
  eq({ rooms: t.rooms, houses: t.houses }, { rooms: 24, houses: 1 }, "drawn");
});

test("several houses: each house with its rooms, in every tab", async (p) => {
  await openMany(p, SEVERAL, false, "rooms");
  const list = await inPanel(p, (sr) => ({
    houses: sr.querySelectorAll(".phouse .block.house").length,
    list: [...sr.querySelectorAll(".pside .hname, .pside .block.room .name")].map((n) => n.innerText),
  }));
  eq(list.houses, 3, "three houses on top");
  eq(list.list, ["Home", "Bedroom", "Living", "Cabin", "Bedroom", "Loft", "Flat", "Studio"], "rooms under their house");

  await openMany(p, SEVERAL, false, "week");
  await p.waitForTimeout(300);
  const week = await inPanel(p, (sr) => [...sr.querySelectorAll(".ps-house, .pw-row .pw-name")].map((n) => n.innerText.trim()));
  eq(week.filter((t) => ["Home", "Cabin", "Flat"].includes(t)).length, 3, "each house named in the schedule: " + JSON.stringify(week));
  eq(week.length, 3 + 5, "every room once in the schedule");

  await openMany(p, SEVERAL, false, "stats");
  await p.waitForTimeout(600);
  const stats = await inPanel(p, (sr) => ({
    houses: [...sr.querySelectorAll("h2.ps-house")].map((n) => n.innerText),
    heat: [...sr.querySelectorAll(".hm .ps-house, .hm .hm-row:not(.hm-head) .hm-name")].map((n) => n.innerText.trim()),
  }));
  eq(stats.houses.length, 3, "each house in the statistics");
  eq(stats.heat, ["Home", "Bedroom", "Living", "Cabin", "Bedroom", "Loft", "Flat", "Studio"], "the heating by hour under each house");

  await openMany(p, SEVERAL, false, "devices");
  const hum = await inPanel(p, (sr) => [...sr.querySelectorAll(".pd-humidity .pd-house, .pd-humidity .pd-row .pd-name > span")].map((n) => n.innerText.trim()));
  eq(hum, ["Home", "Bedroom", "Cabin", "Bedroom"], "the humidity of each Bedroom under its house");

  await openMany(p, SEVERAL, false, "history");
  await p.waitForTimeout(300);
  const hist = await inPanel(p, (sr) => ({
    options: [...sr.querySelectorAll("select.ph-room option")].map((o) => `${o.parentElement.label || ""}|${o.textContent}`),
    lines: [...sr.querySelectorAll(".ph-list .ph-text b")].map((n) => n.innerText),
  }));
  ok(hist.lines.some((t) => t === "Cabin · Bedroom") && hist.lines.some((t) => t === "Home · Bedroom"), "each Bedroom told with its house: " + JSON.stringify([...new Set(hist.lines)]));
  eq(hist.options.filter((o) => o.includes("Bedroom")).length, 2, "both Bedrooms in the filter: " + JSON.stringify(hist.options));
  eq(new Set(hist.options).size, hist.options.length, "every room told apart in the filter: " + JSON.stringify(hist.options));
  await clean(p);
});

test("several houses on a phone: no tab is wider than the screen", async (p) => {
  for (const tab of ["rooms", "week", "stats", "history", "devices"]) {
    await openMany(p, SEVERAL, true, tab);
    await p.waitForTimeout(400);
    eq(await wide(p), 0, `${tab}: wider than the phone by`);
  }
  await clean(p);
}, { viewport: { width: 390, height: 844 } });

test("several houses: a change in one house redraws only that house", async (p) => {
  await openMany(p, SEVERAL, false, "rooms");
  const same = await p.evaluate(async () => {
    const before = [...panel.shadowRoot.querySelectorAll(".phouse .block.house")];
    const h = { ...panel._hass, states: { ...panel._hass.states } };
    h.states["sensor.flat_presence"] = { ...h.states["sensor.flat_presence"], state: "away" };
    panel.hass = h;
    await sleep(100);
    const after = [...panel.shadowRoot.querySelectorAll(".phouse .block.house")];
    return before.map((b, i) => b === after[i]);
  });
  eq(same.filter(Boolean).length, 2, "the other two houses kept: " + JSON.stringify(same));
  await clean(p);
});
