// Compares the card with the card of another version, pixel by pixel.
//
//   node compare.js                  the card in the repository against the base
//   node compare.js --base v2.6.5    against a tag, a branch or a commit
//   node compare.js --self           the base against itself (shows that the
//                                     pictures are the same from run to run)
//   node compare.js --only chart     only the scenes whose name contains "chart"
//   node compare.js --full           every scene in every variant (slow)
//
// The base is by default where the current branch left dev (git merge-base
// HEAD dev), so a refactoring is compared with the code it started from, and
// fixes merged from dev are in the base too.
//
// Both cards are drawn in the same browser, in the same run, with the same
// fixtures and scenes (scenes.js), a frozen clock and no animations, so any
// pixel that differs is a real difference. The services and websocket
// messages each scene sends are compared too. Differences are saved as
// pictures (base, new, and the changed pixels in red) in $CARD_COMPARE_OUT or
// the system temp folder. The exit code is 1 when anything differs.
const { chromium } = require("playwright");
const { execFileSync } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");
const { start, REPO } = require("./server");
const { SCENES, ACTIONS, NOW } = require("./scenes");

const args = process.argv.slice(2);
const opt = (name) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : undefined; };
const OUT = process.env.CARD_COMPARE_OUT || path.join(os.tmpdir(), "card-compare");
const WORKERS = Number(opt("--workers") || 4);

// Light and dark themes, the widths of a phone, a tablet and a desktop, the
// languages and the time formats. A scene is drawn in the basic variants; with
// --full in all of them.
const DARK = { "--primary-background-color": "#111111", "--card-background-color": "#1c1c1c", "--primary-text-color": "#e1e1e1",
  "--secondary-text-color": "#9b9b9b", "--divider-color": "#333333", "--ha-card-background": "#1c1c1c" };
const VARIANTS = [
  { id: "phone", width: 390 },
  { id: "tablet", width: 768 },
  { id: "desktop", width: 1200 },
  { id: "phone-dark", width: 390, dark: true },
  { id: "desktop-dark", width: 1200, dark: true },
  { id: "phone-ro", width: 390, lang: "ro" },
  { id: "desktop-de", width: 1200, lang: "de" },
  { id: "desktop-12h", width: 1200, timeFormat: "12" },
];
const BASIC = ["phone", "desktop", "desktop-dark", "phone-ro", "desktop-de", "desktop-12h"];

function gitBase() {
  const ref = opt("--base");
  if (ref) return ref;
  for (const dev of ["dev", "origin/dev"]) {
    try {
      return execFileSync("git", ["-C", REPO, "merge-base", "HEAD", dev], { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }).trim();
    } catch (_) {
      // Try the next name of dev.
    }
  }
  throw new Error("no base: give --base <ref>");
}

// The integration of the base, in a folder of its own.
function extract(ref) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "card-base-"));
  const tar = execFileSync("git", ["-C", REPO, "archive", ref, "custom_components"], { maxBuffer: 1 << 30 });
  execFileSync("tar", ["-x", "-C", dir], { input: tar });
  return dir;
}

// Elements of Home Assistant the card uses, drawn simply: an icon as a box with
// the start of its name (a changed icon is a changed picture), the card as a
// rounded block.
const STUBS = () => {
  if (!customElements.get("ha-icon")) {
    customElements.define("ha-icon", class extends HTMLElement {
      static get observedAttributes() { return ["icon"]; }
      connectedCallback() { this.draw(); }
      attributeChangedCallback() { this.draw(); }
      set icon(v) { this.setAttribute("icon", v); }
      get icon() { return this.getAttribute("icon"); }
      draw() {
        const root = this.shadowRoot || this.attachShadow({ mode: "open" });
        const name = (this.getAttribute("icon") || "").replace(/^mdi:/, "");
        root.innerHTML = `<span style="display:inline-flex;align-items:center;justify-content:center;width:var(--mdc-icon-size,24px);height:var(--mdc-icon-size,24px);border:1px solid currentColor;border-radius:4px;box-sizing:border-box;font:8px/1 monospace;overflow:hidden">${name.slice(0, 4)}</span>`;
      }
    });
  }
  if (!customElements.get("ha-card")) {
    customElements.define("ha-card", class extends HTMLElement {
      connectedCallback() { this.style.cssText += ";display:block;background:var(--ha-card-background,var(--card-background-color,#fff));border-radius:12px;border:1px solid var(--divider-color,#e0e0e0)"; }
    });
  }
};

async function shoot(browser, srv, scene, variant) {
  const [name, config, hass, act] = scene;
  const ctx = await browser.newContext({
    viewport: { width: variant.width, height: 900 },
    deviceScaleFactor: 1,
    colorScheme: variant.dark ? "dark" : "light",
    timezoneId: "Europe/Bucharest",
    locale: "en-GB",
    reducedMotion: "reduce",
  });
  await ctx.clock.setFixedTime(new Date(NOW));
  await ctx.addInitScript(STUBS);
  const p = await ctx.newPage();
  const errors = [];
  p.on("pageerror", (e) => errors.push(e.message));
  await p.goto(srv.url + "/tests/card/page.html");
  if (variant.dark) {
    await p.evaluate((vars) => { for (const [k, v] of Object.entries(vars)) document.body.style.setProperty(k, v); document.body.style.background = vars["--primary-background-color"]; }, DARK);
  }
  const options = { now: NOW, ...hass, dark: !!variant.dark, lang: variant.lang || hass.lang, timeFormat: variant.timeFormat || hass.timeFormat };
  await p.evaluate(([c, h]) => mount(c, h), [config, options]);
  await p.waitForTimeout(250);
  let failed = null;
  if (act) {
    try {
      await act(p);
    } catch (e) {
      failed = e.message.split("\n")[0];
    }
  }
  // Wait until two pictures in a row are the same (the card finished drawing).
  let png = null;
  for (let i = 0; i < 20; i++) {
    const next = await p.screenshot({ fullPage: true, animations: "disabled", caret: "hide" });
    if (png && png.equals(next)) break;
    png = next;
    await p.waitForTimeout(150);
  }
  const calls = await p.evaluate(() => JSON.stringify(window.calls || null));
  await ctx.close();
  return { name, variant: variant.id, png, calls, failed, errors };
}

