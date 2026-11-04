// The fields of the schedule editor: readable in a dark theme, a time typed digit by digit.
const mount = async (p, config, hass) => { await p.evaluate(([c, h]) => mount(c, h), [config, hass]); await p.waitForTimeout(200); };
const click = (p, sel) => p.evaluate((s) => { const el = card.shadowRoot.querySelector(s); if (!el) throw new Error("no " + s); el.click(); }, sel);
const R = [{ id: "r1", name: "Bedroom" }];
const openEditor = async (p) => {
  await mount(p, {}, { rooms: R, dark: true });
  await click(p, '[data-key="sched-r1"]'); await p.waitForTimeout(100);
  await click(p, '[data-action="edit"][data-room="r1"]'); await p.waitForTimeout(150);
};
// Contrast of two CSS colours (WCAG), from their computed rgb().
const contrast = (a, b) => {
  const lum = (c) => {
    const [r, g, bl] = c.match(/\d+(\.\d+)?/g).slice(0, 3).map(Number).map((v) => {
      v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
    });
    return 0.2126 * r + 0.7152 * g + 0.0722 * bl;
  };
  const [x, y] = [lum(a), lum(b)].sort((m, n) => n - m);
  return (x + 0.05) / (y + 0.05);
};

test("schedule editor in a dark theme: the preset list, the fields and the time of a handle are readable", async (p) => {
  await p.evaluate(() => { document.body.style.cssText += ";--primary-text-color:#e1e1e1;--card-background-color:rgba(30,30,30,0.6);--primary-background-color:#111;background:#111"; });
  await openEditor(p);
  const c = await p.evaluate(() => {
    const sr = card.shadowRoot;
    const style = (el) => { const s = getComputedStyle(el); return { fg: s.color, bg: s.backgroundColor }; };
    const sel = sr.querySelector('select[data-field="preset"]');
    const opt = sel.querySelector("option");
    const time = sr.querySelector('input[data-field="time"]');
    const handle = sr.querySelector(".handle .htime");
    return { sel: style(sel), opt: style(opt), time: style(time), htime: style(handle), scheme: getComputedStyle(card).colorScheme };
  });
  for (const [name, v] of Object.entries({ select: c.sel, option: c.opt, time: c.time, "handle time": c.htime })) {
    ok(!/rgba\(.*, 0(\.\d+)?\)$/.test(v.bg) || v.bg.endsWith(", 1)"), `${name}: background must be opaque, ${v.bg}`);
    ok(contrast(v.fg, v.bg) >= 4.5, `${name}: ${v.fg} on ${v.bg}`);
  }
  eq(c.scheme, "dark", "native pickers in the dark scheme");
}, { dark: true });

test("schedule editor: a time typed digit by digit keeps the field until it is left", async (p) => {
  await openEditor(p);
  const sel = 'input[data-field="time"][data-index="1"]';
  await p.evaluate((s) => card.shadowRoot.querySelector(s).focus(), sel);
  // 06:00 → 07:30, typed as in a real field: hours, then minutes.
  await p.keyboard.type("0730");
  await p.waitForTimeout(150);
  const during = await p.evaluate((s) => ({ focused: card.shadowRoot.activeElement?.matches?.(s) || false, value: card.shadowRoot.querySelector(s)?.value }), sel);
  ok(during.focused, "the field keeps the focus while typing: " + JSON.stringify(during));
  eq(during.value, "07:30", "the whole time is typed");
  // Leaving the field draws the editor again with the new time.
  await p.keyboard.press("Tab"); await p.waitForTimeout(150);
  const after = await p.evaluate(() => card._draft.workday.map((x) => x.time));
  ok(after.includes("07:30"), "kept in the draft: " + JSON.stringify(after));
});

test("schedule editor: a typed time and then Save at once (a real click) saves the new time", async (p) => {
  await openEditor(p);
  const sel = 'input[data-field="time"][data-index="1"]';
  await p.evaluate((s) => card.shadowRoot.querySelector(s).focus(), sel);
  await p.keyboard.type("0730");
  // A real mouse click on Save: the field loses the focus first (the editor is
  // drawn again), then the click must still reach Save.
  const box = await p.evaluate(() => {
    const el = card.shadowRoot.querySelector('[data-action="save"][data-room="r1"]');
    el.scrollIntoView({ block: "center" });
    const r = el.getBoundingClientRect();
    return [r.left + r.width / 2, r.top + r.height / 2];
  });
  await p.mouse.click(box[0], box[1]); await p.waitForTimeout(200);
  const s = (await p.evaluate(() => calls.service)).at(-1);
  ok(s && s.service === "set_schedule", "saved: " + JSON.stringify(s && s.service));
  ok(JSON.stringify(s.data.profiles.workday).includes("07:30"), "with the new time: " + JSON.stringify(s.data.profiles.workday));
});
