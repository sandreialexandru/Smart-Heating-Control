// A sweep of the card and the panel over every scene of scenes.js, in every
// language, light and dark, on a desktop and on a phone, and every tab of the
// panel. Nothing is photographed: each state is checked for what must never
// show (an error of the page, "undefined", "NaN", "Invalid Date", "[object",
// a key of the texts left untranslated, a page wider than a phone).
//   node sweep.js [--only name] [--langs en,ro]
const { chromium } = require("playwright");
const { start } = require("./server");
const { SCENES, ACTIONS, PANEL, NOW } = require("./scenes");

const args = process.argv.slice(2);
const opt = (k) => (args.includes(k) ? args[args.indexOf(k) + 1] : null);
const LANGS = (opt("--langs") || "en,ro,de,nl,fr,it,es").split(",");
const only = opt("--only");
const DARK = { "--primary-background-color": "#111", "--card-background-color": "#1c1c1c", "--primary-text-color": "#e1e1e1", "--secondary-text-color": "#9b9b9b", "--divider-color": "#333" };
const STUBS = `customElements.define("ha-icon", class extends HTMLElement {});`;
const TABS = ["rooms", "week", "stats", "history", "devices"];
const BAD = /\bundefined\b|\bNaN\b|Invalid Date|\[object|\bnull\b(?!\s*\))/;

async function check(browser, srv, scene, v) {
  const [name, config, hass, act] = scene;
  const ctx = await browser.newContext({
    viewport: { width: v.width, height: 900 }, colorScheme: v.dark ? "dark" : "light",
    timezoneId: "Europe/Bucharest", locale: "en-GB", reducedMotion: "reduce",
  });
  await ctx.clock.setFixedTime(new Date(NOW));
  await ctx.addInitScript(STUBS);
  if (v.tab) await ctx.addInitScript((t) => localStorage.setItem("shc-panel-tab", t), v.tab);
  const p = await ctx.newPage();
  const errors = [];
  p.on("pageerror", (e) => errors.push("page error: " + e.message));
  p.on("console", (m) => m.type() === "error" && !/favicon|404/.test(m.text()) && errors.push("console: " + m.text()));
  await p.goto(srv.url + "/tests/card/page.html" + (config.panel && config.hash ? `#${config.hash}` : ""));
  if (v.dark) await p.evaluate((vars) => { for (const [k, x] of Object.entries(vars)) document.body.style.setProperty(k, x); }, DARK);
  const o = { now: NOW, ...hass, dark: v.dark, lang: v.lang, timeFormat: v.h12 ? "12" : hass.timeFormat };
  if (config.panel) await p.evaluate(([h, n]) => { mountPanel(h, { narrow: n }); window.card = window.panel; }, [o, v.width < 870]);
  else await p.evaluate(([c, h]) => mount(c, h), [config, o]);
  await p.waitForTimeout(300);
  if (act && !v.tab) {
    try { await act(p); } catch (e) { errors.push("action: " + e.message.split("\n")[0]); }
  }
  await p.waitForTimeout(350);
  const found = await p.evaluate((bad) => {
    const keys = Object.keys((window.TEXT || {}).en || {});
    const out = [];
    const root = (window.panel || window.card).shadowRoot;
    // Every text shown, the titles and labels too (not the hidden ones).
    const walk = (n) => {
      for (const c of n.childNodes) {
        if (c.nodeType === 3) {
          const t = c.textContent.trim();
          const el = c.parentElement;
          if (t && el && el.offsetParent !== null && el.tagName !== "STYLE" && el.tagName !== "SCRIPT") {
            if (new RegExp(bad).test(t)) out.push("text: " + t.slice(0, 120));
            for (const w of t.split(/[^a-z0-9_]+/)) if (w.includes("_") && keys.includes(w)) out.push("key: " + w + " in " + t.slice(0, 80));
          }
        } else if (c.nodeType === 1) {
          for (const a of ["title", "aria-label", "placeholder"]) {
            const t = c.getAttribute?.(a);
            if (t && new RegExp(bad).test(t)) out.push(a + ": " + t.slice(0, 120));
          }
          walk(c);
          if (c.shadowRoot) walk(c.shadowRoot);
        }
      }
    };
    walk(root);
    const wide = document.documentElement.scrollWidth - document.documentElement.clientWidth;
    return { out, wide };
  }, BAD.source);
  if (v.width < 500 && found.wide > 0) errors.push(`wider than the phone by ${found.wide}px`);
  await ctx.close();
  return [...errors, ...found.out];
}

(async () => {
  const srv = await start();
  const browser = await chromium.launch();
  // The keys of the texts: one shown as is was never translated.
  const kp = await browser.newPage();
  await kp.goto(srv.url + "/tests/card/page.html");
  await kp.waitForFunction(() => window.TEXT || window.translate);
  const keys = await kp.evaluate(() => Object.keys((window.TEXT || {}).en || {}));
  await kp.close();
  const scenes = [...SCENES, ...ACTIONS, ...PANEL].filter((s) => !only || s[0].includes(only));
  const jobs = [];
  for (const s of scenes) {
    for (const lang of LANGS) jobs.push([s, { lang, width: s[1].panel ? 1280 : 560, dark: lang === "ro" }]);
    jobs.push([s, { lang: "de", width: 390, dark: true }]);
    jobs.push([s, { lang: "en", width: 390, dark: false, h12: true }]);
    if (s[1].panel && s[0] === "panel") for (const tab of TABS) for (const w of [1280, 390]) for (const lang of LANGS) jobs.push([s, { lang, width: w, dark: w < 500, tab }]);
  }
  console.log(`${scenes.length} scenes, ${jobs.length} states`);
  const problems = [];
  let done = 0;
  let next = 0;
  await Promise.all(Array.from({ length: 6 }, async () => {
    while (next < jobs.length) {
      const [s, v] = jobs[next++];
      const found = await check(browser, srv, s, { ...v }).catch((e) => ["harness: " + e.message.split("\n")[0]]);
      // Keys are passed in by the page (window.TEXT_KEYS) only when set: filter here instead.
      const real = found.filter((f) => !f.startsWith("key:") || keys.includes(f.split(" ")[1]));
      if (real.length) problems.push({ scene: s[0], v, found: [...new Set(real)] });
      if (++done % 100 === 0) console.log(`  ${done}/${jobs.length}`);
    }
  }));
  await browser.close();
  await srv.close();
  for (const pr of problems) console.log(`\n${pr.scene} ${JSON.stringify(pr.v)}\n  ${pr.found.slice(0, 6).join("\n  ")}`);
  console.log(`\n${problems.length} states with problems`);
})();
