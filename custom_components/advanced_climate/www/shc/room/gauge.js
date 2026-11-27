// The dial of a room: temperature, target, arc, the levels on it.

import { PRESET_COLORS } from "../core/constants.js";
import { esc, num } from "../core/format.js";

// The rules under which the room may not heat: the arc goes grey and says why.
const BLOCKED = new Set(["window_open", "pause", "mode_off", "summer", "out_of_season", "outdoor_cutoff"]);

export const GaugeMixin = (Base) =>
  class extends Base {
    /**
     * Arc of the room temperature: full at the maximum temperature, empty at the
     * frost protection (the limits of the targets). The levels of the room are lines
     * across it, the target the thicker one; "now" is an open ring at the end of the
     * arc, in the colour of heat while the room heats. A small dial (a tile, a row) shows only
     * the target and the ring.
     * ``stateObj``: the decision (its rule greys the arc while the room may not heat).
     */
    _gauge(a, e, size, withTarget = true, stateObj = null) {
      const cur = num(a.current_temperature);
      const tgt = num(a.target_temperature);
      let lo = num(a.min_temperature) ?? 5;
      let hi = num(a.max_temperature) ?? 30;
      if (!(hi > lo)) {
        lo = 5;
        hi = 30;
      }
      const rule = stateObj?.state;
      const blocked = BLOCKED.has(rule);
      // Close to the target (0.3 °C, 0.5 °F) the arc ends exactly at the target line,
      // so a room on its target does not look a hair short or past it.
      const near = String(a.temperature_unit || "").includes("F") ? 0.5 : 0.3;
      const shown = cur !== null && tgt !== null && Math.abs(cur - tgt) <= near ? tgt : cur;
      const frac = (t) => Math.min(1, Math.max(0, (t - lo) / (hi - lo)));
      const f = shown === null ? 0 : frac(shown);
      const sw = size >= 120 ? 10 : size >= 80 ? 6 : 5;
      const r = size / 2 - sw / 2 - 1;
      const c = 2 * Math.PI * r;
      const arc = c * 0.75;
      const mid = size / 2;
      const deg = (t) => 135 + 270 * frac(t);
      // The round end of a line reaches half its width past its length: the value arc is
      // drawn that much shorter, so it ends exactly at the temperature (the centre of the ring).
      const ring = (cls, len, extra = "") =>
        `<circle cx="${mid}" cy="${mid}" r="${r.toFixed(2)}" class="${cls}" stroke-width="${sw}" stroke-dasharray="${len.toFixed(
          1
        )} ${c.toFixed(1)}" transform="rotate(135 ${mid} ${mid})"${extra}></circle>`;
      // A line across the arc at a temperature, with a cut of the card colour on each side
      // (seen also over the arc of its own colour).
      const tw = Math.max(2, sw * 0.3);
      const cut = Math.max(1.5, sw * 0.15);
      const across = (t, color, { thick = false, open = false, title = "" } = {}) => {
        const ang = (deg(t) * Math.PI) / 180;
        const cs = Math.cos(ang);
        const sn = Math.sin(ang);
        // From the inner edge of the arc to the outer one.
        const [x1, y1] = [(mid + (r - sw / 2) * cs).toFixed(1), (mid + (r - sw / 2) * sn).toFixed(1)];
        const [x2, y2] = [(mid + (r + sw / 2) * cs).toFixed(1), (mid + (r + sw / 2) * sn).toFixed(1)];
        const w = thick ? tw * 1.45 : tw;
        const xy = `x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"`;
        const inner = open ? `<line ${xy} class="gcut" stroke-width="${(w / 3).toFixed(1)}"></line>` : "";
        return `<g class="gtick${thick ? " target" : ""}${open ? " next" : ""}">${title ? `<title>${esc(title)}</title>` : ""}<line ${xy} class="gcut" stroke-width="${(
          w +
          2 * cut
        ).toFixed(1)}"></line><line ${xy} stroke="${color}" stroke-width="${w.toFixed(1)}"></line>${inner}</g>`;
      };
      const ticks = [];
      if (tgt !== null) {
        // The target in the colour of its level (the thicker line); a manual value, or none
        // of the levels, in the colour of the text. Before a change (the optimal start) the
        // line of the coming level is open: it is not the level of the time yet.
        const level = !a.override && a.preset ? PRESET_COLORS[a.preset] : null;
        const levels = a.levels || {};
        if (withTarget) {
          for (const [p, t] of Object.entries(levels)) {
            const v = num(t);
            if (v === null || !PRESET_COLORS[p] || v < lo || v > hi) continue;
            // The level of the target is drawn as the target (unless the target was moved off it).
            if (level && p === a.preset && Math.abs(v - tgt) < 0.05) continue;
            ticks.push(across(v, PRESET_COLORS[p], { title: `${this._presetName(a, p)} ${this._temp(v)}` }));
          }
        }
        ticks.push(
          across(tgt, level || "var(--primary-text-color)", {
            thick: true,
            open: rule === "optimal_start",
            title: `${this._t("target_tag")} ${this._temp(tgt)}`,
          })
        );
      }
      // Now: an open ring, turned to its place (so it can turn to a new one). While the room
      // heats it is in the colour of heat, with a halo on a big dial (too small on a tile).
      const rr = Math.max(4, sw * 0.75);
      const hot = !!a.heating && !blocked;
      const rw = Math.max(1.5, sw * 0.25).toFixed(1);
      const at = `cx="${(mid + r).toFixed(2)}" cy="${mid}" r="${rr.toFixed(1)}"`;
      const now =
        cur !== null
          ? `<g class="gnow" style="transform-box:view-box;transform-origin:${mid}px ${mid}px;transform:rotate(${(135 + 270 * f).toFixed(
              2
            )}deg)">${hot && withTarget ? `<circle ${at} class="ghalo" stroke-width="${rw}"></circle>` : ""}<circle ${at} class="gring${
              hot ? " hot" : ""
            }" stroke-width="${rw}"></circle></g>`
          : "";
      // Warming or cooling over the last 30 minutes (the decision sensor; 0 = steady or not known).
      const trend = cur === null ? 0 : Number(a.temperature_trend) || 0;
      const trendWord = trend > 0 ? this._t("trend_up") : trend < 0 ? this._t("trend_down") : "";
      const arrow = trend
        ? `<span class="gtrend ${trend > 0 ? "up" : "down"}" title="${esc(trendWord)}">${this._icon(
            trend > 0 ? "arrow-up-thin" : "arrow-down-thin"
          )}</span>`
        : "";
      const why = blocked && stateObj ? this._label(stateObj) : "";
      const label = `${this._t("room_temp")} ${this._temp(cur)}${trendWord ? `, ${trendWord}` : ""}, ${this._t(
        "target_tag"
      )} ${this._temp(tgt)}${why ? `, ${why}` : ""}`;
      const link = e && e.room_temperature ? this._more(e.room_temperature) : "";
      const len = Math.max(0.1, arc * f - sw / 2);
      const sub = why
        ? `<span class="gsub why">${esc(why)}</span>`
        : `<span class="gsub ${e && e.target_temperature ? "link" : ""}" ${
            e && e.target_temperature ? this._more(e.target_temperature) : ""
          }>${esc(this._t("target_tag"))} ${this._temp(tgt)}</span>`;
      return `<span class="gauge ${link ? "link" : ""} ${blocked ? "blocked" : ""}" style="width:${size}px;height:${size}px;--gs:${size}px" ${link}
          ${link ? "" : 'role="img"'} aria-label="${esc(label)}" data-g="${esc(`${a.room_id}-${size}`)}" data-len="${len.toFixed(
            1
          )}" data-deg="${(135 + 270 * f).toFixed(2)}" data-cur="${cur ?? ""}">
          <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" aria-hidden="true">
            ${ring("gtrack", arc)}${cur !== null ? ring("gvalue", len) : ""}${ticks.join("")}${now}
          </svg>
          ${arrow}<span class="gcenter"><span class="gnum">${this._temp(cur)}</span>${withTarget ? sub : ""}</span>
        </span>`;
    }
  };
