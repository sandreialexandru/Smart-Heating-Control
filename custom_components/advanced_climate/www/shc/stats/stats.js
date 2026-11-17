// Statistics of the panel: the heating time of the house and of each room, by
// day, week or month (the long-term statistics of Home Assistant), with the
// temperature outside and in each room and its target (their mean, minimum and
// maximum), and how many times a day the heat source was asked to start (the
// history of the house demand).

import { stale } from "../core/constants.js";
import { esc, num } from "../core/format.js";

// How many days, weeks or months are shown.
export const STATS_RANGE = { day: 14, week: 12, month: 12 };
const PERIOD_MS = { day: 864e5, week: 7 * 864e5, month: 31 * 864e5 };
// The statistics and the history are asked for again after this long.
const STATS_REFRESH_MS = 5 * 60e3;

export const StatsMixin = (Base) =>
  class extends Base {
    /** The period shown: day, week or month. */
    _statsPeriod() {
      return this._statsP || "day";
    }

    /**
     * The sensors of a house: its heating time and the outdoor temperature, then
     * every room with its heating time, temperature and target.
     */
    _statsSeries(house) {
      const out = [];
      if (house.entities?.heating_runtime) {
        out.push({ id: house.entities.heating_runtime, house: true, name: house.name, outdoor: house.entities.outdoor_average });
      }
      for (const r of house.rooms) {
        const a = r.attributes;
        const e = a.entities || {};
        if (e.heating_runtime) {
          out.push({ id: e.heating_runtime, room: a.room_id, name: a.room_name, color: this._roomColor(a), temp: e.room_temperature, target: e.target_temperature });
        }
      }
      return out;
    }

    /** Every statistic asked for: the heating times and the temperatures. */
    _statsIds(houses) {
      return houses.flatMap((h) => this._statsSeries(h).flatMap((s) => [s.id, s.outdoor, s.temp, s.target])).filter(Boolean);
    }

    /** The statistics of a period, fetched when missing or old (drawn again when they come). */
    _statsData(houses, period) {
      this._stats = this._stats || {};
      const ids = this._statsIds(houses);
      const key = `${period}|${ids.join(",")}`;
      const cached = this._stats[key];
      if (stale(cached, STATS_REFRESH_MS)) this._fetchStats(key, period, ids, houses);
      return cached && !cached.loading ? cached : cached?.data ? cached : null;
    }

    async _fetchStats(key, period, ids, houses) {
      const prev = this._stats[key];
      this._stats[key] = { ...(prev || {}), at: Date.now(), loading: true };
      const span = (STATS_RANGE[period] + 1) * PERIOD_MS[period];
      const start = new Date(Date.now() - span).toISOString();
      const end = new Date().toISOString();
      let data = null;
      let requests = null;
      let failed = false;
      try {
        data = ids.length
          ? await this._hass.callWS({ type: "recorder/statistics_during_period", start_time: start, end_time: end, statistic_ids: ids, period, types: ["change", "mean", "min", "max"] })
          : {};
      } catch (_err) {
        failed = true;
      }
      if (data) await this._fetchNow(data, period, houses);
      if (period === "day") requests = await this._fetchRequests(houses, start, end);
      this._stats[key] = { at: Date.now(), loading: false, data, requests, failed };
      if (this._tab === "stats") this._render();
    }

    /**
     * The heating time of the period now, as the card shows it. The long-term
     * statistics have it only up to the last full hour; the statistic of the
     * calendar period (what the card asks for) also counts the minutes since.
     * It replaces the last row when that is the period now, or is added after
     * it when the period now has no row yet (its first hour).
     */
    async _fetchNow(data, period, houses) {
      const ids = houses.flatMap((h) => this._statsSeries(h).map((x) => x.id));
      const ms = (v) => (typeof v === "number" ? v : Date.parse(v));
      const now = Date.now();
      await Promise.all(
        ids.map(async (id) => {
          const rows = data[id];
          const last = rows?.[rows.length - 1];
          if (!last) return;
          let value;
          try {
            const res = await this._hass.callWS({ type: "recorder/statistic_during_period", statistic_id: id, calendar: { period }, types: ["change"] });
            value = num(res?.change);
          } catch (_err) {
            return;
          }
          if (value === null) return;
          const end = ms(last.end);
          if (end > now) last.change = value;
          else if (now - end < PERIOD_MS[period]) rows.push({ start: end, end: now, change: value });
        })
      );
    }

    /** Times a day each house asked its heat source to start (off → on of the house demand). */
    async _fetchRequests(houses, start, end) {
      const ids = houses.map((h) => h.entities?.heat_demand).filter(Boolean);
      if (!ids.length) return null;
      try {
        const res = await this._hass.callWS({
          type: "history/history_during_period",
          start_time: start,
          end_time: end,
          entity_ids: ids,
          minimal_response: true,
          no_attributes: true,
          significant_changes_only: false,
        });
        const out = {};
        for (const id of ids) {
          // The days before the first value kept are not known (not 0).
          const days = {};
          let last = null;
          let first = null;
          for (const p of res?.[id] || []) {
            const state = p.s ?? p.state;
            const t = (p.lu ?? p.lc ?? 0) * 1000 || Date.parse(p.last_updated || p.last_changed);
            if (first === null && Number.isFinite(t)) first = t;
            if (state === "on" && last === "off") days[this._dayKey(t)] = (days[this._dayKey(t)] || 0) + 1;
            if (state === "on" || state === "off") last = state;
          }
          out[id] = { days, from: first === null ? null : this._dayKey(first) };
        }
        return out;
      } catch (_err) {
        return null;
      }
    }

    /** The day of a moment in the time zone of the card (yyyy-mm-dd). */
    _dayKey(t) {
      const p = this._parts(t);
      return `${p.y}-${String(p.mo).padStart(2, "0")}-${String(p.d).padStart(2, "0")}`;
    }

    /** The values of one sensor: [[start ms, hours], …], the last periods of the range. */
    _statsValues(data, id, period) {
      const rows = (data?.[id] || []).map((r) => [typeof r.start === "number" ? r.start : Date.parse(r.start), num(r.change) ?? 0]);
      return rows.slice(-STATS_RANGE[period]);
    }

    /** A temperature of each period: [[start ms, {mean, min, max}], …] (only the periods it has). */
    _statsTemps(data, id) {
      return new Map(
        (data?.[id] || []).map((r) => [
          typeof r.start === "number" ? r.start : Date.parse(r.start),
          { mean: num(r.mean), min: num(r.min), max: num(r.max) },
        ])
      );
    }

    /**
     * A temperature over some periods: the mean of their means, the lowest
     * minimum and the highest maximum (null when none has a value).
     */
    _statsTempOver(temps, starts) {
      const rows = starts.map((t) => temps.get(t)).filter((r) => r && r.mean !== null);
      if (!rows.length) return null;
      const mins = rows.map((r) => r.min).filter((v) => v !== null);
      const maxs = rows.map((r) => r.max).filter((v) => v !== null);
      return {
        mean: rows.reduce((a, r) => a + r.mean, 0) / rows.length,
        min: mins.length ? Math.min(...mins) : null,
        max: maxs.length ? Math.max(...maxs) : null,
      };
    }

    /** "4.2° (−1.0° … 9.3°)": a temperature with its range. */
    _statsTempText(v) {
      if (!v) return "–";
      return v.min !== null && v.max !== null ? `${this._temp(v.mean)} (${this._temp(v.min)} … ${this._temp(v.max)})` : this._temp(v.mean);
    }

    /** The label of a period under its bar. */
    _statsLabel(t, period) {
      if (period === "month") return this._fmt(t, { month: "short" });
      // On a phone only the day of the month (the bars are narrow).
      if (this._narrow) return this._fmt(t, { day: "numeric" });
      if (period === "week") return this._fmt(t, { day: "numeric", month: "short" });
      return this._fmt(t, { weekday: "short", day: "numeric" });
    }

    /** Hours with one decimal, short enough to stand over a bar ("3.3 h"). */
    _shortHours(h) {
      // "2h25", the same time as "2 h 25 min" elsewhere in a narrow column; whole hours from 100 h.
      const minutes = Math.round(h * 60);
      if (minutes < 60) return `${minutes}min`;
      if (minutes >= 6000) return `${Math.round(minutes / 60)}h`;
      const m = minutes % 60;
      return `${Math.floor(minutes / 60)}h${m ? String(m).padStart(2, "0") : ""}`;
    }

    /** Hours as "3 h 20 min". */
    _hours(h) {
      return h > 0 ? this._duration(h * 60) : "0 min";
    }

    /** The period chosen by a tap on its bar (its start), or null: the whole range. */
    _statsPicked(values) {
      const t = this._statsPick;
      return t != null && values.some(([s]) => s === t) ? t : null;
    }

    /** The whole name of a period: "Tuesday, 11 November", "10 Nov – 16 Nov", "November 2026". */
    _statsLong(t, period) {
      if (period === "month") return this._fmt(t, { month: "long", year: "numeric" });
      if (period === "week") return `${this._fmt(t, { day: "numeric", month: "short" })} – ${this._fmt(t + 6 * 864e5, { day: "numeric", month: "short" })}`;
      return this._fmt(t, { weekday: "long", day: "numeric", month: "long" });
    }

    /** Bars standing up, one per period, the value over each; a tap chooses the period. */
    /**
     * The columns of the periods; ``line`` (a value per column, or null) is
     * drawn over them as a line on a scale of its own (the outdoor temperature).
     */
    _statsColumns(values, label, fmt, color, short = fmt, under = null, line = null) {
      // null: not known (no bar, a dash in its title).
      const max = Math.max(0, ...values.map(([, v]) => v ?? 0));
      const picked = this._statsPicked(values);
      const cols = values
        .map(([t, v]) => {
          const h = max > 0 && v > 0 ? Math.max(2, (v / max) * 100) : 0;
          const state = picked === null ? "" : picked === t ? "picked" : "dim";
          return `<button class="ps-col ${state}" data-action="stats-pick" data-t="${t}" aria-pressed="${picked === t}"
            title="${esc(`${label(t)}: ${fmt(v)}`)}"><span class="ps-val">${esc(v > 0 ? short(v) : "")}</span>
            <span class="ps-area"><span class="ps-bar" style="height:${h.toFixed(1)}%;--c:${color}"></span></span><span class="ps-lab">${esc(
              label(t)
            )}</span>${under ? `<span class="ps-out">${esc(under(t))}</span>` : ""}</button>`;
        })
        .join("");
      return `<div class="ps-cols"><div class="ps-inner">${cols}${line ? this._statsLine(line, !!under) : ""}</div></div>`;
    }

    /**
     * A line over the columns: its points at the centres of the columns, from
     * its lowest value (bottom) to its highest (top), with a tenth of the
     * height kept above and below; a gap where a value is missing.
     */
    _statsLine(values, under) {
      const known = values.filter((v) => v !== null && v !== undefined);
      if (known.length < 2) return "";
      const lo = Math.min(...known);
      const hi = Math.max(...known);
      const n = values.length;
      const x = (i) => `${(((i + 0.5) / n) * 100).toFixed(3)}%`;
      const y = (v) => `${(hi === lo ? 50 : 90 - ((v - lo) / (hi - lo)) * 80).toFixed(2)}%`;
      const parts = [];
      values.forEach((v, i) => {
        if (v === null || v === undefined) return;
        const next = values[i + 1];
        if (next !== null && next !== undefined) parts.push(`<line x1="${x(i)}" y1="${y(v)}" x2="${x(i + 1)}" y2="${y(next)}"/>`);
      });
      values.forEach((v, i) => {
        if (v !== null && v !== undefined) parts.push(`<circle cx="${x(i)}" cy="${y(v)}" r="3"/>`);
      });
      // Its scale: the highest and the lowest value, at the left edge.
      if (hi !== lo) {
        parts.push(`<text x="2" y="10%" dy="-6">${esc(this._temp(hi))}</text>`, `<text x="2" y="90%" dy="14">${esc(this._temp(lo))}</text>`);
      }
      return `<svg class="ps-line ${under ? "under" : ""}" aria-hidden="true">${parts.join("")}</svg>`;
    }

    /** The statistics of every house. */
    _statsHtml(houses) {
      const period = this._statsPeriod();
      const seg = ["day", "week", "month"]
        .map(
          (p) => `<button class="seg ${p === period ? "active" : ""}" data-action="stats-period" data-option="${p}" aria-pressed="${
            p === period
          }">${esc(this._t(`st_${p}`))}</button>`
        )
        .join("");
      const head = `<div class="segmented ps-periods" style="--n:3" role="group">${seg}</div>`;
      const stats = this._statsData(houses, period);
      if (!stats) return `<section class="block ps-stats">${head}<p class="muted">${esc(this._t("loading"))}</p></section>`;
      if (stats.failed) return `<section class="block ps-stats">${head}<p class="muted">${esc(this._t("st_failed"))}</p></section>`;
      const parts = houses.map((house) => {
        const series = this._statsSeries(house);
        const own = series.find((s) => s.house);
        const rooms = series.filter((s) => s.room);
        const total = own ? this._statsValues(stats.data, own.id, period) : [];
        const starts = total.map(([t]) => t);
        const outdoor = own?.outdoor ? this._statsTemps(stats.data, own.outdoor) : new Map();
        const outdoorMean = (t) => {
          const v = outdoor.get(t)?.mean;
          return v === null || v === undefined ? "" : this._temp(v);
        };
        const range = this._t(`st_last_${period}`).replace("{n}", STATS_RANGE[period]);
        const sum = (vals) => vals.reduce((a, [, v]) => a + v, 0);
        // A chosen period: the rooms in that period; else over the whole range.
        const picked = this._statsPicked(total);
        const inPick = (vals) => (picked === null ? sum(vals) : (vals.find(([t]) => t === picked)?.[1] ?? 0));
        const span = picked === null ? starts : [picked];
        const roomTotals = rooms
          .map((r) => ({
            ...r,
            hours: inPick(this._statsValues(stats.data, r.id, period)),
            tempOver: r.temp ? this._statsTempOver(this._statsTemps(stats.data, r.temp), span) : null,
            targetOver: r.target ? this._statsTempOver(this._statsTemps(stats.data, r.target), span) : null,
          }))
          .sort((a, b) => b.hours - a.hours);
        const roomMax = Math.max(0, ...roomTotals.map((r) => r.hours));
        const roomSum = sum(roomTotals.map((r) => [0, r.hours]));
        const roomRows = roomTotals
          .map(
            (r) => `<div class="ps-row" title="${esc(this._statsTempText(r.tempOver))}"><span class="ps-name">${esc(
              r.name
            )}</span><span class="ps-track"><span class="ps-fill" style="width:${
              roomMax > 0 ? ((r.hours / roomMax) * 100).toFixed(1) : 0
            }%;--c:${r.color}"></span></span><span class="ps-temp">${
              r.tempOver
                ? esc(
                    this._t("st_room_temp")
                      .replace("{t}", this._temp(r.tempOver.mean))
                      .replace("{target}", r.targetOver ? this._temp(r.targetOver.mean) : "–")
                  )
                : ""
            }</span><span class="ps-h">${esc(this._hours(r.hours))}</span><span class="ps-pct">${
              roomSum > 0 ? Math.round((r.hours / roomSum) * 100) : 0
            }%</span></div>`
          )
          .join("");
        let requests = "";
        let asked = null;
        const demand = house.entities?.heat_demand;
        if (period === "day" && stats.requests && demand && total.length) {
          const { days = {}, from = null } = stats.requests[demand] || {};
          const values = total.map(([t]) => {
            const day = this._dayKey(t);
            return [t, from === null || day < from ? null : (days[day] ?? 0)];
          });
          if (picked !== null) asked = values.find(([t]) => t === picked)?.[1] ?? null;
          requests = `<h3 class="ps-title">${esc(this._t("st_requests"))}</h3>
            ${this._statsColumns(values, (t) => this._statsLabel(t, period), (v) => (v === null ? "–" : String(v)), "var(--ac-hot)")}
            <p class="muted">${esc(this._t("st_requests_note"))}</p>`;
        }
        const name = houses.length > 1 ? `<h2 class="ps-house">${esc(house.name || "")}</h2>` : "";
        // The chosen period: its name, the time of the house, the starts asked; ✕ back to the range.
        const when = picked === null ? range : this._statsLong(picked, period);
        const detail =
          picked === null
            ? ""
            : `<div class="ps-detail"><span><b>${esc(when)}</b> · ${esc(this._hours(total.find(([t]) => t === picked)?.[1] ?? 0))}${
                outdoor.size ? ` · ${esc(this._t("st_outdoor").replace("{t}", this._statsTempText(this._statsTempOver(outdoor, [picked]))))}` : ""
              }${asked !== null ? ` · ${esc(this._t("st_starts").replace("{n}", asked))}` : ""
              }</span><button class="ps-unpick" data-action="stats-pick" data-t="" title="${esc(this._t("close"))}" aria-label="${esc(
                this._t("close")
              )}">${this._icon("close")}</button></div>`;
        const wholeOutdoor = outdoor.size ? this._statsTempOver(outdoor, starts) : null;
        const outdoorTitle = wholeOutdoor ? ` · ${esc(this._t("st_outdoor").replace("{t}", this._statsTempText(wholeOutdoor)))}` : "";
        const legend = outdoor.size ? `<span class="ps-legend"><i></i>${esc(this._t("st_outdoor_line"))}</span>` : "";
        return `${name}<h3 class="ps-title">${esc(this._t("st_house"))} · ${esc(range)} · ${esc(this._hours(sum(total)))}${outdoorTitle}${legend}</h3>
          ${
            total.length
              ? this._statsColumns(
                  total,
                  (t) => this._statsLabel(t, period),
                  (v) => this._hours(v),
                  "var(--ac-accent)",
                  (v) => this._shortHours(v),
                  outdoor.size ? outdoorMean : null,
                  outdoor.size ? starts.map((t) => outdoor.get(t)?.mean ?? null) : null
                )
              : `<p class="muted">${esc(this._t("st_none"))}</p>`
          }
          ${detail}
          <h3 class="ps-title">${esc(this._t("st_rooms"))} · ${esc(when)}</h3>
          ${roomRows ? `<div class="ps-rows">${roomRows}</div>` : `<p class="muted">${esc(this._t("st_none"))}</p>`}
          ${requests}`;
      });
      return `<section class="block ps-stats">${head}${parts.join("")}</section>`;
    }
  };
