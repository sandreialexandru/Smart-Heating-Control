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
