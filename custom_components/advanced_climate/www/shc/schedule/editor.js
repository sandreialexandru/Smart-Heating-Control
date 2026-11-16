// The schedule of a room and its editor: bars, handles, profiles, copying.

import { PRESET_COLORS } from "../core/constants.js";
import { esc, hhmm, toMinutes } from "../core/format.js";
import { WEEKDAY_KEYS, guessDays, uncoveredDays } from "./profiles.js";

export const ScheduleMixin = (Base) =>
  class extends Base {
    /** Help text of the schedule and whether it decides the room right now. */
    _scheduleIntro(a, stateObj) {
      const scheduleRules = ["schedule", "optimal_start", "optimal_stop"];
      const now = scheduleRules.includes(stateObj.state)
        ? `<p class="hint ok">${this._t("schedule_active")}</p>`
        : `<p class="hint warn">${this._t("schedule_not_active").replace("{rule}", esc(this._label(stateObj)))}</p>`;
      return `<p class="hint">${this._t("schedule_help")}</p>${now}`;
    }

    /** Schedule of the room: day bars, and the editor while editing. */
    _scheduleHtml(a, stateObj) {
      if (!a.schedule_editable) {
        return this._fold(`sched-${a.room_id}`, this._t("schedule"), `<p class="hint">${this._t("not_editable")}</p>`);
      }
      const intro = this._scheduleIntro(a, stateObj);
      const meta = a.profile_days || {};
      if (this._editing !== a.room_id) {
        const gap = this._gapText(uncoveredDays(meta));
        const pending = this._pendingProfile && this._pendingProfile.room === a.room_id ? this._pendingProfile : null;
        const notice = pending
          ? `<div class="confirmbox"><span>${esc(this._t("gap_confirm").replace("{days}", this._gapText(uncoveredDays(pending.days))))}</span>
              ${this._btn(this._t("confirm"), `data-action="profile-confirm" data-room="${esc(a.room_id)}"`, { kind: "soft-warn" })}
              ${this._btn(this._t("cancel"), `data-action="profile-cancel"`, {})}</div>`
          : gap
            ? `<p class="hint warn">${esc(this._t("gap_warning").replace("{days}", gap))}</p>`
            : "";
        const profiles = Object.entries(a.schedule || {})
          .map(([name, slots]) => {
            const rows = this._intervals(slots)
              .map(
                (it) => `<li><span class="dot" style="--c:${PRESET_COLORS[it.preset]}"></span>
                  <span class="range">${esc(it.from)} – ${esc(it.to)}${
                  it.nextDay ? ` <small>${this._t("next_day")}</small>` : ""
                }</span><span class="pname">${esc(this._presetName(a, it.preset))}</span></li>`
              )
              .join("");
            const on = !!(meta[name] && meta[name].enabled);
            return `<div class="profile ${a.profile === name ? "today" : ""} ${on ? "" : "off"}">
                <div class="phead"><b>${esc(name)}</b>${
              a.profile === name ? `<span class="pill">${this._t("today")}</span>` : ""
            }<span class="muted">${esc(this._profileDays(meta[name]))}</span>${this._profileSwitch(a.room_id, name, on, "profile-toggle")}</div>
                <div class="sbar ro">${this._barInner(a, name, slots, false)}</div>
                <ul class="intervals">${rows}</ul></div>`;
          })
          .join("");
        return this._fold(
          `sched-${a.room_id}`,
          this._t("schedule"),
          `${intro}${notice}<div class="profiles">${profiles}</div>
           <div class="row">${this._btn(this._t("edit"), `data-action="edit" data-room="${esc(a.room_id)}"`, {
             icon: "pencil",
             kind: "primary",
           })}</div>`
        );
      }
      const presets = a.presets || Object.keys(PRESET_COLORS);
      const option = (preset, current) =>
        `<option value="${esc(preset)}" ${preset === current ? "selected" : ""}>${esc(
          this._presetName(a, preset)
        )}</option>`;
      const blocks = Object.entries(this._draft || {})
        .map(([name, slots]) => {
          const intervals = this._intervals(slots);
          const sorted = [...slots]
            .map((slot, i) => ({ slot, i }))
            .sort((x, y) => toMinutes(x.slot.time) - toMinutes(y.slot.time));
          const rows = sorted
            .map(({ slot, i }, pos) => {
              const it = intervals[pos];
              return `<div class="slot-row">
                <span class="dot" style="--c:${PRESET_COLORS[slot.preset]}"></span>
                <input type="time" step="300" data-profile="${esc(name)}" data-index="${i}" data-field="time" value="${esc(slot.time)}"
                  aria-label="${this._t("starts")}">
                <span class="until">→ ${esc(it.to)}${it.nextDay ? ` <small>${this._t("next_day")}</small>` : ""}</span>
                <select data-profile="${esc(name)}" data-index="${i}" data-field="preset">${presets
                  .map((p) => option(p, slot.preset))
                  .join("")}</select>
                <button class="btn icon-only" data-action="del-slot" data-profile="${esc(name)}" data-index="${i}"
                  aria-label="${this._t("remove")}" title="${this._t("remove")}">${this._icon("delete-outline")}<span class="x">✕</span></button>
              </div>`;
            })
            .join("");
          const dm = (this._draftDays || {})[name] || { days: guessDays(name), enabled: false };
          const kind = Array.isArray(dm.days) ? "days" : dm.days;
          const daysSelect = `<label class="selectfield"><span>${this._t("days_label")}</span><select data-days="${esc(name)}">${[
            "all",
            "workday",
            "weekend",
            "days",
          ]
            .map((k) => `<option value="${k}" ${k === kind ? "selected" : ""}>${esc(this._t(`days_opt_${k}`))}</option>`)
            .join("")}</select></label>`;
          const dayChecks = Array.isArray(dm.days)
            ? `<div class="daychecks">${WEEKDAY_KEYS.map(
                (d, i) => `<label><input type="checkbox" data-dayof="${esc(name)}" data-day="${d}" ${
                  dm.days.includes(d) ? "checked" : ""
                }>${esc(this._weekdayName(i, "short"))}</label>`
              ).join("")}</div>`
            : "";
          return `<div class="profile edit ${dm.enabled ? "" : "off"}">
              <div class="phead"><b>${esc(name)}</b>${this._profileSwitch(a.room_id, name, !!dm.enabled, "draft-toggle")}
                ${this._copySelect(name)}
                ${this._btn(this._t("remove_profile"), `data-action="del-profile" data-profile="${esc(name)}"`, {
                  icon: "delete-outline",
                  kind: "danger",
                })}</div>
              <div class="row wrap">${daysSelect}${dayChecks}</div>
              <div class="sbar" data-bar="${esc(name)}">${this._barInner(a, name, slots, true)}</div>
              <div class="bar-ticks"><span>00:00</span><span>06:00</span><span>12:00</span><span>18:00</span><span>24:00</span></div>
              <div class="slot-head"><span></span><span>${this._t("starts")}</span><span>${this._t("ends")}</span><span>${this._t(
                "level"
              )}</span><span></span></div>
              ${rows}
              ${this._btn(this._t("add_slot"), `data-action="add-slot" data-profile="${esc(name)}"`, { icon: "plus" })}
            </div>`;
        })
        .join("");
      return `<div class="editor">
          <div class="ehead"><b>${this._t("schedule")}</b></div>
          ${intro}
          <p class="hint">${this._t("drag_hint")}</p>
          ${(() => {
            const gap = this._gapText(uncoveredDays(this._draftDays));
            return gap ? `<p class="hint warn">${esc(this._t("gap_warning").replace("{days}", gap))}</p>` : "";
          })()}
          ${blocks}
          <div class="row wrap">
            <label class="textfield"><span>${this._t("profile_name")}</span>
              <input type="text" class="newprofile" placeholder="home_office"></label>
            ${this._btn(this._t("add_profile"), `data-action="add-profile"`, { icon: "plus" })}
          </div>
          ${this._error[`sched-${a.room_id}`] ? `<p class="error">${esc(this._error[`sched-${a.room_id}`])}</p>` : ""}
          <div class="row wrap end">
            ${this._btn(this._t("cancel"), `data-action="cancel"`, {})}
            ${this._btn(this._t("save"), `data-action="save" data-room="${esc(a.room_id)}"`, {
              icon: "content-save",
              kind: "primary",
            })}
          </div>
        </div>`;
    }

    /** Day bar of a profile; in the editor every start time has a handle that can be dragged. */
    _barInner(a, name, slots, editable) {
      if (!slots || !slots.length) return "";
      const segs = this._segments(slots)
        .map((sg) => {
          const w = ((sg.end - sg.start) / 1440) * 100;
          const label = w >= 14 ? esc(this._presetName(a, sg.preset)) : "";
          return `<div class="sseg" style="left:${(sg.start / 1440) * 100}%;width:${w}%;--c:${
            PRESET_COLORS[sg.preset] || "var(--ac-accent)"
          }" title="${esc(this._presetName(a, sg.preset))} ${hhmm(sg.start)}–${hhmm(sg.end % 1440)}"><span>${label}</span></div>`;
        })
        .join("");
      if (!editable) return segs;
      const handles = slots
        .map((slot, i) => {
          const m = toMinutes(slot.time);
          const dragging = this._drag && this._drag.profile === name && this._drag.index === i;
          return `<div class="handle ${dragging ? "dragging" : ""}" style="left:${(m / 1440) * 100}%" tabindex="0" role="slider"
              aria-label="${esc(this._t("starts"))} ${esc(this._presetName(a, slot.preset))}" aria-valuemin="0" aria-valuemax="1439"
              aria-valuenow="${m}" aria-valuetext="${esc(slot.time)}" data-handle="1" data-profile="${esc(name)}" data-index="${i}">
              <span class="htime">${esc(slot.time)}</span></div>`;
        })
        .join("");
      return segs + handles;
    }

    /** "Copy over…" select of the schedule editor. */
    _copySelect(name) {
      const existing = Object.keys(this._draft || {});
      const targets = [...existing, ...["workday", "weekend", ...WEEKDAY_KEYS].filter((p) => !existing.includes(p))]
        .filter((p) => p !== name);
      const label = (p) => {
        const day = WEEKDAY_KEYS.indexOf(p);
        const suffix = day >= 0 ? ` (${this._weekdayName(day)})` : "";
        return `${p}${suffix}${existing.includes(p) ? "" : ` – ${this._t("new_profile")}`}`;
      };
      return `<select class="copysel" data-copy="${esc(name)}" aria-label="${esc(this._t("copy_to"))}">
          <option value="">${esc(this._t("copy_to"))}</option>
          ${targets.map((p) => `<option value="${esc(p)}">${esc(label(p))}</option>`).join("")}
        </select>`;
    }

    /** Limits of a handle: it stays between its neighbours (5 minutes apart). */
    _handleLimits(slots, index) {
      const order = slots
        .map((slot, i) => ({ i, m: toMinutes(slot.time) }))
        .sort((x, y) => x.m - y.m);
      const pos = order.findIndex((o) => o.i === index);
      const min = pos > 0 ? order[pos - 1].m + 5 : 0;
      const max = pos + 1 < order.length ? order[pos + 1].m - 5 : 1435;
      return [min, max];
    }

    /** Move a slot start of the draft; False when nothing changed. */
    _moveHandle(profile, index, minutes) {
      const slots = this._draft?.[profile];
      if (!slots || !slots[index]) return false;
      const [min, max] = this._handleLimits(slots, index);
      const value = Math.min(max, Math.max(min, minutes));
      if (hhmm(value) === slots[index].time) return false;
      slots[index].time = hhmm(value);
      return true;
    }
  };
