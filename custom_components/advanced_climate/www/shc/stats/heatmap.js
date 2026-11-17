// The heating by hour in the panel (the Statistics tab): for each room, how many
// minutes of each hour it was heated, over the last 7 days (the history of
// Home Assistant: the heat demand of the room while its heat source ran), as
// the mean of those days or for one of them. In the time zone of the house.

import { stale } from "../core/constants.js";
import { esc } from "../core/format.js";

const HEATMAP_DAYS = 7;
const HEATMAP_REFRESH_MS = 5 * 60e3;

export const HeatmapMixin = (Base) =>
  class extends Base {
    /** The 7 days shown (yyyy-mm-dd, oldest first, today last), in the time zone of the house. */
    _heatmapDates() {
      const today = this._dayKey(Date.now());
      const out = [today];
      while (out.length < HEATMAP_DAYS) {
        const [y, m, d] = out[0].split("-").map(Number);
        out.unshift(new Date(Date.UTC(y, m - 1, d - 1)).toISOString().slice(0, 10));
      }
      return out;
    }

    /** The heat demand sensor of each room: [{id, room}]. */
    _heatmapSeries(houses) {
      return houses.flatMap((h) => h.rooms.map((r) => r.attributes)).filter((a) => a.entities?.heat_demand).map((a) => ({ id: a.entities.heat_demand, room: a.room_id }));
    }

    /** The heated stretches of every room ({room_id: [[from, to], …]}), fetched when missing or old. */
    _heatmapData(houses, dates) {
      const series = this._heatmapSeries(houses);
      const key = `${dates[0]}|${series.map((s) => s.id).join(",")}`;
      const h = this._heatmap;
      if (stale(h, HEATMAP_REFRESH_MS) || (!h.loading && h.key !== key)) this._fetchHeatmap(series, dates[0], key);
      return h && (h.data || h.failed) ? h : null;
    }

    async _fetchHeatmap(series, first, key) {
      this._heatmap = { ...(this._heatmap || {}), at: Date.now(), loading: true, key };
      let data = null;
      let failed = false;
      try {
        const end = Date.now();
        const res = await this._hass.callWS({
          type: "history/history_during_period",
          start_time: new Date(this._localMidnight(first)).toISOString(),
          end_time: new Date(end).toISOString(),
          entity_ids: series.map((s) => s.id),
          minimal_response: false,
          no_attributes: false,
          significant_changes_only: false,
        });
        data = {};
        for (const { id, room } of series) {
          const rows = (res?.[id] || [])
            .map((p) => ({ t: (p.lu ?? p.lc) * 1000, on: p.s === "on" && p.a?.heating !== false }))
            .filter((p) => Number.isFinite(p.t));
          // Heated: the demand was on and the heat source ran (older history without the attribute: the demand).
          const spans = [];
          rows.forEach((p, i) => {
            if (p.on) spans.push([p.t, i + 1 < rows.length ? rows[i + 1].t : end]);
          });
          data[room] = spans;
        }
      } catch (_err) {
        failed = true;
      }
      this._heatmap = { at: Date.now(), loading: false, data, failed, key };
      if (this._tab === "stats") this._render();
    }

    /** Minutes heated in an hour, from the stretches of a room (null for an hour still to come). */
    _heatmapMinutes(spans, from, to, now) {
      if (from >= now) return null;
      const end = Math.min(to, now);
      let ms = 0;
      for (const [a, b] of spans || []) ms += Math.max(0, Math.min(b, end) - Math.max(a, from));
      return ms / 60e3;
    }

    /** The section: the day (the mean of the 7, or one of them), then a row of 24 hours for each room. */
    _heatmapHtml(houses) {
      this._tzForce = this._hass?.config?.time_zone || null;
      try {
        return this._heatmapBody(houses);
      } finally {
        this._tzForce = null;
      }
    }

    _heatmapBody(houses) {
      const rooms = houses.flatMap((h) => h.rooms).filter((r) => r.attributes.entities?.heat_demand);
      if (!rooms.length) return "";
      const dates = this._heatmapDates();
      const pick = this._heatDay && dates.includes(this._heatDay) ? this._heatDay : "mean";
      const chips = ["mean", ...dates]
        .map((d) => {
          const t = d === "mean" ? 0 : this._localMidnight(d) + 12 * 3600e3;
          const label =
            d === "mean"
              ? esc(this._t("hm_mean"))
              : `<span class="pw-wd">${esc(this._fmt(t, { weekday: "short" }))}</span> <span class="pw-dn">${esc(this._fmt(t, { day: "numeric" }))}</span>`;
          return `<button class="seg ${d === pick ? "active" : ""}" data-action="heat-day" data-option="${esc(d)}" aria-pressed="${d === pick}">${label}</button>`;
        })
        .join("");
      const head = `<h3 class="ps-title">${esc(this._t("hm_title"))}</h3>
        <div class="segmented many pw-days hm-days" style="--n:${dates.length + 1}" role="group" aria-label="${esc(this._t("wk_day"))}">${chips}</div>`;
      const h = this._heatmapData(houses, dates);
      if (!h) return `<section class="block hm">${head}<p class="muted">${esc(this._t("loading"))}</p></section>`;
      if (h.failed) return `<section class="block hm">${head}<p class="muted">${esc(this._t("hm_failed"))}</p></section>`;
      const now = Date.now();
      const days = pick === "mean" ? dates : [pick];
      const hours = [...Array(24).keys()];
      const cell = (a, hour) => {
        const values = days
          .map((d) => this._heatmapMinutes(h.data?.[a.room_id], this._localMidnight(d, hour), this._localMidnight(d, hour + 1), now))
          .filter((v) => v !== null);
        if (!values.length) return `<span class="hm-cell none"></span>`;
        const min = values.reduce((s, v) => s + v, 0) / values.length;
        const share = Math.min(100, Math.round((min / 60) * 100));
        const hh = String(hour).padStart(2, "0");
        const next = String(hour + 1).padStart(2, "0");
        const title = this._t(pick === "mean" ? "hm_cell_mean" : "hm_cell")
          .replace("{room}", a.room_name)
          .replace("{from}", `${hh}:00`)
          .replace("{to}", `${next}:00`)
          .replace("{min}", String(Math.round(min)));
        return `<span class="hm-cell" style="--p:${share}%" title="${esc(title)}"></span>`;
      };
      const marks = hours.map((hr) => `<span class="hm-hour">${hr % 3 === 0 ? String(hr).padStart(2, "0") : ""}</span>`).join("");
      const rows = this._roomGroups(rooms, this._gmodeNow || "none")
        .map(
          (g) =>
            (g.name !== null ? `<div class="pw-group">${esc(g.name)}</div>` : "") +
            g.rooms
              .map((r) => {
                const a = r.attributes;
                return `<div class="hm-row"><span class="hm-name">${esc(a.room_name)}</span>${hours.map((hr) => cell(a, hr)).join("")}</div>`;
              })
              .join("")
        )
        .join("");
      return `<section class="block hm">${head}<div class="hm-grid"><div class="hm-row hm-head"><span></span>${marks}</div>${rows}</div>
        <div class="hm-legend"><span>0 min</span><i></i><span>60 min</span></div>
        <p class="muted pw-note">${esc(this._t("hm_note"))}</p></section>`;
    }
  };
