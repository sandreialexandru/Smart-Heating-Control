/*
 * Smart Heating Control card – every option of the integration in one card.
 *
 *   type: custom:smart-heating-control-card
 *   title: Heating               # optional
 *   show_title: true             # false (or title: "") hides the title
 *   rooms:                       # optional: decision sensors to show (default: all)
 *     - sensor.living_decision
 *   show_house: true             # house: presence, mode, pause, guests, vacation, stats
 *   show_rooms: true
 *   show_timeline: true          # today's schedule as a temperature profile
 *   show_quick_override: true    # set a level / temperature for a while
 *   show_levels: true            # level temperatures (rooms without Generic Thermostat)
 *   show_details: true           # temperatures, heating rate, runtime, adjustments
 *   show_schedule_editor: true
 *   collapsed: false             # rooms start folded (header only)
 *   compact: false               # one tile per room (and a row for the house); tap to open
 *   runtime_period: day          # heating time shown for: day | week | month (tap to change)
 */

import { EDITOR_LABELS, EDITOR_PERIODS, EDITOR_SCHEMA } from "./card/editor.js";
import { thinPoints } from "./chart/data.js";
import { ShcBase } from "./core/base.js";
import { DEFAULTS } from "./core/constants.js";
import { esc } from "./core/format.js";
import { TEXT } from "./core/i18n.js";
import { STYLE } from "./core/style.js";

const CARD_VERSION = "2.7.1rc7";

class SmartHeatingControlCard extends ShcBase {
  /** Visual editor of the card (Home Assistant form). */
  static getConfigForm() {
    const lang = (document.querySelector("home-assistant")?.hass?.locale?.language || navigator.language || "en").slice(0, 2);
    const labels = EDITOR_LABELS[lang] || EDITOR_LABELS.en;
    const periods = EDITOR_PERIODS[lang] || EDITOR_PERIODS.en;
    return {
      // Each field with the value the card uses when it is not set: the form
      // shows a switch without a value as off, while the card shows that part.
      schema: EDITOR_SCHEMA.map(function shown(field) {
        if (field.schema) return { ...field, schema: field.schema.map(shown) };
        const f = field.name in DEFAULTS ? { ...field, default: DEFAULTS[field.name] } : field;
        return f.name === "runtime_period"
          ? { ...f, selector: { select: { ...f.selector.select, options: f.selector.select.options.map((o) => ({ ...o, label: periods[o.value] || o.label })) } } }
          : f;
      }),
      computeLabel: (schema) => labels[schema.name] || schema.name,
    };
  }

  /** Configuration of a new card: every room of every house. */
  static getStubConfig() {
    return {};
  }

  /** Check and keep the card configuration. */
  setConfig(config) {
    if (config === null || typeof config !== "object" || Array.isArray(config)) {
      throw new Error("Invalid configuration");
    }
    if (config.rooms !== undefined && !Array.isArray(config.rooms)) {
      throw new Error("'rooms' must be a list of Decision sensors");
    }
    const merged = { ...DEFAULTS, ...(config || {}) };
    if (config && config.show_editor === false) merged.show_schedule_editor = false;
    if (config && config.entity && !config.rooms) merged.rooms = [config.entity];
    this._config = merged;
    this._housesMemo = null;
    this._runtimePeriod = null;
    this._lastKey = "";
    this._render();
  }

  /** Approximate height for the masonry dashboard. */
  getCardSize() {
    if (this._config?.compact) return 2 + this._rooms().length;
    return 4 + this._rooms().length * 4;
  }

  /** Size in the sections dashboard. */
  getGridOptions() {
    return { columns: 12, min_columns: 6 };
  }

