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