// Pixels that differ, counted in the browser (no image library needed).
async function diff(browser, a, b) {
  const p = await browser.newPage();
  const r = await p.evaluate(async ([x, y]) => {
    const load = (src) => new Promise((res) => { const i = new Image(); i.onload = () => res(i); i.src = src; });
    const [ia, ib] = await Promise.all([load(x), load(y)]);
    const w = Math.max(ia.width, ib.width), h = Math.max(ia.height, ib.height);
    const data = (img) => { const c = new OffscreenCanvas(w, h); const g = c.getContext("2d"); g.drawImage(img, 0, 0); return g.getImageData(0, 0, w, h).data; };
    const da = data(ia), db = data(ib);
    const out = new OffscreenCanvas(w, h), g = out.getContext("2d"), od = g.createImageData(w, h);
    let n = 0;
    for (let i = 0; i < da.length; i += 4) {
      const same = da[i] === db[i] && da[i + 1] === db[i + 1] && da[i + 2] === db[i + 2] && da[i + 3] === db[i + 3];
      if (!same) n++;
      od.data[i] = same ? da[i] * 0.3 + 178 : 255; od.data[i + 1] = same ? da[i + 1] * 0.3 + 178 : 0;
      od.data[i + 2] = same ? da[i + 2] * 0.3 + 178 : 0; od.data[i + 3] = 255;
    }
    g.putImageData(od, 0, 0);
    const blob = await out.convertToBlob();
    const buf = new Uint8Array(await blob.arrayBuffer());
    let s = ""; for (const v of buf) s += String.fromCharCode(v);
    return { n, size: [ia.width, ia.height, ib.width, ib.height], png: btoa(s) };
  }, ["data:image/png;base64," + a.toString("base64"), "data:image/png;base64," + b.toString("base64")]);
  await p.close();
  return r;
}

async function pool(items, n, fn) {
  const out = new Array(items.length);
  let next = 0;
  await Promise.all(Array.from({ length: n }, async () => {
    while (next < items.length) { const i = next++; out[i] = await fn(items[i]); }
  }));
  return out;
}

(async () => {
  const ref = gitBase();
  const baseDir = extract(ref);
  const base = await start({ card: baseDir });
  const cur = args.includes("--self") ? base : await start();
  const only = opt("--only");
  const full = args.includes("--full");
  const scenes = [...SCENES, ...ACTIONS].filter((s) => !only || s[0].includes(only));
  const jobs = [];
  for (const s of scenes) for (const v of VARIANTS) if (full || BASIC.includes(v.id)) jobs.push([s, v]);
  console.log(`base ${ref.slice(0, 12)}${args.includes("--self") ? " against itself" : ""}: ${scenes.length} scenes, ${jobs.length} pictures`);

  const browser = await chromium.launch();
  fs.rmSync(OUT, { recursive: true, force: true });
  let problems = 0;
  await pool(jobs, WORKERS, async ([s, v]) => {
    const [a, b] = [await shoot(browser, base, s, v), await shoot(browser, cur, s, v)];
    const label = `${a.name} [${a.variant}]`;
    const issues = [];
    if (a.failed) issues.push(`the scene fails on the base: ${a.failed}`);
    if (b.failed && b.failed !== a.failed) issues.push(`the scene fails: ${b.failed}`);
    if (a.errors.length) issues.push(`JS errors on the base: ${a.errors.join(" | ")}`);
    if (b.errors.length) issues.push(`JS errors: ${b.errors.join(" | ")}`);
    if (a.calls !== b.calls) issues.push(`other calls: base ${a.calls} | new ${b.calls}`);
    if (ACTIONS.includes(s) && !(JSON.parse(a.calls)?.service || []).length) issues.push("the action sends no service on the base");
    if (!a.png.equals(b.png)) {
      const d = await diff(browser, a.png, b.png);
      if (d.n) {
        const stem = path.join(OUT, `${a.name}--${a.variant}`);
        fs.mkdirSync(OUT, { recursive: true });
        fs.writeFileSync(`${stem}--base.png`, a.png);
        fs.writeFileSync(`${stem}--new.png`, b.png);
        fs.writeFileSync(`${stem}--diff.png`, Buffer.from(d.png, "base64"));
        issues.push(`${d.n} pixels differ (${d.size[0]}×${d.size[1]} → ${d.size[2]}×${d.size[3]})`);
      }
    }
    if (issues.length) {
      problems++;
      console.log(`DIFF ${label}: ${issues.join("; ")}`);
    }
  });
  await browser.close();
  await base.close();
  if (cur !== base) await cur.close();
  fs.rmSync(baseDir, { recursive: true, force: true });
  console.log(problems ? `\n${problems} of ${jobs.length} pictures differ (saved in ${OUT})` : `\nall ${jobs.length} pictures are the same`);
  process.exit(problems ? 1 : 0);
})();
