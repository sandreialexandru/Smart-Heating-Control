// The chart window.
const mount = async (p, config, hass) => { await p.evaluate(([c, h]) => mount(c, h), [config, hass]); await p.waitForTimeout(200); };
const openChart = async (p, room = "r1") => { await p.evaluate((r) => card.shadowRoot.querySelector(`[data-key="chart-${r}"]`).click(), room); await p.waitForTimeout(300); };
const dlg = (p) => p.evaluate(() => { const d = card.shadowRoot.querySelector("dialog.chartpop"); return d ? { open: d.open, modal: d.matches(":modal") } : null; });
const view = (p, r = "r1") => p.evaluate((room) => { const d = card._charts[room]; return { past: (d.now - d.v0) / 36e5, span: (d.v1 - d.v0) / 36e5, back: (d.now - d.t0) / 864e5 }; }, r);
const R1 = [{ id: "r1", name: "Bedroom" }, { id: "r2", name: "Office" }];

test("opens on the last 24 h and the next 12, 7 days kept", async (p) => {
  await mount(p, {}, { rooms: R1 }); await openChart(p);
  const v = await view(p);
  ok(Math.abs(v.past - 24) < 0.01 && Math.abs(v.span - 36) < 0.01, JSON.stringify(v));
  ok(Math.abs(v.back - 7) < 0.01, "7 days back");
  eq(await dlg(p), { open: true, modal: true }, "modal");
});

test("only one chart window; opening another room switches it", async (p) => {
  await mount(p, {}, { rooms: R1 }); await openChart(p);
  await p.evaluate(() => card._closeChart()); await openChart(p, "r2");
  eq(await p.evaluate(() => [...card.shadowRoot.querySelectorAll("dialog.chartpop")].length), 1, "one window");
  ok(await p.evaluate(() => card.shadowRoot.querySelector("dialog.chartpop .pophead").innerText.includes("Office")), "Office chart");
});

test("updates keep the same modal window (10 updates)", async (p) => {
  await mount(p, {}, { rooms: R1 }); await openChart(p);
  const same = await p.evaluate(async () => {
    const d1 = card.shadowRoot.querySelector("dialog.chartpop");
    for (let i = 1; i <= 10; i++) { card.hass = makeHass({ rooms: [{ id: "r1", name: "Bedroom", current: 20 + i / 10 }, { id: "r2", name: "Office" }], tick: i }); await sleep(30); }
    const d2 = card.shadowRoot.querySelector("dialog.chartpop");
    return d1 === d2 && d2.matches(":modal");
  });
  ok(same, "window replaced or not modal");
});

test("closes with ✕, Esc and outside click; not with a click on its margin", async (p) => {
  await mount(p, {}, { rooms: R1 });
  await openChart(p); await p.evaluate(() => card.shadowRoot.querySelector('[data-action="closechart"]').click()); await p.waitForTimeout(100);
  eq(await dlg(p), null, "✕");
  await openChart(p); await p.keyboard.press("Escape"); await p.waitForTimeout(100);
  eq(await dlg(p), null, "Esc");
  await openChart(p);
  const r = await p.evaluate(() => { const b = card.shadowRoot.querySelector("dialog.chartpop").getBoundingClientRect(); return [b.left, b.top, b.width, b.height]; });
  await p.mouse.click(r[0] + 4, r[1] + r[3] - 4); await p.waitForTimeout(100);
  ok(await dlg(p), "closed on margin click");
  await p.mouse.click(3, 3); await p.waitForTimeout(100);
  eq(await dlg(p), null, "outside");
});

