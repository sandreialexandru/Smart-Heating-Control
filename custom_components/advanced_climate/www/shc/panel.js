/*
 * Smart Heating Control panel: the whole house on its own page in the sidebar.
 *
 * The house on top, the rooms on the side, the chosen room in the middle. On a
 * phone the rooms are a list; a room opens on the whole screen, with Back.
 * It extends the same base as the card (ShcBase): every part of the house and
 * the rooms is the card's own code, only the layout is the panel's.
 * The chosen room is kept in the address (#room) and in the browser.
 * More tabs: the schedule of the week (every room on one day), the statistics
 * (heating time and temperatures by day, week, month), the devices of every
 * room (the unavailable ones first, with their battery) and the history (the alerts on now, the decisions of the rooms, the alerts with
 * their start and end).
 */

import { ShcBase } from "./core/base.js";
import { DEFAULTS } from "./core/constants.js";
import { esc } from "./core/format.js";
import { STYLE } from "./core/style.js";

const STORE = "shc-panel-room";
const TAB_STORE = "shc-panel-tab";
const TABS = ["rooms", "week", "stats", "history", "devices"];

const PANEL_STYLE = `
  :host { display: block; min-height: 100%; background: var(--primary-background-color); }
  .ptop { position: sticky; top: 0; z-index: 2; height: 56px; box-sizing: border-box; display: flex; align-items: center; gap: 4px;
    padding: 0 8px; background: var(--app-header-background-color, var(--primary-color));
    color: var(--app-header-text-color, var(--text-primary-color, #fff)); }
  .ptop h1 { margin: 0 0 0 8px; font-size: 20px; font-weight: 400; flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .ptop button { width: 40px; height: 40px; border: 0; border-radius: 50%; background: none; color: inherit; cursor: pointer;
    display: inline-flex; align-items: center; justify-content: center; padding: 0; }
  .ptop button:hover { background: color-mix(in srgb, currentColor 12%, transparent); }
  .ptop button[hidden] { display: none; }
  .pbody { box-sizing: border-box; max-width: 1400px; margin: 0 auto; padding: 16px; display: grid; gap: 16px;
    grid-template-columns: minmax(260px, 340px) minmax(0, 1fr); grid-template-areas: "house house" "side main"; align-items: start; }
  .phouse { grid-area: house; }
  .pside { grid-area: side; position: sticky; top: 72px; max-height: calc(100vh - 88px); overflow: auto; }
  .pmain { grid-area: main; min-width: 0; }
  .pside .hname { margin: 4px 4px 0; font-size: 0.85em; color: var(--ac-muted); font-weight: 600; }
  /* A row is lit whole on hover (not only the button inside it), the chosen one tinted. */
  .pside .block.room.folded { cursor: pointer; }
  .pside .frow:hover { background: none; }
  .pside .block.room.folded:hover { background: var(--ac-surface-2); }
  .pside .block.room.folded.chosen { border-color: var(--ac-active-line); background: var(--ac-active-bg); }
  .pside .block.room.folded.chosen:hover { background: color-mix(in srgb, var(--ac-accent) 24%, transparent); }
  :host([narrow]) .pbody { padding: 8px; gap: 8px; grid-template-columns: minmax(0, 1fr); grid-template-areas: "house" "side" "main"; }
  :host([narrow]) .pside { position: static; max-height: none; overflow: visible; }
  /* !important: a card element may set its own display. */
  .pbody > [hidden], :host([narrow][room]) .phouse, :host([narrow][room]) .pside { display: none !important; }
  :host([narrow]:not([room])) .pmain { display: none !important; }
  /* The tabs: rooms, statistics, history. */
  .ptabs { box-sizing: border-box; max-width: 1400px; margin: 0 auto; padding: 16px 16px 0; display: flex; justify-content: center; }
  .ptabs .segmented { flex: 0 1 600px; }
  :host([narrow]) .ptabs { padding: 8px 8px 0; }
  :host([narrow][room][tab="rooms"]) .ptabs { display: none; }
  .pextra { grid-column: 1 / -1; }
  :host(:not([tab="rooms"])) .phouse, :host(:not([tab="rooms"])) .pside, :host(:not([tab="rooms"])) .pmain,
  :host([tab="rooms"]) .pextra { display: none !important; }
  .ps-stats .segmented, .ph-filters .segmented { max-width: 420px; }
  .ps-title { margin: 8px 0 0; font-size: 0.95em; font-weight: 600; }
  .ps-house { margin: 12px 0 0; font-size: 1.1em; }
  .ps-cols { display: flex; gap: 6px; height: 190px; overflow-x: auto; }
  .ps-col { flex: 1 0 34px; display: flex; flex-direction: column; align-items: center; gap: 4px; min-width: 0; }
  .ps-area { flex: 1; width: 100%; display: flex; align-items: flex-end; justify-content: center; }
  .ps-bar { width: 100%; max-width: 40px; background: var(--c); border-radius: 6px 6px 2px 2px; }
  .ps-val, .ps-lab { font-size: 0.72em; color: var(--ac-muted); white-space: nowrap; }
  button.ps-col { border: 0; background: none; padding: 0; font: inherit; color: inherit; cursor: pointer; border-radius: 6px; }
  button.ps-col:hover .ps-bar { filter: brightness(1.1); }
  .ps-col.dim .ps-bar { opacity: 0.35; }
  .ps-col.picked .ps-lab, .ps-col.picked .ps-val { color: var(--primary-text-color); font-weight: 600; }
  .ps-detail { display: flex; align-items: center; gap: 8px; padding: 6px 6px 6px 12px; border-radius: 10px;
    background: var(--ac-active-bg); box-shadow: inset 0 0 0 1px var(--ac-active-line); }
  .ps-detail > span { flex: 1; min-width: 0; }
  .ps-unpick { width: 32px; height: 32px; border: 0; border-radius: 50%; background: none; color: inherit; cursor: pointer;
    display: inline-flex; align-items: center; justify-content: center; padding: 0; }
  .ps-unpick:hover { background: var(--ac-surface-2); }
  /* One grid for all the rooms, so their bars and values line up. */
  .ps-rows { display: grid; grid-template-columns: minmax(70px, 160px) minmax(40px, 1fr) auto auto 3em; gap: 8px 10px; }
  .ps-row { grid-column: 1 / -1; display: grid; grid-template-columns: subgrid; align-items: center; }
  .ps-temp { font-size: 0.85em; color: var(--ac-muted); white-space: nowrap; text-align: right; }
  .ps-out { font-size: 0.68em; color: var(--ac-out); white-space: nowrap; min-height: 1.2em; }
  .ps-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .ps-track { height: 10px; border-radius: 5px; background: var(--ac-surface-2); overflow: hidden; }
  .ps-fill { display: block; height: 100%; background: var(--c); border-radius: 5px; }
  .ps-h, .ps-pct { font-size: 0.9em; text-align: right; white-space: nowrap; }
  .ps-pct { color: var(--ac-muted); }
  /* On a phone: narrower bars without their values (the title of a bar has it), a room on two lines. */
  :host([narrow]) .ps-cols { gap: 3px; }
  :host([narrow]) .ps-col { flex-basis: 16px; }
  :host([narrow]) .ps-val { display: none; }
  :host([narrow]) .ps-rows { grid-template-columns: minmax(0, 1fr) auto 3em; column-gap: 8px; }
  :host([narrow]) .ps-temp { grid-column: 1 / -1; grid-row: 3; text-align: left; margin-top: -2px; }
  :host([narrow]) .ps-row { row-gap: 4px; }
  :host([narrow]) .ps-out { display: none; }
  :host([narrow]) .ps-track { grid-column: 1 / -1; grid-row: 2; }
  .ph-filters { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
  .ph-filters .segmented { flex: 1 1 260px; }
  .ph-day { margin: 12px 0 0; font-size: 0.9em; font-weight: 600; color: var(--ac-muted); }
  .ph-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; }
  .ph-list li { display: flex; gap: 10px; align-items: flex-start; padding: 8px 0; border-bottom: 1px solid var(--ac-line); }
  .ph-list li:last-child { border-bottom: 0; }
  .ph-time { flex: none; min-width: 3.2em; color: var(--ac-muted); padding-top: 2px; }
  .ph-ico { flex: none; display: inline-flex; color: var(--ac-muted); }
  .ph-ico.warn { color: var(--ac-warn); }
  .ph-ico.error { color: var(--ac-err); }
  .ph-text { flex: 1; min-width: 0; }
  /* The week: every room on one day, its bar on a shared time line. */
  .pw-days .seg { position: relative; }
  .pw-today { position: absolute; left: 50%; bottom: 3px; width: 4px; height: 4px; margin-left: -2px; border-radius: 50%; background: currentColor; }
  .pw-rows { display: grid; grid-template-columns: minmax(70px, 180px) minmax(0, 1fr) minmax(0, 8em) 40px; gap: 4px 12px; margin-top: 8px; }
  .pw-ticks, .pw-row, .pw-main { grid-column: 1 / -1; display: grid; grid-template-columns: subgrid; align-items: center; }
  .pw-main { grid-column: 1 / 4; }
  .pw-ticks .bar-ticks { margin: 0; }
  button.pw-main { border: 0; background: none; font: inherit; color: inherit; text-align: left; padding: 8px 6px; margin: 0 -6px;
    border-radius: 10px; cursor: pointer; }
  button.pw-main:hover { background: var(--ac-surface-2); }
  div.pw-row > .pw-name { padding: 8px 0; }
  .pw-copy { width: 40px; height: 40px; border: 0; border-radius: 50%; background: none; color: var(--ac-muted); cursor: pointer;
    display: inline-flex; align-items: center; justify-content: center; padding: 0; }
  .pw-copy:hover { background: var(--ac-surface-2); color: var(--primary-text-color); }
  .pw-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 500; }
  .pw-bar.sbar.ro { height: 22px; border-radius: 6px; }
  .pw-now { position: absolute; top: -3px; bottom: -3px; width: 2px; margin-left: -1px; background: var(--primary-text-color); border-radius: 1px; }
  .pw-gap { height: 22px; border-radius: 6px; display: flex; align-items: center; padding: 0 8px; font-size: 0.8em;
    background: repeating-linear-gradient(135deg, color-mix(in srgb, var(--c) 22%, transparent) 0 6px, transparent 6px 12px); }
  .pw-prof, .pw-ext { font-size: 0.85em; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .pw-ext { grid-column: 2 / -1; }
  :host([narrow]) .pw-rows { grid-template-columns: minmax(0, 1fr) auto 40px; }
  :host([narrow]) .pw-ticks > span:not(.bar-ticks) { display: none; }
  :host([narrow]) .pw-ticks .bar-ticks { grid-column: 1 / 3; }
  :host([narrow]) .pw-main { grid-column: 1 / 3; row-gap: 6px; }
  :host([narrow]) .pw-bar, :host([narrow]) .pw-gap { grid-column: 1 / -1; grid-row: 2; }
  :host([narrow]) .pw-ext { grid-column: 1 / -1; grid-row: 2; }
  :host([narrow]) .pw-copy { grid-row: 1; grid-column: 3; }
  .pw-note { margin-top: 12px; }
  :host([narrow]) .pw-rows { grid-template-columns: minmax(0, 1fr) auto; }
  :host([narrow]) .pw-ticks > span:first-child, :host([narrow]) .pw-ticks > span:last-child { display: none; }
  :host([narrow]) .pw-ticks .bar-ticks { grid-column: 1 / -1; }
  :host([narrow]) .pw-bar, :host([narrow]) .pw-gap, :host([narrow]) .pw-ext { grid-column: 1 / -1; grid-row: 2; }
  :host([narrow]) .pw-row { row-gap: 6px; }
  /* Every device of the rooms. */
  .pd-badcount { color: var(--ac-err); }
  .pd-list { list-style: none; margin: 8px 0 0; padding: 0; display: flex; flex-direction: column; }
  .pd-row { display: grid; grid-template-columns: 28px minmax(0, 1fr) minmax(0, 14em) 6em 9em; gap: 4px 12px; align-items: center;
    padding: 8px 6px; margin: 0 -6px; border-radius: 10px; border-bottom: 1px solid var(--ac-line); cursor: pointer; }
  .pd-row:hover { background: var(--ac-surface-2); }
  .pd-ico { display: inline-flex; color: var(--ac-muted); }
  .pd-row.bad .pd-ico, .pd-row.bad .pd-val { color: var(--ac-err); }
  .pd-name { display: flex; flex-direction: column; min-width: 0; }
  .pd-name > span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .pd-name small { color: var(--ac-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .pd-val { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .pd-bat { display: inline-flex; align-items: center; gap: 2px; font-size: 0.9em; white-space: nowrap; }
  .pd-bat.low { color: var(--ac-err); }
  .pd-ago { font-size: 0.85em; text-align: right; white-space: nowrap; }
  :host([narrow]) .pd-row { grid-template-columns: 28px minmax(0, 1fr) auto; }
  :host([narrow]) .pd-val { grid-column: 2 / 3; grid-row: 2; font-size: 0.9em; }
  :host([narrow]) .pd-bat { grid-column: 3; grid-row: 1; }
  :host([narrow]) .pd-ago { grid-column: 3; grid-row: 2; }
  /* The alerts on now, on top of the history. */
  .pa-now { margin-bottom: 16px; }
  .pa-now .acount { display: inline-flex; min-width: 1.4em; justify-content: center; padding: 0 6px; border-radius: 999px; font-size: 0.8em;
    background: var(--ac-warn); color: #000; }
  .pa-list li { align-items: center; flex-wrap: wrap; }
  :host([narrow]) .pa-list .ph-text { flex-basis: calc(100% - 40px); }
  :host([narrow]) .pa-list li > .btn { margin-left: auto; }
  .pa-list .ph-text.link { cursor: pointer; }
  .tabcount { display: inline-flex; min-width: 1.3em; justify-content: center; margin-left: 6px; padding: 0 5px; border-radius: 999px;
    font-size: 0.78em; background: var(--ac-warn); color: #000; }
  /* On a phone the count sits on the corner of the tab, so its name keeps its room. */
  .ptabs .seg { position: relative; }
  :host([narrow]) .ptabs .segmented { padding: 3px; gap: 2px; }
  :host([narrow]) .ptabs .seg { font-size: 0.78em; padding: 0 2px; }
  :host([narrow]) .tabcount { position: absolute; top: 1px; right: 1px; margin: 0; min-width: 1.1em; padding: 0 3px; font-size: 0.68em; }
  /* The open room is not folded from its title in the panel. */
  .pmain .room-title { cursor: default; }
  .pmain .room-title .chev { display: none; }
`;