  // ------------------------------------------------------------------ render
  /**
   * Draw the card. Only the blocks that changed are replaced (title, banners,
   * the house, every room), so the rest keeps its state and does not flicker.
   * On a state change a block whose entities did not change keeps its last
   * drawing for up to a minute (its times are refreshed after that).
   */
  _render(fromState = false) {
    if (!this._config) return;
    this._ensureCard();
    const cfg = this._config;
    const houses = this._hass ? this._houses() : [];
    const title = cfg.show_title === false ? "" : (cfg.title ?? this._t("title"));
    this._blockCache = this._blockCache || {};
    const ver = (ids) =>
      ids
        .filter(Boolean)
        .map((id) => {
          const st = this._hass.states[id];
          return st ? `${st.state}|${st.last_updated}` : "-";
        })
        .join(",");
    const cached = (key, deps, make) => {
      const c = this._blockCache[key];
      if (fromState && c && c.deps === deps && Date.now() - c.at < 60000) return c.html;
      const html = make();
      this._blockCache[key] = { deps, html, at: Date.now() };
      return html;
    };
    const blocks = [];
    if (title) blocks.push({ k: "title", html: `<h2 class="title">${esc(title)}</h2>` });
    if (!houses.length) {
      blocks.push({ k: "empty", html: `<p class="empty">${this._t("no_rooms")}</p>` });
    }
    for (const house of houses) {
      const he = Object.values(house.entities || {});
      const houseRooms = this._discover().rooms.filter((id) => this._hass.states[id]?.attributes?.entry_id === house.id);
      const pause = this._pauseBanner(house);
      if (pause) blocks.push({ k: `pause-${house.id}`, html: pause });
      const guest = this._guestBanner(house);
      if (guest) blocks.push({ k: `guest-${house.id}`, html: guest });
      if (cfg.show_house) {
        blocks.push({
          k: `house-${house.id}`,
          html: cached(`house-${house.id}`, ver([...he, ...houseRooms]) + this._houses().length, () => this._houseHtml(house)),
        });
      }
      if (!cfg.show_rooms) continue;
      if (!house.rooms.length) {
        blocks.push({ k: `norooms-${house.id}`, html: `<p class="empty">${this._t("no_rooms")}</p>` });
        continue;
      }
      const rooms = house.rooms.map((r) => {
        const a = r.attributes;
        const deps = ver([
          r.entity_id,
          ...Object.values(a.entities || {}),
          ...(a.climate_entities || []),
          // The devices shown in the Details (their state now).
          ...(Array.isArray(a.devices) ? a.devices.map((d) => d[0]) : []),
          house.entities.guest_mode,
          house.entities.outdoor_average,
        ]);
        return { k: `room-${a.room_id}`, html: cached(`room-${a.room_id}`, deps, () => this._roomHtml(r)) };
      });
      if (cfg.compact) blocks.push({ k: `list-${house.id}`, html: `<div class="rooms-list"></div>`, children: rooms });
      else blocks.push(...rooms);
    }
    // The chart window first: a node moved by the patch would leave the top
    // layer (no longer modal); the first one is never moved.
    const popup = this._chartPopup();
    if (popup) blocks.unshift(popup);
    this._card.className = cfg.compact ? "compact" : "";
    this._patch(this._card, blocks);
    this._tipColor();
    this._chartModal();
  }

  /** The card element and the styles, made once. */
  _ensureCard() {
    if (this._card) return;
    this._addStyle(STYLE);
    this._card = document.createElement("ha-card");
    this.shadowRoot.appendChild(this._card);
  }
}

// ---------------------------------------------------------------- register
// Some Home Assistant setups replace window.customElements after page load
// (scoped custom element registry). Anything defined before the swap is not
// visible to the new registry and Lovelace reports that the card does not
// exist, so the card is defined again for a few seconds if needed.
const CARD_TAG = "smart-heating-control-card";
// A class can be defined only once, so the tag gets its own subclass.
const defineTag = (tag) => {
  try {
    if (!window.customElements.get(tag)) {
      window.customElements.define(tag, class extends SmartHeatingControlCard {});
    }
    return true;
  } catch (err) {
    console.warn(`${tag}: could not register on the current registry`, err);
    return false;
  }
};
const registerCard = () => defineTag(CARD_TAG);

if (!window.__smartHeatingControlCardLoaded) {
  window.__smartHeatingControlCardLoaded = CARD_VERSION;
  registerCard();
  window.customCards = window.customCards || [];
  if (!window.customCards.some((c) => c.type === CARD_TAG)) {
    window.customCards.push({
      type: CARD_TAG,
      name: "Smart Heating Control",
      description: "House and rooms of Smart Heating Control with every control and an editable schedule.",
      preview: true,
      documentationURL: "https://github.com/sandreialexandru/Smart-Heating-Control#lovelace-card",
    });
  }
  console.info(`%c SMART-HEATING-CONTROL-CARD %c ${CARD_VERSION} `, "color:#fff;background:#f08c00", "");
  let checks = 0;
  const watch = setInterval(() => {
    registerCard();
    if (++checks >= 60) clearInterval(watch); // 30 s
  }, 500);
  window.addEventListener("location-changed", registerCard);
} else {
  registerCard();
}

// For the tests of the card (tests/card/page.html): module code is not global.
export { TEXT, EDITOR_LABELS, thinPoints };