test("zoom buttons: 1h, 6h, +, −, ⤢", async (p) => {
  await mount(p, {}, { rooms: R1 }); await openChart(p);
  const z = (k) => p.evaluate((key) => card.shadowRoot.querySelector(`[data-zoom="${key}"]`).click(), k);
  await z("1h"); ok(Math.abs((await view(p)).span - 1) < 0.01, "1h");
  await z("6h"); ok(Math.abs((await view(p)).span - 6) < 0.01, "6h");
  await z("in"); ok(Math.abs((await view(p)).span - 3) < 0.01, "+");
  for (let i = 0; i < 6; i++) await z("out");
  ok(Math.abs((await view(p)).span - 7.5 * 24) < 0.01, "− to 7.5 days");
  await z("reset"); const v = await view(p);
  ok(Math.abs(v.span - 36) < 0.01 && Math.abs(v.past - 24) < 0.01, "⤢");
  eq(await p.evaluate(() => !!card.shadowRoot.querySelector('[data-zoom="reset"]')), false, "reset hidden on default view");
});

test("double click zooms in around the pointer", async (p) => {
  await mount(p, {}, { rooms: R1 }); await openChart(p);
  const r = await p.evaluate(() => { const b = card.shadowRoot.querySelector(".hchart").getBoundingClientRect(); return [b.left + b.width / 2, b.top + 30]; });
  await p.mouse.dblclick(r[0], r[1]); await p.waitForTimeout(150);
  ok((await view(p)).span < 20, "zoomed: " + JSON.stringify(await view(p)));
});

test("navigation bar: drag the window back in time with the mouse", async (p) => {
  await mount(p, {}, { rooms: R1 }); await openChart(p);
  const box = await p.evaluate(() => { const n = card.shadowRoot.querySelector(".navbar"), w = n.querySelector(".navwin"); const a = n.getBoundingClientRect(), b = w.getBoundingClientRect(); return { y: a.top + a.height / 2, x: b.left + b.width / 2, w: a.width }; });
  await p.mouse.move(box.x, box.y); await p.mouse.down(); await p.mouse.move(box.x - box.w * 0.4, box.y, { steps: 5 }); await p.mouse.up(); await p.waitForTimeout(150);
  const v = await view(p);
  ok(v.past > 24 * 2, "moved back: " + JSON.stringify(v));
  ok(Math.abs(v.span - 36) < 0.01, "span kept");
});

test("navigation bar hidden until the mouse is over the chart", async (p) => {
  await mount(p, {}, { rooms: R1 }); await openChart(p);
  const op = () => p.evaluate(() => +getComputedStyle(card.shadowRoot.querySelector(".navbar")).opacity);
  await p.mouse.move(2, 2); await p.waitForTimeout(400); eq(await op(), 0, "hidden");
  const r = await p.evaluate(() => { const b = card.shadowRoot.querySelector(".hchart").getBoundingClientRect(); return [b.left + 50, b.top + 50]; });
  await p.mouse.move(r[0], r[1]); await p.waitForTimeout(400); eq(await op(), 1, "shown");
});

test("sideways scroll moves through the history and stops at 7 days", async (p) => {
  await mount(p, {}, { rooms: R1 }); await openChart(p);
  const res = await p.evaluate(async () => {
    const ch = () => card.shadowRoot.querySelector(".hchart");
    for (let i = 0; i < 60; i++) ch().dispatchEvent(new WheelEvent("wheel", { deltaX: -1500, bubbles: true, composed: true, cancelable: true }));
    const d = card._charts.r1; return { atStart: Math.abs(d.v0 - d.t0) < 1000, span: (d.v1 - d.v0) / 36e5 };
  });
  ok(res.atStart && Math.abs(res.span - 36) < 0.01, JSON.stringify(res));
});

