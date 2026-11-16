// The devices of the panel: every entity the rooms use, of every house, in
// one list, the unavailable ones first; with the battery of its device (when
// Home Assistant has a battery entity on that device) and when it last
// changed. A tap opens the entity.

import { esc, num } from "../core/format.js";

export const DevicesMixin = (Base) =>
  class extends Base {
    /** Battery entities by device: {device_id: [entity_id, …]} (from the entity registry of the frontend). */
    _batteries() {
      const hass = this._hass;
      if (this._batteryMemo?.hass === hass) return this._batteryMemo.map;
      const map = {};
      for (const [id, entry] of Object.entries(hass.entities || {})) {
        if (!entry?.device_id) continue;
        if (!id.startsWith("sensor.") && !id.startsWith("binary_sensor.")) continue;
        if (hass.states[id]?.attributes?.device_class !== "battery") continue;
        (map[entry.device_id] = map[entry.device_id] || []).push(id);
      }
      this._batteryMemo = { hass, map };
      return map;
    }

    /** The battery of the device of an entity: {id, text, low} or null. */
    _battery(entityId) {
      const device = this._hass.entities?.[entityId]?.device_id;
      if (!device) return null;
      for (const id of this._batteries()[device] || []) {
        const st = this._hass.states[id];
        if (!st || st.state === "unavailable" || st.state === "unknown") continue;
        // A battery sensor in %; a binary one is on when the battery is low.
        if (id.startsWith("binary_sensor.")) return { id, text: this._t(st.state === "on" ? "dv_battery_low" : "dv_battery_ok"), low: st.state === "on" };
        const v = num(st.state);
        if (v !== null) return { id, text: `${Math.round(v)}${st.attributes?.unit_of_measurement || "%"}`, low: false };
      }
      return null;
    }

    /** Every entity of the rooms, once: {id, role, rooms: [names], house}. */
    _deviceList(houses) {
      const byId = new Map();
      for (const house of houses) {
        for (const r of house.rooms) {
          const a = r.attributes;
          for (const [id, role] of Array.isArray(a.devices) ? a.devices : []) {
            if (!byId.has(id)) byId.set(id, { id, role, rooms: [], house });
            byId.get(id).rooms.push(a.room_name);
          }
        }
      }
      return [...byId.values()];
    }

    /** The entities a change of which redraws the devices: theirs and their batteries. */
    _deviceIds(houses) {
      const ids = [];
      for (const d of this._deviceList(houses)) {
        ids.push(d.id);
        const device = this._hass.entities?.[d.id]?.device_id;
        if (device) ids.push(...(this._batteries()[device] || []));
      }
      return ids;
    }

    /** How long ago, in words ("5 minutes ago"). */
    _ago(iso) {
      const t = Date.parse(iso);
      if (Number.isNaN(t)) return "";
      const s = Math.max(0, (Date.now() - t) / 1000);
      const rtf = new Intl.RelativeTimeFormat(this._lang(), { numeric: "auto" });
      if (s < 60) return rtf.format(0, "second");
      if (s < 3600) return rtf.format(-Math.floor(s / 60), "minute");
      if (s < 86400) return rtf.format(-Math.floor(s / 3600), "hour");
      return rtf.format(-Math.floor(s / 86400), "day");
    }

    /** The tab: the unavailable entities first, then by room and name. */
    _devicesTabHtml(houses) {
      const rows = this._deviceList(houses).map((d) => {
        const info = this._deviceInfo(d.id, d.role);
        return { ...d, ...info, battery: this._battery(d.id) };
      });
      if (!rows.length) return `<section class="block pd-devices"><p class="muted">${esc(this._t("dv_none"))}</p></section>`;
      rows.sort(
        (x, y) =>
          Number(y.bad) - Number(x.bad) ||
          Number(!!y.battery?.low) - Number(!!x.battery?.low) ||
          x.rooms[0].localeCompare(y.rooms[0]) ||
          x.name.localeCompare(y.name)
      );
      const bad = rows.filter((r) => r.bad).length;
      const head = `<h3 class="ps-title">${esc(this._t("dv_title").replace("{n}", rows.length))}${
        bad ? ` · <span class="pd-badcount">${esc(this._t("dv_bad").replace("{n}", bad))}</span>` : ""
      }</h3>`;
      const items = rows
        .map((r) => {
          const changed = [r.st?.last_updated, r.st?.last_changed].find((v) => v && !Number.isNaN(Date.parse(v)));
          const where = houses.length > 1 ? `${r.house.name || ""} · ${r.rooms.join(", ")}` : r.rooms.join(", ");
          return `<li class="pd-row ${r.bad ? "bad" : ""} link" ${this._more(r.id)}>
              <span class="pd-ico">${this._icon(r.icon)}</span>
              <span class="pd-name"><span>${esc(r.name)}</span><small>${esc(this._t(`dev_${r.role}`))} · ${esc(where)}</small></span>
              <span class="pd-val">${esc(r.value)}</span>
              <span class="pd-bat ${r.battery?.low ? "low" : ""}">${
                r.battery ? `${this._icon(r.battery.low ? "battery-alert-variant-outline" : "battery-outline")}${esc(r.battery.text)}` : ""
              }</span>
              <span class="pd-ago muted" title="${esc(changed ? this._fmtTime(changed) : "")}">${esc(changed ? this._ago(changed) : "")}</span>
            </li>`;
        })
        .join("");
      return `<section class="block pd-devices">${head}<ul class="pd-list">${items}</ul><p class="muted pw-note">${esc(
        this._t("dv_note")
      )}</p></section>`;
    }
  };
