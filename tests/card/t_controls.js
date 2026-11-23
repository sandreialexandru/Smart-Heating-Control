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
      const free = inp.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
      return free - ctx.measureText(text).width;
    };
    const q = (k) => card.shadowRoot.querySelector(`input[data-quick="${k}"][data-room="r1"]`);
    const arrows = [q("temp"), q("hours")].map((i) => getComputedStyle(i).appearance).join();
    return { arrows, temp: room(q("temp"), "100.5"), hours: room(q("hours"), q("hours").placeholder),
      btn: card.shadowRoot.querySelector('[data-action="quick-temp"]').className.trim() };
  });
  eq(r.arrows, "textfield,textfield", "no arrows over the value");
  ok(r.temp >= 0, "temperature cut: " + r.temp);
  ok(r.hours >= 0, "hours cut: " + r.hours);
  eq(r.btn, "btn", "Set like the other buttons");
});

// Set for a while with only the hours: the current manual change lasts that long from now.
const quickSet = async (p, temp, hours) => {
  await click(p, '[data-key="quick-r1"]'); await p.waitForTimeout(100);
  await p.evaluate(([t, h]) => {
    const q = (k) => card.shadowRoot.querySelector(`input[data-quick="${k}"][data-room="r1"]`);
    q("temp").value = t; q("hours").value = h;
  }, [temp, hours]);
  await click(p, '[data-action="quick-temp"][data-room="r1"]'); await p.waitForTimeout(120);
};
const note = (p) => p.evaluate(() => card.shadowRoot.querySelector(".qnote")?.textContent || null);

test("set for a while: only the hours keep the level of the manual change", async (p) => {
  await mount(p, {}, { rooms: [{ ...R[0], state: "manual_override", override: { origin: "card", until: null, preset: "comfort", temperature: 22 } }] });
  await quickSet(p, "", "2");
  eq(await services(p), [{ domain: "advanced_climate", service: "set_override", data: { room: "r1", preset: "comfort", duration_hours: 2 } }], "call");
  eq(await note(p), null, "no note");
});

test("set for a while: only the hours keep the temperature of a manual change without a level", async (p) => {
  await mount(p, {}, { rooms: [{ ...R[0], state: "manual_override", override: { origin: "device", until: null, preset: null, temperature: 23.5 } }] });
  await quickSet(p, "", "1.5");
  eq(await services(p), [{ domain: "advanced_climate", service: "set_override", data: { room: "r1", temperature: 23.5, duration_hours: 1.5 } }], "call");
});

test("set for a while: only the hours without a manual change say so instead of doing nothing", async (p) => {
  await mount(p, {}, { rooms: R });
  await quickSet(p, "", "2");
  eq((await services(p)).length, 0, "no call");
  eq(await note(p), "No manual change to extend: type a temperature or pick a level.", "note");
  ok(await p.evaluate(() => card.shadowRoot.querySelector('input[data-quick="hours"][data-room="r1"]').value === "2"), "the hours stay typed");
});

test("set for a while: nothing typed asks for a temperature", async (p) => {
  await mount(p, {}, { rooms: [{ ...R[0], state: "manual_override", override: { origin: "card", until: null, preset: "comfort", temperature: 22 } }] });
  await quickSet(p, "", "");
  eq((await services(p)).length, 0, "no call");
  eq(await note(p), "Type a temperature or pick a level.", "note");
});

test("set for a while: a temperature with hours is sent as before", async (p) => {
  await mount(p, {}, { rooms: R });
  await quickSet(p, "22.5", "3");
  eq(await services(p), [{ domain: "advanced_climate", service: "set_override", data: { room: "r1", temperature: 22.5, duration_hours: 3 } }], "call");
});

test("alerts: a silent sensor says whether it is left out or still controls the room", async (p) => {
  await mount(p, {}, { rooms: [R[0]] });
  const texts = await p.evaluate(() =>
    [true, false].map((left_out) =>
      card._alertText({ code: "sensor_silent", params: { entity: "sensor.room_temp", hours: "12", left_out }, message: "m" })
    )
  );
  ok(texts[0].includes("sensor.room_temp has sent no temperature for more than 12 h; it is left out until it reports again."), "left out: " + texts[0]);
  ok(texts[1].includes("sensor.room_temp has sent no temperature for more than 12 h; the room is controlled by an old value."), "still controls: " + texts[1]);
});

