// Clicks, changes, keys and pointers: one listener each on the shadow root, for the card and the panel.

import { RUNTIME_PERIODS } from "./constants.js";
import { esc, hhmm, num, toMinutes } from "./format.js";
import { WEEKDAY_KEYS, guessDays, switchProfile, uncoveredDays } from "../schedule/profiles.js";

export const EventsMixin = (Base) =>
  class extends Base {
    /** Pointer pressed: chart pan, or dragging a handle of the schedule editor. */
    _pointerDown(ev) {
      // A finger on a chart shows its navigation bar (a mouse shows it on hover).
      const chartCard = ev.target.closest?.(".chart-card");
      if (chartCard && ev.pointerType !== "mouse") this._touch(chartCard, true);
      if (this._navPointerDown(ev)) {
        this._nav?.card?.classList.add("navigating");
        return;
      }
      if (this._chartPointerDown(ev)) return;
      const handle = ev.target.closest?.("[data-handle]");
      if (!handle || !this._draft) return;
      ev.preventDefault();
      const bar = handle.closest(".sbar");
      this._drag = { profile: handle.dataset.profile, index: Number(handle.dataset.index), bar };
      try {
        bar.setPointerCapture(ev.pointerId);
      } catch (err) {
        /* ignore */
      }
      handle.classList.add("dragging");
    }

    /** Pointer moved: chart pan / hover, or moving a schedule handle (5 minutes). */
    _pointerMove(ev) {
      if (this._navPointerMove(ev)) return;
      if (!this._drag) {
        if (this._chartPointerMove(ev)) {
          const tip = this._pan?.card?.querySelector(".tip");
          if (tip) tip.hidden = true;
          return;
        }
        const chart = ev.target.closest?.(".hchart") || this._pan?.card?.querySelector(".hchart");
        if (chart) this._chartHover({ type: ev.type, clientX: ev.clientX, target: chart });
        return;
      }
      const { profile, index, bar } = this._drag;
      const rect = bar.getBoundingClientRect();
      const f = Math.min(1, Math.max(0, (ev.clientX - rect.left) / rect.width));
      const minutes = Math.round((f * 1440) / 5) * 5;
      if (this._moveHandle(profile, index, minutes)) {
        const stateObj = this._rooms().find((s) => s.attributes.room_id === this._editing);
        bar.innerHTML = this._barInner(stateObj?.attributes || {}, profile, this._draft[profile], true);
      }
    }

    /** Pointer released: end the pan or the drag. */
    _pointerUp(ev) {
      const card = this._nav?.card || this._pan?.card;
      if (card && ev && ev.pointerType !== "mouse") this._touch(card, false);
      if (this._nav && (!ev || ev.pointerId === this._nav.pointer)) {
        this._nav.card?.classList.remove("navigating");
        this._nav = null;
        return;
      }
      if (ev) this._chartPointerUp(ev);
      if (!this._drag) return;
      this._drag = null;
      this._render();
    }

    /** Arrow keys move the focused schedule handle (Shift: one hour). */
    _keyDown(ev) {
      if ((ev.key === "Enter" || ev.key === " ") && ev.target?.dataset?.action === "more") {
        ev.preventDefault();
        this._onClick(ev);
        return;
      }
      const handle = ev.target.closest?.("[data-handle]");
      if (!handle || !["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(ev.key)) return;
      ev.preventDefault();
      const { profile } = handle.dataset;
      const index = Number(handle.dataset.index);
      const step = (ev.shiftKey ? 60 : 5) * (["ArrowLeft", "ArrowDown"].includes(ev.key) ? -1 : 1);
      const current = toMinutes(this._draft[profile][index].time);
      if (this._moveHandle(profile, index, current + step)) {
        this._render();
        this.shadowRoot
          .querySelector(`[data-handle][data-profile="${CSS.escape(profile)}"][data-index="${index}"]`)
          ?.focus();
      }
    }

    /** Open the schedule editor of a room (a copy of its schedule to change). */
    _startEdit(room) {
      const stateObj = this._rooms().find((s) => s.attributes.room_id === room);
      if (!stateObj) return;
      this._editing = room;
      this._open[`sched-${room}`] = true;
      this._draft = JSON.parse(JSON.stringify(stateObj.attributes.schedule));
      this._draftDays = JSON.parse(JSON.stringify(stateObj.attributes.profile_days || {}));
      this._pendingProfile = null;
    }

    /** An open section of a room (its button opens and closes it). */
    _fold(key, title, content) {
      return `<div class="section" data-section="${esc(key)}"><div class="section-head">${esc(title)}</div>
        <div class="fold-body">${content}</div></div>`;
    }

    // ------------------------------------------------------------------ events
    _onToggle(ev) {
      const el = ev.target;
      if (el?.dataset?.fold) this._open[el.dataset.fold] = el.open;
    }

    /** Selects, numbers and the fields of the schedule editor. */
    async _onChange(ev) {
      const el = ev.target;
      const d = el.dataset || {};
      if (d.action === "select") {
        await this._call("select", "select_option", { entity_id: d.entity, option: el.value });
      } else if (d.action === "number") {
        const value = num(el.value);
        if (value !== null) await this._call("number", "set_value", { entity_id: d.entity, value });
      } else if (d.copy !== undefined && this._draft?.[d.copy]) {
        if (el.value) {
          if (!this._draft[el.value] && this._draftDays) {
            this._draftDays[el.value] = { days: guessDays(el.value), enabled: false };
          }
          this._draft[el.value] = JSON.parse(JSON.stringify(this._draft[d.copy]));
        }
        this._render();
      } else if (d.copyto !== undefined) {
        // A room chosen to take a copy of the schedule.
        this._copyTo = this._copyTo || new Set();
        if (el.checked) this._copyTo.add(d.copyto);
        else this._copyTo.delete(d.copyto);
        el.blur();
        this._render();
      } else if (d.days !== undefined && this._draftDays) {
        // Days of a profile; when it is on, the active profiles that now overlap it are turned off.
        const m = this._draftDays[d.days] || { days: "all", enabled: false };
        m.days = el.value === "days" ? (Array.isArray(m.days) ? m.days : ["mon"]) : el.value;
        this._draftDays[d.days] = m;
        if (m.enabled) this._draftDays = switchProfile(this._draftDays, d.days, true);
        this._render();
      } else if (d.dayof !== undefined && this._draftDays?.[d.dayof]) {
        const m = this._draftDays[d.dayof];
        const list = new Set(Array.isArray(m.days) ? m.days : []);
        if (el.checked) list.add(d.day);
        else if (list.size > 1) list.delete(d.day);
        m.days = WEEKDAY_KEYS.filter((x) => list.has(x));
        if (m.enabled) this._draftDays = switchProfile(this._draftDays, d.dayof, true);
        this._render();
      } else if (d.field && this._draft?.[d.profile]) {
        this._draft[d.profile][Number(d.index)][d.field] = el.value;
        if (d.field === "time") {
          // A time being typed changes with every digit: drawing the editor again
          // would take the field away after the first one. Only the bar follows
          // now; the rows (sorted by time) are drawn again when the field is left.
          const bar = this.shadowRoot.querySelector(`.sbar[data-bar="${CSS.escape(d.profile)}"]`);
          if (bar) {
            const stateObj = this._rooms().find((st) => st.attributes.room_id === this._editing);
            bar.innerHTML = this._barInner(stateObj?.attributes || {}, d.profile, this._draft[d.profile], true);
          }
          if (!el.__redrawOnBlur) {
            el.__redrawOnBlur = true;
            el.addEventListener("blur", (e) => this._redrawAfterTyping(e), { once: true });
          }
          return;
        }
        this._render();
      }
    }

    /**
     * The schedule editor after a time was typed: drawn again (rows sorted by
     * time) once the click that took the focus away is over, so that click (Save,
     * a button of the editor) still reaches its button.
     */
    _redrawAfterTyping(ev) {
      const next = ev.relatedTarget;
      // A button of the card got the focus: its own action draws the editor.
      if (next && this.shadowRoot.contains(next) && next.closest?.("[data-action]")) return;
      const draw = () => {
        const active = this.shadowRoot.activeElement;
        if (active && ["INPUT", "SELECT"].includes(active.tagName)) return; // typing elsewhere
        this._render();
      };
      if (this._pressing) window.addEventListener("pointerup", () => setTimeout(draw, 0), { once: true });
      else draw();
    }

    /** Every button of the card (data-action). */
    async _onClick(ev) {
      // A click on the dark area around the chart window closes it (not one on
      // the window itself, its padding included).
      if (ev.target?.tagName === "DIALOG" && ev.target.classList.contains("chartpop")) {
        const r = ev.target.getBoundingClientRect();
        const inside =
          ev.clientX >= r.left && ev.clientX <= r.right && ev.clientY >= r.top && ev.clientY <= r.bottom;
        if (!inside) {
          this._closeChart();
          return;
        }
      }
      const el = ev.target.closest("[data-action]");
      if (!el || el.tagName === "SELECT" || el.tagName === "INPUT") return;
      const { action, room, profile, index, entity, option, key, house } = el.dataset;
      if (action === "more") {
        this.dispatchEvent(
          new CustomEvent("hass-more-info", { detail: { entityId: entity }, bubbles: true, composed: true })
        );
        return;
      }
      switch (action) {
        case "fold":
          this._open[key] = el.getAttribute("aria-expanded") !== "true";
          // One chart window at a time.
          if (key.startsWith("chart-") && this._open[key]) {
            for (const k of Object.keys(this._open)) if (k !== key && k.startsWith("chart-")) this._open[k] = false;
          }
          break;
        case "closechart":
          this._closeChart();
          return;
        case "period": {
          const next = RUNTIME_PERIODS[(RUNTIME_PERIODS.indexOf(this._period()) + 1) % RUNTIME_PERIODS.length];
          this._runtimePeriod = next;
          break;
        }
        case "zoom": {
          const d = this._charts?.[room];
          if (!d) return;
          const z = el.dataset.zoom;
          if (z === "in") this._zoom(room, 0.5);
          else if (z === "out") this._zoom(room, 2);
          else if (z === "reset") {
            const def = this._defaultView(d);
            this._setView(room, def.v0, def.v1);
          }
          else {
            const span = (z === "1h" ? 1 : 6) * 3600000;
            const end = Math.min(d.t1, Math.max(d.now + span * 0.15, d.t0 + span));
            this._setView(room, end - span, end);
          }
          return;
        }
        case "toggle":
          await this._call(entity.split(".")[0], "toggle", { entity_id: entity });
          return;
        case "mode":
          await this._call("select", "select_option", { entity_id: entity, option });
          return;
        case "press":
          await this._call("button", "press", { entity_id: entity });
          return;
        case "reset-learning":
          // Two clicks: the first asks to confirm (for a few seconds), the second resets.
          clearTimeout(this._confirmTimer);
          if (this._confirmReset !== entity) {
            this._confirmReset = entity;
            this._confirmTimer = setTimeout(() => {
              this._confirmReset = null;
              this._render();
            }, 4000);
            break;
          }
          this._confirmReset = null;
          await this._call("button", "press", { entity_id: entity });
          break;
        case "vacation": {
          const h = this._houses().find((x) => x.id === house);
          if (!h) return;
          const start = this.shadowRoot.querySelector(`input[data-vac="start"][data-house="${CSS.escape(house)}"]`);
          const end = this.shadowRoot.querySelector(`input[data-vac="end"][data-house="${CSS.escape(house)}"]`);
          const data = { config_entry_id: house };
          if (start?.value) data.start = this._fromInput(start.value);
          if (end?.value) data.end = this._fromInput(end.value);
          await this._call("advanced_climate", "set_vacation", data, `vac-${house}`);
          break;
        }
        case "clear":
          await this._call("advanced_climate", "clear_override", { room });
          return;
        case "series":
          this._toggleSeries(el.dataset.series);
          this._redrawChart(room);
          return;
        case "quick-preset": {
          const { data } = this._quickValues(room);
          await this._call("advanced_climate", "set_override", { room, preset: el.dataset.preset, ...data });
          this._quickDone(room);
          return;
        }
        case "quick-temp": {
          const { temp, data } = this._quickValues(room);
          if (temp !== null) {
            await this._call("advanced_climate", "set_override", { room, temperature: temp, ...data });
            this._quickDone(room);
            return;
          }
          // Only the hours: the manual change now lasts that long from now
          // (with what it holds: its level, else its temperature).
          const held = this._rooms().find((s) => s.attributes.room_id === room)?.attributes?.override;
          const keep = held?.preset ? { preset: held.preset } : num(held?.temperature) !== null ? { temperature: num(held.temperature) } : null;
          if (data.duration_hours === undefined || !keep) {
            this._quickNote(room, data.duration_hours === undefined ? "quick_need_temp" : "quick_nothing_to_extend");
            return;
          }
          await this._call("advanced_climate", "set_override", { room, ...keep, ...data });
          this._quickDone(room);
          return;
        }
        case "edit":
          this._startEdit(room);
          break;
        case "cancel":
          this._editing = null;
          this._draft = null;
          this._draftDays = null;
          break;
        case "profile-toggle": {
          // On / off from the schedule: saved at once; days left without a profile ask first.
          const stateObj = this._rooms().find((s) => s.attributes.room_id === room);
          if (!stateObj) return;
          const meta = stateObj.attributes.profile_days || {};
          const on = !(meta[profile] && meta[profile].enabled);
          const days = switchProfile(meta, profile, on);
          const gap = uncoveredDays(days);
          const before = uncoveredDays(meta);
          const worse = gap.days.some((d) => !before.days.includes(d)) || (gap.free_days && !before.free_days) || (gap.workdays && !before.workdays);
          if (worse) {
            this._pendingProfile = { room, days };
            break;
          }
          this._pendingProfile = null;
          await this._call("advanced_climate", "set_schedule", { room, profiles: stateObj.attributes.schedule, profile_days: days }, `sched-${room}`);
          break;
        }
        case "profile-confirm": {
          const pending = this._pendingProfile;
          const stateObj = this._rooms().find((s) => s.attributes.room_id === room);
          this._pendingProfile = null;
          if (!pending || !stateObj) break;
          await this._call(
            "advanced_climate",
            "set_schedule",
            { room, profiles: stateObj.attributes.schedule, profile_days: pending.days },
            `sched-${room}`
          );
          break;
        }
        case "profile-cancel":
          this._pendingProfile = null;
          break;
        case "draft-toggle": {
          if (!this._draftDays) return;
          const on = !(this._draftDays[profile] && this._draftDays[profile].enabled);
          this._draftDays = switchProfile(this._draftDays, profile, on);
          break;
        }
        case "add-slot": {
          // An hour after the last slot, else the first free time after it, else
          // the first free time of the day (5-minute steps); nothing when the day is full.
          const slots = this._draft[profile];
          const taken = new Set(slots.map((x) => toMinutes(x.time)));
          const lastTime = slots.length ? Math.max(...taken) : 0;
          const candidates = [];
          for (let m = Math.min(lastTime + 60, 1435); m <= 1435; m += 5) candidates.push(m);
          for (let m = 0; m <= 1435; m += 5) candidates.push(m);
          const free = candidates.find((m) => !taken.has(m));
          if (free === undefined) return;
          slots.push({ time: hhmm(free), preset: "home" });
          break;
        }
        case "del-slot":
          this._draft[profile].splice(Number(index), 1);
          if (!this._draft[profile].length) delete this._draft[profile];
          break;
        case "del-profile":
          delete this._draft[profile];
          if (this._draftDays) delete this._draftDays[profile];
          break;
        case "add-profile": {
          const input = this.shadowRoot.querySelector(".newprofile");
          // Only what the integration accepts in a profile name: letters, digits,
          // spaces (made "_"), "_" and "-"; it starts with a letter or a digit.
          const name = (input?.value || "")
            .trim()
            .toLowerCase()
            .replace(/[^\p{L}\p{N} _-]/gu, "")
            .replace(/\s+/g, "_")
            .replace(/^[_-]+/, "");
          if (name && !this._draft[name]) {
            this._draft[name] = [{ time: "00:00", preset: "home" }];
            if (this._draftDays) this._draftDays[name] = { days: guessDays(name), enabled: false };
          }
          break;
        }
        case "copy-open":
          this._copyFrom = room;
          this._copyTo = new Set();
          this._copyDone = null;
          break;
        case "copy-cancel":
          this._copyFrom = null;
          this._copyTo = null;
          break;
        case "copy-run":
          await this._copySchedule(room);
          break;
        case "save": {
          const ok = await this._call(
            "advanced_climate",
            "set_schedule",
            {
              room,
              profiles: this._draft,
              profile_days: Object.fromEntries(
                Object.keys(this._draft).map((name) => [
                  name,
                  (this._draftDays || {})[name] || { days: guessDays(name), enabled: false },
                ])
              ),
            },
            `sched-${room}`
          );
          if (ok) {
            this._editing = null;
            this._draft = null;
            this._draftDays = null;
          }
          break;
        }
        default:
          return;
      }
      this._lastKey = "";
      this._render();
    }
  };
