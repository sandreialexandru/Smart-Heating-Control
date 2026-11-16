// What SHC learned, every room side by side (the Statistics tab of the panel):
// the state of the learning, the heating, its inertia, the heat loss and the
// weather curve, as the Details of a room show them. A tap opens the room.

import { esc, num } from "../core/format.js";

export const LearnedMixin = (Base) =>
  class extends Base {
    /** One room: its values, or how far the learning is. */
    _learnedRow(a) {
      const e = a.entities || {};
      const heat = this._state(e.heating_rate);
      if (!heat) return "";
      const cool = this._state(e.cooling_rate);
      const unit = heat.attributes.unit_of_measurement || "min/°C";
      const deg = unit.replace(/^min\//, "");
      const learned = !!heat.attributes.learned;
      const cell = (label, text) =>
        `<span class="pl-val"><small class="pl-lab">${esc(label)}</small>${esc(text)}</span>`;
      let state;
      let values = "";
      if (learned) {
        const err = num(heat.attributes.error_per_hour);
        state = err === null ? this._t("learn_state_done_short") : this._t("learn_state_done").replace("{err}", `${err.toFixed(2)} ${deg}`);
        const rate = num(heat.state);
        const c = num(heat.attributes.weather_curve) ?? 0;
        const loss = cool ? num(cool.state) : null;
        values =
          cell(this._t("learn_heat"), rate === null ? "–" : `${Math.round(rate)} ${unit}`) +
          cell(this._t("learn_inertia"), `${Math.round(num(heat.attributes.inertia_minutes) ?? 0)} min`) +
          cell(this._t("learn_cool"), loss === null ? "–" : `${loss.toFixed(2)} ${cool.attributes.unit_of_measurement || `${deg}/h`}`) +
          cell(
            this._t("learn_curve"),
            Math.abs(c) < 0.0005
              ? this._t("learn_curve_none")
              : this._t("learn_curve_value").replace("{value}", `${c > 0 ? "+" : "−"}${Math.abs(c).toFixed(3)}`).replace("{u}", deg)
          );
      } else {
        const need = num(heat.attributes.hours_needed) ?? 0;
        const v = (h) => String(Math.min(need, num(h) ?? 0));
        state = `${this._t("learn_progress")} ${this._t("learn_bar_heat").replace("{v}", v(heat.attributes.hours_heating)).replace("{need}", String(need))}, ${this._t(
          "learn_bar_idle"
        )
          .replace("{v}", v(heat.attributes.hours_idle))
          .replace("{need}", String(need))}`;
      }
      return `<button class="pl-row ${learned ? "" : "pl-learning"}" data-action="learned-open" data-room="${esc(a.room_id)}" aria-label="${esc(
        `${a.room_name}: ${state}`
      )}"><span class="pl-name">${esc(a.room_name)}</span><span class="pl-state muted">${esc(state)}</span>${values}</button>`;
    }

    /** Every room of every house (only the rooms with a learned model). */
    _learnedHtml(houses) {
      const parts = [];
      for (const house of houses) {
        const rows = house.rooms.map((r) => this._learnedRow(r.attributes)).filter(Boolean);
        if (!rows.length) continue;
        if (houses.length > 1) parts.push(`<h3 class="ps-house">${esc(house.name || "")}</h3>`);
        parts.push(`<div class="pl-rows">${rows.join("")}</div>`);
      }
      if (!parts.length) return "";
      return `<section class="block pl-learned"><h3 class="ps-title">${esc(this._t("le_title"))}</h3>${parts.join(
        ""
      )}<p class="muted pw-note">${esc(this._t("le_note"))}</p></section>`;
    }
  };