const menuIcon = `<svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true"><path fill="currentColor" d="M3 6h18v2H3V6m0 5h18v2H3v-2m0 5h18v2H3v-2Z"/></svg>`;
const backIcon = `<svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true"><path fill="currentColor" d="M20 11v2H8l5.5 5.5-1.42 1.42L4.16 12l7.92-7.92L13.5 5.5 8 11h12Z"/></svg>`;

const readStore = () => {
  try {
    return localStorage.getItem(STORE) || null;
  } catch (_err) {
    return null;
  }
};
const writeStore = (room) => {
  try {
    if (room) localStorage.setItem(STORE, room);
  } catch (_err) {
    // No storage (private window): the address still keeps the room.
  }
};
const readTab = () => {
  try {
    const tab = localStorage.getItem(TAB_STORE);
    return TABS.includes(tab) ? tab : "rooms";
  } catch (_err) {
    return "rooms";
  }
};
const hashRoom = () => decodeURIComponent((location.hash || "").slice(1)) || null;

class ShcPanel extends ShcBase {
  constructor() {
    super();
    // The parts are drawn as in a card with every option on, each room open.
    this._config = { ...DEFAULTS };
    this._room = hashRoom();
    this._tab = readTab();
    this._onHash = () => {
      this._room = hashRoom();
      this._render();
    };
  }

