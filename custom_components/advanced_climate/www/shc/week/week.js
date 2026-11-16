// The schedule of the next days in the panel: today and the next 6, as the
// integration will run them (the websocket command advanced_climate/week):
// the holidays of the Workday integration, the profiles and the levels of the
// calendar events, the planned vacation. Every room on the day chosen, its
// levels on a shared time line (with now on today). A tap on a room opens it
// with the schedule editor; its copy button, with the rooms to copy its
// schedule to.

import { PRESET_COLORS } from "../core/constants.js";
import { esc } from "../core/format.js";

// The days are asked for again after this long; at once when a schedule, the
// vacation or guest mode changes, and when the day changes.
const WEEK_REFRESH_MS = 5 * 60e3;

export const WeekMixin = (Base) =>
  class extends Base {
    /**
     * What the next days depend on, as the panel sees it: the schedules and
     * their days, the vacation and guest mode, and the date of today. When it
     * changes, the days are asked for again at once.
     */
    _weekKey(houses) {
      const st = (id) => (id ? this._hass.states[id]?.state : "");
      const parts = [this._dayKey(Date.now())];
      for (const h of houses) {
        const e = h.entities || {};
        parts.push(st(e.vacation_start), st(e.vacation_end), st(e.guest_mode), st(e.mode));
        for (const r of h.rooms) {
          const a = r.attributes;
          parts.push(a.room_id, JSON.stringify(a.schedule || {}), JSON.stringify(a.profile_days || {}));
        }
      }
      return parts.join("|");
    }

    /** The next days of every house, fetched when missing, old or out of date (drawn again when they come). */
    _weekData(houses) {
      const w = this._weekLog;
      const key = this._weekKey(houses);
      if (!w || (!w.loading && (Date.now() - w.at > WEEK_REFRESH_MS || w.key !== key))) this._fetchWeek(key);
      return w && (w.data || w.failed) ? w : null;
    }

    async _fetchWeek(key) {
      this._weekLog = { ...(this._weekLog || {}), at: Date.now(), loading: true, key };
      let data = null;
      let failed = false;
      try {
        data = await this._hass.callWS({ type: "advanced_climate/week" });
      } catch (_err) {
        failed = true;
      }
      this._weekLog = { at: Date.now(), loading: false, data, failed, key };
      if (this._tab === "week") this._render();
    }

    /** The moment a clock hour of a day (yyyy-mm-dd) comes in the time zone shown (that of the house here). */
    _localMidnight(date, hour = 0) {
      const [y, m, d] = date.split("-").map(Number);
      const wall = Date.UTC(y, m - 1, d, hour);
      return wall - this._offset(wall - this._offset(wall));
    }

    /** The levels of a room between two moments: [{from, to, preset}] (ms), from its list of changes. */
    _weekSegments(changes, from, to) {
      const list = (changes || []).map((c) => ({ t: Date.parse(c.at), preset: c.preset })).filter((c) => !Number.isNaN(c.t));
      const out = [];
      list.forEach((c, i) => {
        const end = i + 1 < list.length ? list[i + 1].t : to;
        const a = Math.max(c.t, from);
        const b = Math.min(end, to);
        if (b > a) out.push({ from: a, to: b, preset: c.preset });
      });
      return out;
    }

    /** One stretch over the bar of a day: its place in percent of the day. */
    _weekPlace(from, to, start, len) {
      return `left:${(((from - start) / len) * 100).toFixed(3)}%;width:${(((to - from) / len) * 100).toFixed(3)}%`;
    }

    /** One room on the day: its name, the bar of its levels with the calendar and the vacation over it, the profile. */
    _weekRow(r, w, day, start, end, nowPct) {
      const a = r.attributes;
      const name = `<span class="pw-name">${esc(a.room_name)}</span>`;
      if (!a.schedule_editable || w?.editable === false) {
        return `<div class="pw-row">${name}<span class="pw-ext muted">${esc(this._t("not_editable"))}</span></div>`;
      }
      if (w?.failed) {
        return `<div class="pw-row">${name}<span class="pw-ext muted">${esc(this._t("wk_room_failed"))}</span></div>`;
      }
      const len = end - start;
      const hm = (t) => this._fmt(t, { hour: "2-digit", minute: "2-digit" });
      const segs = this._weekSegments(w?.changes, start, end)
        .map((s) => {
          const label = (s.to - s.from) / len >= 0.14 ? esc(this._presetName(a, s.preset)) : "";
          return `<div class="sseg" style="${this._weekPlace(s.from, s.to, start, len)};--c:${PRESET_COLORS[s.preset] || "var(--ac-accent)"}" title="${esc(
            `${this._presetName(a, s.preset)} ${hm(s.from)}–${hm(s.to)}`
          )}"><span>${label}</span></div>`;
        })
        .join("");
      // Over the levels: a calendar event titled with a level of the room, the vacation.
      const over = [];
      for (const lv of w?.levels || []) {
        const a0 = Math.max(Date.parse(lv.start), start);
        const b0 = Math.min(Date.parse(lv.end), end);
        if (b0 > a0) {
          over.push(
            `<span class="pw-ov" style="${this._weekPlace(a0, b0, start, len)};--c:${PRESET_COLORS[lv.preset] || "var(--ac-accent)"}" title="${esc(
              `${this._t("wk_cal_short")}: ${this._presetName(a, lv.preset)} ${hm(a0)}–${hm(b0)}`
            )}"></span>`
          );
        }
      }
      const vac = this._weekVacation;
      if (vac && !vac.guests) {
        const a0 = Math.max(vac.from, start);
        const b0 = Math.min(vac.to, end);
        if (b0 > a0) {
          over.push(
            `<span class="pw-ov pw-vac" style="${this._weekPlace(a0, b0, start, len)};--c:${PRESET_COLORS[vac.preset]}" title="${esc(
              `${this._t("wk_vacation_short")}: ${this._presetName(a, vac.preset)} ${hm(a0)}–${hm(b0)}`
            )}"></span>`
          );
        }
      }
      const prof = (w?.profiles || [])[day] || {};
      const profile = prof.profile ? `${prof.profile}${prof.forced ? ` · ${this._t("wk_cal_short")}` : ""}` : "";
      // No active profile that day: the frost protection, said in words.
      const bar = !w
        ? `<span class="pw-gap muted">${esc(this._t("loading"))}</span>`
        : segs && prof.profile !== null
          ? `<span class="sbar ro pw-bar">${segs}${over.join("")}${
              nowPct === null ? "" : `<span class="pw-now" style="left:${nowPct}%"></span>`
            }</span>`
          : `<span class="pw-gap" style="--c:${PRESET_COLORS.frost}">${esc(this._t("wk_none"))}</span>`;
      const label = this._t("wk_edit").replace("{room}", a.room_name);
      const copy = this._t("wk_copy").replace("{room}", a.room_name);
      return `<div class="pw-row"><button class="pw-main" data-action="week-edit" data-room="${esc(a.room_id)}" aria-label="${esc(
        label
      )}" title="${esc(label)}">${name}${bar}<span class="pw-prof muted">${esc(profile)}</span></button>${
        this._copyTargets(a).length
          ? `<button class="pw-copy" data-action="week-copy" data-room="${esc(a.room_id)}" aria-label="${esc(copy)}" title="${esc(copy)}">${this._icon(
              "content-copy"
            )}</button>`
          : "<span></span>"
      }</div>`;
    }

    /** What is special about a day in a house: a holiday, a profile or a level of the calendar, the vacation. */
    _weekNotes(h, day, start, end) {
      const notes = [];
      const d = h.days?.[day];
      if (d && d.weekday < 5 && d.workday === false) notes.push(this._t("wk_holiday"));
      if (d && d.weekday >= 5 && d.workday === true) notes.push(this._t("wk_workday_weekend"));
      const forced = new Set((h.rooms || []).map((r) => r.profiles?.[day]).filter((p) => p?.forced).map((p) => p.profile));
      for (const p of forced) notes.push(this._t("wk_cal_profile").replace("{profile}", p));
      const hm = (t) => this._fmt(t, { hour: "2-digit", minute: "2-digit" });
      const seen = new Set();
      for (const r of h.rooms || []) {
        for (const lv of r.levels || []) {
          const a0 = Math.max(Date.parse(lv.start), start);
          const b0 = Math.min(Date.parse(lv.end), end);
          const key = `${lv.summary}|${a0}|${b0}`;
          if (b0 > a0 && !seen.has(key)) {
            seen.add(key);
            notes.push(this._t("wk_cal_level").replace("{level}", lv.summary).replace("{from}", hm(a0)).replace("{to}", hm(b0)));
          }
        }
      }
      const v = this._weekVacation;
      if (v && v.to > start && v.from < end) {
        const when = (t) => this._fmt(t, { weekday: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
        notes.push(this._t(v.guests ? "wk_vacation_guests" : "wk_vacation").replace("{from}", when(v.from)).replace("{to}", when(v.end)));
      }
      return notes;
    }

    /** The next days: a day to choose, what is special about it, then every room of every house. */
    _weekHtml(houses) {
      // In the time zone of the house: the schedule is set in it, whatever the profile shows elsewhere.
      this._tzForce = this._hass?.config?.time_zone || null;
      try {
        return this._weekBody(houses);
      } finally {
        this._tzForce = null;
      }
    }

    /** The marks of the hours over the bars, where those hours fall on that day (a day may have 23 or 25). */
    _weekTicks(date, start, end) {
      const marks = [0, 6, 12, 18]
        .map((h) => [h, this._localMidnight(date, h)])
        .concat([[24, end]])
        .map(([h, t]) => `<span style="left:${(((t - start) / (end - start)) * 100).toFixed(3)}%">${String(h).padStart(2, "0")}:00</span>`)
        .join("");
      return `<div class="pw-ticks" aria-hidden="true"><span></span><span class="bar-ticks pw-tickline">${marks}</span><span></span><span></span></div>`;
    }

    _weekBody(houses) {
      const w = this._weekData(houses);
      if (w?.failed) return `<section class="block pw-week"><p class="muted">${esc(this._t("wk_failed"))}</p></section>`;
      const data = Object.fromEntries((w?.data?.houses || []).map((h) => [h.entry_id, h]));
      const first = (w?.data?.houses || [])[0];
      const dates = first?.days?.map((d) => d.date) || [];
      // The day chosen is kept by its date: once it is past, today.
      const day = Math.max(dates.indexOf(this._weekDay), 0);
      const chips = dates
        .map((date, i) => {
          const t = this._localMidnight(date) + 12 * 3600e3;
          return `<button class="seg ${i === day ? "active" : ""}" data-action="week-day" data-option="${esc(date)}" aria-pressed="${i === day}" title="${esc(
            this._fmt(t, { weekday: "long", day: "numeric", month: "long" })
          )}"><span class="pw-wd">${esc(this._fmt(t, { weekday: "short" }))}</span> <span class="pw-dn">${esc(this._fmt(t, { day: "numeric" }))}</span>${
            i === 0 ? '<span class="pw-today" aria-hidden="true"></span>' : ""
          }</button>`;
        })
        .join("");
      const parts = [];
      if (dates.length) {
        parts.push(`<div class="segmented many pw-days" style="--n:${dates.length}" role="group" aria-label="${esc(this._t("wk_day"))}">${chips}</div>`);
      }
      const date = dates[day];
      const start = date ? this._localMidnight(date) : null;
      const end = date ? this._localMidnight(dates[day + 1] || this._nextDate(date)) : null;
      if (date) {
        parts.push(
          `<h3 class="ps-title">${esc(this._fmt(start + 12 * 3600e3, { weekday: "long", day: "numeric", month: "long" }))}${
            day === 0 ? ` · ${esc(this._t("today"))}` : ""
          }</h3>`
        );
      }
      const now = Date.now();
      const nowPct = start !== null && now >= start && now < end ? (((now - start) / (end - start)) * 100).toFixed(2) : null;
      const ticks = date ? this._weekTicks(date, start, end) : "";
      for (const house of houses) {
        if (!house.rooms.length) continue;
        const h = data[house.id] || {};
        const v = h.vacation;
        this._weekVacation = v
          ? {
              from: v.start ? Date.parse(v.start) : 0,
              to: Date.parse(v.resume || v.end),
              end: Date.parse(v.end),
              preset: v.preset,
              guests: !!v.guests,
            }
          : null;
        if (houses.length > 1) parts.push(`<h3 class="ps-house">${esc(house.name || "")}</h3>`);
        const notes = start !== null ? this._weekNotes(h, day, start, end) : [];
        if (notes.length) parts.push(`<ul class="pw-notes">${notes.map((n) => `<li>${esc(n)}</li>`).join("")}</ul>`);
        const byRoom = Object.fromEntries((h.rooms || []).map((r) => [r.room_id, r]));
        const rows = house.rooms.map((r) => this._weekRow(r, w ? byRoom[r.attributes.room_id] : null, day, start, end, nowPct)).join("");
        parts.push(`<div class="pw-rows">${ticks}${rows}</div>`);
      }
      this._weekVacation = null;
      if (!w) parts.push(`<p class="muted">${esc(this._t("loading"))}</p>`);
      parts.push(`<p class="muted pw-note">${esc(this._t("wk_note"))}</p>`);
      return `<section class="block pw-week">${parts.join("")}</section>`;
    }

    /** The day after a date (yyyy-mm-dd). */
    _nextDate(date) {
      const [y, m, d] = date.split("-").map(Number);
      return new Date(Date.UTC(y, m - 1, d + 1)).toISOString().slice(0, 10);
    }
  };
