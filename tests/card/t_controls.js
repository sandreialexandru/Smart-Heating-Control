// Details, buttons, quick set and the schedule editor.
const mount = async (p, config, hass) => { await p.evaluate(([c, h]) => mount(c, h), [config, hass]); await p.waitForTimeout(200); };
const click = (p, sel) => p.evaluate((s) => { const el = card.shadowRoot.querySelector(s); if (!el) throw new Error("no " + s); el.click(); }, sel);
const services = (p) => p.evaluate(() => calls.service);
const R = [{ id: "r1", name: "Bedroom", humidity: 62, wall: 84.4 }];

test("reset learning asks to confirm, then presses the button", async (p) => {
  await mount(p, {}, { rooms: R }); await click(p, '[data-key="details-r1"]'); await p.waitForTimeout(100);
  await click(p, '[data-action="reset-learning"]'); await p.waitForTimeout(100);
  eq((await services(p)).length, 0, "no call on first click");
  ok(await p.evaluate(() => card.shadowRoot.querySelector('[data-action="reset-learning"]').classList.contains("soft-warn")), "confirm shown");
  await click(p, '[data-action="reset-learning"]'); await p.waitForTimeout(100);
  eq(await services(p), [{ domain: "button", service: "press", data: { entity_id: "button.bedroom_reset_learning" } }], "press");
});

test("reset confirmation expires after a few seconds", async (p) => {
  await mount(p, {}, { rooms: R }); await click(p, '[data-key="details-r1"]'); await p.waitForTimeout(100);
  await click(p, '[data-action="reset-learning"]'); await p.waitForTimeout(4300);
  ok(!(await p.evaluate(() => card.shadowRoot.querySelector('[data-action="reset-learning"]').classList.contains("soft-warn"))), "still confirming");
  await click(p, '[data-action="reset-learning"]'); await p.waitForTimeout(100);
  eq((await services(p)).length, 0, "a single click after it expired must not reset");
});

test("learning rows open the sensor (more info)", async (p) => {
  await mount(p, {}, { rooms: R }); await click(p, '[data-key="details-r1"]'); await p.waitForTimeout(100);
  const id = await p.evaluate(() => new Promise((res) => {
    card.addEventListener("hass-more-info", (e) => res(e.detail.entityId), { once: true });
    [...card.shadowRoot.querySelectorAll(".ltile")].find((x) => x.innerText.includes("Weather curve")).click();
  }));
  eq(id, "sensor.bedroom_heating_rate", "entity");
});

test("quick set: a level for 2 hours calls set_override", async (p) => {
  await mount(p, {}, { rooms: R }); await click(p, '[data-key="quick-r1"]'); await p.waitForTimeout(100);
  await p.evaluate(() => { const h = card.shadowRoot.querySelector('input[data-quick="hours"][data-room="r1"]'); if (h) { h.value = "2"; h.dispatchEvent(new Event("change", { bubbles: true })); } });
  await click(p, '[data-action="quick-preset"][data-preset="eco"]'); await p.waitForTimeout(100);
  const s = (await services(p)).at(-1);
  ok(s && s.domain === "advanced_climate" && s.service === "set_override" && s.data.preset === "eco" && s.data.room === "r1", JSON.stringify(s));
});

test("a failing service does not break the card (Home Assistant shows its own error)", async (p) => {
  await mount(p, {}, { rooms: R, serviceFails: true }); await click(p, '[data-key="quick-r1"]'); await p.waitForTimeout(100);
  await click(p, '[data-action="quick-preset"][data-preset="eco"]'); await p.waitForTimeout(150);
  ok((await p.evaluate(() => card.shadowRoot.querySelector("ha-card").innerText)).includes("Bedroom"), "card still there");
  await click(p, '[data-key="chart-r1"]'); await p.waitForTimeout(250);
  ok(await p.evaluate(() => !!card.shadowRoot.querySelector("dialog.chartpop")), "chart still opens");
});

test("schedule editor: edit, move nothing, save sends both profiles with their days", async (p) => {
  await mount(p, {}, { rooms: R }); await click(p, '[data-key="sched-r1"]'); await p.waitForTimeout(100);
  await click(p, '[data-action="edit"][data-room="r1"]'); await p.waitForTimeout(100);
  await click(p, '[data-action="save"][data-room="r1"]'); await p.waitForTimeout(150);
  const s = (await services(p)).at(-1);
  ok(s.service === "set_schedule", "service");
  eq(Object.keys(s.data.profiles), ["workday", "weekend"], "profiles");
  eq(s.data.profile_days.workday, { days: "workday", enabled: true }, "days kept");
});

test("schedule editor while a chart was open and closed again", async (p) => {
  await mount(p, {}, { rooms: R });
  await click(p, '[data-key="chart-r1"]'); await p.waitForTimeout(250);
  await p.keyboard.press("Escape"); await p.waitForTimeout(100);
  await click(p, '[data-key="sched-r1"]'); await click(p, '[data-action="edit"][data-room="r1"]'); await p.waitForTimeout(150);
  ok(await p.evaluate(() => !!card.shadowRoot.querySelector('[data-action="save"][data-room="r1"]')), "editor open");
});

test("level number change sends number.set_value", async (p) => {
  await mount(p, {}, { rooms: R }); await click(p, '[data-key="levels-r1"]').catch(() => {}); await p.waitForTimeout(100);
  const done = await p.evaluate(() => {
    const inp = card.shadowRoot.querySelector('input[data-entity^="number."]');
    if (!inp) return false;
    inp.value = "20.5"; inp.dispatchEvent(new Event("change", { bubbles: true })); return inp.dataset.entity;
  });
  ok(done, "level input found");
  await p.waitForTimeout(100);
  const s = (await services(p)).at(-1);
  ok(s && s.domain === "number" && s.service === "set_value" && s.data.value === 20.5, JSON.stringify(s));
});

test("mold badge on the open room shows the alert text", async (p) => {
  await mount(p, {}, { rooms: [{ ...R[0], alerts: [{ code: "mold_risk", params: { surface: 84, humidity: 62 }, room: "r1", message: "m" }] }] });
  const t = await p.evaluate(() => { const i = card.shadowRoot.querySelector('.pill ha-icon[icon="mdi:water-alert-outline"]'); return i ? i.parentElement.title : null; });
  ok(t && t.includes("84"), "badge: " + t);
});

test("set for a while on a narrow card: the values fit their fields, Set is a plain button", async (p) => {
  await p.evaluate(() => { document.getElementById("host").style.maxWidth = "300px"; });
  await mount(p, {}, { rooms: R }); await click(p, '[data-key="quick-r1"]'); await p.waitForTimeout(100);
  const r = await p.evaluate(() => {
    const ctx = document.createElement("canvas").getContext("2d");
    const room = (inp, text) => {
      const cs = getComputedStyle(inp);
      ctx.font = `${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
      // The arrows of a number field take about 18 px.
      const free = inp.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight) - 18;
      return free - ctx.measureText(text).width;
    };
    const q = (k) => card.shadowRoot.querySelector(`input[data-quick="${k}"][data-room="r1"]`);
    return { temp: room(q("temp"), "100.5"), hours: room(q("hours"), q("hours").placeholder),
      btn: card.shadowRoot.querySelector('[data-action="quick-temp"]').className.trim() };
  });
  ok(r.temp >= 0, "temperature cut: " + r.temp);
  ok(r.hours >= 0, "hours cut: " + r.hours);
  eq(r.btn, "btn", "Set like the other buttons");
});