test("tooltip: past shows the measured temperature, future the prediction", async (p) => {
  await mount(p, {}, { rooms: R1 }); await openChart(p);
  const at = (f) => p.evaluate((frac) => { const b = card.shadowRoot.querySelector(".hchart").getBoundingClientRect(); return [b.left + b.width * frac, b.top + 30]; }, f);
  let r = await at(0.3); await p.mouse.move(r[0], r[1]); await p.waitForTimeout(120);
  const past = await p.evaluate(() => card.shadowRoot.querySelector(".tip").innerText);
  ok(/\d+\.\d°/.test(past) && !past.includes("predicted"), "past: " + past);
  r = await at(0.85); await p.mouse.move(r[0], r[1]); await p.waitForTimeout(120);
  const fut = await p.evaluate(() => card.shadowRoot.querySelector(".tip").innerText);
  ok(fut.includes("predicted"), "future: " + fut);
});

test("a line at every midnight, under the weekday labels", async (p) => {
  await mount(p, {}, { rooms: R1 }); await openChart(p);
  for (let i = 0; i < 6; i++) await p.evaluate(() => card.shadowRoot.querySelector('[data-zoom="out"]').click());
  const r = await p.evaluate(() => {
    const sr = card.shadowRoot, svg = sr.querySelector(".hchart svg").getBoundingClientRect();
    const lines = [...sr.querySelectorAll(".daysep")].map((l) => svg.left + (+l.getAttribute("x1") / 1000) * svg.width);
    const labels = [...sr.querySelectorAll(".ticks span")].map((s) => { const b = s.getBoundingClientRect(); return { x: b.left + b.width / 2, t: s.textContent }; });
    return { lines, labels };
  });
  ok(r.lines.length >= 7, "lines: " + r.lines.length);
  for (const lab of r.labels) ok(r.lines.some((x) => Math.abs(x - lab.x) < 3), `label ${lab.t} not on a midnight line`);
});

test("history fails: the chart still opens, no JS error, retried later", async (p) => {
  await mount(p, {}, { rooms: R1, historyFails: true }); await openChart(p);
  ok(await dlg(p), "window");
  const n1 = await p.evaluate(() => calls.ws.length);
  await p.evaluate(async () => { card._hist.r1.at -= 6 * 60e3; card.hass = makeHass({ rooms: [{ id: "r1", name: "Bedroom" }, { id: "r2", name: "Office" }], historyFails: true, tick: 1 }); await sleep(150); });
  ok((await p.evaluate(() => calls.ws.length)) > n1, "retried");
});

test("empty history: the plan and the prediction are drawn", async (p) => {
  await mount(p, {}, { rooms: R1, emptyHistory: true }); await openChart(p);
  const r = await p.evaluate(() => ({ segs: card._charts.r1.segs.length, pred: card._charts.r1.pred.length, line: !!card.shadowRoot.querySelector(".predline") }));
  ok(r.segs > 0 && r.pred > 0 && r.line, JSON.stringify(r));
});

test("later fetches ask only for the last hour and keep 7 days sorted", async (p) => {
  await mount(p, {}, { rooms: R1 }); await openChart(p);
  const r = await p.evaluate(async () => {
    const before = card._hist.r1.temp.length;
    card._hist.r1.at -= 6 * 60e3; card.hass = makeHass({ rooms: [{ id: "r1", name: "Bedroom" }, { id: "r2", name: "Office" }], tick: 2 }); await sleep(200);
    const m = calls.ws.filter((c) => c.type === "history/history_during_period").at(-1);
    const h = card._hist.r1; const t = h.temp.map((x) => x[0]);
    return { hours: (Date.parse(m.end_time) - Date.parse(m.start_time)) / 36e5, sorted: t.every((v, i) => !i || v >= t[i - 1]), before, after: t.length,
      span: (t.at(-1) - t[0]) / 864e5 };
  });
  ok(r.hours < 1.1, "hours " + r.hours); ok(r.sorted, "sorted"); ok(r.span > 6.9 && r.span < 7.1, "span " + r.span);
  ok(Math.abs(r.after - r.before) < 10, "no duplicates: " + r.before + " -> " + r.after);
});

