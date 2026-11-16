// The schedule of the week in the panel: every room on one day, the bars of the
// profile that day uses on a shared time line (with now on today). A tap on a
// room opens it with the schedule editor.

import { PRESET_COLORS } from "../core/constants.js";
import { esc } from "../core/format.js";
import { WEEKDAY_KEYS, profileForDay } from "../schedule/profiles.js";

export const WeekMixin = (Base) =>
  class extends Base {
    /** The day shown: the one chosen, else today (0 = Monday). */
    _weekDayShown() {
      if (Number.isInteger(this._weekDay)) return this._weekDay;
      return (new Date().getDay() + 6) % 7;
    }

    /** One room on the day: its name, the bar of its profile, the profile's name. */
    _weekRow(r, day, nowPct) {
      const a = r.attributes;
      const name = `<span class="pw-name">${esc(a.room_name)}</span>`;
      if (!a.schedule_editable) {
        return `<div class="pw-row"><span class="pw-name">${esc(a.room_name)}</span><span class="pw-ext muted">${esc(
          this._t("not_editable")
        )}</span></div>`;
      }
      const profile = profileForDay(a.profile_days, day);
      const slots = profile ? (a.schedule || {})[profile] : null;
      const bar = slots && slots.length
        ? `<span class="sbar ro pw-bar">${this._barInner(a, profile, slots, false)}${
            nowPct === null ? "" : `<span class="pw-now" style="left:${nowPct}%"></span>`
          }</span>`
        : `<span class="pw-gap" style="--c:${PRESET_COLORS.frost}">${esc(this._t("wk_none"))}</span>`;
      const label = this._t("wk_edit").replace("{room}", a.room_name);
      return `<button class="pw-row" data-action="week-edit" data-room="${esc(a.room_id)}" aria-label="${esc(label)}" title="${esc(
        label
      )}">${name}${bar}<span class="pw-prof muted">${esc(profile || "")}</span></button>`;
    }

    /** The week: a day to choose, then every room of every house on that day. */
    _weekHtml(houses) {
      const day = this._weekDayShown();
      const today = (new Date().getDay() + 6) % 7;
      const now = new Date();
      const nowPct = day === today ? (((now.getHours() * 60 + now.getMinutes()) / 1440) * 100).toFixed(2) : null;
      const days = WEEKDAY_KEYS.map(
        (d, i) => `<button class="seg ${i === day ? "active" : ""}" data-action="week-day" data-option="${i}" aria-pressed="${
          i === day
        }" title="${esc(this._weekdayName(i))}">${esc(this._weekdayName(i, "short"))}${i === today ? '<span class="pw-today" aria-hidden="true"></span>' : ""}</button>`
      ).join("");
      const parts = [
        `<div class="segmented many pw-days" style="--n:7" role="group" aria-label="${esc(this._t("wk_day"))}">${days}</div>`,
        `<h3 class="ps-title">${esc(this._weekdayName(day))}${day === today ? ` · ${esc(this._t("today"))}` : ""}</h3>`,
      ];
      const ticks = `<div class="pw-ticks" aria-hidden="true"><span></span><span class="bar-ticks"><span>00:00</span><span>06:00</span><span>12:00</span><span>18:00</span><span>24:00</span></span><span></span></div>`;
      for (const house of houses) {
        if (!house.rooms.length) continue;
        if (houses.length > 1) parts.push(`<h3 class="ps-house">${esc(house.name || "")}</h3>`);
        parts.push(`<div class="pw-rows">${ticks}${house.rooms.map((r) => this._weekRow(r, day, nowPct)).join("")}</div>`);
      }
      parts.push(`<p class="muted pw-note">${esc(this._t("wk_note"))}</p>`);
      return `<section class="block pw-week">${parts.join("")}</section>`;
    }
  };
