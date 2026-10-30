// Screenshots of the card for the README, from invented data (page.html).
// Run: node tools/screenshots/shoot.js  (needs Playwright with Chromium)
const { chromium } = require('playwright');
const path = require('path');
const OUT = path.join(__dirname, '..', '..', 'docs', 'images');
(async () => {
  const b = await chromium.launch();
  const shot = async (name, cfg, setup, opts = {}) => {
    const p = await b.newPage({ viewport: { width: 552, height: 1000 }, deviceScaleFactor: 2, timezoneId: 'Europe/Bucharest' });
    p.on('pageerror', e => console.log(name, 'PAGEERROR', e.message));
    await p.clock.setFixedTime(new Date('2026-11-04T17:40:00+02:00'));
    await p.addInitScript(`window.CFG=${JSON.stringify(cfg)};`);
    await p.goto('file://' + __dirname + '/page.html');
    if (opts.light) await p.evaluate(() => { document.body.classList.add('light'); hass.themes = { darkMode: false }; });
    if (setup) await p.evaluate(setup);
    await p.waitForTimeout(500);
    const el = await p.evaluateHandle((sel) => sel ? [...card.shadowRoot.querySelectorAll(sel.q)].find(x => !sel.text || x.textContent.includes(sel.text)) : card.shadowRoot.querySelector('ha-card'), opts.sel || null);
    await el.asElement().screenshot({ path: path.join(OUT, `card-${name}.png`) });
    await p.close();
  };
  const open = (keys) => `(() => { ${keys.map(k => `card._open['${k}'] = true;`).join('')} card._lastKey=''; card._render(); })()`;
  await shot('hero', { collapsed: true, title: 'Heating' }, open(['room-living_room']));
  await shot('room-chart', { collapsed: true }, open(['room-living_room', 'chart-living_room']), { sel: { q: '.block.room.open', text: 'Living room' } });
  await shot('compact', { compact: true, title: 'Heating' }, null);
  await shot('room-light', { collapsed: true }, open(['room-bathroom', 'quick-bathroom']), { light: true, sel: { q: '.block.room.open', text: 'Bathroom' } });
  await b.close();
})();
