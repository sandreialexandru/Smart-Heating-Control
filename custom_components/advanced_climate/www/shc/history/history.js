// History of the panel: the decisions of every room and the alerts of the house
// with their start and end, newest first, as the integration keeps them
// (the websocket command advanced_climate/history).

import { ALERT_ERRORS } from "../core/constants.js";
import { esc } from "../core/format.js";

// The history is asked for again after this long (and after each change of a room).
const HISTORY_REFRESH_MS = 60e3;

export const HistoryMixin = (Base) =>
  class extends Base {
    /** The history of every house, fetched when missing or old (drawn again when it comes). */
    _historyData() {
      const h = this._historyLog;
      if (!h || (!h.loading && Date.now() - h.at > HISTORY_REFRESH_MS)) this._fetchHistoryLog();
      return h && (h.data || h.failed) ? h : null;
    }

    async _fetchHistoryLog() {
      this._historyLog = { ...(this._historyLog || {}), at: Date.now(), loading: true };
      let data = null;
      let failed = false;
      try {
        data = await this._hass.callWS({ type: "advanced_climate/history" });
      } catch (_err) {
        failed = true;
      }
      this._historyLog = { at: Date.now(), loading: false, data, failed };
      if (this._tab === "history") this._render();
    }

    /** Every line of the history: {t, room, kind, html}, newest first. */
    _historyItems(houses, data) {
      const items = [];
      const attrs = {};
      for (const house of houses) for (const r of house.rooms) attrs[r.attributes.room_id] = r.attributes;
      for (const h of data?.houses || []) {
        const names = Object.fromEntries((h.rooms || []).map((r) => [r.room_id, r.name]));
        for (const r of h.rooms || []) {
          const a = attrs[r.room_id] || {};
          for (const d of r.decisions || []) {
            const text = this._reasonText({
              reason_key: d.reason_key,
              reason_params: d.reason_params,
              reason: d.description,
              preset_names: a.preset_names || {},
              offsets: [],
            });
            items.push({
              t: Date.parse(d.time),
              room: r.room_id,
              kind: "decision",
              html: `<span class="ph-ico">${this._icon(this._ruleIcon(d.rule))}</span><span class="ph-text"><b>${esc(r.name)}</b> ${esc(text)}</span>`,
            });
          }
        }
        for (const al of h.alerts || []) {
          const named = this._t(`at_${al.code}`);
          const title = named === `at_${al.code}` ? this._t("at_other") : named;
          const start = Date.parse(al.start);
          const end = al.end ? Date.parse(al.end) : null;
          const until = end === null
            ? this._t("hi_still")
            : `${this._t("hi_until")} ${this._fmtTime(al.end)} (${this._duration((end - start) / 60e3)})${al.restart ? ` · ${this._t("hi_restart")}` : ""}`;
          const kind = ALERT_ERRORS.includes(al.code) ? "error" : "warn";
          const where = al.room ? names[al.room] || "" : this._t("hi_house");
          // "Mold risk: the coldest wall …" after the title "Mold risk": the subject once (as in the room).
          let text = this._alertText(al);
          if (text.toLowerCase().startsWith(`${title.toLowerCase()}: `)) text = text.slice(title.length + 2).replace(/^./, (c) => c.toUpperCase());
          const icon = al.code === "mold_risk" ? "water-alert-outline" : kind === "error" ? "alert-circle-outline" : "alert-outline";
          items.push({
            t: start,
            room: al.room || "",
            kind: "alert",
            html: `<span class="ph-ico ${kind}">${this._icon(icon)}</span><span class="ph-text"><b>${esc(where)}</b> ${esc(title)}: ${esc(
              text
            )}<span class="muted"> · ${esc(until)}</span></span>`,
          });
        }
      }
      return items.filter((i) => !Number.isNaN(i.t)).sort((x, y) => y.t - x.t);
    }

    /**
     * The alerts on now, of every house, once each: {key, house, room, al}. The
     * rooms report their own alerts and those of the whole house; the journal
     * of the history (when loaded) tells which room an alert is for and since
     * when, else an alert reported by every room of a house is the house's.
     */
    _activeAlerts(houses) {
      const open = {};
      for (const h of this._historyLog?.data?.houses || []) {
        for (const al of h.alerts || []) if (!al.end) open[`${h.entry_id}/${al.key}`] = al;
      }
      const out = [];
      for (const house of houses) {
        const seen = new Map();
        for (const r of house.rooms) {
          const a = r.attributes;
          for (const al of a.alerts || []) {
            // The key of the integration; an alert without one stays the room's.
            const id = `${house.id}/${al.key ?? `${al.code}|${a.room_id}`}`;
            if (!seen.has(id)) seen.set(id, { key: id, house, al, rooms: [] });
            seen.get(id).rooms.push(a.room_id);
          }
        }
        for (const item of seen.values()) {
          const journal = open[item.key];
          const room = journal
            ? journal.room || null
            : item.rooms.length === 1 && house.rooms.length > 1
              ? item.rooms[0]
              : null;
          out.push({ ...item, room, start: journal ? Date.parse(journal.start) : null });
        }
      }
      return out;
    }

    /** The alerts on now, on top of the history: where, what, since when, and the room a tap opens. */
    _alertsNowHtml(houses) {
      const alerts = this._activeAlerts(houses);
      const names = Object.fromEntries(houses.flatMap((h) => h.rooms.map((r) => [r.attributes.room_id, r.attributes.room_name])));
      const head = `<h3 class="ps-title">${esc(this._t("an_title"))}${alerts.length ? ` <span class="acount">${alerts.length}</span>` : ""}</h3>`;
      if (!alerts.length) return `<section class="block pa-now">${head}<p class="muted">${esc(this._t("an_none"))}</p></section>`;
      const items = alerts
        .map(({ al, room, start, house }) => {
          const p = al.params || {};
          const entity = p.entity || (Array.isArray(p.entities) ? p.entities[0] : null);
          const kind = ALERT_ERRORS.includes(al.code) ? "error" : "warn";
          const icon = al.code === "mold_risk" ? "water-alert-outline" : kind === "error" ? "alert-circle-outline" : "alert-outline";
          const named = this._t(`at_${al.code}`);
          const title = named === `at_${al.code}` ? this._t("at_other") : named;
          let text = this._alertText(al);
          if (text.toLowerCase().startsWith(`${title.toLowerCase()}: `)) text = text.slice(title.length + 2).replace(/^./, (c) => c.toUpperCase());
          const where = room ? names[room] || "" : houses.length > 1 ? `${house.name || ""} · ${this._t("hi_house")}` : this._t("hi_house");
          const since =
            start !== null && !Number.isNaN(start)
              ? ` · ${this._t("an_since").replace("{t}", this._fmt(start, { weekday: "short", hour: "2-digit", minute: "2-digit" }))}`
              : "";
          const open = room
            ? this._btn(this._t("an_open"), `data-action="alert-room" data-room="${esc(room)}"`, { icon: "arrow-right" })
            : "";
          return `<li class="${kind}"><span class="ph-ico ${kind}">${this._icon(icon)}</span><span class="ph-text ${entity ? "link" : ""}" ${this._more(
            entity
          )}><b>${esc(where)}</b> ${esc(title)}: ${esc(text)}<span class="muted">${esc(since)}</span></span>${open}</li>`;
        })
        .join("");
      return `<section class="block pa-now">${head}<ul class="ph-list pa-list">${items}</ul></section>`;
    }

    /** The history: filters (what, which room), then the lines by day. */
    _historyHtml(houses) {
      const kind = this._historyKind || "all";
      const room = this._historyRoom || "";
      const seg = ["all", "decision", "alert"]
        .map(
          (k) => `<button class="seg ${k === kind ? "active" : ""}" data-action="history-kind" data-option="${k}" aria-pressed="${
            k === kind
          }">${esc(this._t(`hi_${k}`))}</button>`
        )
        .join("");
      const rooms = houses.flatMap((h) => h.rooms.map((r) => r.attributes));
      const options = [`<option value="" ${room ? "" : "selected"}>${esc(this._t("hi_every_room"))}</option>`]
        .concat(rooms.map((a) => `<option value="${esc(a.room_id)}" ${a.room_id === room ? "selected" : ""}>${esc(a.room_name)}</option>`))
        .join("");
      const head = `<div class="ph-filters"><div class="segmented" style="--n:3" role="group">${seg}</div>
        <select class="ph-room" data-action="history-room" aria-label="${esc(this._t("hi_every_room"))}">${options}</select></div>`;
      const h = this._historyData();
      if (!h) return `<section class="block ph-history">${head}<p class="muted">${esc(this._t("loading"))}</p></section>`;
      if (h.failed) return `<section class="block ph-history">${head}<p class="muted">${esc(this._t("hi_failed"))}</p></section>`;
      // A room shows its alerts and those of the whole house.
      const items = this._historyItems(houses, h.data).filter(
        (i) => (kind === "all" || i.kind === kind) && (!room || i.room === room || (i.kind === "alert" && !i.room))
      );
      let day = "";
      const lines = [];
      for (const i of items) {
        const d = this._dayKey(i.t);
        if (d !== day) {
          if (day) lines.push("</ul>");
          lines.push(`<h3 class="ph-day">${esc(this._fmt(i.t, { weekday: "long", day: "numeric", month: "long" }))}</h3><ul class="ph-list">`);
          day = d;
        }
        lines.push(`<li class="ph-${i.kind}"><span class="ph-time">${esc(this._fmt(i.t, { hour: "2-digit", minute: "2-digit" }))}</span>${i.html}</li>`);
      }
      if (day) lines.push("</ul>");
      const body = lines.length ? lines.join("") : `<p class="muted">${esc(this._t("hi_empty"))}</p>`;
      return `<section class="block ph-history">${head}${body}<p class="muted ph-note">${esc(this._t("hi_note"))}</p></section>`;
    }
  };
