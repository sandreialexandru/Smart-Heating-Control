// Random gestures on the chart (mouse, touch, pinch, the bar, the wheel, the buttons):
// after each one the window is a time, the tooltip shows a real time, nothing fails.
for (const [seed, mobile] of [[1, false], [2, true], [3, true], [4, false], [5, true]]) {
  test(`fuzz chart gestures seed ${seed} ${mobile ? "phone" : "desktop"}`, async (p) => {
    const errors = [];
    p.on("pageerror", (e) => errors.push(e.message));
    await p.evaluate(() => mount({}, { rooms: [{ id: "r1", name: "Bedroom" }] }));
    await p.waitForTimeout(200);
    await p.evaluate(() => card.shadowRoot.querySelector('[data-key="chart-r1"]').click());
    await p.waitForTimeout(300);
    let s = seed * 9301;
    const rnd = () => ((s = (s * 16807) % 2147483647) / 2147483647);
    const bad = [];
    for (let i = 0; i < 120; i++) {
      const kind = Math.floor(rnd() * 7);
      const a = rnd(), b = rnd(), c = rnd();
      await p.evaluate(async ([kind, a, b, c]) => {
        const root = card.shadowRoot;
        const chart = root.querySelector("dialog.chartpop[open] .hchart") || root.querySelector(".hchart");
        const nav = root.querySelector("dialog.chartpop[open] .navbar") || root.querySelector(".navbar");
        const ev = (el, type, x, y, id, extra = {}) => el.dispatchEvent(new PointerEvent(type, { bubbles: true, composed: true, clientX: x, clientY: y, pointerId: id, pointerType: "touch", isPrimary: id === 1, button: 0, buttons: type === "pointerup" ? 0 : 1, ...extra }));
        const box = (el) => el.getBoundingClientRect();
        const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
        if (!chart) return;
        const r = box(chart);
        const y = r.top + r.height * 0.4;
        if (kind === 0) { // pan by a finger
          const x0 = r.left + r.width * a, x1 = r.left + r.width * b;
          ev(chart, "pointerdown", x0, y, 1);
          for (let k = 1; k <= 4; k++) { ev(chart, "pointermove", x0 + ((x1 - x0) * k) / 4, y, 1); await sleep(5); }
          ev(chart, "pointerup", x1, y, 1);
        } else if (kind === 1) { // pinch, sometimes lifting one finger then moving the other
          const cx = r.left + r.width * a, d0 = 20 + 100 * b, d1 = 10 + 200 * c;
          ev(chart, "pointerdown", cx - d0 / 2, y, 1); ev(chart, "pointerdown", cx + d0 / 2, y, 2);
          for (let k = 1; k <= 4; k++) { const d = d0 + ((d1 - d0) * k) / 4; ev(chart, "pointermove", cx - d / 2, y, 1); ev(chart, "pointermove", cx + d / 2, y, 2); await sleep(5); }
          if (c > 0.5) { ev(chart, "pointerup", cx + d1 / 2, y, 2); ev(chart, "pointermove", cx - d1 / 2 + 30, y, 1); ev(chart, "pointerup", cx - d1 / 2 + 30, y, 1); }
          else { ev(chart, "pointercancel", cx - d1 / 2, y, 1); ev(chart, "pointercancel", cx + d1 / 2, y, 2); }
        } else if (kind === 2 && nav) { // the bar: drag the window, also past its ends
          const n = box(nav); const x0 = n.left + n.width * a, x1 = n.left + n.width * (b * 1.4 - 0.2);
          ev(nav, "pointerdown", x0, n.top + n.height / 2, 1);
          for (let k = 1; k <= 4; k++) { ev(nav, "pointermove", x0 + ((x1 - x0) * k) / 4, n.top + n.height / 2, 1); await sleep(5); }
          ev(nav, "pointerup", x1, n.top + n.height / 2, 1);
        } else if (kind === 3) { // wheel: ctrl zoom or sideways
          chart.dispatchEvent(new WheelEvent("wheel", { bubbles: true, composed: true, clientX: r.left + r.width * a, clientY: y, deltaY: b > 0.5 ? 120 : -120, deltaX: c > 0.5 ? 200 * (b - 0.5) : 0, ctrlKey: c <= 0.5, cancelable: true }));
        } else if (kind === 4) { // the zoom buttons
          const btns = root.querySelectorAll('dialog.chartpop[open] [data-action="zoom"]');
          if (btns.length) btns[Math.floor(a * btns.length)].click();
        } else if (kind === 5) { // a fresh copy of the data (a hass update) in the middle of a gesture
          const x0 = r.left + r.width * a;
          ev(chart, "pointerdown", x0, y, 1);
          card.hass = { ...card._hass, states: { ...card._hass.states } };
          await sleep(20);
          ev(chart, "pointermove", x0 + 40, y, 1); ev(chart, "pointerup", x0 + 40, y, 1);
        } else { // double tap
          chart.dispatchEvent(new MouseEvent("dblclick", { bubbles: true, composed: true, clientX: r.left + r.width * a, clientY: y }));
        }
        await sleep(30);
      }, [kind, a, b, c]);
      await p.waitForTimeout(40);
      const st = await p.evaluate(() => {
        const d = card._charts?.r1, v = card._view?.r1;
        return { d: d && [d.v0, d.v1, d.t0, d.t1], v: v && [v.v0, v.v1] };
      });
      const fin = (xs) => !xs || xs.every((x) => Number.isFinite(x));
      if (!fin(st.v) || (st.v && st.v[1] <= st.v[0])) bad.push(`step ${i} kind ${kind}: view ${JSON.stringify(st.v)}`);
      // hover: a real time
      const pt = await p.evaluate((f) => { const c = card.shadowRoot.querySelector("dialog.chartpop[open] .hchart") || card.shadowRoot.querySelector(".hchart"); const r = c.getBoundingClientRect(); return [r.left + r.width * f, r.top + r.height * 0.4]; }, rnd());
      await p.mouse.move(pt[0], pt[1]);
      await p.waitForTimeout(30);
      const tip = await p.evaluate(() => { const t = card.shadowRoot.querySelector("dialog.chartpop[open] .tip") || card.shadowRoot.querySelector(".tip"); return t && !t.hidden ? t.innerText : ""; });
      if (/invalid|NaN|undefined/i.test(tip)) bad.push(`step ${i} kind ${kind}: tip ${tip}`);
      const head = await p.evaluate(() => (card.shadowRoot.querySelector("dialog.chartpop[open] .crange, dialog.chartpop[open] .ctop") || {}).innerText || "");
      if (/invalid|NaN/i.test(head)) bad.push(`step ${i}: header ${head}`);
    }
    eq(errors, [], "no page error");
    eq(bad.slice(0, 5), [], "every window a time");
  }, mobile ? { viewport: { width: 390, height: 844 }, touch: true } : {});
}
