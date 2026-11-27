// The dial of a room (the levels across the arc, the ring of now, hot while heating, a room
// that may not heat) and the motion after a drawing.
const mount = async (p, config, hass) => { await p.evaluate(([c, h]) => mount(c, h), [config, hass]); await p.waitForTimeout(200); };
const update = async (p, hass) => { await p.evaluate((h) => { card.hass = makeHass(h); }, hass); await p.waitForTimeout(50); };
const ticks = (p, sel = ".hero .gauge") =>
  p.evaluate((s) => [...card.shadowRoot.querySelector(s).querySelectorAll(".gtick")].map((g) => ({
    cls: g.getAttribute("class"),
    color: g.querySelectorAll("line")[1].getAttribute("stroke"),
    title: g.querySelector("title")?.textContent || "",
  })), sel);

test("arc: a line for every level of the room, the target the thicker one in the colour of its level", async (p) => {
  // Fixture levels: home 21, eco 18, away 16, sleep 18.5, comfort 22, activity 19; the target home 21.
  await mount(p, {}, { rooms: [{ id: "r1", name: "Bedroom" }] });
  const t = await ticks(p);
  eq(t.length, 6, "five levels and the target (home drawn once, as the target)");
  const target = t.filter((x) => x.cls.includes("target"));
  eq(target.length, 1, "one target");
  eq(target[0].color, "#f2a900", "home colour");
  ok(target[0].title.includes("21"), target[0].title);
  ok(t.some((x) => x.title.startsWith("Comfort") && x.color === "#c2255c"), "comfort: " + JSON.stringify(t));
  ok(await p.evaluate(() => !!card.shadowRoot.querySelector(".hero .gauge .gring")), "the ring of now");
});

test("arc: a manual target in the colour of the text, the level of the time drawn as a level", async (p) => {
  const override = { temperature: 23, until: null, origin: "card", preset: null, applied: true };
  await mount(p, {}, { rooms: [{ id: "r1", name: "Bedroom", target: 23, override, state: "manual_override" }] });
  const t = await ticks(p);
  const target = t.find((x) => x.cls.includes("target"));
  eq(target.color, "var(--primary-text-color)", "manual");
  ok(t.some((x) => !x.cls.includes("target") && x.color === "#f2a900"), "home still on the arc");
});

test("arc: a small dial shows only the target and the ring", async (p) => {
  await mount(p, { collapsed: true }, { rooms: [{ id: "r1", name: "Bedroom" }] });
  const t = await ticks(p, ".gauge");
  eq(t.length, 1, "the target only");
  ok(t[0].cls.includes("target"), "target");
});

test("arc: the ring in the colour of heat while the room heats, a halo only on the big dial", async (p) => {
  const ring = (p) => p.evaluate(() => {
    const g = card.shadowRoot.querySelector(".gauge");
    return { hot: g.querySelector(".gring").classList.contains("hot"), halo: !!g.querySelector(".ghalo") };
  });
  await mount(p, {}, { rooms: [{ id: "r1", name: "Bedroom", current: 19, heating: true }] });
  eq(await ring(p), { hot: true, halo: true }, "heating");
  await mount(p, {}, { rooms: [{ id: "r1", name: "Bedroom", current: 19, heating: false, demand: false }] });
  eq(await ring(p), { hot: false, halo: false }, "not heating");
  await mount(p, { collapsed: true }, { rooms: [{ id: "r1", name: "Bedroom", current: 19, heating: true }] });
  eq(await ring(p), { hot: true, halo: false }, "a small dial: no halo");
  await mount(p, {}, { rooms: [{ id: "r1", name: "Living", window: true, state: "window_open", reasonKey: "window_open", heating: true }] });
  eq(await ring(p), { hot: false, halo: false }, "a room that may not heat");
});

test("arc: grey with the reason while the room may not heat (a window open)", async (p) => {
  await mount(p, {}, { rooms: [{ id: "r1", name: "Living", window: true, state: "window_open", reasonKey: "window_open", demand: false, heating: false }] });
  const r = await p.evaluate(() => {
    const g = card.shadowRoot.querySelector(".hero .gauge");
    return { blocked: g.classList.contains("blocked"), why: g.querySelector(".gsub.why")?.textContent || "", label: g.getAttribute("aria-label") };
  });
  ok(r.blocked, "grey");
  ok(r.why.length > 0, "a reason under the number");
  ok(r.label.endsWith(r.why), r.label);
  await mount(p, {}, { rooms: [{ id: "r1", name: "Bedroom" }] });
  ok(await p.evaluate(() => !card.shadowRoot.querySelector(".hero .gauge.blocked .gsub.why")), "a room that heats: the target");
});

test("arc: before a change (the optimal start) the line of the coming level is open", async (p) => {
  await mount(p, {}, { rooms: [{ id: "r1", name: "Bedroom", state: "optimal_start", preset: "comfort", target: 22, current: 19 }] });
  const t = await ticks(p);
  const target = t.find((x) => x.cls.includes("target"));
  ok(target.cls.includes("next"), target.cls);
  eq(target.color, "#c2255c", "comfort");
});

test("motion: a new temperature moves the arc, the ring and the number; nothing the first time", async (p) => {
  await mount(p, {}, { rooms: [{ id: "r1", name: "Bedroom", current: 19 }] });
  const first = await p.evaluate(() => card.shadowRoot.querySelector(".hero .gvalue").getAnimations().length);
  eq(first, 0, "drawn, not moved");
  await update(p, { rooms: [{ id: "r1", name: "Bedroom", current: 20 }] });
  const r = await p.evaluate(() => {
    const g = card.shadowRoot.querySelector(".hero .gauge");
    return { arc: g.querySelector(".gvalue").getAnimations().length, ring: g.querySelector(".gnow").getAnimations().length };
  });
  ok(r.arc === 1 && r.ring === 1, JSON.stringify(r));
  await p.waitForTimeout(800);
  ok((await p.evaluate(() => card.shadowRoot.querySelector(".hero .gnum").textContent)).startsWith("20"), "the number ends on its value");
});

test("motion: none with reduced motion", async (p) => {
  await p.emulateMedia({ reducedMotion: "reduce" });
  try {
    await mount(p, {}, { rooms: [{ id: "r1", name: "Bedroom", current: 19 }] });
    await update(p, { rooms: [{ id: "r1", name: "Bedroom", current: 20 }] });
    eq(await p.evaluate(() => card.shadowRoot.querySelector(".hero .gvalue").getAnimations().length), 0, "still");
  } finally {
    await p.emulateMedia({ reducedMotion: "no-preference" });
  }
});

test("motion: a chart draws itself from the left when it opens, once", async (p) => {
  await mount(p, {}, { rooms: [{ id: "r1", name: "Bedroom" }] });
  await p.evaluate(() => card.shadowRoot.querySelector('[data-key="chart-r1"]').click());
  await p.waitForTimeout(150);
  const n = await p.evaluate(() => card.shadowRoot.querySelector(".hchart svg").getAnimations().length);
  eq(n, 1, "drawn in");
  await p.waitForTimeout(800);
  await update(p, { rooms: [{ id: "r1", name: "Bedroom", current: 20.4 }] });
  eq(await p.evaluate(() => card.shadowRoot.querySelector(".hchart svg").getAnimations().length), 0, "not again on an update");
});
