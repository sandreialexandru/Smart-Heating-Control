// The chart data: history, plan segments and the prediction (the same model as the integration).

import { ANSWER_WAIT_MS, FLAT_RULES, TEMPORARY_RULES, stale } from "../core/constants.js";
import { num } from "../core/format.js";

export const MIN_ZOOM_SPAN = 20 * 60 * 1000; // closest zoom: 20 minutes

// The chart keeps 7 days of history to scroll back to; it opens on the last 24
// hours and the next 12 (the plan).
export const HISTORY_DAYS = 7;

export const VIEW_PAST = 24 * 3600 * 1000;

export const VIEW_AHEAD = 12 * 3600 * 1000;

/**
 * The points of a line worth drawing: per unit of the chart width (1000
 * units, about one pixel on most screens) the first, the lowest, the highest
 * and the last, in time order. The line looks the same, but 7 days of a sensor
 * that reports every minute become a few thousand points instead of 10 000+,
 * which keeps zooming and moving the chart smooth on a phone.
 */
export const thinPoints = (points, xOf) => {
  if (points.length < 400) return points;
  const out = [];
  let column = null;
  let group = [];
  const flush = () => {
    if (!group.length) return;
    let lo = group[0];
    let hi = group[0];
    for (const p of group) {
      if (p[1] < lo[1]) lo = p;
      if (p[1] > hi[1]) hi = p;
    }
    const keep = new Set([group[0], lo, hi, group[group.length - 1]]);
    out.push(...[...keep].sort((a, b) => a[0] - b[0]));
    group = [];
  };
  for (const p of points) {
    const c = Math.round(xOf(p[0]));
    if (c !== column) {
      flush();
      column = c;
    }
    group.push(p);
  }
  flush();
  return out;
};

