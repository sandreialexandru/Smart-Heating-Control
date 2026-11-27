// How the optimal start got to the level, in the room (early, late, reached late).
const mount = async (p, config, hass) => { await p.evaluate(([c, h]) => mount(c, h), [config, hass]); await p.waitForTimeout(200); };
const H = 3600e3;
const now = () => Date.now();
const nowText = (p) => p.evaluate(() => card.shadowRoot.querySelector(".chip.line").innerText);

test("optimal start: early, with a tick, the time it got there and how early", async (p) => {
  const at = new Date(now() + 0.5 * H).toISOString();
  const reached = new Date(now() - 0.2 * H).toISOString();
  await mount(p, {}, { rooms: [{ id: "r1", name: "Bedroom", state: "optimal_start", current: 21, target: 21, preheat: { state: "early", at, reached, preset: "home", target: 21 } }] });
  const r = await p.evaluate(() => {
    const el = card.shadowRoot.querySelector(".csub.preheat");
    return el ? { ok: el.classList.contains("ok"), tick: !!el.querySelector("ha-icon"), text: el.innerText } : null;
  });
  ok(r && r.ok && r.tick, JSON.stringify(r));
  ok(/21\.0° at .+, 42 min early/.test(r.text), r.text);
});

test("optimal start: late while it heats, beside the time to the target; then reached late, plain", async (p) => {
  const at = new Date(now() - 0.25 * H).toISOString();
  await mount(p, {}, { rooms: [{ id: "r1", name: "Bedroom", current: 20.2, target: 21, preheat: { state: "late", at, reached: null, preset: "home", target: 21 } }] });
  ok((await nowText(p)).includes("~35 min · late"), await nowText(p));
  ok(await p.evaluate(() => !card.shadowRoot.querySelector(".csub.preheat")), "no line yet");
  const reached = new Date(now() - 0.05 * H).toISOString();
  await mount(p, {}, { rooms: [{ id: "r1", name: "Bedroom", current: 21, target: 21, preheat: { state: "reached_late", at, reached, preset: "home", target: 21 } }] });
  const r = await p.evaluate(() => {
    const el = card.shadowRoot.querySelector(".csub.preheat");
    return { ok: el.classList.contains("ok"), tick: !!el.querySelector("ha-icon"), text: el.innerText };
  });
  ok(!r.ok && !r.tick, "plain: " + JSON.stringify(r));
  ok(/21\.0° at .+, 12 min late/.test(r.text), r.text);
});

test("optimal start: nothing without one", async (p) => {
  await mount(p, {}, { rooms: [{ id: "r1", name: "Bedroom" }] });
  ok(await p.evaluate(() => !card.shadowRoot.querySelector(".csub.preheat")), "none");
  ok(!(await nowText(p)).includes("late"), await nowText(p));
});

test("the same cold: hours per degree between the targets and outside, the last whole period against the one before", async (p) => {
  await mount(p, {}, { rooms: [{ id: "r1", name: "Bedroom" }] });
  const r = await p.evaluate(() => {
    const m = (pairs) => new Map(pairs.map(([t, mean]) => [t, { mean, min: null, max: null }]));
    const total = [[0, 10], [864e5, 12], [2 * 864e5, 5]]; // the last one: the day now, not whole
    const outdoor = m([[0, 4], [864e5, 3], [2 * 864e5, 2]]);
    const targets = [m([[0, 21], [864e5, 21]]), m([[0, 20], [864e5, 22]])];
    const div = document.createElement("div");
    div.innerHTML = card._statsWeather(total, outdoor, targets, "day", null);
    const p0 = div.firstElementChild;
    // 12 h / (21.5 − 3) = 0.65 h/° against 10 h / (20.5 − 4) = 0.61 h/°: +7 %.
    const chosenFirst = card._statsWeather(total, outdoor, targets, "day", 0);
    const warm = card._statsWeather(total, m([[0, 25], [864e5, 3]]), targets, "day", null);
    return { text: p0?.innerText, tip: p0?.title, less: p0?.classList.contains("less"), chosenFirst, warm };
  });
  ok(/: \+7% against /.test(r.text), r.text);
  ok(r.tip.includes("0.65 h/° against 0.61 h/°"), r.tip);
  eq(r.less, false, "more heating: not green");
  eq(r.chosenFirst, "", "the first period has none before it");
  eq(r.warm, "", "outside warmer than the targets: no comparison");
});
