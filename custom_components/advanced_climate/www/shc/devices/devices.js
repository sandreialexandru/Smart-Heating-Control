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
            if (!byId.has(id)) byId.set(id, { id, role, rooms: [], roomIds: [], house });
            byId.get(id).rooms.push(a.room_name);
            byId.get(id).roomIds.push(a.room_id);
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

    /**
     * Humidity of every room with a humidity sensor: the air and the coldest
     * wall, those at risk of mold first (an active mold alert, or 80 % or more
     * at the wall, as in the Details of the room). A tap opens its Details.
     */
    _humidityTabHtml(houses) {
      const all = houses.flatMap((h) => h.rooms);
      const rows = all
        .map((r) => r.attributes)
        .filter((a) => num(a.humidity) !== null)
        .map((a) => {
          const wall = num(a.surface_humidity);
          const alert = (a.alerts || []).some((x) => x.code === "mold_risk");
          return { a, air: num(a.humidity), wall, risk: alert || (wall !== null && wall >= 80) };
        });
      if (!rows.length) return "";
      rows.sort((x, y) => Number(y.risk) - Number(x.risk) || (y.wall ?? y.air) - (x.wall ?? x.air));
      const pct = (v) => (v === null ? "–" : `${Math.round(v)}%`);
      const item = ({ a, air, wall, risk }) =>
        `<li class="pd-row ph-hum ${risk ? "risk" : ""} link" data-action="humidity-room" data-room="${esc(a.room_id)}" role="button" tabindex="0">
            <span class="pd-ico">${this._icon(risk ? "water-alert-outline" : "water-percent")}</span>
            <span class="pd-name"><span>${esc(a.room_name)}</span>${risk ? `<small class="warn">${esc(this._t("humidity_risk"))}</small>` : ""}</span>
            <span class="pd-val"><small class="pl-lab">${esc(this._t("hu_air"))}</small> ${esc(pct(air))}</span>
            <span class="pd-bat"><small class="pl-lab">${esc(this._t("hu_wall"))}</small> ${esc(pct(wall))}</span>
            <span></span>
          </li>`;
      // Each house (its name when there are several), then the groups of its rooms.
      const items = houses
        .map((house) => {
          const ids = new Set(house.rooms.map((r) => r.attributes.room_id));
          const own = rows.filter((r) => ids.has(r.a.room_id));
          if (!own.length) return "";
          const groupOf = this._groupOf(house.rooms, this._gmodeNow || "none");
          const order = this._roomGroups(house.rooms, this._gmodeNow || "none");
          const byGroup = new Map(order.map((g) => [g.key, []]));
          for (const r of own) byGroup.get(groupOf(r.a.room_id)?.key ?? "")?.push(r);
          const title = houses.length > 1 ? `<li class="pd-group pd-house">${esc(house.name || "")}</li>` : "";
          return (
            title +
            order
              .filter((g) => byGroup.get(g.key).length)
              .map((g) => (g.name !== null ? `<li class="pd-group">${esc(g.name)}</li>` : "") + byGroup.get(g.key).map(item).join(""))
              .join("")
          );
        })
        .join("");
      const risky = rows.filter((r) => r.risk).length;
      return `<section class="block pd-humidity"><h3 class="ps-title">${esc(this._t("hu_title"))}${
        risky ? ` · <span class="pd-badcount">${esc(this._t("hu_risky").replace("{n}", risky))}</span>` : ""
      }</h3><ul class="pd-list">${items}</ul><p class="muted pw-note">${esc(this._t("hu_note"))}</p></section>`;
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
      // In the groups of the rooms (an entity of several rooms: in the group of its first room).
      const all = houses.flatMap((h) => h.rooms);
      const groupOf = this._groupOf(all, this._gmodeNow || "none");
      const order = this._roomGroups(all, this._gmodeNow || "none");
      const byGroup = new Map(order.map((g) => [g.key, []]));
      for (const r of rows) byGroup.get(groupOf(r.roomIds[0])?.key ?? "")?.push(r);
      const item = (r) => {
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
      };
      const items = order
        .filter((g) => byGroup.get(g.key).length)
        .map((g) => (g.name !== null ? `<li class="pd-group">${esc(g.name)}</li>` : "") + byGroup.get(g.key).map(item).join(""))
        .join("");
      return `<section class="block pd-devices">${head}<ul class="pd-list">${items}</ul><p class="muted pw-note">${esc(
        this._t("dv_note")
      )}</p></section>`;
    }
  };