  connectedCallback() {
    super.connectedCallback();
    window.addEventListener("hashchange", this._onHash);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    window.removeEventListener("hashchange", this._onHash);
  }

  /** Set by Home Assistant: a narrow screen (phone) shows the list or one room. */
  set narrow(value) {
    if (!!value === this._narrow) return;
    this._narrow = !!value;
    this.toggleAttribute("narrow", this._narrow);
    this._render();
  }

  get narrow() {
    return !!this._narrow;
  }

  /** Set by Home Assistant (the panel and its route): nothing to read from them. */
  set panel(_value) {}
  set route(_value) {}

  /** The room shown: the one in the address, else (wide) the last one or the first. */
  _chosen(rooms) {
    const ids = rooms.map((r) => r.attributes.room_id);
    if (this._room && ids.includes(this._room)) return this._room;
    if (this._narrow) return null;
    const stored = readStore();
    return stored && ids.includes(stored) ? stored : ids[0] || null;
  }

  /** Open a room (null: back to the list), in the address too. */
  _choose(room) {
    this._room = room;
    writeStore(room);
    const url = `${location.pathname}${location.search}${room ? `#${encodeURIComponent(room)}` : ""}`;
    history.replaceState(history.state, "", url);
    this._render();
    if (this._narrow) window.scrollTo(0, 0);
  }