test("dense history (one point a minute for 7 days) draws and pans fast", async (p) => {
  await mount(p, {}, { rooms: R1, historyStepMin: 1 }); await openChart(p); await p.waitForTimeout(500);
  const r = await p.evaluate(() => {
    const t0 = performance.now(); card._render(); const full = performance.now() - t0;
    const t1 = performance.now(); for (let i = 0; i < 20; i++) card._setView("r1", card._charts.r1.v0 - 3600e3, card._charts.r1.v1 - 3600e3); const pan = (performance.now() - t1) / 20;
    return { points: card._hist.r1.temp.length, full, pan };
  });
  ok(r.points > 9000, "points " + r.points);
  ok(r.pan < 60, "pan ms " + r.pan.toFixed(1));
  ok(r.full < 400, "render ms " + r.full.toFixed(1));
  console.log("   dense:", JSON.stringify({ points: r.points, render_ms: +r.full.toFixed(1), pan_ms: +r.pan.toFixed(1) }));
});

test("touch: the bar shows while touching, line and values hide after", async (p) => {
  await mount(p, {}, { rooms: R1 }); await openChart(p);
  const r = await p.evaluate(async () => {
    const sr = card.shadowRoot, ch = sr.querySelector(".hchart"), b = ch.getBoundingClientRect();
    const op = () => +getComputedStyle(sr.querySelector(".navbar")).opacity;
    const o = { bubbles: true, composed: true, pointerType: "touch", pointerId: 3, clientX: b.left + 100, clientY: b.top + 40 };
    ch.dispatchEvent(new PointerEvent("pointerdown", o)); ch.dispatchEvent(new PointerEvent("pointermove", { ...o, clientX: o.clientX + 30 }));
    await sleep(350); const during = op(); ch.dispatchEvent(new PointerEvent("pointerup", o));
    // Hidden a moment after the finger is lifted (waited for up to 6 s, a slow machine included).
    for (let i = 0; i < 60 && op() > 0; i++) await sleep(100);
    return { during, after: op(), cross: !sr.querySelector(".cross").hidden };
  });
  eq(r, { during: 1, after: 0, cross: false }, "touch");
}, { touch: true, viewport: { width: 400, height: 800 } });

test("optimal start ahead: shaded, prediction heats from its start", async (p) => {
  const now = Date.now();
  const est = { kind: "optimal_start", at: new Date(now + 5 * 3600e3).toISOString(), preset: "comfort", minutes: 90,
    starts_at: new Date(now + 3.5 * 3600e3).toISOString(), started_at: null, outdoor: 5, outdoor_source: "now", learned: true, sent_as: "temperature", temperature: 22 };
  await mount(p, {}, { rooms: [{ id: "r1", name: "Bedroom", estimate: est, current: 18.5 }] }); await openChart(p);
  const r = await p.evaluate((startsAt) => {
    const d = card._charts.r1; const s = Date.parse(startsAt);
    const heatAfter = d.predHeat.some(([a, b]) => b > s && a < s + 3600e3);
    return { band: !!card.shadowRoot.querySelector(".optband"), heatAfter, opt: d.segs.some((x) => x.opt) };
  }, est.starts_at);
  ok(r.band && r.opt && r.heatAfter, JSON.stringify(r));
  // The line and the band start at the level (22°), not at the top of the chart;
  // the label sits right above the top of the line.
  const g = await p.evaluate(() => {
    const sr = card.shadowRoot, line = sr.querySelector(".optline"), band = sr.querySelector(".optband");
    const lab = sr.querySelector(".optlab"), svg = sr.querySelector(".hchart svg").getBoundingClientRect();
    const level = [...sr.querySelectorAll(".tline.future")].map((l) => +l.getAttribute("y1")).reduce((a, b) => Math.min(a, b));
    const lineTop = +line.getAttribute("y1");
    const lb = lab.getBoundingClientRect(), topPx = svg.top + (lineTop / 100) * svg.height;
    return { lineTop, bandTop: +band.getAttribute("y"), level, labBottom: lb.bottom, topPx };
  });
  ok(Math.abs(g.lineTop - g.level) < 0.01 && Math.abs(g.bandTop - g.level) < 0.01 && g.lineTop > 6, "line top " + JSON.stringify(g));
  ok(g.labBottom <= g.topPx + 0.5 && g.labBottom > g.topPx - 12, "label above the line " + JSON.stringify(g));
});

