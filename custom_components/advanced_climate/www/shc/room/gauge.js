// The dial of a room: temperature, target, arc.

import { esc, num } from "../core/format.js";

export const GaugeMixin = (Base) =>
  class extends Base {
    /**
     * Arc of the room temperature: full at the maximum temperature, empty at the
     * frost protection (the limits of the targets). Tapping it opens the sensor.
     */
    _gauge(a, e, size, withTarget = true) {
      const cur = num(a.current_temperature);
      const tgt = num(a.target_temperature);
      let lo = num(a.min_temperature) ?? 5;
      let hi = num(a.max_temperature) ?? 30;
      if (!(hi > lo)) {
        lo = 5;
        hi = 30;
      }
      // Close to the target (0.3 °C, 0.5 °F) the arc ends exactly at the target dot,
      // so a room on its target does not look a hair short or past it.
      const near = String(a.temperature_unit || "").includes("F") ? 0.5 : 0.3;
      const shown = cur !== null && tgt !== null && Math.abs(cur - tgt) <= near ? tgt : cur;
      const f = shown === null ? 0 : Math.min(1, Math.max(0, (shown - lo) / (hi - lo)));
      const sw = size >= 120 ? 10 : size >= 80 ? 6 : 5;
      const r = size / 2 - sw / 2 - 1;
      const c = 2 * Math.PI * r;
      const arc = c * 0.75;
      const mid = size / 2;
      // The round end of a line reaches half its width past its length: the value arc is
      // drawn that much shorter, so it ends exactly at the temperature (and at the target mark when equal).
      const ring = (cls, len) =>
        `<circle cx="${mid}" cy="${mid}" r="${r.toFixed(2)}" class="${cls}" stroke-width="${sw}" stroke-dasharray="${len.toFixed(
          1
        )} ${c.toFixed(1)}" transform="rotate(135 ${mid} ${mid})"></circle>`;
      // The target as a dot on the arc (a scale mark, not a handle), on the same scale.
      let mark = "";
      if (tgt !== null) {
        const ft = Math.min(1, Math.max(0, (tgt - lo) / (hi - lo)));
        const ang = ((135 + 270 * ft) * Math.PI) / 180;
        const cx = (mid + r * Math.cos(ang)).toFixed(1);
        const cy = (mid + r * Math.sin(ang)).toFixed(1);
        mark = `<circle cx="${cx}" cy="${cy}" r="${(size >= 120 ? 6 : sw * 0.72).toFixed(1)}" class="gmark" stroke-width="${size >= 120 ? 3 : 2}"></circle>`;
      }
      // Warming or cooling over the last 30 minutes (the decision sensor; 0 = steady or not known).
      const trend = cur === null ? 0 : Number(a.temperature_trend) || 0;
      const trendWord = trend > 0 ? this._t("trend_up") : trend < 0 ? this._t("trend_down") : "";
      const arrow = trend
        ? `<span class="gtrend ${trend > 0 ? "up" : "down"}" title="${esc(trendWord)}">${this._icon(
            trend > 0 ? "arrow-up-thin" : "arrow-down-thin"
          )}</span>`
        : "";
      const label = `${this._t("room_temp")} ${this._temp(cur)}${trendWord ? `, ${trendWord}` : ""}, ${this._t(
        "target_tag"
      )} ${this._temp(tgt)}`;
      const link = e && e.room_temperature ? this._more(e.room_temperature) : "";
      return `<span class="gauge ${link ? "link" : ""}" style="width:${size}px;height:${size}px;--gs:${size}px" ${link}
          ${link ? "" : 'role="img"'} aria-label="${esc(label)}">
          <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" aria-hidden="true">
            ${ring("gtrack", arc)}${cur !== null ? ring("gvalue", Math.max(0.1, arc * f - sw / 2)) : ""}${mark}
          </svg>
          ${arrow}<span class="gcenter"><span class="gnum">${this._temp(cur)}</span>${
            withTarget
              ? `<span class="gsub ${e && e.target_temperature ? "link" : ""}" ${
                  e && e.target_temperature ? this._more(e.target_temperature) : ""
                }>${esc(this._t("target_tag"))} ${this._temp(tgt)}</span>`
              : ""
          }</span>
        </span>`;
    }
  };
