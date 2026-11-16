// Alerts of a room: their texts, icons and how serious they are.

import { ALERT_ERRORS } from "../core/constants.js";
import { esc } from "../core/format.js";

export const AlertsMixin = (Base) =>
  class extends Base {
    /** Text of one alert in the language of the card. */
    _alertText(al) {
      const p = al.params || {};
      const code =
        al.code === "sensor_unavailable"
          ? `sensor_unavailable_${p.fallback || "device"}`
          : al.code === "sensor_silent" && p.left_out
            ? "sensor_silent_left_out"
            : al.code;
      let text = code ? this._t(`al_${code}`) : "";
      if (!text || text === `al_${code}`) text = al.message || "";
      const values = {
        ...p,
        entities: Array.isArray(p.entities) ? p.entities.join(", ") : p.entities,
        rooms: Array.isArray(p.rooms) ? p.rooms.map(([n, g]) => `${n} (−${g}°)`).join(", ") : p.rooms,
      };
      if (al.code === "schedule_gap") values.days = this._gapText(p);
      if (Array.isArray(p.features)) values.features = p.features.map((f) => this._t(`wf_${f}`)).join(", ");
      return text.replace(/\{(\w+)\}/g, (m, k) => (values[k] !== undefined ? String(values[k]) : m));
    }

    /** The alert icon of a room (folded and open); its title lists the alerts, the Details say more. */
    /** A drop while the mold risk alert of the room is active (it shows and ends with the alert). */
    _moldIcon(a, cls) {
      const al = (a.alerts || []).find((x) => x.code === "mold_risk");
      if (!al) return "";
      const text = this._alertText(al);
      return `<span class="${cls} warn" title="${esc(text)}" role="img" aria-label="${esc(text)}">${this._icon(
        "water-alert-outline"
      )}</span>`;
    }

    _alertIcon(a, small = false) {
      const alerts = a.alerts || [];
      if (!alerts.length) return "";
      const text = alerts.map((al) => this._alertText(al)).join("\n");
      // Red when something does not work, amber for warnings (as the outline of the room).
      const warn = this._alertLevel(a) === "al-warn" ? "warn" : "";
      return `<span class="alerticon ${warn} ${small ? "sm" : ""}" title="${esc(text)}" role="img" aria-label="${esc(
        `${this._t("alerts")}: ${text}`
      )}">${this._icon("alert-outline")}</span>`;
    }

    /** How serious the alerts of a room are: "al-error", "al-warn" or "" (the outline of the room). */
    _alertLevel(a) {
      const alerts = a.alerts || [];
      if (alerts.some((al) => ALERT_ERRORS.includes(al.code))) return "al-error";
      return alerts.length ? "al-warn" : "";
    }

    /** Alerts of the room and of the whole house: title, text, and the entity a tap opens. */
    _alertsHtml(a) {
      const alerts = a.alerts || [];
      if (!alerts.length) return "";
      const items = alerts
        .map((al) => {
          const p = al.params || {};
          const entity = p.entity || (Array.isArray(p.entities) ? p.entities[0] : null);
          const kind = ALERT_ERRORS.includes(al.code) ? "error" : "warn";
          const icon = al.code === "mold_risk" ? "water-alert-outline" : kind === "error" ? "alert-circle-outline" : "alert-outline";
          const named = this._t(`at_${al.code}`);
          const title = named === `at_${al.code}` ? this._t("at_other") : named;
          // "Mold risk: the coldest wall …" under the title "Mold risk": the subject once.
          let text = this._alertText(al);
          if (text.toLowerCase().startsWith(`${title.toLowerCase()}: `)) text = text.slice(title.length + 2).replace(/^./, (c) => c.toUpperCase());
          return `<li class="${kind} ${entity ? "link" : ""}" ${this._more(entity)}><span class="micon">${this._icon(icon)}</span>
              <span class="atext"><b>${esc(title)}</b><span>${esc(text)}</span></span>${
                entity ? '<span class="mchev" aria-hidden="true"></span>' : ""
              }</li>`;
        })
        .join("");
      return `<section class="alertbox" aria-label="${esc(this._t("alerts"))}"><div class="ahead"><span>${esc(
        this._t("alerts")
      )}</span><span class="acount">${alerts.length}</span></div><ul class="alerts">${items}</ul></section>`;
    }
  };
