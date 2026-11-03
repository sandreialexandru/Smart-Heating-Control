// Tests of the Lovelace card in a real browser (Chromium through Playwright).
//
//   cd tests/card && npm install && npx playwright install chromium
//   node run.js                 every t_*.js file
//   node run.js t_chart.js      one file
//   node run.js t_chart.js sun  the tests of one file whose name contains "sun"
//
// page.html loads the card from custom_components and a fake Home Assistant
// (fixtures.js). A failing test saves a screenshot in $CARD_TEST_SHOTS (or the
// system temp folder).
const { chromium } = require("playwright");
const fs = require("fs");
const os = require("os");
const path = require("path");

const here = __dirname;
const shots = process.env.CARD_TEST_SHOTS || path.join(os.tmpdir(), "card-test-shots");
const files = process.argv[2] ? [process.argv[2]] : fs.readdirSync(here).filter((f) => /^t_.*\.js$/.test(f)).sort();
const only = process.argv[3];
// Mutation testing (Stryker, tests/mutation): stop at the first failure, and
// tell the changed card which mutant is active (it reads it from the page).
const failFast = !!process.env.CARD_TEST_FAIL_FAST;
const activeMutant = process.env.__STRYKER_ACTIVE_MUTANT__;

global.ok = (cond, msg) => {
  if (!cond) throw new Error(msg || "assertion failed");
};
global.eq = (a, b, msg) => {
  if (JSON.stringify(a) !== JSON.stringify(b)) throw new Error(`${msg || "not equal"}: ${JSON.stringify(a)} != ${JSON.stringify(b)}`);
};

(async () => {
  const browser = await chromium.launch();
  let pass = 0;
  let fail = 0;
  for (const file of files) {
    const tests = [];
    global.test = (name, fn, opts = {}) => tests.push({ name, fn, opts });
    require(path.resolve(here, file));
    console.log(`\n# ${file}`);
    for (const t of tests) {
      if (only && !t.name.includes(only)) continue;
      const ctx = await browser.newContext({
        viewport: t.opts.viewport || { width: 1200, height: 900 },
        hasTouch: !!t.opts.touch,
        isMobile: !!t.opts.touch,
        colorScheme: t.opts.dark ? "dark" : "light",
        timezoneId: t.opts.tz || "Europe/Bucharest",
        locale: t.opts.locale || "en-GB",
      });
      if (activeMutant !== undefined) {
        await ctx.addInitScript((id) => {
          window.__stryker__ = Object.assign(window.__stryker__ || {}, { activeMutant: id });
        }, activeMutant);
      }
      const p = await ctx.newPage();
      const errs = [];
      p.on("pageerror", (e) => errs.push("pageerror: " + e.message));
      p.on("console", (m) => {
        if (m.type() === "error" && !/ERR_|net::/.test(m.text())) errs.push("console: " + m.text());
      });
      await p.goto("file://" + path.join(here, "page.html"));
      try {
        await t.fn(p);
        if (errs.length && !t.opts.allowErrors) throw new Error("JS errors: " + errs.join(" | "));
        pass++;
        console.log("PASS", t.name);
      } catch (e) {
        fail++;
        console.log("FAIL", t.name, "->", e.message.split("\n")[0]);
        try {
          fs.mkdirSync(shots, { recursive: true });
          await p.screenshot({ path: path.join(shots, `fail-${t.name.replace(/\W+/g, "_")}.png`) });
        } catch (_) {
          // No screenshot: the failure is still reported.
        }
      }
      await ctx.close();
      if (failFast && fail) break;
    }
    if (failFast && fail) break;
  }
  console.log(`\n${pass} passed, ${fail} failed`);
  await browser.close();
  process.exit(fail ? 1 : 0);
})();