  /** Show a tab (rooms, statistics, history), kept in the browser. */
  _showTab(tab) {
    this._tab = TABS.includes(tab) ? tab : "rooms";
    try {
      localStorage.setItem(TAB_STORE, this._tab);
    } catch (_err) {
      // No storage: the tab is not kept.
    }
    this._render();
  }

  /** The skeleton (bar, tabs, house, list, room, statistics or history) and the styles, made once. */
  _ensureCard() {
    if (this._card) return;
    this._addStyle(STYLE + PANEL_STYLE);
    const root = this.shadowRoot;
    const top = document.createElement("div");
    top.className = "ptop";
    top.innerHTML = `<button class="pmenu" aria-label="Menu">${menuIcon}</button>
      <button class="pback" hidden>${backIcon}</button><h1>SHC</h1>`;
    top.querySelector(".pmenu").addEventListener("click", () =>
      this.dispatchEvent(new Event("hass-toggle-menu", { bubbles: true, composed: true }))
    );
    top.querySelector(".pback").addEventListener("click", () => this._choose(null));
    const body = document.createElement("div");
    body.className = "pbody";
    body.innerHTML = `<ha-card class="phouse"></ha-card><ha-card class="pside"></ha-card><ha-card class="pmain"></ha-card>
      <ha-card class="pextra"></ha-card>`;
    const tabs = document.createElement("nav");
    tabs.className = "ptabs";
    // The chart window: alone in its holder, so a patch never moves it (it stays modal).
    this._popHolder = document.createElement("div");
    root.append(this._popHolder, top, tabs, body);
    this._tabs = tabs;
    this._extra = body.querySelector(".pextra");
    this._top = top;
    this._house = body.querySelector(".phouse");
    this._side = body.querySelector(".pside");
    this._card = body.querySelector(".pmain");
  }

