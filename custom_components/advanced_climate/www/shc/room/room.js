// A room, open: header, dial, reason, today, its sections.

import { PRESET_COLORS, TEMP_COLOR } from "../core/constants.js";
import { esc, hhmm, num, toMinutes } from "../core/format.js";

export const RoomMixin = (Base) =>
  class extends Base {
    /** Lines next to the arc: the reason, the time to target, the TRV boost, the device reading. */
    _chipsHtml(a, e, stateObj, eta) {
      // Now: why the room is at this level, and the time to the target.
      const sub = eta && eta === this._t("eta_learning") ? this._heatDefault(e) : "";
      const etaLine = eta
        ? `<span class="csub" title="${esc(this._t(a.stop_forecast ? "stop_help" : "eta_help"))}">${esc(eta)}${
            sub ? ` · ${esc(sub)}` : ""
          }</span>`
        : "";
      const chips = [
        `<span class="chip line"><span class="clabel">${esc(this._t("now_tag"))}</span><span class="cval">${esc(
          this._reasonText(a)
        )}</span>${etaLine}</span>`,
      ];
      // Next: the next change of level and when.
      if (a.next_change) {
        const level = a.next_preset ? num(a.levels?.[a.next_preset]) : null;
        chips.push(
          `<span class="chip line"><span class="clabel">${esc(this._t("next"))}</span><span class="cval"><span class="dot" style="--c:${
            PRESET_COLORS[a.next_preset] || TEMP_COLOR
          }"></span>${esc(
            this._t("next_at")
              .replace("{preset}", `${this._presetName(a, a.next_preset)}${level !== null ? ` ${this._temp(level)}` : ""}`)
              .replace("{time}", this._fmtTime(a.next_change))
          )}</span></span>`
        );
      }
      if (this._guestOn(a)) {
        chips.push(`<span class="chip guest">${this._icon("account-group-outline")}<span>${esc(this._t("guests_chip"))}</span></span>`);
      }
      if (a.trv_boost) {
        chips.push(
          `<span class="chip soft ${a.trv_boost.active ? "on" : ""}">${this._icon("lightning-bolt-outline")}<span>${esc(
            this._t(a.trv_boost.active ? "trv_boost_chip" : "trv_boost_chip_off").replace("{temp}", this._temp(a.trv_boost.temperature))
          )}</span></span>`
        );
      }
      // What the device itself measures (a Generic Thermostat reads the room sensor).
      if (a.source !== "generic_thermostat") {
        const dev = (a.climate_entities || [])
          .map((id) => this._state(id))
          .find((s) => s && num(s.attributes.current_temperature) !== null);
        if (dev) {
          const off = dev.state === "off";
          const text = this._t("device_temp").replace("{temp}", this._temp(dev.attributes.current_temperature));
          const label = off ? `${this._t("thermostat_off")} · ${text}` : null;
          chips.push(
            `<span class="chip soft neutral link" ${this._more(dev.entity_id, label)}${label ? ` aria-label="${esc(label)}"` : ""}>${this._icon(off ? "power" : "thermostat")}<span>${esc(text)}</span></span>`
          );
        }
      }
      return chips.join("");
    }

    /** Today's profile as a bar from 00 to 24, with the time now. */
    _todayHtml(a) {
      const slots = a.profile && a.schedule ? a.schedule[a.profile] : null;
      if (!slots || !slots.length) return "";
      // The schedule day starts at the day start of the house (Day starts at), as the integration counts it;
      // before its first time the last time of the profile goes on.
      const start = ((Math.round(num(a.day_boundary) ?? 0) % 1440) + 1440) % 1440;
      const key = (m) => (m - start + 1440) % 1440;
      const sorted = slots
        .map((sl) => ({ k: key(toMinutes(sl.time)), preset: sl.preset }))
        .sort((x, y) => x.k - y.k);
      const parts = [];
      if (sorted[0].k > 0) parts.push({ s: 0, e: sorted[0].k, preset: sorted[sorted.length - 1].preset });
      sorted.forEach((sl, i) => parts.push({ s: sl.k, e: i + 1 < sorted.length ? sorted[i + 1].k : 1440, preset: sl.preset }));
      const clock = (k) => hhmm((k + start) % 1440);
      const segs = parts
        .filter((sg) => sg.e > sg.s)
        .map(
          (sg) =>
            `<i style="left:${(sg.s / 1440) * 100}%;width:${((sg.e - sg.s) / 1440) * 100}%;--c:${
              PRESET_COLORS[sg.preset] || TEMP_COLOR
            }" title="${esc(`${this._presetName(a, sg.preset)} ${clock(sg.s)}–${clock(sg.e)}`)}"></i>`
        )
        .join("");
      const p = this._parts(Date.now());
      const now = (key(p.h * 60 + p.mi) / 1440) * 100;
      const label = (k) => {
        const text = clock(k);
        return text.endsWith(":00") ? text.slice(0, 2) : text;
      };
      return `<div class="today">
          <span class="tlabel">${esc(this._t("today"))} · ${esc(a.profile)}</span>
          <div class="tbar">${segs}<b style="left:${now}%"></b></div>
          <div class="tticks">${[0, 360, 720, 1080, 1440].map((k) => `<span>${label(k)}</span>`).join("")}</div>
        </div>`;
    }

    /** Buttons that open the room sections (independently), then the open sections in a fixed order. */
    _sectionsHtml(a, e, stateObj) {
      const parts = this._sectionParts(a, e, stateObj);
      return parts ? `${parts.buttons}${parts.bodies}` : "";
    }

    /**
     * The buttons of the room sections and the open sections, apart.
     * ``inlineChart``: the chart is drawn beside the room (the panel), so it has no button.
     */
    _sectionParts(a, e, stateObj, inlineChart = false) {
      const cfg = this._config;
      const id = a.room_id;
      const defs = [];
      if (cfg.show_quick_override) defs.push([`quick-${id}`, "btn_quick", "timer-edit-outline", () => this._quickHtml(a, e)]);
      if (cfg.show_schedule_editor) defs.push([`sched-${id}`, "schedule", "calendar-edit", () => this._scheduleHtml(a, stateObj)]);
      // The chart opens on its own button (its history is loaded only then).
      if (cfg.show_timeline && !inlineChart) defs.push([`chart-${id}`, "chart", "chart-line", () => this._timelineHtml(a)]);
      if (cfg.show_levels && Object.entries(e).some(([k, id]) => k.startsWith("level_") && this._state(id))) {
        defs.push([`levels-${id}`, "btn_levels", "tune-variant", () => this._levelsHtml(a, e)]);
      }
      if (cfg.show_details) defs.push([`details-${id}`, "details", "information-outline", () => this._detailsHtml(a, e)]);
      const lock = e.child_lock ? this._state(e.child_lock) : null;
      if (!defs.length && !lock && !a.override) return null;
      const open = (k) => !!this._open[k] || (k === `sched-${id}` && this._editing === id);
      const locked = lock?.state === "on";
      // While there is a manual change: back to automatic, first in the row.
      const back = a.override
        ? `<button class="sbtn back" data-action="clear" data-room="${esc(id)}" title="${esc(this._t("clear_override"))}">${this._icon(
            "autorenew"
          )}<span>${esc(this._t("auto_short"))}</span></button>`
        : "";
      const buttons =
        back +
        defs
          .map(
            ([k, label, icon]) => `<button class="sbtn ${open(k) ? "on" : ""}" data-action="fold" data-key="${esc(k)}"
            aria-expanded="${open(k)}">${this._icon(icon)}<span>${esc(this._t(label))}</span></button>`
          )
          .join("") +
        (lock
          ? `<button class="sbtn lock ${locked ? "on" : ""}" data-action="toggle" data-entity="${esc(e.child_lock)}" role="switch"
            aria-checked="${locked}" title="${esc(this._t("child_lock"))}">${this._icon(
              locked ? "lock-outline" : "lock-open-variant-outline"
            )}<span>${esc(this._t("lock_short"))}</span></button>`
          : "");
      const count = defs.length + (lock ? 1 : 0) + (a.override ? 1 : 0);
      // The chart is not drawn here: it opens in a window (``_chartPopup``).
      const bodies = defs
        .filter(([k]) => open(k) && !k.startsWith("chart-"))
        .map(([, , , html]) => html())
        .join("");
      // Up to 3 per row; 4 as two rows of 2 (no button left alone on a row).
      const cols = count <= 3 ? count : count === 4 ? 2 : 3;
      return { buttons: `<div class="sbtns" style="--cols:${cols}">${buttons}</div>`, bodies };
    }

    /** The colour of the level of a room (its name, arc and marks). */
    _roomColor(a) {
      return PRESET_COLORS[a.preset] || "var(--secondary-text-color)";
    }

    /** Room block (or one compact tile / folded row); the sections are shown when it is open. */
    _roomHtml(stateObj) {
      const cfg = this._config;
      const a = stateObj.attributes;
      const e = a.entities || {};
      const key = a.room_id;
      const folded =
        this._open[`room-${key}`] === undefined ? cfg.collapsed || cfg.compact : !this._open[`room-${key}`];
      const color = this._roomColor(a);
      if (cfg.compact && folded) return this._compactRow(stateObj, color);
      if (folded) return this._foldedRow(stateObj, color);
      const { head, hero, overrideMsg } = this._roomTop(stateObj);
      // The buttons (and the sections they open) right under the arc, before the day bar and the chart.
      const parts = [
        head,
        hero,
        overrideMsg,
        this._noHeatHtml(a),
        this._alertsHtml(a),
        this._sectionsHtml(a, e, stateObj),
        this._todayHtml(a),
      ];
      return `<section class="block room open ${this._alertLevel(a)}" style="--c:${color}">${parts.join("")}</section>`;
    }

    /** The title row of an open room (name, reason, badges), its arc with the chips, and its manual change. */
    _roomTop(stateObj) {
      const a = stateObj.attributes;
      const e = a.entities || {};
      const key = a.room_id;
      const badges = [];
      let overrideMsg = "";
      // "Heating" (pulsing) while the heat source runs for the room; "Asks for heat" while it waits.
      if (a.heat_demand) badges.push(this._flame(!!a.heating, e.heat_demand));
      const alertIcon = this._alertIcon(a);
      if (alertIcon) badges.push(alertIcon);
      if (a.window_open)
        badges.push(`<span class="pill warn link" ${this._more(e.window_open)}>${this._icon("window-open-variant")}${this._t("window")}</span>`);
      const mold = (a.alerts || []).find((x) => x.code === "mold_risk");
      if (mold) {
        badges.push(
          `<span class="pill warn" title="${esc(this._alertText(mold))}">${this._icon("water-alert-outline")}${esc(
            this._t("humidity_risk")
          )}</span>`
        );
      }
      if (a.override) {
        const until = this._overrideUntil(a);
        const src = a.override.source_device;
        const origin =
          a.override.origin === "room" && src
            ? ` · ${this._t("origin_room").replace("{device}", this._hass?.states?.[src]?.attributes?.friendly_name || src)}`
            : a.override.origin
              ? ` · ${this._t(`origin_${a.override.origin}`)}`
              : "";
        // While a higher rule wins: not sent yet, or set again once it ends.
        // (The maximum temperature limits the manual value for good.)
        const blocked = !["manual_override", "maximum_temperature"].includes(stateObj.state);
        const back = !blocked
          ? ""
          : a.override.applied === false
            ? ` · ${this._t("applied_after").replace("{rule}", this._label(stateObj))}`
            : a.override.interrupted
              ? ` · ${this._t("back_after").replace("{rule}", this._label(stateObj))}`
              : "";
        overrideMsg = this._msg({
          kind: "plain override",
          icon: "hand-back-right-outline",
          lead: this._t("override"),
          text: `${until}${origin}${back}`,
          link: e.manual_override,
        });
      }

      const head = `
        <div class="room-head">
          <div class="rh-left">
            <button class="room-title" data-action="fold" data-key="room-${esc(key)}" aria-expanded="true">
              <span class="chev open"></span><span class="name">${esc(a.room_name)}</span>
            </button>
          </div>
          <span class="pill rule link" ${this._more(e.decision)}><span class="dot"></span>${esc(
            a.preset ? `${this._presetName(a, a.preset)} · ${this._label(stateObj)}` : this._label(stateObj)
          )}</span>
          ${badges.length ? `<div class="decision">${badges.join("")}</div>` : ""}
        </div>`;
      const hero = `<div class="hero">${this._gauge(a, e, 168)}<div class="chips">${this._chipsHtml(
        a,
        e,
        stateObj,
        this._eta(a)
      )}</div></div>`;

      return { head, hero, overrideMsg };
    }

    /** The level the room is at (its colour and name); a temperature without a level shows only the value. */
    _presetPill(a, withTarget = false) {
      const target = withTarget ? ` ${this._temp(a.target_temperature)}` : "";
      if (!a.preset) return withTarget ? `<span class="pill preset">${this._temp(a.target_temperature)}</span>` : "";
      return `<span class="pill preset"><span class="dot"></span>${esc(this._presetName(a, a.preset))}${target}</span>`;
    }

    /** A room shows power off only when every configured thermostat confirms it. */
    _thermostatsOff(a) {
      const ids = a.climate_entities || [];
      return a.source === "climate" && ids.length > 0 && ids.every((id) => this._state(id)?.state === "off");
    }

    _roomHeatIcon(a, small = false) {
      if (this._thermostatsOff(a)) {
        const label = esc(this._t("thermostat_off"));
        return `<span class="${small ? "cicon" : "tstat"} thermostat-off" role="img" title="${label}" aria-label="${label}">${this._icon("power")}</span>`;
      }
      return a.heat_demand ? this._flame(!!a.heating, null, small) : "";
    }

    /** Small icons of a folded room: heating, window open, manual change. */
    _statusIcons(a) {
      const icons = [this._roomHeatIcon(a, true)];
      if ((a.alerts || []).length) icons.push(this._alertIcon(a, true));
      if (a.window_open) icons.push(`<span class="cicon warn" title="${esc(this._t("window"))}">${this._icon("window-open-variant")}</span>`);
      icons.push(this._moldIcon(a, "cicon"));
      if (a.override) icons.push(`<span class="cicon" title="${esc(`${this._t("override")} ${this._overrideUntil(a)}`)}">${this._icon("hand-back-right-outline")}</span>`);
      if (this._guestOn(a)) icons.push(`<span class="cicon teal" title="${esc(this._t("guests_banner"))}">${this._icon("account-group-outline")}</span>`);
      return icons.join("");
    }

    /** True while the guest mode of the room's house is on. */
    _guestOn(a) {
      return this._state(a.house_entities?.guest_mode)?.state === "on";
    }
  };