test("the schedule copied to other rooms of the house: only the rooms whose schedule can be written; each one replaced", async (p) => {
  const rooms = [
    { id: "r1", name: "Bedroom" },
    { id: "r2", name: "Kid" },
    { id: "r3", name: "Living", scheduleEditable: false },
  ];
  await mount(p, {}, { rooms });
  await click(p, '[data-key="sched-r1"]'); await p.waitForTimeout(100);
  await click(p, '[data-action="copy-open"][data-room="r1"]'); await p.waitForTimeout(100);
  const box = await p.evaluate(() => ({
    rooms: [...card.shadowRoot.querySelectorAll("[data-copyto]")].map((c) => c.dataset.copyto),
    disabled: card.shadowRoot.querySelector('[data-action="copy-run"]').disabled,
  }));
  eq(box, { rooms: ["r2"], disabled: true }, "the other rooms that can take it; nothing chosen yet");
  await click(p, '[data-copyto="r2"]'); await p.waitForTimeout(100);
  await p.evaluate(() => { window.calls.service = []; });
  await click(p, '[data-action="copy-run"]'); await p.waitForTimeout(200);
  const sent = await p.evaluate(() => window.calls.service);
  eq(sent.length, 1, "one call");
  eq([sent[0].service, sent[0].data.room, Object.keys(sent[0].data.profiles), sent[0].data.profile_days.weekend],
    ["set_schedule", "r2", ["workday", "weekend"], { days: "weekend", enabled: true }], "the profiles and their days of the room");
  const after = await p.evaluate(() => ({
    box: !!card.shadowRoot.querySelector(".copybox"),
    done: card.shadowRoot.querySelector('[data-section="sched-r1"] .hint.ok:last-of-type')?.innerText || [...card.shadowRoot.querySelectorAll('[data-section="sched-r1"] .hint.ok')].map((h) => h.innerText).join("|"),
  }));
  ok(!after.box && /Copied to: Kid/.test(after.done), "said so: " + after.done);
  // Closing the schedule ends the message.
  await click(p, '[data-key="sched-r1"]'); await p.waitForTimeout(80);
  await click(p, '[data-key="sched-r1"]'); await p.waitForTimeout(80);
  eq(await p.evaluate(() => /Copied to/.test(card.shadowRoot.querySelector('[data-section="sched-r1"]').innerText)), false, "gone after closing the schedule");
});

test("a copy that a room refuses: the error, and that room stays chosen", async (p) => {
  await mount(p, {}, { rooms: [{ id: "r1", name: "Bedroom" }, { id: "r2", name: "Kid" }, { id: "r3", name: "Office" }], serviceFailsFor: "r3" });
  await click(p, '[data-key="sched-r1"]'); await p.waitForTimeout(100);
  await click(p, '[data-action="copy-open"][data-room="r1"]'); await p.waitForTimeout(100);
  await click(p, '[data-copyto="r2"]'); await p.waitForTimeout(50);
  await click(p, '[data-copyto="r3"]'); await p.waitForTimeout(50);
  await click(p, '[data-action="copy-run"]'); await p.waitForTimeout(200);
  const r = await p.evaluate(() => ({
    error: card.shadowRoot.querySelector('[data-section="sched-r1"] .error')?.innerText || "",
    chosen: [...card.shadowRoot.querySelectorAll("[data-copyto]")].filter((c) => c.checked).map((c) => c.dataset.copyto),
    text: card.shadowRoot.querySelector('[data-section="sched-r1"]').innerText,
  }));
  ok(/boom/.test(r.error) || /boom/.test(r.text), "the error: " + r.error);
  eq(r.chosen, ["r3"], "the room that refused stays chosen");
  ok(/Copied to: Kid/.test(r.text), "the one that took it");
});

test("details: since when the room asks for heat and heats, the heat source and its minimum time (#30)", async (p) => {
  const now = await p.evaluate(() => Date.now());
  const iso = (m) => new Date(now + m * 60000).toISOString();
  const waiting = { id: "r1", name: "Bedroom", demand: true, heating: false, attrs: {
    demand_since: iso(-25), heating_since: iso(-90),
    heat_source: { entity_id: "switch.boiler", on: false, since: iso(-4), waiting: "min_off", until: iso(3) },
  } };
  await mount(p, {}, { rooms: [waiting] }); await click(p, '[data-key="details-r1"]'); await p.waitForTimeout(100);
  const all = await p.evaluate(() => [...card.shadowRoot.children].map((c) => c.innerText || "").join("\n"));
  const text = all;
  ok(/Asks for heat\s*Yes · since \d\d:\d\d \(25 min\)/.test(all), "asks since");
  ok(/Heating\s*No · since \d\d:\d\d \(1 h 30 min\)/.test(all), "stopped since");
  ok(/Heat source\s*Off · since \d\d:\d\d \(4 min\) · kept off 3 min more \(minimum off time\)/.test(all), "held off");
  ok(text.length > 0, "details shown");
  // A tap on the heat source opens it.
  const id = await p.evaluate(() => new Promise((res) => {
    card.addEventListener("hass-more-info", (e) => res(e.detail.entityId), { once: true });
    [...card.shadowRoot.querySelectorAll(".details .link")].find((x) => x.innerText.includes("Heat source")).click();
  }));
  eq(id, "switch.boiler", "more info of the heat source");
  // The flame: grey while it only asks, the colour of heat with a glow while it heats.
  const flame = () => p.evaluate(() => { const f = card.shadowRoot.querySelector(".hero .flame, .badges .flame, .flame"); return f ? f.className : null; });
  ok(!(await flame()).includes(" on"), "asking: not on");
  await mount(p, {}, { rooms: [{ id: "r1", name: "Bedroom", demand: true, heating: true }] });
  const cls = await p.evaluate(() => [...card.shadowRoot.querySelectorAll(".flame")].map((f) => f.className));
  ok(cls.some((c) => c.includes("on") && c.includes("glow")), "heating: on with a glow " + JSON.stringify(cls));
});