  /** What redraws the panel: on the Devices tab also every device, its battery, and each minute (how long ago). */
  _watched() {
    const ids = super._watched();
    if (this._tab !== "devices") return ids;
    return [...ids, ...this._deviceIds(this._houses()), `minute:${Math.floor(Date.now() / 60000)}`];
  }

  /** Open a room on the Rooms tab; with a part of it (its schedule, its Details) shown. */
  _openRoom(room, key = null) {
    this._tab = "rooms";
    try {
      localStorage.setItem(TAB_STORE, this._tab);
    } catch (_err) {
      // No storage: the tab is not kept.
    }
    this._choose(room);
    if (!key) return;
    const part = this._card?.querySelector(`[data-section="${CSS.escape(key)}"], [data-key="${CSS.escape(key)}"]`);
    part?.scrollIntoView({ block: "start", behavior: "smooth" });
  }

  /** Draw the panel: only the blocks that changed are replaced (as in the card). */
  _render() {
    if (!this._config || !this._hass) return;
    this._ensureCard();
    const houses = this._hass ? this._houses() : [];
    const rooms = houses.flatMap((h) => h.rooms);
    const room = this._chosen(rooms);
    const chosen = rooms.find((r) => r.attributes.room_id === room);
    this.toggleAttribute("room", !!chosen);
    const tab = this._tab;
    this.setAttribute("tab", tab);
    // The alerts on now, counted on the History tab.
    const alerts = this._activeAlerts(houses).length;
    this._patch(this._tabs, [
      {
        k: "tabs",
        html: `<div class="segmented" style="--n:${TABS.length}" role="tablist">${TABS.map(
          (t) => `<button class="seg ${t === tab ? "active" : ""}" role="tab" aria-selected="${t === tab}" data-action="panel-tab"
            data-option="${t}">${esc(this._t(`tab_${t}`))}${
              t === "history" && alerts ? `<span class="tabcount" aria-label="${esc(`${this._t("an_title")}: ${alerts}`)}">${alerts}</span>` : ""
            }</button>`
        ).join("")}</div>`,
      },
    ]);

    // The bar: Back and the name of the room on a phone, else SHC.
    const back = this._top.querySelector(".pback");
    back.hidden = !(this._narrow && chosen);
    back.setAttribute("aria-label", this._t("back"));
    // The menu of Home Assistant: its sidebar has its own button when docked,
    // so ours only on a phone or with the sidebar always hidden.
    const sidebar = this._hass?.dockedSidebar === "always_hidden";
    this._top.querySelector(".pmenu").hidden = !!(this._narrow && chosen) || !(this._narrow || sidebar);
    this._top.querySelector("h1").textContent = this._narrow && chosen ? chosen.attributes.room_name : "SHC";

    // The house (each house, with its banners).
    const top = [];
    if (!houses.length) top.push({ k: "empty", html: `<p class="empty">${this._t("no_rooms")}</p>` });
    for (const house of houses) {
      const pause = this._pauseBanner(house);
      if (pause) top.push({ k: `pause-${house.id}`, html: pause });
      const guest = this._guestBanner(house);
      if (guest) top.push({ k: `guest-${house.id}`, html: guest });
      top.push({ k: `house-${house.id}`, html: this._houseHtml(house) });
    }
    this._patch(this._house, top);

    // The rooms: a folded row each, the chosen one marked; the house names when there are several.
    const list = [];
    for (const house of houses) {
      if (houses.length > 1) list.push({ k: `hname-${house.id}`, html: `<p class="hname">${esc(house.name || "")}</p>` });
      for (const r of house.rooms) {
        const a = r.attributes;
        list.push({ k: `row-${a.room_id}`, html: this._foldedRow(r, this._roomColor(a)) });
      }
    }
    this._side.hidden = !rooms.length;
    this._patch(this._side, list);
    for (const node of this._side.children) node.classList.toggle("chosen", node.__k === `row-${room}`);

    // The chosen room, open.
    if (chosen) this._open[`room-${chosen.attributes.room_id}`] = true;
    this._card.hidden = !chosen;
    this._patch(this._card, chosen ? [{ k: `room-${room}`, html: this._roomHtml(chosen) }] : []);

    // The week, the statistics or the history
    // (the alerts on now on top); fetched only while shown.
    const extra = [];
    if (tab === "week") extra.push({ k: "week", html: this._weekHtml(houses) });
    if (tab === "stats") extra.push({ k: "stats", html: this._statsHtml(houses) });
    if (tab === "devices") extra.push({ k: "devices", html: this._devicesTabHtml(houses) });
    if (tab === "history") {
      const history = this._historyHtml(houses);
      extra.push({ k: "alerts-now", html: this._alertsNowHtml(houses) }, { k: "history", html: history });
    }
    this._patch(this._extra, extra);

    const popup = this._chartPopup();
    this._patch(this._popHolder, popup ? [popup] : []);
    this._tipColor();
    this._chartModal();
  }

