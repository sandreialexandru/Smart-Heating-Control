// Setting a room for a while, and the temperatures of its levels.

import { PRESET_COLORS } from "../core/constants.js";
import { esc, num } from "../core/format.js";

export const QuickMixin = (Base) =>
  class extends Base {
    /** Quick manual change: a level or a temperature, for an optional number of hours. */
    _quickHtml(a, e = {}) {
      const presets = (a.presets || Object.keys(PRESET_COLORS).filter((p) => p !== "frost"))
        .map(
          (p) => `<button class="preset" style="--c:${PRESET_COLORS[p] || "var(--primary-color)"}"
            data-action="quick-preset" data-room="${esc(a.room_id)}" data-preset="${esc(p)}"><span class="dot"></span>${esc(
            this._presetName(a, p)
          )}${num(a.levels?.[p]) !== null ? ` <small>${num(a.levels[p])}°</small>` : ""}</button>`
        )
        .join("");
      const unit = a.temperature_unit || "°C";
      const fahrenheit = unit === "°F";
      const target = num(a.target_temperature) ?? (fahrenheit ? 70 : 21);
      return this._fold(
        `quick-${a.room_id}`,
        this._t("quick"),
        `<p class="hint">${this._t("quick_hint")}</p>
          <div class="presets">${presets}</div>
          <div class="quickset" data-ov="${esc(a.override ? `${a.override.since || ""}|${a.override.until || ""}` : "")}">
            ${this._btn(this._t("apply"), `data-action="quick-temp" data-room="${esc(a.room_id)}"`, {
              icon: "thermometer-check",
            })}
            <label class="numfield"><input type="number" step="0.1" min="${
              num(a.min_temperature) ?? (fahrenheit ? 41 : 5)
            }" max="${num(a.max_temperature) ?? (fahrenheit ? 86 : 30)}" aria-label="${esc(this._t("target_tag"))}"
              data-quick="temp" data-room="${esc(a.room_id)}" value="${target}"><em>${esc(unit)}</em></label>
            <label class="numfield"><span>${this._t("for_hours")}</span><input type="number" step="0.5" min="0.5" max="72"
              data-quick="hours" data-room="${esc(a.room_id)}" placeholder="auto"><em>${this._t("hours")}</em></label>
          </div>`
      );
    }

    /** Temperatures of the levels the integration sets (number entities). */
    _levelsHtml(a, e) {
      const numbers = Object.entries(e).filter(([k]) => k.startsWith("level_"));
      if (!numbers.length) return "";
      const rows = numbers
        .map(([k, id]) => {
          const s = this._state(id);
          if (!s) return "";
          const preset = k.replace("level_", "");
          const name = s.attributes.friendly_name?.replace(`${a.room_name} `, "") || this._presetName(a, preset);
          return `<label class="numfield level"><span class="dot" style="--c:${
            PRESET_COLORS[preset] || "var(--divider-color)"
          }"></span><span class="lname">${esc(name)}</span><input type="number" step="${s.attributes.step || 0.1}" min="${
            s.attributes.min ?? 5
          }" max="${s.attributes.max ?? 30}" data-action="number" data-entity="${esc(id)}" value="${esc(
            s.state
          )}"><em>${esc(s.attributes.unit_of_measurement || "°C")}</em></label>`;
        })
        .join("");
      return this._fold(`levels-${a.room_id}`, this._t("levels"), `<div class="grid">${rows}</div>`);
    }

    /** A short note under the quick manual change, without drawing the card again
     * (the fields keep what was typed); it goes away after a few seconds. */
    _quickNote(room, key) {
      const set = this.shadowRoot.querySelector(`input[data-quick="temp"][data-room="${CSS.escape(room)}"]`)?.closest(".quickset");
      if (!set) return;
      let note = set.parentElement.querySelector(".qnote");
      if (!note) {
        note = document.createElement("p");
        note.className = "hint qnote";
        note.setAttribute("role", "status");
        set.after(note);
      }
      note.textContent = this._t(key);
      clearTimeout(this._quickNoteTimer);
      this._quickNoteTimer = setTimeout(() => note.remove(), 5000);
    }

    /** Temperature and duration entered in the quick manual change. */
    /**
     * After a manual change from the card: the fields lose the focus (while a field
     * has it the card is not drawn again) and the hours typed go, so the next one
     * starts from the target of the room.
     */
    _quickDone(room) {
      const sel = (k) => this.shadowRoot.querySelector(`input[data-quick="${k}"][data-room="${CSS.escape(room)}"]`);
      const hours = sel("hours");
      if (hours) hours.value = "";
      this.shadowRoot.activeElement?.blur?.();
      this._lastKey = null;
      this._render(true);
    }

    _quickValues(room) {
      const temp = this.shadowRoot.querySelector(`input[data-quick="temp"][data-room="${CSS.escape(room)}"]`);
      const hours = this.shadowRoot.querySelector(`input[data-quick="hours"][data-room="${CSS.escape(room)}"]`);
      const data = {};
      const h = num(hours?.value);
      if (h !== null) data.duration_hours = h;
      return { temp: num(temp?.value), data };
    }
  };