test("time zone of New York: midnight lines follow the card clock", async (p) => {
  await mount(p, {}, { rooms: R1, tz: "America/New_York" }); await openChart(p);
  const r = await p.evaluate(() => {
    const sr = card.shadowRoot; const d = card._charts.r1;
    return [...sr.querySelectorAll(".daysep")].map((l) => d.v0 + (+l.getAttribute("x1") / 1000) * (d.v1 - d.v0))
      .map((t) => new Date(t).toLocaleString("en-US", { timeZone: "America/New_York", hour: "2-digit", minute: "2-digit", hour12: false }));
  });
  ok(r.length && r.every((s) => s === "00:00" || s === "24:00"), JSON.stringify(r));
}, { tz: "America/New_York", locale: "en-US" });

test("learned sun: the prediction is warmer and Details show the sun", async (p) => {
  const pred = async (sunGain) => {
    await mount(p, {}, { rooms: [{ id: "r1", name: "Bedroom", current: 21, sunGain }], sun: 0.4 }); await openChart(p);
    return p.evaluate(() => card._charts.r1.pred.map((x) => x[1]));
  };
  const none = await pred(0), sunny = await pred(2);
  const mean = (a) => a.reduce((x, y) => x + y, 0) / a.length;
  ok(mean(sunny) > mean(none) + 0.2, `${mean(sunny)} vs ${mean(none)}`);
});

test("prediction follows the band of the device; self-regulating holds the target", async (p) => {
  const run = async (room) => {
    await mount(p, {}, { rooms: [{ id: "r1", name: "Bedroom", current: 21, target: 21, ...room }] }); await openChart(p);
    return p.evaluate(() => { const d = card._charts.r1; const v = d.pred.filter(([t]) => t < d.now + 2.5 * 3600e3).map((x) => x[1]);
      return { min: Math.min(...v), max: Math.max(...v), heat: d.predHeat.filter(([a]) => a < d.now + 2.5 * 3600e3).length }; });
  };
  const hold = await run({});
  const gt = await run({ band: [0.3, 0.3], tau: 60 });
  const inertia = await run({ band: [0.3, 0.3], tau: 60, inertia: true });
  ok(hold.max - hold.min < 0.1 && hold.heat <= 2, "hold: " + JSON.stringify(hold));
  ok(gt.max - gt.min > 0.4 && gt.heat >= 1, "band: " + JSON.stringify(gt));
  ok(gt.max > 21.3 && inertia.max < gt.max - 0.1 && inertia.max <= 21.36, "inertia " + JSON.stringify([gt, inertia]));
});

test("legend hides and shows a series, remembered", async (p) => {
  await p.evaluate(() => { try { localStorage.removeItem("shc-hidden-series"); } catch (e) {} });
  await p.evaluate(([c, h]) => mount(c, h), [{}, { rooms: [{ id: "r1", name: "Bedroom" }] }]); await p.waitForTimeout(250);
  await p.evaluate(() => card.shadowRoot.querySelector('[data-key="chart-r1"]').click()); await p.waitForTimeout(400);
  const n = (sel) => p.evaluate((s) => card.shadowRoot.querySelectorAll(s).length, sel);
  ok((await n(".templine")) === 1 && (await n(".oline")) > 0, "drawn");
  await p.evaluate(() => card.shadowRoot.querySelector('[data-action="series"][data-series="temp"]').click()); await p.waitForTimeout(150);
  eq(await n(".templine"), 0, "temperature hidden");
  ok(await p.evaluate(() => card.shadowRoot.querySelector('[data-series="temp"]').classList.contains("off")), "legend off");
  await p.evaluate(() => card.shadowRoot.querySelector('[data-action="series"][data-series="out"]').click()); await p.waitForTimeout(150);
  eq(await n(".oline"), 0, "outdoor hidden");
  eq(await p.evaluate(() => JSON.parse(localStorage.getItem("shc-hidden-series")).sort()), ["out", "temp"], "kept");
  await p.evaluate(() => card.shadowRoot.querySelector('[data-action="series"][data-series="temp"]').click()); await p.waitForTimeout(150);
  eq(await n(".templine"), 1, "shown again");
  await p.evaluate(() => { localStorage.removeItem("shc-hidden-series"); });
});

