// The card and the panel on many screens before a release: phones (small to
// big), tablets, desktops and wide screens, light, dark, a custom theme, high
// contrast and big text, in long languages; the card also in a narrow column.
// Every state is checked for an error of the page, texts that must never show,
// a page wider than the screen and anything sticking out of the card or the
// panel. Some states are photographed into matrix-out/ to look at.
//   node matrix.js [--only name] [--shots]
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");
const { start } = require("./server");
const { SCENES, ACTIONS, PANEL, NOW } = require("./scenes");

const args = process.argv.slice(2);
const only = args.includes("--only") ? args[args.indexOf("--only") + 1] : null;
const SHOTS = args.includes("--shots");
const OUT = path.join(__dirname, "matrix-out");
if (SHOTS) fs.mkdirSync(OUT, { recursive: true });

const THEMES = {
  light: {},
  dark: { "--primary-background-color": "#111111", "--card-background-color": "#1c1c1c", "--primary-text-color": "#e1e1e1",
    "--secondary-text-color": "#9b9b9b", "--divider-color": "#333333", "--ha-card-background": "#1c1c1c" },
  // A theme of the community: another accent, square cards with a border, coloured backgrounds.
  custom: { "--primary-color": "#7c4dff", "--accent-color": "#ff4081", "--primary-background-color": "#1a1b2e", "--card-background-color": "#25263f",
    "--ha-card-background": "#25263f", "--primary-text-color": "#f0f0ff", "--secondary-text-color": "#a8a8d0", "--divider-color": "#3c3d63",
    "--ha-card-border-radius": "0px", "--ha-card-border-width": "2px", "--ha-card-border-color": "#7c4dff", "--state-icon-color": "#ffcc80" },
  contrast: { "--primary-color": "#ffd600", "--primary-background-color": "#000000", "--card-background-color": "#000000", "--ha-card-background": "#000000",
    "--primary-text-color": "#ffffff", "--secondary-text-color": "#ffffff", "--divider-color": "#ffffff", "--warning-color": "#ffab00", "--error-color": "#ff5252" },
};
const DEVICES = {
  phoneS: { width: 320, height: 568, mobile: true },
  phone: { width: 360, height: 800, mobile: true },
  phoneM: { width: 390, height: 844, mobile: true },
  phoneL: { width: 430, height: 932, mobile: true },
  tablet: { width: 768, height: 1024, mobile: true },
  tabletL: { width: 1024, height: 768, mobile: true },
  laptop: { width: 1280, height: 800 },
  desktop: { width: 1920, height: 1080 },
  wide: { width: 2560, height: 1440 },
};
// A real icon takes room: the stub is a 24 px box (the size of ha-icon).
const STUBS = `customElements.define("ha-icon", class extends HTMLElement { connectedCallback() { this.style.cssText += ";display:inline-block;width:var(--mdc-icon-size,24px);height:var(--mdc-icon-size,24px);flex:none"; } });`;
const BAD = /\bundefined\b|\bNaN\b|Invalid Date|\[object/;

async function run(browser, srv, scene, v) {
  const [name, config, hass, act] = scene;
  const dev = DEVICES[v.device];
  const ctx = await browser.newContext({
    viewport: { width: dev.width, height: dev.height }, isMobile: !!dev.mobile, hasTouch: !!dev.mobile,
    deviceScaleFactor: v.shot ? 2 : 1, colorScheme: v.theme === "light" ? "light" : "dark",
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
  await p.evaluate(([vars, big]) => {
    for (const [k, x] of Object.entries(vars)) document.body.style.setProperty(k, x);
    document.body.style.background = vars["--primary-background-color"] || "#fafafa";
    // Big text (Android text size, a zoomed browser): every em grows.
    if (big) document.body.style.fontSize = "125%";
  }, [THEMES[v.theme], !!v.big]);
  const o = { now: NOW, ...hass, dark: v.theme !== "light", lang: v.lang };
  if (config.panel) await p.evaluate(([h, n]) => { mountPanel(h, { narrow: n }); window.card = window.panel; }, [o, dev.width < 870]);
  else await p.evaluate(([c, h, w]) => { mount(c, h); if (w) document.getElementById("host").style.width = w + "px"; }, [config, o, v.column]);
  await p.waitForTimeout(300);
  if (act && !v.tab) {
    try { await act(p); } catch (e) { errors.push("action: " + e.message.split("\n")[0]); }
  }
  await p.waitForTimeout(350);
  const found = await p.evaluate((bad) => {
    const out = [];
    const host = window.panel || window.card;
    const root = host.shadowRoot;
    const box = host.getBoundingClientRect();
    const keys = Object.keys((window.TEXT || {}).en || {});
    const sticking = new Set();
    const shown = (el) => {
      if (!el || el.offsetParent === null) return false;
      const cs = getComputedStyle(el);
      return cs.visibility !== "hidden" && cs.opacity !== "0";
    };
    // Inside a scrolling box (a list, a table, the chart window) sticking out is scrolling.
    const scrolled = (el) => {
      for (let e = el.parentElement; e && e !== document.body; e = e.parentElement || e.getRootNode().host) {
        const cs = getComputedStyle(e);
        if (/(auto|scroll|hidden|clip)/.test(cs.overflowX) && e !== host) return true;
        if (e.tagName === "DIALOG") return true;
      }
      return false;
    };
    const walk = (n) => {
      for (const c of n.childNodes) {
        if (c.nodeType === 3) {
          const t = c.textContent.trim();
          const el = c.parentElement;
          if (t && shown(el) && el.tagName !== "STYLE") {
            if (new RegExp(bad).test(t)) out.push("text: " + t.slice(0, 100));
            for (const w of t.split(/[^a-z0-9_]+/)) if (w.includes("_") && keys.includes(w)) out.push("key: " + w);
          }
        } else if (c.nodeType === 1) {
          for (const a of ["title", "aria-label"]) {
            const t = c.getAttribute(a);
            if (t && new RegExp(bad).test(t)) out.push(a + ": " + t.slice(0, 100));
          }
          if (shown(c) && !scrolled(c)) {
            const r = c.getBoundingClientRect();
            if (r.width && (r.right > box.right + 1.5 || r.left < box.left - 1.5)) {
              sticking.add(`${c.tagName.toLowerCase()}.${[...c.classList].join(".")} ${Math.round(r.left - box.left)}..${Math.round(r.right - box.left)} of ${Math.round(box.width)}`);
            }
          }
          walk(c);
          if (c.shadowRoot) walk(c.shadowRoot);
        }
      }
    };
    walk(root);
    for (const s of [...sticking].slice(0, 4)) out.push("sticks out: " + s);
    return { out, wide: document.documentElement.scrollWidth - document.documentElement.clientWidth };
  }, BAD.source);
  if (found.wide > 0) errors.push(`page wider than the screen by ${found.wide}px`);
  if (v.shot) await p.screenshot({ path: path.join(OUT, `${v.shot}.png`), fullPage: true });
  await ctx.close();
  return [...errors, ...found.out];
}

(async () => {
  const srv = await start();
  const browser = await chromium.launch();
  const scenes = [...SCENES, ...ACTIONS, ...PANEL].filter((s) => !only || s[0].includes(only));
  const jobs = [];
  for (const s of scenes) {
    const panel = !!s[1].panel;
    jobs.push([s, { device: "phoneS", theme: "light", lang: "de", big: true }]);
    jobs.push([s, { device: "phone", theme: "dark", lang: "es" }]);
    jobs.push([s, { device: "phoneL", theme: "contrast", lang: "fr" }]);
    jobs.push([s, { device: panel ? "tablet" : "tabletL", theme: "custom", lang: "nl" }]);
    jobs.push([s, { device: panel ? "wide" : "desktop", theme: "dark", lang: "en" }]);
    if (!panel) {
      // The card in a narrow column of a dashboard (masonry on a phone, a small section).
      jobs.push([s, { device: "laptop", theme: "custom", lang: "de", column: 280 }]);
      jobs.push([s, { device: "laptop", theme: "light", lang: "it", column: 380 }]);
    }
  }
  // Every tab of the panel on every screen, in every theme.
  const panelScene = PANEL.find((s) => s[0] === "panel") || PANEL[0];
  if (!only || panelScene[0].includes(only)) {
    for (const tab of ["rooms", "week", "stats", "history", "devices"]) {
      for (const device of Object.keys(DEVICES)) {
        for (const theme of Object.keys(THEMES)) {
          const shot = SHOTS && ["light", "custom"].includes(theme) && ["phoneS", "tablet", "wide"].includes(device) ? `${tab}-${device}-${theme}` : null;
          jobs.push([panelScene, { device, theme, lang: theme === "custom" ? "es" : "de", tab, big: device === "phoneS", shot }]);
        }
      }
    }
  }
  if (SHOTS) {
    for (const [name, v] of [["card-col280", { device: "laptop", theme: "custom", lang: "de", column: 280 }], ["card-phoneS-big", { device: "phoneS", theme: "light", lang: "de", big: true }], ["card-contrast", { device: "phoneL", theme: "contrast", lang: "fr" }]]) {
      jobs.push([SCENES[0], { ...v, shot: name }]);
    }
  }
  console.log(`${scenes.length} scenes, ${jobs.length} states`);
  const problems = [];
  let next = 0;
  let done = 0;
  await Promise.all(Array.from({ length: 6 }, async () => {
    while (next < jobs.length) {
      const [s, v] = jobs[next++];
      const found = await run(browser, srv, s, v).catch((e) => ["harness: " + e.message.split("\n")[0]]);
      if (found.length) problems.push({ scene: s[0], v, found: [...new Set(found)] });
      if (++done % 100 === 0) console.log(`  ${done}/${jobs.length}`);
    }
  }));
  await browser.close();
  await srv.close();
  for (const pr of problems) console.log(`\n${pr.scene} ${JSON.stringify(pr.v)}\n  ${pr.found.slice(0, 6).join("\n  ")}`);
  console.log(`\n${problems.length} states with problems`);
})();
