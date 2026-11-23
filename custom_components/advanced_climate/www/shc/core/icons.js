// Icons, buttons and switches drawn the same everywhere.

import { esc } from "./format.js";

export const IconMixin = (Base) =>
  class extends Base {
    /** Material Design icon. */
    _icon(name) {
      return name ? `<ha-icon icon="mdi:${name}"></ha-icon>` : "";
    }

    /** Button with an optional icon. */
    _btn(label, attrs, { icon = "", kind = "" } = {}) {
      return `<button class="btn ${kind}" ${attrs}>${this._icon(icon)}<span>${esc(label)}</span></button>`;
    }

    /** On / off switch for an entity. */
    _toggle(entityId, label) {
      const s = this._state(entityId);
      if (!s) return "";
      const on = s.state === "on";
      return `<button class="toggle ${on ? "on" : ""}" role="switch" aria-checked="${on}"
        data-action="toggle" data-entity="${esc(entityId)}"><span class="knob"></span><span>${esc(
        label
      )}</span></button>`;
    }

    /**
     * The flame: an outlined circle while there is a demand for heat, a full one
     * that flickers while the heat source runs. The words are in its title.
     */
    _flame(heating, entityId = null, small = false, glow = !small) {
      const text = this._t(heating ? "heating" : "asks_heat");
      const link = entityId ? this._more(entityId, text) : `title="${esc(text)}"`;
      // Grey while it only asks (the heat source does not run yet), the colour of
      // heat and its flicker while it heats; a glow too where it is shown big.
      return `<span class="flame ${heating ? "on" : ""} ${heating && glow ? "glow" : ""} ${small ? "sm" : ""} ${entityId ? "link" : ""}" ${link}
        aria-label="${esc(text)}">${this._icon("fire")}</span>`;
    }
  };