  /** A row of the list opens its room; the title of the open room does not fold it. */
  async _onClick(ev) {
    // The whole row of a room, its margin too.
    const row = ev.target.closest?.(".block.room.folded");
    const pick = row && this._side?.contains(row) ? row.querySelector('[data-action="fold"][data-key^="room-"]') : null;
    if (pick) {
      this._choose(pick.dataset.key.slice(5));
      return;
    }
    const fold = ev.target.closest?.('[data-action="fold"][data-key^="room-"]');
    if (fold && this._card?.contains(fold)) return;
    // The tabs and the choices of the statistics and the history.
    // A room opened from the week (its schedule editor, or the rooms to copy its schedule to) or from an alert.
    const go = ev.target.closest?.('[data-action="week-edit"], [data-action="week-copy"], [data-action="alert-room"]');
    if (go) {
      const room = go.dataset.room;
      const action = go.dataset.action;
      if (action === "week-edit") this._startEdit(room);
      if (action === "week-copy") {
        this._copyFrom = room;
        this._copyTo = new Set();
        this._copyDone = null;
      }
      const key = action === "week-edit" || action === "week-copy" ? `sched-${room}` : null;
      if (key) this._open[key] = true;
      this._openRoom(room, key);
      return;
    }
    const own = ev.target.closest?.(
      '[data-action="panel-tab"], [data-action="stats-period"], [data-action="stats-pick"], [data-action="history-kind"], [data-action="week-day"]'
    );
    if (own) {
      const option = own.dataset.option;
      const action = own.dataset.action;
      if (action === "panel-tab") this._showTab(option);
      else if (action === "stats-period") {
        this._statsP = option;
        this._statsPick = null; // another period: the whole range again
      } else if (action === "stats-pick") {
        // A tap on a bar chooses its period; on the chosen one (or ✕) the whole range again.
        const t = own.dataset.t ? Number(own.dataset.t) : null;
        this._statsPick = t === this._statsPick ? null : t;
      } else if (action === "week-day") this._weekDay = Number(option);
      else this._historyKind = option;
      this._render();
      return;
    }
    return super._onClick(ev);
  }

  /** The room chosen for the history. */
  async _onChange(ev) {
    if (ev.target?.dataset?.action === "history-room") {
      this._historyRoom = ev.target.value;
      ev.target.blur();
      this._render();
      return;
    }
    return super._onChange(ev);
  }
}

if (!customElements.get("shc-panel")) customElements.define("shc-panel", ShcPanel);
