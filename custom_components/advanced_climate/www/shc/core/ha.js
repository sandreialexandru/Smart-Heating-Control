// Home Assistant: the houses and rooms found, states, services, statistics.

import { esc, num } from "./format.js";

export const HaMixin = (Base) =>
  class extends Base {
    /**
     * Entity ids of the rooms (Decision sensors) and houses (Presence sensors).
     * Looking through every entity of Home Assistant is done at most every 30 s,
     * not on every state change.
     */
    _discover() {
      const states = this._hass.states;
      const cache = this._found;
      const fresh =
        cache &&
        Date.now() - cache.at < 30000 &&
        [...cache.rooms, ...cache.houses].every((id) => states[id]);
      if (fresh) return cache;
      const rooms = [];
      const houses = [];
      for (const [id, s] of Object.entries(states)) {
        const a = s.attributes;
        if (!a || !a.entry_id) continue;
        if (a.room_id && a.schedule) rooms.push(id);
        else if (a.advanced_climate_house) houses.push(id);
      }
      this._found = { at: Date.now(), rooms, houses };
      return this._found;
    }

    /** Decision sensors of the rooms shown, sorted by name. */
    _rooms() {
      if (!this._hass) return [];
      const wanted = this._config?.rooms;
      if (Array.isArray(wanted) && wanted.length) {
        return wanted.map((id) => this._hass.states[id]).filter(Boolean);
      }
      return this._discover()
        .rooms.map((id) => this._hass.states[id])
        .filter(Boolean)
        .sort((a, b) => String(a.attributes.room_name).localeCompare(String(b.attributes.room_name)));
    }

    /** Houses with their entities and rooms (computed once per update). */
    _houses() {
      if (this._housesMemo) return this._housesMemo;
      const houses = new Map();
      const filtered = Array.isArray(this._config?.rooms) && this._config.rooms.length;
      for (const id of this._discover().houses) {
        const s = this._hass.states[id];
        const a = s?.attributes || {};
        if (!a.advanced_climate_house || !a.entry_id) continue;
        houses.set(a.entry_id, {
          id: a.entry_id,
          name: a.house_name,
          entities: a.house_entities || {},
          rooms: [],
          standalone: true,
        });
      }
      for (const room of this._rooms()) {
        const a = room.attributes;
        if (!houses.has(a.entry_id)) {
          houses.set(a.entry_id, {
            id: a.entry_id,
            name: a.house_name,
            entities: a.house_entities || {},
            rooms: [],
          });
        }
        const house = houses.get(a.entry_id);
        house.standalone = false;
        house.rooms.push(room);
      }
      // With an explicit room list, only the houses of those rooms are shown.
      this._housesMemo = [...houses.values()].filter((h) => !filtered || h.rooms.length);
      return this._housesMemo;
    }

    /** Entities whose change redraws the card. */
    _watched() {
      const ids = [];
      for (const house of this._houses()) {
        ids.push(...Object.values(house.entities));
        for (const room of house.rooms) {
          ids.push(room.entity_id, ...Object.values(room.attributes.entities || {}));
          ids.push(...(room.attributes.climate_entities || []));
        }
      }
      return ids;
    }

    /** State object of an entity, if any. */
    _state(id) {
      return id ? this._hass.states[id] : undefined;
    }

    /** Call a service; the error is shown under the section when it fails. */
    async _call(domain, service, data, errorKey) {
      try {
        await this._hass.callService(domain, service, data);
        if (errorKey) delete this._error[errorKey];
        return true;
      } catch (err) {
        if (errorKey) this._error[errorKey] = `${this._t("error")}: ${err?.message || err}`;
        this._lastKey = "";
        this._render();
        return false;
      }
    }

    /** Attributes that open the more-info dialog of an entity on click. */
    _more(entityId, title = null) {
      if (!entityId) return title ? `title="${esc(title)}"` : "";
      return `data-action="more" data-entity="${esc(entityId)}" role="link" tabindex="0" title="${esc(
        title || this._t("open_entity")
      )}"`;
    }

    /** Hours of heating in the current day / week / month, from the long-term statistics. */
    _runtimeValue(entityId) {
      const period = this._period();
      const key = `${entityId}|${period}`;
      this._runtime = this._runtime || {};
      const cached = this._runtime[key];
      if (!cached || (!cached.loading && Date.now() - cached.at > 5 * 60 * 1000)) {
        this._fetchRuntime(entityId, period, key);
      }
      return cached && !cached.failed ? cached.value : null;
    }

    /** Fetch the heating time of the period from the long-term statistics. */
    async _fetchRuntime(entityId, period, key) {
      this._runtime[key] = { ...(this._runtime[key] || {}), at: Date.now(), loading: true };
      if (!this._hass?.callWS) return;
      let value = null;
      let failed = false;
      try {
        const res = await this._hass.callWS({
          type: "recorder/statistic_during_period",
          statistic_id: entityId,
          calendar: { period },
          types: ["change"],
        });
        value = num(res?.change) ?? 0;
      } catch (err) {
        failed = true;
      }
      this._runtime[key] = { at: Date.now(), loading: false, value, failed };
      const active = this.shadowRoot.activeElement;
      if (this._editing || this._drag || this._pan || (active && ["INPUT", "SELECT"].includes(active.tagName))) return;
      this._lastKey = "";
      this._render();
    }
  };
