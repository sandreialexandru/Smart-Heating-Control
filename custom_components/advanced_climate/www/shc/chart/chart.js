// The chart window: drawing, view, legend, tooltip.

import { MIN_ZOOM_SPAN, VIEW_PAST, thinPoints } from "./data.js";
import { PRESET_COLORS, TEMP_COLOR } from "../core/constants.js";
import { esc, num } from "../core/format.js";

export const ChartMixin = (Base) =>
  class extends Base {
    /** The window a chart opens on: the last 24 hours and the next 12. */
    _defaultView(d) {
      return { v0: Math.max(d.t0, d.now - VIEW_PAST), v1: d.t1 };
    }

    /**
     * Visible time window of a chart. Until it is zoomed or moved it is the
     * default one and follows the time; ``zoomed`` is true otherwise.
     */
    _viewOf(room, d) {
      // A window that is not a time (a gesture gone wrong) is dropped: the default one again.
      if (this._view?.[room] && !(Number.isFinite(this._view[room].v0) && Number.isFinite(this._view[room].v1))) delete this._view[room];
      const v = this._view?.[room] || this._defaultView(d);
      const span = Math.min(d.t1 - d.t0, Math.max(MIN_ZOOM_SPAN, v.v1 - v.v0));
      const v0 = Math.min(d.t1 - span, Math.max(d.t0, v.v0));
      return { v0, v1: v0 + span, zoomed: !!this._view?.[room] };
    }

    /** Show the time window v0 … v1 (within the 7 days and the next 12 hours); the default one follows the time again. */
    /** Show ``v0`` … ``v1`` of the chart; ``perFrame`` (a finger, a drag, the wheel) draws once per frame. */
    _setView(room, v0, v1, perFrame = false) {
      const d = this._charts?.[room];
      if (!d) return;
      this._view = this._view || {};
      const span = Math.min(d.t1 - d.t0, Math.max(MIN_ZOOM_SPAN, v1 - v0));
      const start = Math.min(d.t1 - span, Math.max(d.t0, v0));
      // Not a time (a gesture from values that were not): the window stays as it was.
      if (!Number.isFinite(start) || !Number.isFinite(span)) return;
      const def = this._defaultView(d);
      if (Math.abs(start - def.v0) < 60000 && Math.abs(start + span - def.v1) < 60000) {
        delete this._view[room];
      } else {
        this._view[room] = { v0: start, v1: start + span };
      }
      // What is shown now, for the next move. While a finger or the mouse moves,
      // the chart is drawn once per frame, so a phone that is slower than the
      // finger does not fall behind.
      d.v0 = start;
      d.v1 = start + span;
      if (!perFrame) {
        this._redrawChart(room);
        return;
      }
      this._redrawRooms = this._redrawRooms || new Set();
      if (!this._redrawRooms.size) {
        requestAnimationFrame(() => {
          const rooms = [...this._redrawRooms];
          this._redrawRooms.clear();
          rooms.forEach((r) => this._redrawChart(r));
        });
      }
      this._redrawRooms.add(room);
    }

    /**
     * The window shown now: the one of the last move (``d.v0`` … ``d.v1``, ahead
     * of the drawing while a finger moves) when it is a time, else the one drawn.
     */
    _win(room, d) {
      return Number.isFinite(d.v0) && Number.isFinite(d.v1) && d.v1 > d.v0 ? { v0: d.v0, v1: d.v1 } : this._viewOf(room, d);
    }

    /** Zoom by ``factor`` (< 1 = closer) keeping ``center`` in place. */
    _zoom(room, factor, center, perFrame = false) {
      const d = this._charts?.[room];
      if (!d) return;
      const { v0, v1 } = this._win(room, d);
      const c = center ?? (Math.min(Math.max(d.now, v0), v1) === d.now ? d.now : (v0 + v1) / 2);
      this._setView(room, c - (c - v0) * factor, c + (v1 - c) * factor, perFrame);
    }

    /** The series hidden from the charts by a tap on the legend (kept in this browser). */
    _hidden() {
      if (!this._hiddenSeries) {
        let saved = [];
        try {
          saved = JSON.parse(localStorage.getItem("shc-hidden-series") || "[]");
        } catch (err) {
          saved = [];
        }
        this._hiddenSeries = new Set(Array.isArray(saved) ? saved : []);
      }
      return this._hiddenSeries;
    }

    /** Hide or show one series of the charts. */
    _toggleSeries(key) {
      const hidden = this._hidden();
      if (hidden.has(key)) hidden.delete(key);
      else hidden.add(key);
      try {
        localStorage.setItem("shc-hidden-series", JSON.stringify([...hidden]));
      } catch (err) {
        // Not kept (private window): hidden until the page is loaded again.
      }
    }

    /** Redraw only the chart of a room (zoom and pan), not the whole card. */
    _redrawChart(room) {
      const card = this.shadowRoot.querySelector(`[data-chartcard="${CSS.escape(room)}"]`);
      const stateObj = this._rooms().find((s) => s.attributes.room_id === room);
      if (!card || !stateObj) return;
      card.innerHTML = this._timelineHtml(stateObj.attributes, true);
    }

    /** Chart of the room: past temperature, target and heating, the plan ahead, zoom bar. */
    _timelineHtml(a, innerOnly = false) {
      const d = this._chartData(a);
      if (!d.segs.length && !d.temp.length) return "";
      const hidden = this._hidden();
      const shows = (k) => !hidden.has(k);
      this._charts = this._charts || {};
      this._charts[a.room_id] = d;
      const view = this._viewOf(a.room_id, d);
      d.v0 = view.v0;
      d.v1 = view.v1;
      // The scales follow what is visible (7 days are kept, a part is shown).
      const inView = (t) => t >= view.v0 - 3600000 && t <= view.v1 + 3600000;
      const vis = [
        ...d.temp.filter(([t]) => inView(t)).map((p) => p[1]),
        ...d.segs.filter((sg) => sg.e >= view.v0 && sg.s <= view.v1).map((sg) => sg.v),
        ...d.pred.filter(([t]) => inView(t)).map((p) => p[1]),
      ].filter((v) => v !== null);
      if (vis.length) {
        const fine = view.v1 - view.v0 < 6 * 3600000;
        let lo = fine ? Math.floor((Math.min(...vis) - 0.3) * 2) / 2 : Math.floor(Math.min(...vis) - 0.5);
        let hi = fine ? Math.ceil((Math.max(...vis) + 0.3) * 2) / 2 : Math.ceil(Math.max(...vis) + 0.5);
        const least = fine ? 1 : 4;
        if (hi - lo < least) {
          const mid = (hi + lo) / 2;
          lo = fine ? Math.floor((mid - least / 2) * 2) / 2 : Math.floor(mid - least / 2);
          hi = lo + least;
        }
        d.lo = lo;
        d.hi = hi;
      }
      const outVis = [...d.outdoor.filter(([t]) => inView(t)), ...d.forecast.filter(([t]) => inView(t))].map((p) => p[1]);
      if (outVis.length) {
        d.olo = Math.floor(Math.min(...outVis));
        d.ohi = Math.ceil(Math.max(...outVis));
        if (d.ohi - d.olo < 4) {
          const mid = (d.olo + d.ohi) / 2;
          d.olo = Math.floor(mid - 2);
          d.ohi = d.olo + 4;
        }
      }
      const W = 1000;
      const H = 100;
      // The energy lane at the top (a row for the price, one for the PV surplus), when shown.
      const ROW = 3;
      const en = d.energy && shows("energy") ? d.energy : null;
      const ELANE = en ? en.rows * ROW + (en.rows - 1) * 0.6 : 0;
      const TOP = en ? ELANE + 6 : 6;
      // The plot ends above a band for the outdoor temperature (when known)
      // and a separate lane for the heating periods.
      const LANE = 7;
      const hasOut = d.olo !== null;
      const OBOT = H - LANE - 5;
      const OTOP = hasOut ? OBOT - 19 : OBOT;
      const BOTTOM = hasOut ? OTOP - 11 : H - LANE - 4;
      const x = (t) => ((t - view.v0) / (view.v1 - view.v0)) * W;
      const y = (v) => BOTTOM - ((v - d.lo) / (d.hi - d.lo)) * (BOTTOM - TOP);
      const pct = (t) => (x(t) / W) * 100;
      const gid = `g-${String(a.room_id).replace(/[^a-z0-9]/gi, "")}`;
      const nowX = x(d.now);

      const range = d.hi - d.lo;
      const gstep = range > 8 ? 2 : range > 3 ? 1 : 0.5;
      const gridValues = [];
      for (let v = Math.ceil(d.lo / gstep) * gstep; v <= d.hi + 1e-9; v += gstep) gridValues.push(+v.toFixed(1));
      const grid = gridValues
        .map((v) => `<line x1="0" x2="${W}" y1="${y(v)}" y2="${y(v)}" class="grid"></line>`)
        .join("");
      const heat = `<rect x="0" y="${H - LANE}" width="${W}" height="${LANE}" class="heatlane"></rect>${(shows("heat") ? d.heat : [])
        .filter(([s, e]) => e >= view.v0 && s <= view.v1)
        .map(
          ([s, e]) =>
            `<rect x="${x(s)}" y="${H - LANE}" width="${Math.max(2, x(e) - x(s))}" height="${LANE}" class="heatbar"></rect>`
        )
        .join("")}${(shows("heat") ? d.predHeat || [] : [])
        .filter(([s, e]) => e >= view.v0 && s <= view.v1)
        .map(
          ([s, e]) =>
            `<rect x="${x(s)}" y="${H - LANE}" width="${Math.max(2, x(e) - x(s))}" height="${LANE}" class="heatbar future"></rect>`
        )
        .join("")}`;
      let energy = "";
      if (en) {
        // The price on the first row, the PV surplus on the next one (the first without a price).
        const rowY = (kind) => (kind === "pv" && en.hasPrice ? ROW + 0.6 : 0);
        const lanes = [en.hasPrice ? "high" : null, en.hasPv ? "pv" : null]
          .filter(Boolean)
          // Until now: a sensor gives no values ahead.
          .map((k) => `<rect x="0" y="${rowY(k)}" width="${Math.min(W, Math.max(0, nowX))}" height="${ROW}" class="elane"></rect>`)
          .join("");
        energy = lanes + en.periods
          .filter(([s, e]) => e >= view.v0 && s <= view.v1)
          .map(
            ([s, e, kind]) =>
              `<rect x="${x(s)}" y="${rowY(kind)}" width="${Math.max(2, x(e) - x(s))}" height="${ROW}" class="ebar ${kind}"></rect>`
          )
          .join("");
      }
      // A fine line at every midnight (in the time zone of the card), between the days.
      const days = [];
      const off = this._offset(view.v0);
      for (let t = Math.ceil((view.v0 + off) / 3600000) * 3600000 - off; t <= view.v1; t += 3600000) {
        const p = this._parts(t);
        if (p.h === 0 && p.mi === 0 && t > view.v0) days.push(`<line x1="${x(t)}" x2="${x(t)}" y1="0" y2="${H}" class="daysep"></line>`);
      }
      const segs = (shows("target") ? d.segs : [])
        .map((sg) => {
          const c = PRESET_COLORS[sg.preset] || TEMP_COLOR;
          const x0 = x(sg.s);
          const x1 = x(sg.e);
          const yy = y(sg.v);
          return `<line x1="${x0}" x2="${x1}" y1="${yy}" y2="${yy}" stroke="${c}" class="tline ${sg.future ? "future" : ""}"></line>`;
        })
        .join("");
      const steps = (shows("target") ? d.segs : [])
        .slice(1)
        .map((sg, i) => {
          const prev = d.segs[i];
          return `<line x1="${x(sg.s)}" x2="${x(sg.s)}" y1="${y(prev.v)}" y2="${y(sg.v)}" class="tstep"></line>`;
        })
        .join("");
      let tempPath = "";
      let tempArea = "";
      // Only what is visible (and a point on each side), so 7 days draw fast.
      const first = d.temp.findIndex(([t]) => t >= view.v0);
      const lastIn = d.temp.findLastIndex(([t]) => t <= view.v1);
      const shown = thinPoints(
        first < 0 ? [] : d.temp.slice(Math.max(0, first - 1), Math.min(d.temp.length, lastIn + 2)),
        (t) => x(Math.max(t, d.t0))
      );
      if (shown.length > 1 && shows("temp")) {
        const pts = shown.map(([t, v]) => `${x(Math.max(t, d.t0)).toFixed(1)} ${y(v).toFixed(1)}`);
        tempPath = `M${pts.join(" L")}`;
        tempArea = `${tempPath} L${x(shown[shown.length - 1][0]).toFixed(1)} ${BOTTOM} L${x(
          Math.max(shown[0][0], d.t0)
        ).toFixed(1)} ${BOTTOM} Z`;
      }
      // The temperature the learned model expects ahead (dashed).
      const predPath =
        shows("pred") && d.pred.length > 1 && d.pred.at(-1)[0] >= view.v0 && d.pred[0][0] <= view.v1
          ? `M${d.pred.map(([t, v]) => `${x(t).toFixed(1)} ${y(v).toFixed(1)}`).join(" L")}`
          : "";
      const last = d.temp.length ? d.temp[d.temp.length - 1] : null;

      // Outdoor band: its own scale, measured line and the forecast (dashed steps).
      let outdoorSvg = "";
      let outLabels = "";
      if (hasOut) {
        const oy = (v) => OBOT - ((v - d.olo) / (d.ohi - d.olo)) * (OBOT - OTOP);
        const path = (pts) =>
          pts.length > 1 ? `M${pts.map(([t, v]) => `${x(Math.max(t, d.t0)).toFixed(1)} ${oy(v).toFixed(1)}`).join(" L")}` : "";
        const measured = path(thinPoints(d.outdoor, (t) => x(Math.max(t, d.t0))));
        const steps = [];
        const start = d.outdoor.length ? d.outdoor[d.outdoor.length - 1] : null;
        if (start) steps.push(start);
        // The measured value stands until the next forecast hour (as for the optimal start / stop).
        for (const [t, v] of d.forecast.filter(([ft]) => ft > d.now)) {
          if (steps.length) steps.push([t, steps[steps.length - 1][1]]);
          steps.push([t, v]);
        }
        if (steps.length) steps.push([Math.min(d.t1, (d.forecast.at(-1)?.[0] ?? d.now) + 3600000), steps[steps.length - 1][1]]);
        const cutoff =
          d.cutoffAt !== null && d.cutoffAt >= d.olo && d.cutoffAt <= d.ohi
            ? `<line x1="0" x2="${W}" y1="${oy(d.cutoffAt)}" y2="${oy(d.cutoffAt)}" class="ocut"></line>`
            : "";
        // The sun expected ahead (0 to the full sun), as a faint area from the bottom of the band.
        let sunArea = "";
        const sunPts = d.sun.filter(([t]) => t >= view.v0 - 900000 && t <= view.v1 + 900000);
        if (shows("sun") && sunPts.some(([, v]) => v > 0)) {
          const sy = (v) => OBOT - Math.min(1, Math.max(0, v)) * (OBOT - OTOP);
          const line = sunPts.map(([t, v]) => `${x(t).toFixed(1)} ${sy(v).toFixed(1)}`).join(" L");
          sunArea = `<path d="M${x(sunPts[0][0]).toFixed(1)} ${OBOT} L${line} L${x(sunPts.at(-1)[0]).toFixed(1)} ${OBOT} Z" class="sunarea"></path>`;
        }
        outdoorSvg = `<rect x="0" y="${OTOP}" width="${W}" height="${OBOT - OTOP}" class="oband"></rect>${sunArea}${
          shows("out")
            ? `${cutoff}
          ${measured ? `<path d="${measured}" class="oline"></path>` : ""}
          ${steps.length > 1 ? `<path d="${path(steps.filter(([t]) => t >= d.now - 1))}" class="oline future"></path>` : ""}`
            : ""
        }`;
        outLabels = (shows("out") ? [d.olo, d.ohi] : [])
          .map((v) => `<span class="olab" style="top:${(oy(v) / H) * 100}%">${v}°</span>`)
          .join("");
        d.oy = oy;
      }

      // The next optimal start / stop: from when it begins to the change.
      let optimal = "";
      let optimalLabel = "";
      // Where that label is ([x, y, width]): no level label over it.
      let optimalPlace = null;
      const est = a.next_estimate;
      if (est && (est.started_at || num(est.minutes))) {
        const s0 = Date.parse(est.started_at || est.starts_at);
        const s1 = Date.parse(est.at);
        if (Number.isFinite(s0) && Number.isFinite(s1) && s1 > view.v0 && s0 < view.v1) {
          const c = PRESET_COLORS[est.preset] || TEMP_COLOR;
          const xa = Math.max(0, x(s0));
          const xb = Math.min(W, x(s1));
          // From the higher of the two levels (the next one for a start, the
          // one of now for a stop) down to the bottom, like the steps of the plan.
          const before = d.segs.find((sg) => sg.s <= s0 - 1 && s0 - 1 < sg.e);
          const levels = [num(est.temperature), before ? before.v : null].filter((v) => v !== null);
          const yTop = levels.length ? Math.min(BOTTOM, Math.max(TOP, y(Math.max(...levels)))) : TOP;
          optimal = `<rect x="${xa}" y="${yTop}" width="${Math.max(1, xb - xa)}" height="${BOTTOM - yTop}" fill="${c}" class="optband"></rect>
            <line x1="${x(s0)}" x2="${x(s0)}" y1="${yTop}" y2="${BOTTOM}" stroke="${c}" class="optline"></line>`;
          const text = this._t(est.kind === "optimal_start" ? "est_mark_start" : "est_mark_stop").replace(
            "{time}",
            this._fmtTime(est.started_at || est.starts_at)
          );
          if (x(s0) >= 0 && x(s0) <= W) {
            // Right above the top of the line; below it when there is no room above.
            const end = x(s0) > W * 0.7;
            const below = yTop < TOP + 4;
            optimalLabel = `<span class="optlab ${end ? "end" : ""} ${below ? "below" : ""}" style="left:${(x(s0) / W) * 100}%;top:${
              (yTop / H) * 100
            }%;--c:${c}">${esc(text)}</span>`;
            optimalPlace = [end ? x(s0) - 170 : x(s0), yTop, 170];
          }
        }
      }

      // Labels of the levels (HTML, so the text is not stretched).
      const visible = (sg) => [Math.max(0, x(sg.s)), Math.min(W, x(sg.e))];
      // A label for each level wide enough, not over another label.
      const placed = optimalPlace ? [optimalPlace] : [];
      const labels = (shows("target") ? d.segs : [])
        .filter((sg, i) => {
          // The rest of the same level after an optimal start / stop has no second label.
          const before = d.segs[i - 1];
          if (before && before.opt && before.v === sg.v && before.preset === sg.preset && before.e >= sg.s - 1000) return false;
          const [xs, xe] = visible(sg);
          const yy = y(sg.v);
          const wide = sg.preset ? 190 : 90;
          // Where the label starts: near the right edge it ends with the segment.
          const lx = xs > W * 0.7 ? xe - wide : xs;
          if (xe - xs < (sg.preset ? 110 : 60) || placed.some(([px, py, pw]) => Math.abs(lx - px) < Math.max(wide, pw) && Math.abs(yy - py) < 14)) {
            return false;
          }
          placed.push([lx, yy, wide]);
          return true;
        })
        .map((sg) => {
          const [xs, xe] = visible(sg);
          // Near the right edge the label ends with the segment, so it stays inside.
          const place =
            xs > W * 0.7 ? `right:${100 - (xe / W) * 100}%` : `left:${(xs / W) * 100}%`;
          const name = sg.preset ? `${esc(this._presetName(a, sg.preset))} ` : "";
          return `<span class="lvl ${sg.future ? "future" : ""} ${xs > W * 0.7 ? "end" : ""}" style="${place};top:${
            (y(sg.v) / H) * 100
          }%;--c:${PRESET_COLORS[sg.preset] || TEMP_COLOR}">${name}${sg.v}°</span>`;
        })
        .join("");
      const yLabels = gridValues
        .map((v) => `<span style="top:${(y(v) / H) * 100}%">${v}°</span>`)
        .join("");

      // Ticks adapt to the zoom: from every 6 hours down to every 5 minutes.
      const span = view.v1 - view.v0;
      const stepMin = [5, 10, 15, 30, 60, 120, 180, 360, 720, 1440].find((m) => span / (m * 60000) <= 7) || 1440;
      const ticks = [];
      // In the time zone of the card: a tick every step of its clock (midnight shows the weekday).
      const inc = 60000 * Math.min(stepMin, 60);
      const off0 = this._offset(view.v0);
      for (let t = Math.ceil((view.v0 + off0) / inc) * inc - off0; t <= view.v1; t += inc) {
        const p = this._parts(t);
        const minutes = p.h * 60 + p.mi;
        if (minutes % stepMin !== 0) continue;
        const label =
          minutes === 0 ? this._fmt(t, { weekday: "short" }) : this._fmt(t, { hour: "2-digit", minute: "2-digit" });
        ticks.push(`<span style="left:${pct(t)}%">${esc(label)}</span>`);
      }
      const fmt = (t) => this._fmt(t, { hour: "2-digit", minute: "2-digit" });
      const zoomBtn = (zoom, label, title, active = false) =>
        `<button class="zbtn ${active ? "active" : ""}" data-action="zoom" data-zoom="${zoom}" data-room="${esc(
          a.room_id
        )}" title="${esc(title)}" aria-label="${esc(title)}">${label}</button>`;
      const spanH = Math.round(span / 3600000);
      const zoombar = `<div class="zoombar">
          <span class="zrange">${
            view.zoomed
              ? span > 20 * 3600000
                ? `${esc(this._fmt(view.v0, { weekday: "short", hour: "2-digit", minute: "2-digit" }))} – ${esc(
                    this._fmt(view.v1, { weekday: "short", hour: "2-digit", minute: "2-digit" })
                  )}`
                : `${esc(fmt(view.v0))} – ${esc(fmt(view.v1))}`
              : esc(this._t("chart_label"))
          }</span>
          <span class="zbtns">
            ${zoomBtn("1h", "1h", this._t("zoom_1h"), view.zoomed && spanH === 1)}
            ${zoomBtn("6h", "6h", this._t("zoom_6h"), view.zoomed && spanH === 6)}
            ${zoomBtn("out", "−", this._t("zoom_out"))}
            ${zoomBtn("in", "+", this._t("zoom_in"))}
            ${view.zoomed ? zoomBtn("reset", "⤢", this._t("zoom_reset")) : ""}
          </span>
        </div>`;

      const nowIn = d.now >= view.v0 && d.now <= view.v1;
      // Each legend item hides or shows its series.
      const legend = (k, label) =>
        `<button class="lg ${shows(k) ? "" : "off"}" data-action="series" data-series="${k}" data-room="${esc(a.room_id)}"
          aria-pressed="${shows(k)}" title="${esc(this._t(shows(k) ? "series_hide" : "series_show"))}"><i class="lg-${k}"></i>${esc(
          this._t(label)
        )}</button>`;
      const inner = `
          ${zoombar}
          <div class="hchart ${view.zoomed ? "zoomed" : ""} ${hasOut ? "with-out" : ""}" data-chart="${esc(a.room_id)}">
            <svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" role="img" aria-label="${esc(this._t("chart_label"))}">
              <defs><linearGradient id="${gid}" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0" stop-color="var(--ac-accent)" stop-opacity="0.14"></stop>
                <stop offset="1" stop-color="var(--ac-accent)" stop-opacity="0"></stop>
              </linearGradient></defs>
              <rect x="${Math.min(W, Math.max(0, nowX))}" y="0" width="${W - Math.min(W, Math.max(0, nowX))}" height="${BOTTOM}" class="futurebg"></rect>
              ${grid}${days.join("")}${energy}${optimal}${heat}${segs}${steps}${outdoorSvg}
              ${tempArea ? `<path d="${tempArea}" fill="url(#${gid})" class="tempfill"></path>` : ""}
              ${tempPath ? `<path d="${tempPath}" class="templine"></path>` : ""}
              ${predPath ? `<path d="${predPath}" class="predline"></path>` : ""}
              <line x1="${nowX}" x2="${nowX}" y1="0" y2="${BOTTOM}" class="now"></line>
            </svg>
            <div class="overlay">
              ${labels}
              <div class="ylabels">${yLabels}${outLabels}</div>
              ${optimalLabel}
              ${nowIn ? `<span class="nowlabel" style="left:${pct(d.now)}%">${this._t("now_tag")}</span>` : ""}
              ${
                shows("temp") && last && last[0] >= view.v0 && last[0] <= view.v1
                  ? `<span class="nowdot" style="left:${pct(last[0])}%;top:${(y(last[1]) / H) * 100}%"></span>`
                  : ""
              }
              <div class="cross" hidden></div>
              <div class="tip" hidden></div>
            </div>
          </div>
          <div class="ticks">${ticks.join("")}</div>
          ${this._navHtml(a.room_id, d, view)}
          <div class="readout">
            ${legend("temp", "legend_temp")}${legend("target", "legend_target")}${legend("heat", "legend_heat")}
            ${d.pred.length ? legend("pred", "legend_pred") : ""}
            ${hasOut ? legend("out", "legend_outdoor") : ""}
            ${hasOut && d.sun.some(([, v]) => v > 0) ? legend("sun", "legend_sun") : ""}
            ${d.energy ? legend("energy", "legend_energy") : ""}
            ${d.loading ? `<span class="muted">${this._t("loading")}</span>` : ""}
          </div>
`;
      if (innerOnly) return inner;
      const touching = this._touched === a.room_id ? " touching" : "";
      return `<div class="chart-card${touching}" data-chartcard="${esc(a.room_id)}">${inner}</div>`;
    }

    /** Bar of the whole period with the visible window (only when zoomed). */
    _navHtml(room, d, view) {
      const total = d.t1 - d.t0;
      const pc = (t) => (((Math.min(d.t1, Math.max(d.t0, t)) - d.t0) / total) * 100).toFixed(2);
      const heat = d.heat
        .map(([s, e]) => `<i class="navheat" style="left:${pc(s)}%;width:${Math.max(0.3, pc(e) - pc(s))}%"></i>`)
        .join("");
      return `<div class="navbar" data-nav="${esc(room)}" role="scrollbar" aria-label="${esc(this._t("nav_help"))}"
          title="${esc(this._t("nav_help"))}">
          ${heat}<i class="navnow" style="left:${pc(d.now)}%"></i>
          <i class="navwin" style="left:${pc(view.v0)}%;width:${(pc(view.v1) - pc(view.v0)).toFixed(2)}%"></i>
        </div>`;
    }

    /** Crosshair and values under the pointer (the legend stays visible). */
    _chartHover(ev) {
      const chart = ev.target.closest?.(".hchart");
      if (!chart) return;
      const room = chart.dataset.chart;
      const d = this._charts?.[room];
      const cross = chart.querySelector(".cross");
      const tip = chart.querySelector(".tip");
      if (!d || !cross || !tip) return;
      if (ev.type === "pointerleave" && ev.target !== chart) return;
      if (ev.type === "pointerleave") {
        cross.hidden = true;
        tip.hidden = true;
        return;
      }
      const stateObj = this._rooms().find((s) => s.attributes.room_id === room);
      const a = stateObj?.attributes || {};
      const rect = chart.getBoundingClientRect();
      const f = Math.min(1, Math.max(0, (ev.clientX - rect.left) / rect.width));
      const w = this._win(room, d);
      const t = w.v0 + f * (w.v1 - w.v0);
      // Not a time: nothing rather than wrong values ("Invalid Date", the outdoor now).
      if (!Number.isFinite(t)) {
        cross.hidden = true;
        tip.hidden = true;
        return;
      }
      let temp = null;
      for (const [pt, v] of d.temp) {
        if (pt <= t) temp = v;
        else break;
      }
      const seg = d.segs.find((sg) => sg.s <= t && t < sg.e);
      const heating = d.heat.some(([s, e]) => s <= t && t <= e);
      const predHeating = t > d.now && (d.predHeat || []).some(([s, e]) => s <= t && t <= e);
      let out = null;
      let outForecast = false;
      if (t <= d.now) {
        for (const [pt, v] of d.outdoor || []) {
          if (pt <= t) out = v;
          else break;
        }
      } else {
        for (const [pt, v] of (d.forecast || []).filter(([ft]) => ft > d.now)) {
          if (pt <= t) {
            out = v;
            outForecast = true;
          } else break;
        }
        // No forecast: the outdoor now only for the hour ahead, not further.
        if (out === null && d.outdoor?.length && t - d.now <= 3600000) out = d.outdoor[d.outdoor.length - 1][1];
      }
      const time = this._fmt(t, { weekday: "short", hour: "2-digit", minute: "2-digit" });
      const rows = [`<b>${esc(time)}</b>`];
      const hidden = this._hidden();
      if (hidden.has("temp")) temp = null;
      if (hidden.has("out")) out = null;
      if (t <= d.now && temp !== null) rows.push(`<span><i class="lg-temp"></i>${temp.toFixed(1)}°</span>`);
      if (t > d.now && d.pred?.length && !hidden.has("pred")) {
        let pred = null;
        for (const [pt, v] of d.pred) {
          if (pt <= t) pred = v;
          else break;
        }
        if (pred !== null) rows.push(`<span><i class="lg-pred"></i>${esc(this._t("tip_pred"))} ${pred.toFixed(1)}°</span>`);
      }
      if (seg && seg.opt && !hidden.has("target")) {
        rows.push(`<span class="optword">${esc(this._t(seg.opt === "optimal_start" ? "tip_early_start" : "tip_early_stop"))}</span>`);
      }
      if (seg && !hidden.has("target")) {
        rows.push(
          `<span><i style="background:${PRESET_COLORS[seg.preset] || TEMP_COLOR}"></i>${
            seg.future ? this._t("planned") : this._t("target_tag")
          } ${seg.v}° · ${esc(this._presetName(a, seg.preset) || "")}</span>`
        );
      }
      if (heating && !hidden.has("heat")) rows.push(`<span class="hotword"><i class="lg-heat"></i>${this._t("heating")}</span>`);
      if (predHeating && !hidden.has("heat")) {
        rows.push(`<span class="hotword"><i class="lg-heat future"></i>${this._t("heating")} · ${esc(this._t("tip_pred"))}</span>`);
      }
      if (out !== null) {
        rows.push(
          `<span><i class="lg-out"></i>${esc(this._t("legend_outdoor"))} ${out.toFixed(1)}°${
            outForecast ? ` · ${esc(this._t("legend_forecast"))}` : ""
          }</span>`
        );
      }
      // The warming the sun is expected to give then (the learned gain × the sun signal).
      if (t > d.now && d.sun?.length && !hidden.has("sun")) {
        let sun = null;
        for (const [pt, v] of d.sun) {
          if (pt <= t) sun = v;
          else break;
        }
        if (sun !== null && sun > 0) {
          rows.push(`<span><i class="lg-sun"></i>${esc(this._t("legend_sun"))} +${(d.sunGain * sun).toFixed(2)}°/h</span>`);
        }
      }
      // The price and the PV surplus then (until now: sensors give no values ahead).
      if (d.energy && !hidden.has("energy") && t <= d.now) {
        const at = (pts) => {
          let v = null;
          for (const [pt, pv] of pts) {
            if (pt <= t) v = pv;
            else break;
          }
          return v;
        };
        const kind = d.energy.periods.filter(([s, e]) => s <= t && t <= e).map((p) => p[2]);
        const value = (v, unit) => `${+v.toFixed(3)}${unit ? ` ${esc(unit)}` : ""}`;
        const price = d.energy.hasPrice ? at(d.energy.price) : null;
        if (price !== null) {
          const state = kind.includes("high") ? "off_tariff_high" : kind.includes("low") ? "off_tariff_low" : null;
          rows.push(
            `<span><i class="ebar-i ${state ? kind.find((k) => k !== "pv") : ""}"></i>${esc(this._t("tip_price"))} ${value(price, d.energy.priceUnit)}${
              state ? ` · ${esc(this._t(state))}` : ""
            }</span>`
          );
        }
        const surplus = d.energy.hasPv ? at(d.energy.pv) : null;
        if (surplus !== null) {
          const name = this._t("off_pv_surplus");
          rows.push(
            `<span><i class="ebar-i ${kind.includes("pv") ? "pv" : ""}"></i>${esc(name.charAt(0).toUpperCase() + name.slice(1))} ${value(
              surplus,
              d.energy.pvUnit
            )}</span>`
          );
        }
      }
      cross.hidden = false;
      cross.style.left = `${f * 100}%`;
      tip.hidden = false;
      tip.innerHTML = rows.join("");
      tip.style.left = `${f * 100}%`;
      tip.style.transform = f > 0.6 ? "translateX(calc(-100% - 10px))" : "translateX(10px)";
    }

    /**
     * The chart of the open room, in a window over the dashboard (one at a time).
     *
     * The window itself stays the same element while it is open (only its
     * content is patched), so an update does not close and open it again: no
     * flicker, the focus and the scrolling are kept.
     */
    _chartPopup() {
      if (!this._config.show_timeline || !this._hass) return null;
      const key = Object.keys(this._open).find((k) => k.startsWith("chart-") && this._open[k]);
      if (!key) return null;
      const room = key.slice(6);
      const stateObj = this._rooms().find((st) => st.attributes.room_id === room);
      if (!stateObj) return null;
      const a = stateObj.attributes;
      const failed = this._hist?.[room]?.failed ? `<p class="hint warn">${esc(this._t("chart_failed"))}</p>` : "";
      const body = failed + (this._timelineHtml(a) || `<p class="empty">${esc(this._t("loading"))}</p>`);
      const head = `<div class="pophead"><span class="name">${esc(a.room_name)}</span>
            <button class="popclose" data-action="closechart" title="${esc(this._t("close"))}" aria-label="${esc(
              this._t("close")
            )}">${this._icon("close")}</button></div>`;
      return {
        k: `chartpop-${room}`,
        html: `<dialog class="chartpop" aria-label="${esc(a.room_name)}"></dialog>`,
        children: [
          { k: "head", html: head },
          { k: "body", html: `<div class="popbody">${body}</div>` },
        ],
      };
    }

    /**
     * Make the chart window opaque whatever the theme: a theme may give the cards
     * a transparent or half transparent background (glass themes), which over the
     * dashboard would make the chart unreadable. The color of the theme is kept,
     * laid over the page background, then over white or black.
     */
    _opaque(dlg) {
      const color = this._opaqueColor(dlg);
      if (color) dlg.style.backgroundColor = color;
    }

    /**
     * The background of ``el`` made opaque: laid over the page background, then
     * over white or black (None when it is opaque already).
     */
    _opaqueColor(el) {
      const rgba = (color) => {
        const ctx = (this._colorCtx ||= document.createElement("canvas").getContext("2d", { willReadFrequently: true }));
        if (!ctx || !color) return null;
        ctx.clearRect(0, 0, 1, 1);
        ctx.fillStyle = "#000";
        ctx.fillStyle = color;
        ctx.fillRect(0, 0, 1, 1);
        const [r, g, b, a] = ctx.getImageData(0, 0, 1, 1).data;
        return [r, g, b, a / 255];
      };
      const over = (top, base) => top.slice(0, 3).map((c, i) => Math.round(c * top[3] + base[i] * (1 - top[3])));
      const style = getComputedStyle(el);
      const own = rgba(style.backgroundColor) || [0, 0, 0, 0];
      if (own[3] >= 0.99) return null;
      const dark = this._hass?.themes?.darkMode ?? matchMedia("(prefers-color-scheme: dark)").matches;
      let base = dark ? [28, 28, 28] : [255, 255, 255];
      const page = rgba(style.getPropertyValue("--primary-background-color").trim());
      if (page && page[3] > 0) base = over(page, base);
      const [r, g, b] = over(own, base);
      return `rgb(${r}, ${g}, ${b})`;
    }

    /** The info box of the charts is opaque too, whatever the theme (``--ac-opaque``). */
    _tipColor() {
      if (!this._card) return;
      const own = getComputedStyle(this._card).backgroundColor;
      if (own === this._tipBase) return;
      this._tipBase = own;
      const color = this._opaqueColor(this._card) || own;
      this.style.setProperty("--ac-opaque", color);
      // Native pickers (the list of a select, the time picker) follow the theme:
      // white text on a white list is unreadable in a dark theme.
      const rgb = String(color).match(/\d+(\.\d+)?/g)?.slice(0, 3).map(Number);
      if (rgb && rgb.length === 3) {
        const light = 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2] > 140;
        this._scheme = light ? "light" : "dark";
        this.style.colorScheme = this._scheme;
      }
    }

    /** Close the chart window. */
    _closeChart() {
      for (const k of Object.keys(this._open)) if (k.startsWith("chart-")) this._open[k] = false;
      this._render();
    }
  };
