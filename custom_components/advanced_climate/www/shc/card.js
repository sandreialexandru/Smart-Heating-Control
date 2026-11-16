/*
 * Smart Heating Control card – every option of the integration in one card.
 *
 *   type: custom:smart-heating-control-card
 *   title: Heating               # optional
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

import { ChartMixin } from "./chart/chart.js";
import { ChartDataMixin, thinPoints } from "./chart/data.js";
import { ChartInteractMixin } from "./chart/interact.js";
import { DEFAULTS, RUNTIME_PERIODS } from "./core/constants.js";
import { FormatMixin, esc, hhmm, num, toMinutes } from "./core/format.js";
import { HaMixin } from "./core/ha.js";
import { TEXT } from "./core/i18n.js";
import { IconMixin } from "./core/icons.js";
import { STYLE } from "./core/style.js";
import { HouseMixin } from "./house/house.js";
import { AlertsMixin } from "./room/alerts.js";
import { CompactMixin } from "./room/compact.js";
import { DetailsMixin } from "./room/details.js";
import { GaugeMixin } from "./room/gauge.js";
import { QuickMixin } from "./room/quick.js";
import { ReasonMixin } from "./room/reason.js";
import { RoomMixin } from "./room/room.js";
import { ScheduleMixin } from "./schedule/editor.js";
import { ProfilesMixin, WEEKDAY_KEYS, guessDays, switchProfile, uncoveredDays } from "./schedule/profiles.js";

const CARD_VERSION = "2.6.5";

class SmartHeatingControlCard extends HouseMixin(CompactMixin(RoomMixin(AlertsMixin(DetailsMixin(QuickMixin(ReasonMixin(GaugeMixin(ScheduleMixin(ProfilesMixin(ChartInteractMixin(ChartMixin(ChartDataMixin(HaMixin(IconMixin(FormatMixin(HTMLElement)))))))))))))))) {
  /** Event listeners are set once on the shadow root; the content is redrawn by _render. */
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._editing = null;
    this._draft = null;
    this._open = {};
    this._lastKey = "";
    this._error = {};
    this.shadowRoot.addEventListener("click", (ev) => this._onClick(ev));
    this.shadowRoot.addEventListener("change", (ev) => this._onChange(ev));
    // Whether a mouse button or a finger is down (see _redrawAfterTyping).
    this._pressing = false;
    this.shadowRoot.addEventListener("pointerdown", () => (this._pressing = true), true);
    // On the window (a finger let go outside the card counts too); added while
    // the card is on the page (connectedCallback), so a removed card is freed.
    this._onWindowUp = (ev) => {
      this._pressing = false;
      // A pan let go outside the card (e.g. outside the window) still ends,
      // else the card would stop following Home Assistant.
      if ((this._pan || this._nav) && !ev.composedPath().includes(this)) this._pointerUp(ev);
    };
    this.shadowRoot.addEventListener("toggle", (ev) => this._onToggle(ev), true);
    this.shadowRoot.addEventListener("pointerdown", (ev) => this._pointerDown(ev));
    this.shadowRoot.addEventListener("pointermove", (ev) => this._pointerMove(ev));
    this.shadowRoot.addEventListener("pointerup", (ev) => this._pointerUp(ev));
    this.shadowRoot.addEventListener("pointercancel", (ev) => this._pointerUp(ev));
    this.shadowRoot.addEventListener("wheel", (ev) => this._chartWheel(ev), { passive: false });
    this.shadowRoot.addEventListener("dblclick", (ev) => this._chartDblClick(ev));
    this.shadowRoot.addEventListener("pointerleave", (ev) => this._chartHover(ev), true);
    this.shadowRoot.addEventListener("keydown", (ev) => this._keyDown(ev));
  }

  /** The animations (flame, pulse) stop while the card is not on the screen. */
  connectedCallback() {
    window.addEventListener("pointerup", this._onWindowUp, true);
    window.addEventListener("pointercancel", this._onWindowUp, true);
    if (!this._io && "IntersectionObserver" in window) {
      this._io = new IntersectionObserver((entries) => {
        for (const entry of entries) this.toggleAttribute("offscreen", !entry.isIntersecting);
      });
    }
    this._io?.observe(this);
    clearTimeout(this._leaveTimer);
    // A moved card: its open chart window becomes modal again at once.
    if (this._hass && this._card && this.shadowRoot.querySelector("dialog.chartpop")) this._render();
  }

  disconnectedCallback() {
    this._io?.disconnect();
    window.removeEventListener("pointerup", this._onWindowUp, true);
    window.removeEventListener("pointercancel", this._onWindowUp, true);
    // Leaving the dashboard closes the chart window, so it does not pop up
    // again later. A card only moved (the columns laid out again, e.g. a phone
    // turned) is back at once and keeps it.
    clearTimeout(this._leaveTimer);
    this._leaveTimer = setTimeout(() => {
      if (this.isConnected) return;
      clearTimeout(this._touchTimer);
      this._touched = null;
      if (Object.keys(this._open || {}).some((k) => k.startsWith("chart-") && this._open[k])) this._closeChart();
    }, 1000);
  }

  /** Visual editor of the card (Home Assistant form). */
  static getConfigForm() {
    const lang = (document.querySelector("home-assistant")?.hass?.locale?.language || navigator.language || "en").slice(0, 2);
    const labels = EDITOR_LABELS[lang] || EDITOR_LABELS.en;
    const periods = EDITOR_PERIODS[lang] || EDITOR_PERIODS.en;
    return {
      schema: EDITOR_SCHEMA.map((field) =>
        field.name === "runtime_period"
          ? { ...field, selector: { select: { ...field.selector.select, options: field.selector.select.options.map((o) => ({ ...o, label: periods[o.value] || o.label })) } } }
          : field
      ),
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

  /** Called on every state change; redraws only when a watched entity changed. */
  set hass(hass) {
    this._hass = hass;
    this._housesMemo = null; // computed once per update
    // The scheme of the card background when known (a dark theme may not set darkMode).
    this.style.colorScheme = this._scheme || (hass?.themes?.darkMode ? "dark" : "light");
    if (this._editing || this._pan) return;
    const active = this.shadowRoot.activeElement;
    if (active && ["INPUT", "SELECT"].includes(active.tagName)) return;
    let timed = false;
    let key = this._watched()
      .map((id) => {
        const s = hass.states[id];
        if (s?.attributes?.override?.until) timed = true;
        return s ? `${id}:${s.state}:${s.last_updated}` : id;
      })
      .join("|");
    // A manual change shows the time it has left: drawn again every minute while there is one.
    const minute = timed ? `|${Math.floor(Date.now() / 60000)}` : "";
    key += minute;
    if (key !== this._lastKey) {
      this._lastKey = key;
      this._render(true);
    }
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

  /** 12 or 24 hour clock, as set in the profile of the user (Time format). */
  _hour12() {
    const format = this._hass?.locale?.time_format;
    if (format === "12") return true;
    if (format === "24") return false;
    // "language": the clock of the language; "system": the one of the browser.
    const locale = format === "system" ? undefined : this._lang();
    const cycle = new Intl.DateTimeFormat(locale, { hour: "numeric" }).resolvedOptions().hourCycle;
    return cycle === "h11" || cycle === "h12";
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
    const title = cfg.title ?? this._t("title");
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
    const dlg = this.shadowRoot.querySelector("dialog.chartpop");
    const modal = (d) => {
      try {
        return d.matches(":modal");
      } catch (_err) {
        return d.open; // a browser without :modal
      }
    };
    if (dlg && typeof dlg.showModal === "function" && !modal(dlg)) {
      if (!dlg.__cancel) {
        dlg.__cancel = true;
        dlg.addEventListener("cancel", (ev) => {
          ev.preventDefault();
          this._closeChart();
        });
      }
      if (dlg.open) dlg.close();
      dlg.showModal();
      this._opaque(dlg);
    }
  }

  /** The card element and the styles, made once. */
  _ensureCard() {
    if (this._card) return;
    const root = this.shadowRoot;
    if ("adoptedStyleSheets" in root && typeof CSSStyleSheet !== "undefined" && "replaceSync" in CSSStyleSheet.prototype) {
      const sheet = new CSSStyleSheet();
      sheet.replaceSync(STYLE);
      root.adoptedStyleSheets = [...root.adoptedStyleSheets, sheet];
    } else {
      const style = document.createElement("style");
      style.textContent = STYLE;
      root.appendChild(style);
    }
    this._card = document.createElement("ha-card");
    root.appendChild(this._card);
  }

  /** Put the blocks in ``parent``: a block drawn the same as before keeps its element. */
  _patch(parent, blocks) {
    const old = new Map();
    for (const node of parent.children) if (node.__k) old.set(node.__k, node);
    const make = (html) => {
      const tpl = document.createElement("template");
      tpl.innerHTML = html.trim();
      return tpl.content.firstElementChild;
    };
    const nodes = [];
    for (const b of blocks) {
      let node = old.get(b.k);
      if (!node || node.__src !== b.html) {
        node = make(b.html);
        if (!node) continue;
        node.__src = b.html;
        node.__k = b.k;
      }
      if (b.children) this._patch(node, b.children);
      nodes.push(node);
    }
    nodes.forEach((node, i) => {
      if (parent.children[i] !== node) parent.insertBefore(node, parent.children[i] || null);
    });
    while (parent.children.length > nodes.length) parent.lastElementChild.remove();
  }

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
      case "edit": {
        const stateObj = this._rooms().find((s) => s.attributes.room_id === room);
        this._editing = room;
        this._open[`sched-${room}`] = true;
        this._draft = JSON.parse(JSON.stringify(stateObj.attributes.schedule));
        this._draftDays = JSON.parse(JSON.stringify(stateObj.attributes.profile_days || {}));
        this._pendingProfile = null;
        break;
      }
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
}

// ---------------------------------------------------------------------- editor
const EDITOR_SCHEMA = [
  { name: "title", selector: { text: {} } },
  {
    name: "rooms",
    selector: { entity: { multiple: true, filter: { integration: "advanced_climate", domain: "sensor" } } },
  },
  {
    type: "grid",
    name: "",
    schema: [
      { name: "show_house", selector: { boolean: {} } },
      { name: "show_rooms", selector: { boolean: {} } },
      { name: "show_timeline", selector: { boolean: {} } },
      { name: "show_quick_override", selector: { boolean: {} } },
      { name: "show_levels", selector: { boolean: {} } },
      { name: "show_details", selector: { boolean: {} } },
      { name: "show_schedule_editor", selector: { boolean: {} } },
      { name: "collapsed", selector: { boolean: {} } },
      { name: "compact", selector: { boolean: {} } },
    ],
  },
  {
    name: "runtime_period",
    selector: {
      select: {
        mode: "dropdown",
        options: [
          { value: "day", label: "Day" },
          { value: "week", label: "Week" },
          { value: "month", label: "Month" },
        ],
      },
    },
  },
];

// The periods of the heating time in the editor, in the language of the user.
const EDITOR_PERIODS = {
  en: {"day": "Day", "week": "Week", "month": "Month"},
  ro: {"day": "Zi", "week": "Săptămână", "month": "Lună"},
  de: {"day": "Tag", "week": "Woche", "month": "Monat"},
  nl: {"day": "Dag", "week": "Week", "month": "Maand"},
  fr: {"day": "Jour", "week": "Semaine", "month": "Mois"},
  it: {"day": "Giorno", "week": "Settimana", "month": "Mese"},
};

const EDITOR_LABELS = {
  en: {
    title: "Title",
    rooms: "Rooms (Decision sensors; empty = all)",
    show_house: "House: presence, mode, pause, guests, vacation",
    show_rooms: "Rooms",
    show_timeline: "Chart: last 24 hours and the next 12",
    show_quick_override: "Set for a while",
    show_levels: "Level temperatures",
    show_details: "Details",
    show_schedule_editor: "Schedule editor",
    collapsed: "Rooms start folded",
    compact: "Compact: one tile per room, tap to open",
    runtime_period: "Heating time shown for (tap the value in the card to change it)",
  },
  ro: {
    title: "Titlu",
    rooms: "Camere (senzorii Decizie; gol = toate)",
    show_house: "Casa: prezență, mod, pauză, oaspeți, vacanță",
    show_rooms: "Camere",
    show_timeline: "Grafic: ultimele 24 de ore și următoarele 12",
    show_quick_override: "Setează temporar",
    show_levels: "Temperaturile nivelurilor",
    show_details: "Detalii",
    show_schedule_editor: "Editor de program",
    collapsed: "Camerele pornesc pliate",
    compact: "Compact: o placă pe cameră, se deschide la atingere",
    runtime_period: "Timpul de încălzire afișat pentru (se schimbă și apăsând valoarea în card)",
  },
  de: {
    title: "Titel",
    rooms: "Räume (Entscheidungs-Sensoren; leer = alle)",
    show_house: "Haus: Anwesenheit, Modus, Pause, Gäste, Urlaub",
    show_rooms: "Räume",
    show_timeline: "Diagramm: letzte 24 Stunden und die nächsten 12",
    show_quick_override: "Für eine Weile setzen",
    show_levels: "Temperaturen der Stufen",
    show_details: "Details",
    show_schedule_editor: "Zeitplan-Editor",
    collapsed: "Räume starten eingeklappt",
    compact: "Kompakt: eine Kachel pro Raum, zum Öffnen antippen",
    runtime_period: "Angezeigte Heizzeit für (in der Karte durch Antippen des Werts änderbar)",
  },
  nl: {
    title: "Titel",
    rooms: "Kamers (Beslissing-sensoren; leeg = alle)",
    show_house: "Huis: aanwezigheid, modus, pauze, gasten, vakantie",
    show_rooms: "Kamers",
    show_timeline: "Grafiek: laatste 24 uur en de komende 12",
    show_quick_override: "Tijdelijk instellen",
    show_levels: "Temperaturen van de niveaus",
    show_details: "Details",
    show_schedule_editor: "Schema-editor",
    collapsed: "Kamers starten ingeklapt",
    compact: "Compact: één tegel per kamer, tik om te openen",
    runtime_period: "Verwarmingstijd getoond voor (tik op de waarde in de kaart om te wisselen)",
  },
  fr: {
    title: "Titre",
    rooms: "Pièces (capteurs Décision ; vide = toutes)",
    show_house: "Maison : présence, mode, pause, invités, vacances",
    show_rooms: "Pièces",
    show_timeline: "Graphique : dernières 24 heures et les 12 prochaines",
    show_quick_override: "Régler pour un moment",
    show_levels: "Températures des niveaux",
    show_details: "Détails",
    show_schedule_editor: "Éditeur de planning",
    collapsed: "Pièces repliées au départ",
    compact: "Compact : une tuile par pièce, touchez pour ouvrir",
    runtime_period: "Temps de chauffe affiché pour (touchez la valeur dans la carte pour le changer)",
  },
  it: {
    title: "Titolo",
    rooms: "Stanze (sensori Decisione; vuoto = tutte)",
    show_house: "Casa: presenza, modalità, pausa, ospiti, vacanza",
    show_rooms: "Stanze",
    show_timeline: "Grafico: ultime 24 ore e le prossime 12",
    show_quick_override: "Imposta temporaneamente",
    show_levels: "Temperature dei livelli",
    show_details: "Dettagli",
    show_schedule_editor: "Editor del programma",
    collapsed: "Stanze chiuse all'avvio",
    compact: "Compatta: un riquadro per stanza, tocca per aprire",
    runtime_period: "Tempo di riscaldamento mostrato per (tocca il valore nella scheda per cambiarlo)",
  },
};

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
