const mount = async (p, config, hass) => { await p.evaluate(([c, h]) => mount(c, h), [config, hass]); await p.waitForTimeout(200); };
const open = (p) => p.evaluate(() => card.shadowRoot.querySelector('[data-key="chart-r1"]').click());
test("leaving the dashboard with the chart open and coming back later: closed", async (p) => {
  await mount(p, {}, { rooms: [{ id: "r1", name: "Bedroom" }] }); await open(p); await p.waitForTimeout(250);
  const r = await p.evaluate(async () => {
    const host = document.getElementById("host"); host.removeChild(card); await sleep(1300);
    host.appendChild(card); card.hass = makeHass({ rooms: [{ id: "r1", name: "Bedroom" }], tick: 5 }); await sleep(150);
    return !!card.shadowRoot.querySelector("dialog.chartpop");
  });
  eq(r, false, "chart window popped up again");
});
test("a card moved to another column keeps the chart open and modal", async (p) => {
  await mount(p, {}, { rooms: [{ id: "r1", name: "Bedroom" }] }); await open(p); await p.waitForTimeout(250);
  const r = await p.evaluate(async () => {
    const host = document.getElementById("host"); const other = document.createElement("div"); document.body.appendChild(other);
    other.appendChild(card); await sleep(1300);
    const d = card.shadowRoot.querySelector("dialog.chartpop"); return d ? d.matches(":modal") : null;
  });
  eq(r, true, "chart kept and modal");
});

test("a pan let go outside the card ends once; a card taken off the page no longer listens", async (p) => {
  await mount(p, {}, { rooms: [{ id: "r1", name: "Bedroom" }] });
  const r = await p.evaluate(async () => {
    let calls = 0;
    card._pointerUp = () => { calls += 1; card._pan = null; };
    const up = (target) => target.dispatchEvent(new PointerEvent("pointerup", { bubbles: true, composed: true }));
    // Outside the card: the window ends the pan.
    card._pan = {}; up(document.body); const outside = calls;
    // Inside the card: only the card's own listener, not a second time from the window.
    card._pan = {}; up(card.shadowRoot.querySelector("ha-card, div") || card.shadowRoot.firstElementChild); const inside = calls - outside;
    // Taken off the page: the window no longer reaches it.
    const host = card.parentNode; host.removeChild(card);
    card._pan = {}; up(document.body); const removed = calls - outside - inside;
    host.appendChild(card);
    card._pan = {}; up(document.body); const back = calls - outside - inside - removed;
    card._pan = null;
    return { outside, inside, removed, back };
  });
  eq(r, { outside: 1, inside: 1, removed: 0, back: 1 }, "pointerup handling");
});
