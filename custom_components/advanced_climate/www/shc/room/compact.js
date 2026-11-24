// A room folded: a row, or a tile in the compact card.

import { esc } from "../core/format.js";

export const CompactMixin = (Base) =>
  class extends Base {
    /** A folded room: small arc, name, reason, target; a tap opens it. */
    _foldedRow(stateObj, color) {
      const a = stateObj.attributes;
      // One line: the level and its target, then the time to the target or the next change.
      const level = a.preset
        ? `${this._presetName(a, a.preset)} ${this._temp(a.target_temperature)}`
        : this._temp(a.target_temperature);
      const line = [level, this._roomNext(a)].filter(Boolean).join(" · ");
      const icons = this._statusIcons(a);
      return `<section class="block room folded ${this._alertLevel(a)}" style="--c:${color}">
          <button class="frow" data-action="fold" data-key="room-${esc(a.room_id)}" aria-expanded="false">
            ${this._gauge(a, null, 60, false)}
            <span class="ftext"><span class="fname"><span class="name">${esc(a.room_name)}</span></span>
              <span class="freason"><span class="dot"></span><span>${esc(line)}</span></span></span>
            ${icons ? `<span class="ficons">${icons}</span>` : ""}
            <span class="chev"></span>
          </button>
        </section>`;
    }

    /** One tile per room in the compact card: arc, level, target; a tap opens the room. */
    _compactRow(stateObj, color) {
      const a = stateObj.attributes;
      // Every state that applies, as small round icons (heating pulses).
      const status = [
        this._roomHeatIcon(a),
        this._alertIcon(a),
        a.window_open ? `<span class="tstat warn" title="${esc(this._t("window"))}">${this._icon("window-open-variant")}</span>` : "",
        this._moldIcon(a, "tstat"),
        a.override ? `<span class="tstat" title="${esc(this._t("override"))}">${this._icon("hand-back-right-outline")}</span>` : "",
        this._guestOn(a) ? `<span class="tstat teal" title="${esc(this._t("guests_banner"))}">${this._icon("account-group-outline")}</span>` : "",
      ].join("");
      // While heating the time to the target, else the next change (the icons above say the rest).
      const line = this._roomNext(a);
      return `<button class="tile ${this._alertLevel(a)}" data-action="fold" data-key="room-${esc(a.room_id)}" aria-expanded="false" style="--c:${color}"
          aria-label="${esc(`${a.room_name}, ${this._temp(a.current_temperature)}, ${this._label(stateObj)}${this._thermostatsOff(a) ? `, ${this._t("thermostat_off")}` : ""}`)}">
          <span class="tile-head"><span class="tname"><span class="cname">${esc(a.room_name)}</span></span>${
            status ? `<span class="tstats">${status}</span>` : ""
          }</span>
          <span class="tile-body">${this._gauge(a, null, 84, false)}
            <span class="tile-info"><span class="tsub">${esc(this._t("target_tag"))}</span>
              <span class="tval">${this._temp(a.target_temperature)}</span>
              ${line ? `<span class="muted">${esc(line)}</span>` : ""}</span>
          </span>
          ${this._presetPill(a)}
        </button>`;
    }
  };
