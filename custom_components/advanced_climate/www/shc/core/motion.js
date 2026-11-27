// The motion after a drawing: only what changed moves, and nothing with reduced motion
// or while the element is not on the screen.

const EASE = "cubic-bezier(.2,.7,.2,1)";
const CHART_MS = 700;
const BARS_MS = 600;

export const MotionMixin = (Base) =>
  class extends Base {
    /** Whether things may move now. */
    _mayMove() {
      if (this.hasAttribute("offscreen")) return false;
      try {
        return !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      } catch (_err) {
        return true;
      }
    }

    /**
     * After a drawing: a dial drawn anew goes from where it was to where it is now;
     * a chart shown for the first time draws itself from the left.
     */
    _afterDraw() {
      const root = this.shadowRoot;
      if (!root || typeof Element === "undefined" || !Element.prototype.animate) return;
      const move = this._mayMove();
      this._gaugeWas ||= {};
      for (const g of root.querySelectorAll(".gauge[data-g]")) {
        if (g.__drawn) continue;
        g.__drawn = true;
        const key = g.dataset.g;
        const was = this._gaugeWas[key];
        const now = { len: Number(g.dataset.len), deg: Number(g.dataset.deg), cur: g.dataset.cur === "" ? null : Number(g.dataset.cur) };
        this._gaugeWas[key] = now;
        if (!move || !was || (was.len === now.len && was.cur === now.cur)) continue;
        this._moveGauge(g, was, now);
      }
      this._chartSeen ||= {};
      const charts = new Set();
      for (const ch of root.querySelectorAll(".hchart[data-chart]")) {
        const room = ch.dataset.chart;
        charts.add(room);
        const svg = ch.querySelector("svg");
        if (!svg || svg.__drawn) continue;
        svg.__drawn = true;
        // Drawn again while it draws itself (its history came): it goes on from where it was.
        const since = this._chartSeen[room] === undefined ? 0 : performance.now() - this._chartSeen[room];
        if (this._chartSeen[room] === undefined) this._chartSeen[room] = performance.now();
        if (move && since < CHART_MS) {
          const an = svg.animate([{ clipPath: "inset(0 100% 0 0)" }, { clipPath: "inset(0 0 0 0)" }], { duration: CHART_MS, easing: EASE });
          an.currentTime = since;
        }
      }
      // A chart closed: drawn again from the left the next time it opens.
      for (const room of Object.keys(this._chartSeen)) if (!charts.has(room)) delete this._chartSeen[room];
    }

    /** A dial from the values it had to the ones it has: the arc, the ring and the number. */
    _moveGauge(g, was, now) {
      const opts = { duration: 650, easing: EASE };
      const value = g.querySelector(".gvalue");
      if (value && Number.isFinite(was.len) && Number.isFinite(now.len)) {
        const gap = value.getAttribute("stroke-dasharray").split(" ")[1];
        value.animate([{ strokeDasharray: `${was.len} ${gap}` }, { strokeDasharray: `${now.len} ${gap}` }], opts);
      }
      const ring = g.querySelector(".gnow");
      if (ring && Number.isFinite(was.deg) && Number.isFinite(now.deg)) {
        ring.animate([{ transform: `rotate(${was.deg}deg)` }, { transform: `rotate(${now.deg}deg)` }], opts);
      }
      const num = g.querySelector(".gnum");
      if (!num || was.cur === null || now.cur === null || was.cur === now.cur) return;
      // The number counts to its value; then the text drawn, exactly.
      const text = num.textContent;
      const start = performance.now();
      const step = (t) => {
        if (!num.isConnected) return;
        const k = Math.min(1, (t - start) / opts.duration);
        const e = 1 - (1 - k) ** 3;
        if (k >= 1) {
          num.textContent = text;
          return;
        }
        num.textContent = this._temp(Math.round((was.cur + (now.cur - was.cur) * e) * 10) / 10);
        requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
    }

    /** A short fade of an element shown anew (the chosen room in the panel). */
    _fadeIn(el) {
      if (el && this._mayMove() && el.animate) el.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 200, easing: "ease-out" });
    }

    /** Bars that grow from their foot (the statistics, once per period shown), ``since`` ms on. */
    _growBars(els, since = 0) {
      const move = this._mayMove() && since < BARS_MS;
      for (const el of els) {
        el.__grown = true;
        if (!move || !el.animate) continue;
        el.style.transformOrigin = "50% 100%";
        const an = el.animate([{ transform: "scaleY(0)" }, { transform: "scaleY(1)" }], { duration: BARS_MS, easing: EASE });
        an.currentTime = since;
      }
    }
  };
