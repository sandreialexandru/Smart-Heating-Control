// Texts, times, dates, temperatures and durations as the user reads them.

import { dateLanguage, translate } from "./i18n.js";

export const esc = (value) =>
  String(value ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]
  );

export const toMinutes = (hhmm) => {
  const [h, m] = String(hhmm).split(":").map((x) => parseInt(x, 10));
  return (h || 0) * 60 + (m || 0);
};

export const hhmm = (minutes) =>
  `${String(Math.floor(minutes / 60)).padStart(2, "0")}:${String(minutes % 60).padStart(2, "0")}`;

export const num = (value) => {
  const n = parseFloat(value);
  return Number.isFinite(n) ? n : null;
};

export const FormatMixin = (Base) =>
  class extends Base {
    // ------------------------------------------------------------------ data
    _t(key) {
      return translate(this._hass, key);
    }

    /** Language of the user, for dates and times. */
    _lang() {
      return dateLanguage(this._hass);
    }

    /** State or option as Home Assistant shows it (translated). */
    _label(stateObj, value) {
      if (!stateObj) return value ?? "";
      if (this._hass.formatEntityState) {
        try {
          return this._hass.formatEntityState(stateObj, value);
        } catch (e) {
          /* older frontends */
        }
      }
      return value ?? stateObj.state;
    }

    /** Name of a level for the user (custom names included). */
    _presetName(attrs, preset) {
      const name = preset === "frost" ? this._t("frost_level") : (attrs.preset_names && attrs.preset_names[preset]) || preset;
      // Shown as a name: the first letter capital (Home, Eco, Antiîngheț).
      const text = String(name ?? "");
      return text ? text.charAt(0).toLocaleUpperCase(this._lang()) + text.slice(1) : text;
    }

    /**
     * Time zone of the times shown: the server's when the user chose it in the
     * Home Assistant profile (Time zone: server), otherwise the device's.
     */
    _tz() {
      // The time zone of the house, for a part drawn in it (the next days of the panel).
      if (this._tzForce) return this._tzForce;
      const h = this._hass;
      return h?.locale?.time_zone === "server" && h?.config?.time_zone ? h.config.time_zone : undefined;
    }

    /** Clock parts of a moment in the time zone of the card. */
    _parts(t) {
      const tz = this._tz() || "";
      this._fmtCache = this._fmtCache || {};
      const f =
        this._fmtCache[tz] ||
        (this._fmtCache[tz] = new Intl.DateTimeFormat("en-US", {
          timeZone: tz || undefined,
          hourCycle: "h23",
          year: "numeric",
          month: "2-digit",
          day: "2-digit",
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        }));
      const o = {};
      for (const part of f.formatToParts(new Date(t))) o[part.type] = part.value;
      return { y: +o.year, mo: +o.month, d: +o.day, h: +o.hour % 24, mi: +o.minute, s: +o.second };
    }

    /** Offset of the card time zone from UTC at a moment (ms). */
    _offset(t) {
      const p = this._parts(t);
      return Date.UTC(p.y, p.mo - 1, p.d, p.h, p.mi, p.s) - Math.floor(t / 1000) * 1000;
    }

    /** A moment as text in the language and time zone of the card. */
    _fmt(t, opts) {
      const o = { ...opts, timeZone: this._tz() };
      if (o.hour) o.hour12 = this._hour12();
      return new Date(t).toLocaleString(this._lang(), o);
    }

    /** ISO datetime -> value for <input type="datetime-local"> (card time zone). */
    _toInput(iso) {
      if (!iso || iso === "unknown" || iso === "unavailable") return "";
      const t = Date.parse(iso);
      if (Number.isNaN(t)) return "";
      const p = this._parts(t);
      const pad = (n) => String(n).padStart(2, "0");
      return `${p.y}-${pad(p.mo)}-${pad(p.d)}T${pad(p.h)}:${pad(p.mi)}`;
    }

    /** <input type="datetime-local"> value (card time zone) -> ISO with the offset, so the server reads it right. */
    _fromInput(value) {
      if (!value) return null;
      const [day, clock] = value.split("T");
      const [y, mo, d] = day.split("-").map(Number);
      const [h, mi] = (clock || "0:0").split(":").map(Number);
      const wall = Date.UTC(y, mo - 1, d, h, mi);
      // Twice: the offset of the result can differ from the guess around a DST change.
      let t = wall - this._offset(wall);
      t = wall - this._offset(t);
      return new Date(t).toISOString();
    }

    /** Time of a moment; with the weekday when it is not today. */
    _fmtTime(iso) {
      if (!iso) return "–";
      const t = Date.parse(iso);
      if (Number.isNaN(t)) return "–";
      const a = this._parts(t);
      const b = this._parts(Date.now());
      const sameDay = a.y === b.y && a.mo === b.mo && a.d === b.d;
      const opts = sameDay
        ? { hour: "2-digit", minute: "2-digit" }
        : { weekday: "short", hour: "2-digit", minute: "2-digit" };
      return this._fmt(t, opts);
    }

    /** Temperature with one decimal, or a dash. */
    _temp(value) {
      const n = num(value);
      return n === null ? "–" : `${n.toFixed(1)}°`;
    }

    /** "35 min", "1 h 30 min", "2 h": above an hour in 5-minute steps (1 h 58 min is 2 h, not "1 h 60 min"). */
    _duration(minutes) {
      const m = Math.round(minutes);
      if (m < 60) return `${m} min`;
      const total = Math.round(m / 5) * 5;
      const h = Math.floor(total / 60);
      const r = total % 60;
      return r ? `${h} h ${r} min` : `${h} h`;
    }

    /** "Pause: only frost …" → ["Pause:", "only frost …"] (the subject in bold); no colon: all is text. */
    _split(text) {
      const i = text.indexOf(": ");
      return i > 0 && i < 40 ? [text.slice(0, i + 1), text.slice(i + 2)] : ["", text];
    }
  };
