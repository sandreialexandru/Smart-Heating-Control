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
import { DEFAULTS, PRESET_COLORS } from "./core/constants.js";
import { esc, num } from "./core/format.js";
import { STYLE } from "./core/style.js";

const STORE = "shc-panel-room";
const TAB_STORE = "shc-panel-tab";
// How the rooms are grouped (none, by floor, by circuit), kept in the browser.
const GROUP_STORE = "shc-panel-group";
const TABS = ["rooms", "week", "stats", "history", "devices"];
// The name of the integration, the title when there are several houses.
const NAME = "Smart Heating Control";

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
  .pbody { box-sizing: border-box; max-width: 1600px; margin: 0 auto; padding: 16px; display: grid; gap: 16px;
    grid-template-columns: minmax(300px, 380px) minmax(0, 1fr); grid-template-areas: "house house" "side main"; align-items: start; }
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
  .ptabs { box-sizing: border-box; max-width: 1600px; margin: 0 auto; padding: 16px 16px 0; display: flex; justify-content: center;
    flex-wrap: wrap; gap: 8px; }
  .ptabs .segmented { flex: 0 1 720px; }
  /* The tabs and the grouping, laid out by the bar of the tabs. */
  .ptabrow { display: contents; }
  .pgroup { height: 40px; padding: 0 10px; border-radius: 10px; border: 1px solid var(--ac-line); background: var(--ac-surface-2);
    color: var(--primary-text-color); font: inherit; font-size: 0.9em; }
  .gname { font-size: 0.8em; text-transform: uppercase; letter-spacing: 0.04em; }
  .pw-group, .pd-group { grid-column: 1 / -1; margin-top: 8px; font-size: 0.8em; font-weight: 600; color: var(--ac-muted);
    text-transform: uppercase; letter-spacing: 0.04em; }
  /* The name of a house when there are several (two of their rooms can share a name). */
  .pw-group.ps-house, .pd-group.pd-house { margin-top: 14px; font-size: 1em; text-transform: none; letter-spacing: 0; color: var(--primary-text-color); }
  .pw-group.ps-house:first-child, .pd-group.pd-house:first-child { margin-top: 0; }
  :host([narrow]) .ptabs { padding: 8px 8px 0; }
  :host([narrow]) .pgroup { flex: 1 1 100%; }
  :host([narrow][room][tab="rooms"]) .ptabs { display: none; }
  .pextra { grid-column: 1 / -1; }
  :host(:not([tab="rooms"])) .phouse, :host(:not([tab="rooms"])) .pside, :host(:not([tab="rooms"])) .pmain,
  :host([tab="rooms"]) .pextra { display: none !important; }
  .ps-stats .segmented, .ph-filters .segmented { max-width: 420px; }
  .ps-title { margin: 8px 0 0; font-size: 0.95em; font-weight: 600; }
  .ps-house { margin: 12px 0 0; font-size: 1.1em; }
  /* The columns touch (their room is padding), so the centre of column i is at (i + ½) / n of the width:
     the line of the outdoor temperature is drawn over them in those units. */
  .ps-cols { height: 190px; overflow-x: auto; }
  .ps-inner { position: relative; display: flex; min-width: 100%; height: 100%; }
  .ps-col { flex: 1 0 40px; box-sizing: border-box; padding: 0 3px; display: flex; flex-direction: column; align-items: center;
    gap: 4px; min-width: 0; }
  .ps-col .ps-val, .ps-col .ps-lab { height: 14px; line-height: 14px; }
  .ps-col .ps-out { height: 13px; line-height: 13px; min-height: 0; }
  svg.ps-line { position: absolute; left: 0; right: 0; top: 18px; bottom: 18px; width: 100%; height: calc(100% - 36px);
    overflow: visible; pointer-events: none; }
  svg.ps-line .ps-hit { fill: transparent; stroke: none; pointer-events: all; cursor: pointer; }
  svg.ps-line circle.on { fill: var(--primary-text-color); }
  /* The mean, lowest and highest of a point tapped, next to it. */
  .ps-tip { position: absolute; top: calc(18px + (100% - 36px) * var(--y)); transform: translate(10px, -50%); z-index: 1;
    display: flex; flex-direction: column; padding: 4px 8px; border-radius: 8px; font-size: 0.8em; white-space: nowrap;
    background: var(--ha-card-background, var(--card-background-color, #fff)); box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25);
    pointer-events: none; }
  .ps-tip.right { transform: translate(calc(-100% - 10px), -50%); }
  .ps-tip small { color: var(--ac-muted); }
  :host([narrow]) .ps-tip { top: calc((100% - 18px) * var(--y)); }
  svg.ps-line.under { bottom: 35px; height: calc(100% - 53px); }
  svg.ps-line line { stroke: var(--ac-out); stroke-width: 2; stroke-linecap: round; }
  svg.ps-line text { fill: var(--ac-out); font-size: 11px; font-weight: 600; paint-order: stroke;
    stroke: var(--ha-card-background, var(--card-background-color, #fff)); stroke-width: 3px; }
  svg.ps-line circle { fill: var(--ac-out); stroke: var(--ha-card-background, var(--card-background-color, #fff)); stroke-width: 1.5; }
  .ps-legend { display: inline-flex; align-items: center; gap: 6px; margin-left: 10px; font-size: 0.85em; font-weight: 400;
    color: var(--ac-muted); }
  .ps-legend i { width: 16px; height: 2px; border-radius: 1px; background: var(--ac-out); }
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
  :host([narrow]) .ps-col { flex-basis: 19px; padding: 0 1.5px; }
  :host([narrow]) svg.ps-line, :host([narrow]) svg.ps-line.under { top: 0; bottom: 18px; height: calc(100% - 18px); }
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
  /* On a phone the weekday over the day of the month, so both fit. */
  :host([narrow]) .pw-days .seg { display: flex; flex-direction: column; align-items: center; justify-content: center; line-height: 1.15; height: auto; min-height: 44px; }
  :host([narrow]) .pw-wd { font-size: 0.85em; }
  :host([narrow]) .pw-dn { font-weight: 600; }
  .pw-today { position: absolute; left: 50%; bottom: 3px; width: 4px; height: 4px; margin-left: -2px; border-radius: 50%; background: currentColor; }
  .pw-rows { display: grid; grid-template-columns: minmax(70px, 180px) minmax(0, 1fr) minmax(0, 8em) 40px; gap: 4px 12px; margin-top: 8px; }
  .pw-ticks, .pw-row, .pw-main { grid-column: 1 / -1; display: grid; grid-template-columns: subgrid; align-items: center; }
  .pw-main { grid-column: 1 / 4; }
  .pw-ticks .bar-ticks { margin: 0; }
  /* Each hour where it falls on that day (23 or 25 hours at a change of the clock). */
  .pw-tickline { position: relative; display: block; height: 1.3em; }
  .pw-tickline > span { position: absolute; top: 0; transform: translateX(-50%); }
  .pw-tickline > span:first-child { transform: none; }
  .pw-tickline > span:last-child { transform: translateX(-100%); }
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
  .pw-ov { position: absolute; top: 0; bottom: 0; box-sizing: border-box; border: 2px solid var(--c); border-radius: 4px;
    background: repeating-linear-gradient(135deg, color-mix(in srgb, var(--c) 75%, transparent) 0 5px, color-mix(in srgb, var(--c) 35%, transparent) 5px 10px); }
  .pw-notes { list-style: none; margin: 6px 0 0; padding: 0; display: flex; flex-wrap: wrap; gap: 6px; }
  .pw-notes li { padding: 4px 10px; border-radius: 12px; font-size: 0.85em; background: var(--ac-active-bg); box-shadow: inset 0 0 0 1px var(--ac-active-line); }
  :host([narrow]) .pw-ticks > span:first-child, :host([narrow]) .pw-ticks > span:last-child { display: none; }
  :host([narrow]) .pw-bar, :host([narrow]) .pw-gap, :host([narrow]) .pw-ext { grid-column: 1 / -1; grid-row: 2; }
  :host([narrow]) .pw-row { row-gap: 6px; }
  /* Every device of the rooms. */
  .pd-badcount { color: var(--ac-err); }
  .pd-humidity { margin-bottom: 16px; }
  .ph-hum.risk .pd-ico, .ph-hum.risk .pd-name small { color: var(--ac-warn); }
  .ph-hum .pl-lab { font-size: 0.75em; color: var(--ac-muted); }
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
  /* The heating by hour: a row of 24 hours for each room, the darker the more minutes heated. */
  .hm { margin-top: 16px; }
  .hm-days { margin: 8px 0; }
  .hm-grid { display: grid; gap: 3px; }
  .hm-row { display: grid; grid-template-columns: minmax(70px, 140px) repeat(24, minmax(0, 1fr)); gap: 2px; align-items: center; }
  .hm-name { font-size: 0.85em; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; padding-right: 6px; }
  .hm-hour { font-size: 0.68em; color: var(--ac-muted); }
  .hm-cell { height: 22px; border-radius: 3px; background: color-mix(in srgb, var(--ac-hot) var(--p), var(--ac-surface-2)); }
  .hm-cell.none { background: none; box-shadow: inset 0 0 0 1px var(--ac-line); }
  button.hm-cell { border: 0; padding: 0; margin: 0; cursor: pointer; font: inherit; min-width: 0; }
  button.hm-cell:hover { filter: brightness(1.1); }
  .hm-cell.picked { box-shadow: 0 0 0 2px var(--primary-text-color); }
  .hm-detail { margin-top: 8px; }
  .hm-legend { display: flex; align-items: center; gap: 8px; margin-top: 8px; font-size: 0.75em; color: var(--ac-muted); }
  .hm-legend i { width: 120px; height: 10px; border-radius: 3px; background: linear-gradient(90deg, var(--ac-surface-2), var(--ac-hot)); }
  /* On a phone: the name of a room on a line of its own, above its 24 hours. */
  :host([narrow]) .hm-row { grid-template-columns: repeat(24, minmax(0, 1fr)); gap: 1px; }
  :host([narrow]) .hm-name { grid-column: 1 / -1; padding: 4px 0 1px; }
  :host([narrow]) .hm-head > span:first-child { display: none; }
  :host([narrow]) .hm-cell { height: 18px; border-radius: 2px; }
  :host([narrow]) .hm-days .seg { font-size: 0.8em; padding: 0 1px; }
  /* The Mean chip as wide as its word, the 7 days share the rest. */
  :host([narrow]) .hm-days { grid-template-columns: auto repeat(calc(var(--n) - 1), minmax(0, 1fr)); }
  :host([narrow]) .hm-days .seg:first-child { padding: 0 6px; }
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
  /* The house on a wide screen: the name, the people and the values on a row; the mode, the source, the scenarios and the buttons under it. */
  .pbar { gap: 10px; padding: 12px 16px; }
  .pb-row { display: flex; align-items: center; gap: 8px 12px; flex-wrap: wrap; min-width: 0; }
  .pb-row .avatars { padding: 2px; }
  .pb-stats { display: flex; align-items: center; gap: 4px; flex-wrap: wrap; margin-left: auto; }
  .pb-stat { display: inline-flex; flex-direction: column; align-items: flex-start; gap: 1px; padding: 4px 12px; border-radius: 8px; border: 0;
    border-left: 1px solid var(--ac-line); background: none; font: inherit; color: inherit; text-align: left; white-space: nowrap; cursor: default; }
  .pb-stat .k { display: inline-flex; align-items: center; gap: 4px; font-size: 0.75em; color: var(--ac-muted); }
  .pb-stat .v { font-size: 1.1em; font-weight: 600; font-variant-numeric: tabular-nums; }
  .pb-stat.link, button.pb-stat { cursor: pointer; }
  .pb-stat.link:hover, button.pb-stat:hover { background: var(--ac-surface-2); }
  .pb-stat ha-icon { --mdc-icon-size: 14px; }
  .pb-stat.hot .v { color: var(--ac-hot); }
  .pb-actions { display: flex; flex-wrap: wrap; gap: 6px; margin-left: auto; }
  .pb-actions .abtn { min-height: 40px; padding: 0 12px; border-radius: 10px; }
  .pb-row2 { display: flex; align-items: center; gap: 8px 16px; flex-wrap: wrap; }
  .pb-row2 > .segmented { flex: 1 1 420px; max-width: 640px; }
  .pb-row2 .scenarios { flex-direction: row; align-items: center; flex: 1 1 320px; }
  .pb-row2 .scenarios.sources { flex-basis: 460px; }
  .pb-row2 .scenarios > .segmented { flex: 1; min-width: 0; }
  .pb-row2 .scen-grid { flex: 1; grid-template-columns: none; grid-auto-flow: column; grid-auto-columns: minmax(0, 1fr); }
  .pb-row2 .scenarios .sclabel { white-space: nowrap; }
  /* The chosen room on a wide screen: the room and its chart side by side, the day and the levels under them. */
  /* Side by side while both have room, else one under the other. !important: a card element may set its own display. */
  .pmain.wide { display: grid !important; grid-template-columns: minmax(0, 1fr); align-items: start; }
  .pbody { container-type: inline-size; }
  /* The room keeps room for its buttons with their names (else it goes over the chart). */
  @container (min-width: 1350px) {
    .pmain.wide { grid-template-columns: minmax(440px, 2fr) minmax(0, 3fr); }
  }
  .pmain.wide > .prw-below { grid-column: 1 / -1; }
  .pmain.wide > .prw-chart { padding: 0; min-width: 0; border: 0; background: none; }
  .prw-chart .chart-card { margin: 0; }
  .prw-levels { display: flex; flex-wrap: wrap; gap: 6px; }
  .prw-level { display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 999px; font-size: 0.85em;
    background: var(--ac-surface-2); }
  .prw-level .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--c); }
  .prw-level b { font-variant-numeric: tabular-nums; }
  .prw-level.on { box-shadow: inset 0 0 0 1.5px var(--c); font-weight: 600; }
  /* The scale of the outdoor temperature of the statistics, on its own right of the columns. */
  .ps-chart { display: flex; align-items: stretch; }
  .ps-chart > .ps-cols { flex: 1; min-width: 0; }
  .ps-axis { --t: 18px; --b: 18px; position: relative; flex: none; width: 3.2em; height: 190px; margin-left: 4px;
    border-left: 1px solid color-mix(in srgb, var(--ac-out) 45%, transparent); }
  .ps-axis.under { --b: 35px; }
  .ps-axis.empty { border-left-color: transparent; }
  .ps-axis span { position: absolute; left: 6px; top: calc(var(--t) + (100% - var(--t) - var(--b)) * var(--y)); transform: translateY(-50%);
    font-size: 11px; font-weight: 600; color: var(--ac-out); white-space: nowrap; }
  :host([narrow]) .ps-axis, :host([narrow]) .ps-axis.under { --t: 0px; --b: 18px; width: 30px; margin-left: 2px; }
  :host([narrow]) .ps-axis span { left: 3px; font-size: 10px; }
  /* The copy button of a row of the week: on hover or focus (always on a touch screen). */
  @media (hover: hover) {
    :host(:not([narrow])) .pw-copy { opacity: 0; transition: opacity .15s; }
    :host(:not([narrow])) .pw-row:hover .pw-copy, :host(:not([narrow])) .pw-copy:focus-visible { opacity: 1; }
  }
  /* The keyboard: every place it is on is seen. */
  .pside .frow:focus-visible, .ptabs .seg:focus-visible, .pb-stat:focus-visible {
    outline: 2px solid var(--ac-accent); outline-offset: 2px; }
  .pside .frow:focus-visible { outline-offset: -2px; border-radius: 12px; }
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
const readGroup = () => {
  try {
    return localStorage.getItem(GROUP_STORE) || "none";
  } catch (_err) {
    return "none";
  }
};
// The address: "#<room>" a room on the Rooms tab, "#week", "#stats", ... another tab (a room id is never a tab name).
const readHash = () => {
  const h = decodeURIComponent((location.hash || "").slice(1)) || null;
  return TABS.includes(h) ? { tab: h, room: null } : { tab: h ? "rooms" : null, room: h };
};

class ShcPanel extends ShcBase {
  constructor() {
    super();
    // The parts are drawn as in a card with every option on, each room open.
    this._config = { ...DEFAULTS };
    const { tab, room } = readHash();
    this._room = room;
    this._tab = tab || readTab();
    this._group = readGroup();
    // A changed address: its tab (kept as the last one) and its room.
    this._onHash = () => {
      const { tab, room } = readHash();
      if (tab) this._keepTab(tab);
      if (tab === "rooms" || !tab) this._room = room;
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
    this._writeHash();
    this._render();
    if (this._narrow) window.scrollTo(0, 0);
  }

  /** The address of what is shown: the room on the Rooms tab, else the tab (a link to it). */
  _writeHash() {
    const at = this._tab === "rooms" ? this._room : this._tab;
    history.replaceState(history.state, "", `${location.pathname}${location.search}${at ? `#${encodeURIComponent(at)}` : ""}`);
  }

  /** The tab shown, kept in the browser as the last one. */
  _keepTab(tab) {
    this._tab = TABS.includes(tab) ? tab : "rooms";
    try {
      localStorage.setItem(TAB_STORE, this._tab);
    } catch (_err) {
      // No storage: the tab is not kept.
    }
  }

  /** Show a tab (rooms, schedule, statistics, history, devices), in the address too. */
  _showTab(tab) {
    this._keepTab(tab);
    this._writeHash();
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
    // The keyboard: the arrows go from room to room in the list and from tab to tab.
    this._side.addEventListener("keydown", (ev) => this._listKey(ev));
    tabs.addEventListener("keydown", (ev) => this._tabKey(ev));
  }

  /** Up / Down (Home / End) in the list of rooms: the next room is chosen and keeps the focus. */
  _listKey(ev) {
    const step = { ArrowDown: 1, ArrowUp: -1, Home: -Infinity, End: Infinity }[ev.key];
    if (step === undefined || ev.altKey || ev.ctrlKey || ev.metaKey) return;
    const rows = [...this._side.querySelectorAll('.frow[data-key^="room-"]')];
    if (!rows.length) return;
    ev.preventDefault();
    const at = rows.indexOf(ev.target.closest?.(".frow"));
    const next = rows[Math.max(0, Math.min(rows.length - 1, Number.isFinite(step) ? (at < 0 ? 0 : at + step) : step < 0 ? 0 : rows.length - 1))];
    const room = next.dataset.key.slice(5);
    this._choose(room);
    this._side.querySelector(`.frow[data-key="room-${CSS.escape(room)}"]`)?.focus();
  }

  /** Left / Right on the tabs: the next tab, focused. */
  _tabKey(ev) {
    const step = { ArrowRight: 1, ArrowLeft: -1 }[ev.key];
    const tab = ev.target.closest?.('[data-action="panel-tab"]');
    if (!step || !tab) return;
    ev.preventDefault();
    const next = TABS[(TABS.indexOf(tab.dataset.option) + step + TABS.length) % TABS.length];
    this._showTab(next);
    this._tabs.querySelector(`[data-option="${next}"]`)?.focus();
  }

  /**
   * The house on a wide screen: name, presence, people and the values (outdoor,
   * season, demand, heating time) on a row; the mode, the heat source, the
   * scenarios and the buttons under it.
   */
  _houseBarHtml(house) {
    const e = house.entities;
    const presence = this._state(e.presence);
    const mode = this._state(e.mode);
    const source = this._state(e.heat_source);
    const outdoor = this._state(e.outdoor_average);
    const season = this._state(e.heating_season);
    const cutoff = this._state(e.outdoor_cutoff);
    const demand = this._state(e.heat_demand);
    const runtime = this._state(e.heating_runtime);
    const pause = this._state(e.pause);
    const people = this._people(house);
    const presenceIcon =
      { home: "home-outline", nearby: "map-marker-radius-outline", far: "map-marker-distance" }[presence?.state] || "home-search-outline";
    const onOff = (st) => (st ? (st.state === "on" ? this._t("on") : this._t("off")) : "–");
    const stat = (icon, label, value, entityId, cls = "") =>
      `<span class="pb-stat ${cls} ${entityId ? "link" : ""}" ${this._more(entityId)}><span class="k">${this._icon(icon)}<span>${esc(
        label
      )}</span></span><span class="v">${esc(value)}</span></span>`;
    // The heating time; a tap changes its period (as in the card).
    const period = this._period();
    const runtimeChip = runtime
      ? `<button class="pb-stat" data-action="period" title="${esc(this._t("period_hint"))}"><span class="k">${this._icon("timer-outline")}<span>${esc(`${this._t("runtime")} · ${this._t(`period_${period}`)}`)}</span></span><span
          class="v">${esc(this._runtimeText(e.heating_runtime))}</span></button>`
      : "";
    const modeOptions = mode?.attributes?.options || ["auto", "away", "vacation", "off", "summer"];
    const modes = modeOptions
      .map(
        (opt) => `<button class="seg ${mode?.state === opt ? "active" : ""}" data-action="mode" aria-pressed="${mode?.state === opt}"
          data-entity="${esc(e.mode)}" data-option="${esc(opt)}">${esc(this._label(mode, opt))}</button>`
      )
      .join("");
    return `<section class="block house pbar">
        <div class="pb-row">
          <span class="htitle">${this._icon("home-thermometer-outline")}<span class="name">${esc(house.name || this._t("title"))}</span></span>
          <span class="pill presence-state ${esc(presence?.state)} link" ${this._more(e.presence)}>${this._icon(presenceIcon)}${esc(
            this._label(presence)
          )}</span>
          ${people.count ? `<div class="avatars sm ${people.overlap}" title="${esc(people.who)}">${people.list(true, 8)}</div>` : ""}
          ${presence?.attributes?.arriving ? `<span class="pill arriving">${this._icon("arrow-right")}${esc(this._t("arriving"))}</span>` : ""}
          ${demand?.state === "on" ? this._flame(this._houseHeating(house), e.heat_demand) : ""}
          <div class="pb-stats">
            ${stat("weather-partly-cloudy", this._outdoorLabel(outdoor), this._temp(outdoor?.state), e.outdoor_average)}
            ${stat("calendar-range", this._t("season"), onOff(season), e.heating_season, season?.state === "on" ? "" : "off")}
            ${stat("fire", this._t("demand"), onOff(demand), e.heat_demand, demand?.state === "on" ? "hot" : "off")}
            ${runtimeChip}
          </div>
        </div>
        <div class="pb-row2">
          <div class="segmented ${modeOptions.length > 5 ? "many" : ""}" style="--n:${modeOptions.length}" role="group" aria-label="${esc(
            this._t("mode")
          )}">${modes}</div>
          ${source ? this._sourceHtml(source, e.heat_source) : ""}
          ${this._scenariosHtml(house)}
          <div class="pb-actions">${this._houseActions(house).join("")}</div>
        </div>
        ${this._cutoffHtml(outdoor, cutoff, e.outdoor_cutoff, mode, season, pause)}
        ${this._vacPanelHtml(house)}
      </section>`;
  }

  /** The level temperatures of a room as chips ("Eco 18°"), the level it is on marked. */
  _levelChips(a) {
    const levels = Object.keys(a.levels || {}).filter((p) => num(a.levels[p]) !== null);
    if (!levels.length) return "";
    return `<div class="prw-levels" role="list" aria-label="${esc(this._t("levels"))}">${levels
      .map(
        (p) => `<span role="listitem" class="prw-level ${a.preset === p ? "on" : ""}" style="--c:${PRESET_COLORS[p] || "var(--ac-accent)"}"><span
          class="dot"></span>${esc(this._presetName(a, p))} <b>${esc(this._levelTemp(a, p))}</b></span>`
      )
      .join("")}</div>`;
  }

  /** The chosen room on a wide screen: the room (arc, reason, next, buttons), its chart, then its day, levels and open sections. */
  _wideRoomBlocks(stateObj) {
    const a = stateObj.attributes;
    const e = a.entities || {};
    const id = a.room_id;
    const color = this._roomColor(a);
    const { head, hero, overrideMsg } = this._roomTop(stateObj);
    const sections = this._sectionParts(a, e, stateObj, true);
    const blocks = [
      {
        k: `room-${id}`,
        html: `<section class="block room open prw-left ${this._alertLevel(a)}" style="--c:${color}">${[
          head,
          hero,
          overrideMsg,
          this._noHeatHtml(a),
          this._alertsHtml(a),
          sections ? sections.buttons : "",
        ].join("")}</section>`,
      },
    ];
    if (this._config.show_timeline) {
      const failed = this._hist?.[id]?.failed ? `<p class="hint warn">${esc(this._t("chart_failed"))}</p>` : "";
      blocks.push({
        k: `chart-${id}`,
        html: `<section class="block prw-chart">${failed}${this._timelineHtml(a) || `<p class="empty">${esc(this._t("loading"))}</p>`}</section>`,
      });
    }
    const below = [this._todayHtml(a), this._levelChips(a), sections ? sections.bodies : ""].filter(Boolean).join("");
    if (below) blocks.push({ k: `below-${id}`, html: `<section class="block prw-below" style="--c:${color}">${below}</section>` });
    return blocks;
  }


  /** What redraws the panel: on the Devices tab also every device, its battery, and each minute (how long ago). */
  _watched() {
    const ids = super._watched();
    if (this._tab !== "devices") return ids;
    return [...ids, ...this._deviceIds(this._houses()), `minute:${Math.floor(Date.now() / 60000)}`];
  }

  /** Open a room on the Rooms tab; with a part of it (its schedule, its Details) shown. */
  _openRoom(room, key = null) {
    this._keepTab("rooms");
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
    // The grouping of the rooms (when the rooms have floors or circuits).
    const modes = this._groupModes(rooms);
    const gmode = this._groupMode(rooms);
    this._gmodeNow = gmode;
    const groupPick =
      modes.length > 1
        ? `<select class="pgroup" data-action="panel-group" aria-label="${esc(this._t("gr_label"))}" title="${esc(this._t("gr_label"))}">${modes
            .map((m) => `<option value="${m}" ${m === gmode ? "selected" : ""}>${esc(this._t(`gr_${m}`))}</option>`)
            .join("")}</select>`
        : "";
    this._patch(this._tabs, [
      {
        k: "tabs",
        html: `<div class="ptabrow"><div class="segmented" style="--n:${TABS.length}" role="tablist">${TABS.map(
          (t) => `<button class="seg ${t === tab ? "active" : ""}" role="tab" aria-selected="${t === tab}" data-action="panel-tab"
            data-option="${t}">${esc(this._t(`tab_${t}`))}${
              t === "history" && alerts ? `<span class="tabcount" aria-label="${esc(`${this._t("an_title")}: ${alerts}`)}">${alerts}</span>` : ""
            }</button>`
        ).join("")}</div>${groupPick}</div>`,
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
    // The name of the house; with several houses (or none named) the name of the integration.
    const title = houses.length === 1 && houses[0].name ? houses[0].name : NAME;
    this._top.querySelector("h1").textContent = this._narrow && chosen && tab === "rooms" ? chosen.attributes.room_name : title;

    // The house (each house, with its banners).
    const top = [];
    if (!houses.length) top.push({ k: "empty", html: `<p class="empty">${this._t("no_rooms")}</p>` });
    for (const house of houses) {
      const pause = this._pauseBanner(house);
      if (pause) top.push({ k: `pause-${house.id}`, html: pause });
      const guest = this._guestBanner(house);
      if (guest) top.push({ k: `guest-${house.id}`, html: guest });
      top.push({ k: `house-${house.id}`, html: this._narrow ? this._houseHtml(house) : this._houseBarHtml(house) });
    }
    this._patch(this._house, top);

    // The rooms: a folded row each, the chosen one marked; the house names when there are several.
    const list = [];
    for (const house of houses) {
      if (houses.length > 1) list.push({ k: `hname-${house.id}`, html: `<p class="hname">${esc(house.name || "")}</p>` });
      for (const g of this._roomGroups(house.rooms, gmode)) {
        if (g.name !== null) list.push({ k: `gname-${house.id}-${g.key}`, html: `<p class="hname gname">${esc(g.name)}</p>` });
        for (const r of g.rooms) {
          const a = r.attributes;
          list.push({ k: `row-${a.room_id}`, html: this._foldedRow(r, this._roomColor(a)) });
        }
      }
    }
    this._side.hidden = !rooms.length;
    this._patch(this._side, list);
    for (const node of this._side.children) node.classList.toggle("chosen", node.__k === `row-${room}`);

    // The chosen room, open.
    if (chosen) this._open[`room-${chosen.attributes.room_id}`] = true;
    this._card.hidden = !chosen;
    // Wide: the room, its chart beside it and its day under them; on a phone the room as in the card.
    const wide = !!chosen && !this._narrow;
    this._card.classList.toggle("wide", wide);
    this._patch(
      this._card,
      !chosen ? [] : wide ? this._wideRoomBlocks(chosen) : [{ k: `room-${room}`, html: this._roomHtml(chosen) }]
    );

    // The week, the statistics or the history
    // (the alerts on now on top); fetched only while shown.
    const extra = [];
    if (tab === "week") extra.push({ k: "week", html: this._weekHtml(houses) });
    if (tab === "stats") {
      extra.push({ k: "stats", html: this._statsHtml(houses) });
      const heat = this._heatmapHtml(houses);
      if (heat) extra.push({ k: "heatmap", html: heat });
    }
    if (tab === "devices") {
      const humidity = this._humidityTabHtml(houses);
      if (humidity) extra.push({ k: "humidity", html: humidity });
      extra.push({ k: "devices", html: this._devicesTabHtml(houses) });
    }
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
    const go = ev.target.closest?.(
      '[data-action="week-edit"], [data-action="week-copy"], [data-action="alert-room"], [data-action="humidity-room"]'
    );
    if (go) {
      const room = go.dataset.room;
      const action = go.dataset.action;
      if (action === "week-edit") this._startEdit(room);
      if (action === "week-copy") {
        this._copyFrom = room;
        this._copyTo = new Set();
        this._copyDone = null;
      }
      const key =
        action === "week-edit" || action === "week-copy" ? `sched-${room}` : action === "humidity-room" ? `details-${room}` : null;
      if (key) this._open[key] = true;
      this._openRoom(room, key);
      return;
    }
    const own = ev.target.closest?.(
      '[data-action="panel-tab"], [data-action="stats-period"], [data-action="stats-pick"], [data-action="history-kind"], [data-action="week-day"], [data-action="heat-day"], [data-action="stats-dot"], [data-action="heat-cell"]'
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
      } else if (action === "week-day") this._weekDay = option;
      else if (action === "heat-day") {
        this._heatDay = option;
        this._heatCell = null;
      } else if (action === "stats-dot") {
        // A tap on a point of the outdoor line: its mean, lowest and highest (again: hidden).
        const t = Number(own.dataset.t);
        this._statsDot = t === this._statsDot ? null : t;
      } else if (action === "heat-cell") {
        // A tap on an hour of the heating by hour: its minutes (again, or ✕: hidden).
        const cell = own.dataset.cell || null;
        this._heatCell = cell === this._heatCell ? null : cell;
      }
      else this._historyKind = option;
      this._render();
      return;
    }
    return super._onClick(ev);
  }

  /** The room chosen for the history. */
  async _onChange(ev) {
    if (ev.target?.dataset?.action === "panel-group") {
      this._group = ev.target.value;
      try {
        localStorage.setItem(GROUP_STORE, this._group);
      } catch (_err) {
        // No storage: the grouping is not kept.
      }
      ev.target.blur();
      this._render();
      return;
    }
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