export const ChartDataMixin = (Base) =>
  class extends Base {
    // ------------------------------------------------------------------ history chart
    /** Cached history of the room (fetched in the background, refreshed every 5 minutes). */
    _history(a) {
      const key = a.room_id;
      this._hist = this._hist || {};
      const cached = this._hist[key];
      if (stale(cached, ANSWER_WAIT_MS)) this._fetchHistory(a);
      return cached && cached.temp ? cached : null;
    }

    /**
     * Fetch the room temperature, target, heat demand and outdoor temperature of
     * the last 7 days; later only what came since the last fetch (with an hour
     * of overlap), joined to what is kept.
     */
    async _fetchHistory(a) {
      const key = a.room_id;
      const e = a.entities || {};
      const outdoorId = a.house_entities?.outdoor_average;
      const ids = [e.room_temperature, e.target_temperature, e.heat_demand, outdoorId].filter(Boolean);
      const previous = this._hist[key];
      if (!ids.length || !this._hass?.callWS) {
        this._hist[key] = { at: Date.now(), loading: false, temp: [], target: [], heat: [], outdoor: [] };
        return;
      }
      this._hist[key] = { ...(previous || {}), at: Date.now(), loading: true };
      const end = new Date();
      const oldest = end.getTime() - HISTORY_DAYS * 24 * 3600 * 1000;
      const join = previous && previous.temp && !previous.failed && previous.end && previous.ids === ids.join("|");
      const from = join ? Math.max(oldest, previous.end - 3600 * 1000) : oldest;
      const start = new Date(from);
      try {
        const res = await this._hass.callWS({
          type: "history/history_during_period",
          start_time: start.toISOString(),
          end_time: end.toISOString(),
          entity_ids: ids,
          minimal_response: false,
          no_attributes: false,
          significant_changes_only: false,
        });
        const rows = (id) =>
          ((id && res[id]) || [])
            .map((p) => ({ t: (p.lu ?? p.lc) * 1000, s: p.s, a: p.a || {} }))
            .filter((p) => Number.isFinite(p.t));
        const fresh = {
          temp: rows(e.room_temperature)
            .map((p) => [p.t, num(p.s)])
            .filter((p) => p[1] !== null),
          target: rows(e.target_temperature).map((p) => ({ t: p.t, v: num(p.s), preset: p.a.preset })),
          // Heated: the heat source ran (older history without the attribute: the demand).
          heat: rows(e.heat_demand).map((p) => [p.t, p.s === "on" && p.a.heating !== false]),
          // Measured outdoor temperature (the latest value of the house).
          outdoor: rows(outdoorId)
            .map((p) => [p.t, num(p.a.latest)])
            .filter((p) => p[1] !== null),
        };
        // What is kept before the new part, then the new part (its first point is
        // the state at its start); older than 7 days is dropped.
        const time = (p) => (Array.isArray(p) ? p[0] : p.t);
        const merged = {};
        for (const name of Object.keys(fresh)) {
          const kept = join ? (previous[name] || []).filter((p) => time(p) < from && time(p) >= oldest - 3600 * 1000) : [];
          merged[name] = [...kept, ...fresh[name]].sort((p, q) => time(p) - time(q));
        }
        this._hist[key] = { at: Date.now(), end: end.getTime(), ids: ids.join("|"), loading: false, ...merged };
      } catch (err) {
        this._hist[key] = { at: Date.now(), loading: false, temp: [], target: [], heat: [], outdoor: [], failed: true };
      }
      const active = this.shadowRoot.activeElement;
      if (this._editing || this._drag || (active && ["INPUT", "SELECT"].includes(active.tagName))) return;
      this._lastKey = "";
      this._render();
    }

    /** Everything drawn by the chart, in time order. */
    _chartData(a) {
      const HOUR = 3600 * 1000;
      const now = Date.now();
      const t0 = now - HISTORY_DAYS * 24 * HOUR;
      const t1 = now + VIEW_AHEAD;
      const hist = this._history(a);
      // A day without an active profile keeps the frost protection.
      const levels = { ...(a.levels || {}), frost: a.min_temperature };

      // Target: history for the past, the plan for the future.
      const segs = [];
      if (hist && hist.target.length) {
        const points = hist.target.filter((p) => p.v !== null);
        points.forEach((p, i) => {
          const s = Math.max(t0, p.t);
          const e = i + 1 < points.length ? Math.min(points[i + 1].t, now) : now;
          if (e > s) segs.push({ s, e, v: p.v, preset: p.preset, future: false });
        });
      }
      const plan = (a.plan || [])
        .map((p) => ({ t: Date.parse(p.at), preset: p.preset }))
        .filter((p) => Number.isFinite(p.t))
        .sort((x, y) => x.t - y.t);
      let upcoming = plan.filter((p) => p.t > now && p.t < t1);
      let cursor = now;
      let preset = a.preset;
      let value = num(a.target_temperature);
      const rule = this._rooms().find((r) => r.attributes.room_id === a.room_id)?.state;
      // Hold a value until a known moment, then the schedule of that moment.
      const holdThen = (until) => {
        const end = Math.min(until, t1);
        if (value !== null) segs.push({ s: now, e: end, v: value, preset, future: true });
        cursor = end;
        const atEnd = plan.filter((p) => p.t <= until).at(-1);
        preset = atEnd ? atEnd.preset : a.preset;
        value = atEnd ? num(levels[preset]) : null;
        upcoming = plan.filter((p) => p.t > until && p.t < t1);
      };
      const ovUntil = a.override?.until ? Date.parse(a.override.until) : NaN;
      const hold = a.hold_until ? Date.parse(a.hold_until) : NaN;
      const holdKnown = Number.isFinite(hold) && hold > now;
      if (FLAT_RULES.includes(rule) && !(rule === "vacation" && holdKnown)) {
        // Lasts until something changes (mode, presence, pause, sensors, warm
        // outside): the schedule does not apply meanwhile.
        upcoming = [];
      } else if (a.override && Number.isFinite(ovUntil) && ovUntil > now) {
        // A manual change for a set time keeps its value until it ends (also while
        // a window or frost protection interrupts it), limited by the maximum.
        const held = num(a.override.temperature);
        if (held !== null) {
          const max = num(a.max_temperature);
          value = max !== null ? Math.min(held, max) : held;
          preset = a.override.preset ?? null;
        }
        holdThen(ovUntil);
      } else if (holdKnown) {
        // A planned vacation (until its preheating) or a calendar event (until its end).
        holdThen(hold);
      } else if (TEMPORARY_RULES.includes(rule) && plan.length && plan[0].t <= now + 60000) {
        // A window open, frost protection or the valve exercise last only a while:
        // ahead the plan shows the schedule (they are seen in the past and now).
        preset = plan[0].preset;
        value = num(levels[preset]);
      }
      for (const change of upcoming) {
        if (value !== null) segs.push({ s: cursor, e: change.t, v: value, preset, future: true });
        cursor = change.t;
        preset = change.preset;
        value = num(levels[preset]);
      }
      if (value !== null && cursor < t1) segs.push({ s: cursor, e: t1, v: value, preset, future: true });
      // Optimal start / stop: from its beginning the target is already the next
      // level (the shaded period of the chart, limited by the room settings).
      const est = a.next_estimate;
      if (est && (est.started_at || num(est.minutes))) {
        const b0 = Math.max(Date.parse(est.started_at || est.starts_at), now);
        const b1 = Date.parse(est.at);
        const bv = num(est.temperature) ?? num(levels[est.preset]);
        if (Number.isFinite(b0) && Number.isFinite(b1) && b1 > b0 && b0 < t1 && bv !== null) {
          // The planned parts in that period give way to the next level.
          const split = [];
          for (const sg of segs) {
            if (!sg.future || sg.e <= b0 || sg.s >= b1) {
              split.push(sg);
              continue;
            }
            if (sg.s < b0) split.push({ ...sg, e: b0 });
            if (sg.e > b1) split.push({ ...sg, s: b1 });
          }
          split.push({ s: b0, e: Math.min(b1, t1), v: bv, preset: est.preset, future: true, opt: est.kind });
          split.sort((p, q) => p.s - q.s);
          segs.length = 0;
          segs.push(...split);
        }
      }
      // Neighbours with the same level form one segment.
      const merged = [];
      for (const sg of segs) {
        const prev = merged[merged.length - 1];
        if (
          prev &&
          prev.v === sg.v &&
          prev.preset === sg.preset &&
          prev.future === sg.future &&
          prev.opt === sg.opt &&
          prev.e >= sg.s - 1000
        ) {
          prev.e = sg.e;
        } else {
          merged.push({ ...sg });
        }
      }
      segs.length = 0;
      segs.push(...merged);

      const temp = hist ? hist.temp.filter((p) => p[0] >= t0 - HOUR) : [];
      const current = num(a.current_temperature);
      if (current !== null) temp.push([now, current]);

      const heat = [];
      if (hist) {
        let on = null;
        for (const [t, state] of hist.heat) {
          if (state && on === null) on = Math.max(t, t0);
          if (!state && on !== null) {
            heat.push([on, t]);
            on = null;
          }
        }
        if (on !== null) heat.push([on, now]);
      } else if (a.heating ?? a.heat_demand) {
        heat.push([now - 5 * 60 * 1000, now]);
      }

      const values = [...segs.map((x) => x.v), ...temp.map((p) => p[1])].filter((v) => v !== null);
      let lo = values.length ? Math.floor(Math.min(...values) - 0.5) : 15;
      let hi = values.length ? Math.ceil(Math.max(...values) + 0.5) : 23;
      if (hi - lo < 4) {
        const mid = (hi + lo) / 2;
        lo = Math.floor(mid - 2);
        hi = lo + 4;
      }
      // Outdoor: measured for the past, the hourly forecast ahead.
      const outdoorState = this._state(a.house_entities?.outdoor_average);
      const outdoor = hist ? (hist.outdoor || []).filter((p) => p[0] >= t0 - HOUR) : [];
      const latest = num(outdoorState?.attributes?.latest);
      if (latest !== null) outdoor.push([now, latest]);
      const forecast = (outdoorState?.attributes?.forecast || [])
        .map(([at, v]) => [Date.parse(at), num(v)])
        .filter(([t, v]) => Number.isFinite(t) && v !== null && t < t1)
        .sort((p, q) => p[0] - q[0]);
      const outValues = [...outdoor.map((p) => p[1]), ...forecast.map((p) => p[1])];
      let olo = outValues.length ? Math.floor(Math.min(...outValues)) : null;
      let ohi = outValues.length ? Math.ceil(Math.max(...outValues)) : null;
      if (olo !== null && ohi - olo < 4) {
        const mid = (olo + ohi) / 2;
        olo = Math.floor(mid - 2);
        ohi = olo + 4;
      }
      const cutoffAt = outdoorState?.attributes?.cutoff_enabled ? num(outdoorState.attributes.cutoff_temperature) : null;
      const sun = (outdoorState?.attributes?.sun_forecast || [])
        .map(([at, v]) => [Date.parse(at), num(v)])
        .filter(([t, v]) => Number.isFinite(t) && v !== null)
        .sort((p, q) => p[0] - q[0]);
      const { pts: pred, heat: predHeat } = this._prediction(a, segs, forecast, latest, now, t1, sun);
      // The learned sun gain (°C/h for the full sun), in the unit of the chart: 0 until seen.
      const rateState = this._state(a.entities?.heating_rate);
      const gainC = num(rateState?.attributes?.model?.s) ?? 0;
      const sunGain = String(rateState?.attributes?.unit_of_measurement || "").endsWith("°F") ? gainC * 1.8 : gainC;
      return {
        t0, t1, now, segs, temp, heat, predHeat, lo, hi, outdoor, forecast, olo, ohi, cutoffAt, pred,
        sun: sunGain > 0 ? sun.filter(([t]) => t < t1) : [], sunGain, loading: !hist,
      };
    }

    /**
     * The room temperature the learned model expects until the end of the chart,
     * following the planned target: a minute by minute simulation of
     * rise per hour = (h − c × outdoor) × q − k × (room − outdoor) + s × sun, as
     * in the integration, with q following the heating with the inertia. The
     * heating is switched as the device does it (``model.band``, °C below and
     * above the target): Generic Thermostat by its tolerances, relays, on / off
     * control and the TRV boost by the hysteresis (and, with ``inertia_control``,
     * stopped and started early by the learned inertia, as the integration does),
     * thermostats without hvac_action by the hysteresis. Thermostats and TRVs
     * that regulate by themselves (no band) hold the target: their heating is
     * drawn as one period instead of many short ones. The outdoor temperature is
     * the hourly forecast (the measured value until its first hour); the sun
     * signal is the one expected every 15 minutes (``sun_forecast``, 0 after it
     * ends). Empty until learned.
     */
    _prediction(a, segs, forecast, outdoorNow, now, t1, sun = []) {
      const s = this._state(a.entities?.heating_rate);
      const m = s?.attributes?.model;
      const current = num(a.current_temperature);
      if (!m || current === null) return { pts: [], heat: [] };
      // The model is in °C; the chart in the unit of the house.
      const fahrenheit = String(s.attributes.unit_of_measurement || "").endsWith("°F");
      const toC = (v) => (v === null ? null : fahrenheit ? (v - 32) / 1.8 : v);
      const fromC = (v) => (fahrenheit ? v * 1.8 + 32 : v);
      const h = num(m.h) ?? 1;
      const c = num(m.c) ?? 0;
      const k = num(m.k) ?? 0;
      const tau = num(m.tau) ?? 0;
      const sunGain = num(m.s) ?? 0;
      const constant = !!m.constant_loss;
      const mean = num(m.outdoor_mean);
      const band = Array.isArray(m.band) ? [Math.max(0, num(m.band[0]) ?? 0), Math.max(0, num(m.band[1]) ?? 0)] : null;
      const byInertia = !!(band && m.inertia_control);
      const future = segs.filter((sg) => sg.future && sg.e > now);
      const steps = forecast.filter(([t]) => t > now);
      const outdoorAt = (t) => {
        let out = toC(outdoorNow);
        for (const [ft, v] of steps) {
          if (ft <= t) out = toC(v);
          else break;
        }
        return out ?? mean;
      };
      // The sun signal between two points of the 15 minute grid, in proportion.
      const sunAt = (t) => {
        if (!sunGain || !sun.length || t < sun[0][0]) return 0;
        let lo = 0;
        let hi = sun.length - 1;
        while (lo < hi) {
          const mid = (lo + hi + 1) >> 1;
          if (sun[mid][0] <= t) lo = mid;
          else hi = mid - 1;
        }
        const [ta, va] = sun[lo];
        const next = sun[lo + 1];
        if (!next) return t - ta <= 15 * 60000 ? va : 0;
        return va + ((next[1] - va) * (t - ta)) / (next[0] - ta);
      };
      // One minute of the room: [temperature, q] after it, with input u (0 or 1).
      const step = (temp, q, u, t) => {
        let qMean = u;
        let qEnd = u;
        if (tau > 0) {
          const decay = Math.exp(-1 / tau);
          qMean = u + (q - u) * tau * (1 - decay);
          qEnd = u + (q - u) * decay;
        }
        const out = constant ? null : outdoorAt(t);
        const heating = constant || out === null ? h : Math.max(0, h - c * out);
        const loss = constant ? k : out === null ? 0 : k * (temp - out);
        return [temp + (heating * qMean - loss + sunGain * sunAt(t - 30000)) / 60, qEnd];
      };
      // As the integration: the highest temperature ahead without heating, or the
      // lowest one with heating (at most 24 hours, twice the longest inertia,
      // until the room turned by 0.05 °C).
      const extreme = (temp, q, heating, t) => {
        let best = temp;
        for (let j = 1; j <= 1440; j++) {
          [temp, q] = step(temp, q, heating ? 1 : 0, t + j * 60000);
          if (heating ? temp < best : temp > best) best = temp;
          if (heating ? temp > best + 0.05 : temp < best - 0.05) break;
        }
        return best;
      };
      let temp = toC(current);
      let q = Math.min(1, Math.max(0, num(m.q) ?? 0));
      let on = !!a.heating;
      const pts = [[now, current]];
      // The periods the simulation heats: [start, end].
      const heat = [];
      const minutes = Math.floor((t1 - now) / 60000);
      let seg = 0;
      for (let i = 1; i <= minutes; i++) {
        const t = now + i * 60000;
        while (seg < future.length && future[seg].e <= t) seg++;
        const sg = future[seg] && future[seg].s <= t ? future[seg] : null;
        const target = sg ? toC(sg.v) : null;
        if (target === null) on = false;
        else if (!band) on = temp < target;
        else if (temp <= target - band[0]) on = true;
        else if (temp >= target + band[1]) on = false;
        else if (byInertia && on) on = extreme(temp, q, false, t) < target + band[1];
        else if (byInertia) on = extreme(temp, q, true, t) <= target - band[0];
        // A device that regulates by itself: its short simulated pulses are one period.
        const gap = band ? 60000 : 30 * 60000;
        if (on && (!heat.length || heat.at(-1)[1] < t - gap)) heat.push([t - 60000, t]);
        else if (on) heat.at(-1)[1] = t;
        [temp, q] = step(temp, q, on ? 1 : 0, t);
        if (i % 5 === 0 || i === minutes) pts.push([t, +fromC(temp).toFixed(2)]);
      }
      return { pts, heat };
    }
  };