test("expected sun: a faint area in the outdoor band, only with a learned gain", async (p) => {
  await p.evaluate(([c, h]) => mount(c, h), [{}, { rooms: [{ id: "r1", name: "Bedroom", sunGain: 1.5 }], sun: 0.4 }]); await p.waitForTimeout(250);
  await p.evaluate(() => card.shadowRoot.querySelector('[data-key="chart-r1"]').click()); await p.waitForTimeout(400);
  eq(await p.evaluate(() => card.shadowRoot.querySelectorAll(".sunarea").length), 1, "sun area");
  eq(await p.evaluate(() => card.shadowRoot.querySelectorAll('[data-series="sun"]').length), 1, "sun legend");
  await p.evaluate(([c, h]) => mount(c, h), [{}, { rooms: [{ id: "r1", name: "Bedroom" }], sun: 0.4 }]); await p.waitForTimeout(250);
  await p.evaluate(() => card.shadowRoot.querySelector('[data-key="chart-r1"]').click()); await p.waitForTimeout(400);
  eq(await p.evaluate(() => card.shadowRoot.querySelectorAll(".sunarea").length), 0, "no sun area without a gain");
});

test("a week of a sensor that reports every 30 s is drawn with far fewer points, keeping its peaks", async (p) => {
  const r = await p.evaluate(() => {
    const t0 = Date.UTC(2026, 10, 1), pts = [];
    for (let i = 0; i < 7 * 24 * 120; i++) pts.push([t0 + i * 30000, 20 + Math.sin(i / 50) + (i === 12345 ? 3 : 0)]);
    const span = pts.at(-1)[0] - t0;
    const thin = thinPoints(pts, (t) => ((t - t0) / span) * 1000);
    return { n: thin.length, max: Math.max(...thin.map((q) => q[1])), min: Math.min(...thin.map((q) => q[1])),
      first: thin[0] === pts[0], last: thin.at(-1) === pts.at(-1), sorted: thin.every((q, i) => !i || q[0] > thin[i - 1][0]) };
  });
  ok(r.n <= 4004 && r.n < 20160 / 4, "points: " + r.n);
  ok(Math.abs(r.max - 23 - Math.sin(12345 / 50)) < 1e-9, "the spike is kept: " + r.max);
  ok(r.min < 19.0001, "the lowest is kept: " + r.min);
  ok(r.first && r.last && r.sorted, "first, last, in order");
});

test("time format of the user profile: 24 h, 12 h, and the one of the language", async (p) => {
  const next = async (timeFormat, lang) => {
    await mount(p, {}, { rooms: R1, timeFormat, lang });
    return p.evaluate(() => card._fmt(Date.UTC(2026, 0, 5, 15, 30), { hour: "2-digit", minute: "2-digit" }));
  };
  eq(await next("24", "en"), "17:30", "24 h with English");
  ok(/5:30\s?PM/i.test(await next("12", "en")), "12 h");
  ok(/5:30\s?PM/i.test(await next("language", "en")), "English language: 12 h");
  eq(await next("language", "ro"), "17:30", "Romanian language: 24 h");
});
