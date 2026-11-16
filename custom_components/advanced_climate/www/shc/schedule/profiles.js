// Profiles of the schedule: their days, the slots as segments and intervals.

import { esc, toMinutes } from "../core/format.js";

export const WEEKDAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];

/** True when two active profiles cannot be on together (as the integration checks). */
export function profileOverlap(a, b) {
  const la = Array.isArray(a);
  const lb = Array.isArray(b);
  if (la && lb) return a.some((d) => b.includes(d));
  if (la || lb) return false; // chosen weekdays are above the other kinds of days
  if (a === "all" || b === "all") return true;
  return a === b;
}

/** Days without an active profile (as the integration reports them). */
export function uncoveredDays(meta) {
  const active = Object.values(meta || {}).filter((m) => m && m.enabled).map((m) => m.days);
  const specific = new Set(active.filter(Array.isArray).flat());
  const all = active.includes("all");
  const work = all || active.includes("workday");
  const free = all || active.includes("weekend");
  return {
    days: WEEKDAY_KEYS.filter((d, i) => !specific.has(d) && !(i < 5 ? work : free)),
    free_days: !free && WEEKDAY_KEYS.slice(0, 5).some((d) => !specific.has(d)),
    workdays: !work && WEEKDAY_KEYS.slice(5).some((d) => !specific.has(d)),
  };
}

/** Days a new profile is for, from its name (it starts off). */
export function guessDays(name) {
  if (name === "workday" || name === "weekend") return name;
  if (WEEKDAY_KEYS.includes(name)) return [name];
  return "all";
}

/** Turn a profile on or off; the active profiles that overlap it are turned off. */
export function switchProfile(meta, name, on) {
  const next = JSON.parse(JSON.stringify(meta || {}));
  if (!next[name]) next[name] = { days: guessDays(name), enabled: false };
  next[name].enabled = on;
  if (on) {
    for (const [other, m] of Object.entries(next)) {
      if (other !== name && m.enabled && profileOverlap(m.days, next[name].days)) m.enabled = false;
    }
  }
  return next;
}

export const ProfilesMixin = (Base) =>
  class extends Base {
    /** Which days a profile is for, in words. */
    _profileDays(meta) {
      const days = meta ? meta.days : "all";
      if (days === "workday") return this._t("days_workday");
      if (days === "weekend") return this._t("days_weekend");
      if (Array.isArray(days)) return days.map((d) => this._weekdayName(WEEKDAY_KEYS.indexOf(d), "short")).join(", ");
      return this._t("days_all");
    }

    /** On / off switch of a profile (in the schedule and in the editor). */
    _profileSwitch(room, name, on, action) {
      return `<button class="toggle sm ${on ? "on" : ""}" role="switch" aria-checked="${on}" aria-label="${esc(
        this._t(on ? "profile_on" : "profile_off")
      )}" title="${esc(this._t(on ? "profile_on" : "profile_off"))}" data-action="${action}" data-room="${esc(room)}" data-profile="${esc(
        name
      )}"><span class="knob"></span><span>${esc(this._t(on ? "profile_on" : "profile_off"))}</span></button>`;
    }

    /** Days without an active profile, in words ("" when every day has one). */
    _gapText(gap) {
      if (!gap) return "";
      const parts = (gap.days || []).map((d) => this._weekdayName(WEEKDAY_KEYS.indexOf(d)));
      if (gap.free_days) parts.push(this._t("gap_free_days"));
      if (gap.workdays) parts.push(this._t("gap_weekend_workdays"));
      return parts.join(", ");
    }

    /** Weekday name in the language of the user (0 = Monday). */
    _weekdayName(index, style = "long") {
      // 2024-01-01 was a Monday.
      return new Date(2024, 0, 1 + index).toLocaleDateString(this._lang(), { weekday: style });
    }

    /** Segments of a profile over one day (the last slot continues past midnight). */
    _segments(slots) {
      const sorted = [...slots].sort((x, y) => toMinutes(x.time) - toMinutes(y.time));
      const segments = [];
      const last = sorted[sorted.length - 1];
      if (toMinutes(sorted[0].time) > 0) {
        segments.push({ start: 0, end: toMinutes(sorted[0].time), preset: last.preset });
      }
      sorted.forEach((slot, i) => {
        const end = i + 1 < sorted.length ? toMinutes(sorted[i + 1].time) : 1440;
        segments.push({ start: toMinutes(slot.time), end, preset: slot.preset });
      });
      return segments.filter((s) => s.end > s.start);
    }

    /** Intervals as people read them: from a slot to the next one; the last one ends at the first slot of the next day. */
    _intervals(slots) {
      const sorted = [...slots].sort((x, y) => toMinutes(x.time) - toMinutes(y.time));
      return sorted.map((slot, i) => {
        if (i + 1 < sorted.length) {
          return { from: slot.time, to: sorted[i + 1].time, preset: slot.preset, nextDay: false };
        }
        const first = sorted[0];
        if (sorted.length > 1 && toMinutes(first.time) === 0) {
          return { from: slot.time, to: "24:00", preset: slot.preset, nextDay: false };
        }
        return { from: slot.time, to: first.time, preset: slot.preset, nextDay: true };
      });
    }
  };
