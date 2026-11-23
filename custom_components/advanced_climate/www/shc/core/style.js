// The style of the card and the panel: colours from the Home Assistant theme.

export const STYLE = `
  :host {
    --ac-surface: color-mix(in srgb, var(--primary-text-color) 4%, transparent);
    --ac-surface-2: color-mix(in srgb, var(--primary-text-color) 7%, transparent);
    --ac-line: color-mix(in srgb, var(--primary-text-color) 12%, transparent);
    --ac-muted: var(--secondary-text-color);
    --ac-accent: var(--primary-color);
    --ac-fixed: color-mix(in srgb, var(--primary-text-color) 65%, transparent);
    --ac-out: #7d8ea8;
    --ac-sun: #ffc61a;
    --ac-hot: #d9480f;
    --ac-warn: #c98a12;
    --ac-err: var(--error-color, #db4437);
    --ac-teal: #2f9e8f;
    /* The chosen button (mode, scenario): tinted with the accent, never only bold. */
    --ac-active-bg: color-mix(in srgb, var(--ac-accent) 18%, transparent);
    --ac-active-fg: color-mix(in srgb, var(--ac-accent) 72%, var(--primary-text-color));
    --ac-active-line: color-mix(in srgb, var(--ac-accent) 55%, transparent);
    /* Text on an amber or red tint stays readable in a light and a dark theme. */
    --ac-warn-fg: color-mix(in srgb, var(--warning-color, #f0ad4e) 62%, var(--primary-text-color));
    --ac-err-fg: color-mix(in srgb, var(--ac-err) 75%, var(--primary-text-color));
    color: var(--primary-text-color);
    font-variant-numeric: tabular-nums;
  }
  ha-card { padding: 16px; color: var(--primary-text-color); display: flex; flex-direction: column; gap: 12px; }
  .title { margin: 0; font-size: 1.35em; font-weight: 500; letter-spacing: -0.01em; }
  .empty { margin: 0; color: var(--ac-muted); }
  .muted { color: var(--ac-muted); font-size: 0.85em; }
  .block { border: 1px solid transparent; border-radius: 16px; padding: 16px; display: flex; flex-direction: column; gap: 12px;
    background: var(--ac-surface); }
  .house { background: var(--ac-surface); }
  .name { font-weight: 600; font-size: 1.1em; }
  .label { font-size: 0.8em; color: var(--ac-muted); margin-bottom: -4px; }
  .row { display: flex; gap: 10px; align-items: center; }
  .row.wrap { flex-wrap: wrap; }
  .row.end { justify-content: flex-end; }
  .controls { align-items: flex-end; }
  .controls .toggle { min-height: 36px; }
  .hint { margin: 0; font-size: 0.85em; color: var(--ac-muted); line-height: 1.45; }
  .hint.ok { color: #2f9e8f; }
  .hint.warn { color: var(--ac-warn); }
  .error { margin: 0; color: var(--error-color, #db4437); font-size: 0.85em; }

  button.period { font: inherit; color: inherit; text-align: left; cursor: pointer; border: none; background: none; padding: 0; }
  .details button.period { width: 100%; }
  .stack { display: grid; }
  .stack > span { grid-area: 1 / 1; visibility: hidden; }
  .stack > span.on { visibility: visible; }
  .details button.period dt { font-size: 0.75em; color: var(--ac-muted); }
  .details button.period dd { margin: 2px 0 0; font-variant-numeric: tabular-nums; font-weight: 500; }
  button.period:hover .k, button.period:hover dt { text-decoration: underline dotted; }

  /* pills */
  .pill { display: inline-flex; align-items: center; gap: 4px; font-size: 0.8em; padding: 3px 10px;
    border-radius: 999px; background: var(--ac-surface-2); white-space: nowrap; }
  .pill { min-height: 26px; box-sizing: border-box; font-weight: 500; }
  .pill.rule { background: var(--ac-surface-2); color: var(--primary-text-color); font-weight: 500; }
  .pill.active, .pill.arriving { background: var(--ac-active-bg); color: var(--ac-active-fg); box-shadow: inset 0 0 0 1px var(--ac-active-line); font-weight: 600; }
  .pill.hot { background: var(--ac-hot); color: #fff; }
  .pill.warn { background: color-mix(in srgb, var(--warning-color, #f0ad4e) 18%, transparent); color: var(--ac-warn-fg); }
  .presence-state.home { background: color-mix(in srgb, #f08c00 18%, transparent); }
  .presence-state.nearby { background: color-mix(in srgb, #2f9e8f 22%, transparent); }
  .presence-state.far { background: color-mix(in srgb, #8a96a3 25%, transparent); }

  /* buttons */
  .btn { display: inline-flex; align-items: center; gap: 6px; font: inherit; font-size: 0.9em; font-weight: 500;
    padding: 7px 14px; border-radius: 10px; border: 1px solid var(--ac-line); background: var(--card-background-color);
    color: var(--primary-text-color); cursor: pointer; transition: background .15s, border-color .15s; }
  .btn:hover { background: var(--ac-surface-2); }
  .house-actions { display: grid; grid-template-columns: repeat(auto-fit, minmax(0, 1fr)); gap: 8px; }
  .house-actions .btn { justify-content: center; padding: 7px 8px; min-width: 0; }
  .house-actions .btn span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .btn.soft-accent { color: color-mix(in srgb, var(--ac-accent) 75%, var(--primary-text-color)); background: color-mix(in srgb, var(--ac-accent) 12%, transparent);
    border-color: color-mix(in srgb, var(--ac-accent) 40%, transparent); }
  .btn.soft-warn { color: color-mix(in srgb, var(--warning-color, #f0ad4e) 70%, var(--primary-text-color)); background: color-mix(in srgb, var(--warning-color, #f0ad4e) 12%, transparent);
    border-color: color-mix(in srgb, var(--warning-color, #f0ad4e) 45%, transparent); }
  .btn.soft-accent:hover, .btn.soft-warn:hover { filter: brightness(1.1); }
  .btn ha-icon { --mdc-icon-size: 18px; }
  .btn.primary { background: var(--ac-accent); border-color: var(--ac-accent); color: var(--text-primary-color, #fff); }
  .btn.primary:hover { filter: brightness(1.08); }
  .btn.danger { color: var(--error-color, #db4437); border-color: color-mix(in srgb, var(--error-color, #db4437) 40%, transparent); }
  .btn.icon-only { padding: 6px; }
  .btn.icon-only .x { display: none; }
  .btn.icon-only ha-icon:not(:defined) + .x { display: inline; }
  .segmented { display: grid; grid-template-columns: repeat(var(--n, 4), minmax(0, 1fr)); padding: 4px; gap: 4px;
    border-radius: 12px; background: var(--ac-surface-2); }
  .seg { border: none; background: none; min-height: 36px; padding: 0 8px; border-radius: 9px; font: inherit; font-size: 0.88em;
    font-weight: 500; color: var(--ac-muted); cursor: pointer; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0; }
  .seg:hover { color: var(--primary-text-color); background: var(--ac-surface); }
  .scenarios { display: flex; flex-direction: column; gap: 8px; }
  .scenarios .sclabel { display: inline-flex; align-items: center; gap: 6px; font-size: 0.85em; color: var(--ac-muted); }
  .scenarios .sclabel ha-icon { --mdc-icon-size: 16px; }
  .segmented.many .seg { font-size: 0.82em; padding: 0 2px; }
  .seg.active, .seg.active:hover { background: var(--ac-active-bg); color: var(--ac-active-fg); font-weight: 600;
    box-shadow: inset 0 0 0 1px var(--ac-active-line); }
  .toggle { display: inline-flex; align-items: center; gap: 8px; background: none; border: none; font: inherit;
    color: var(--primary-text-color); cursor: pointer; padding: 4px 0; }
  .toggle .knob { width: 34px; height: 20px; border-radius: 10px; background: var(--disabled-color, #bdbdbd); position: relative; flex: none; }
  .toggle .knob::after { content: ""; position: absolute; top: 3px; left: 3px; width: 14px; height: 14px;
    border-radius: 50%; background: #fff; transition: transform .15s; }
  .toggle.on .knob { background: var(--ac-accent); }
  .toggle.on .knob::after { transform: translateX(14px); }
  button:focus-visible, input:focus-visible, select:focus-visible, summary:focus-visible {
    outline: 2px solid var(--ac-accent); outline-offset: 2px; }

  /* fields */
  input, select { font: inherit; color: var(--primary-text-color); background: var(--ac-opaque, var(--card-background-color));
    border: 1px solid var(--ac-line); border-radius: 10px; padding: 7px 10px; min-height: 36px; box-sizing: border-box; }
  option, optgroup { color: var(--primary-text-color); background: var(--ac-opaque, var(--card-background-color, #fff)); }
  input:hover, select:hover { border-color: color-mix(in srgb, var(--primary-text-color) 30%, transparent); }
  input:focus, select:focus { border-color: var(--ac-accent); outline: none; }
  .dates { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 10px; }
  .datefield, .selectfield, .textfield { display: flex; flex-direction: column; gap: 4px; font-size: 0.8em; color: var(--ac-muted); }
  .datefield input, .selectfield select, .textfield input { font-size: 1.1em; }
  /* A field never wider than its room (a long option on a small phone with big text). */
  .datefield, .selectfield, .textfield { min-width: 0; max-width: 100%; }
  .datefield input, .selectfield select, .textfield input { max-width: 100%; min-width: 0; box-sizing: border-box; }
  .datefield input { width: 100%; }
  input[type="datetime-local"]::-webkit-calendar-picker-indicator,
  input[type="time"]::-webkit-calendar-picker-indicator { cursor: pointer; opacity: .7; }
  .numfield { display: inline-flex; align-items: center; gap: 6px; font-size: 0.9em; }
  .numfield span { color: var(--ac-muted); font-size: 0.9em; }
  .numfield em { font-style: normal; color: var(--ac-muted); }
  .numfield input { width: 5em; text-align: right; }
  .numfield.level { display: grid; grid-template-columns: 10px 1fr auto auto; padding: 6px 10px; border-radius: 12px; background: var(--ac-surface); }
  .numfield.level .lname { color: var(--primary-text-color); }

  /* rooms */
  .room-title { display: inline-flex; align-items: center; gap: 8px; background: none; border: none; padding: 0;
    font: inherit; color: inherit; cursor: pointer; text-align: left; }
  .chev { width: 8px; height: 8px; border-right: 2px solid var(--ac-muted); border-bottom: 2px solid var(--ac-muted);
    transform: rotate(-45deg); transition: transform .15s; }
  .chev.open { transform: rotate(45deg); }
  .toggle.sm { font-size: 0.85em; margin-left: auto; }
  .quickset { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
  .qnote { margin: 6px 0 0; color: color-mix(in srgb, var(--warning-color, #f0ad4e) 75%, var(--primary-text-color)); }
  .quickset .btn { min-height: 36px; }
  .quickset .numfield { gap: 4px; white-space: nowrap; }
  /* No arrows: they covered the value ("17" for 17.5, "aut" for auto); the
     value is typed, or changed with the arrow keys. Room for "100.5" (°F). */
  .quickset .numfield input { width: 4.8em; padding: 7px 8px; text-align: center; -moz-appearance: textfield; appearance: textfield; }
  .quickset .numfield input::-webkit-inner-spin-button,
  .quickset .numfield input::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
  .lockrow { display: flex; align-items: center; background: var(--ac-surface); border-radius: 10px; padding: 4px 10px; }
  .lockrow .toggle { width: 100%; justify-content: space-between; flex-direction: row-reverse; font-size: 0.9em; }
  .lockrow .toggle .knob { background: var(--ac-line); }
  .lockrow .toggle.on .knob { background: var(--ac-accent); }
  .profile.off > .sbar, .profile.off > .intervals { opacity: 0.45; }
  .confirmbox { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; padding: 8px 10px; border-radius: 10px;
    background: color-mix(in srgb, var(--ac-warn) 14%, transparent); }
  .confirmbox > span { flex: 1 1 200px; }
  .copybox { display: flex; flex-direction: column; gap: 8px; margin-top: 8px; padding: 10px 12px; border-radius: 10px; background: var(--ac-surface-2); }
  .copybox .daychecks label { min-height: 32px; }
  .btn[disabled] { opacity: 0.5; cursor: default; }
  .daychecks { display: flex; flex-wrap: wrap; gap: 6px 10px; align-items: center; font-size: 0.9em; }
  .daychecks label { display: inline-flex; gap: 4px; align-items: center; }
  dd small.sub { display: block; font-size: 0.8em; color: var(--ac-muted); }
  .decision { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }
  .reason { margin: 0; color: var(--ac-muted); font-size: 0.9em; }
  .pill.wrap { white-space: normal; text-align: left; }

  .link { cursor: pointer; }
  .link:hover { filter: brightness(0.96); }
  .link:focus-visible { outline: 2px solid var(--ac-accent); outline-offset: 2px; }
  /* messages: one shape, the colour says how much it matters */
  .msg { --t: var(--ac-muted); --tb: var(--ac-surface-2); display: flex; align-items: center; gap: 12px; padding: 12px;
    border-radius: 12px; background: var(--tb); font-size: 0.9em; line-height: 1.45; }
  .msg.warn { --t: var(--ac-warn-fg); --tb: color-mix(in srgb, var(--warning-color, #f0ad4e) 15%, transparent); }
  .msg.teal { --t: color-mix(in srgb, var(--ac-teal) 75%, var(--primary-text-color)); --tb: color-mix(in srgb, var(--ac-teal) 15%, transparent); }
  .msg.error { --t: var(--ac-err-fg); --tb: color-mix(in srgb, var(--ac-err) 13%, transparent); }
  .msg.plain { --t: var(--primary-text-color); --tb: transparent; box-shadow: inset 0 0 0 1px var(--ac-line); }
  .micon { width: 32px; height: 32px; flex: none; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center;
    color: var(--t); background: color-mix(in srgb, currentColor 16%, transparent); }
  .msg.info .micon, .msg.plain .micon { background: var(--ac-surface-2); }
  .micon ha-icon { --mdc-icon-size: 18px; }
  .mtext { flex: 1; min-width: 0; overflow-wrap: anywhere; }
  .mtext b { font-weight: 600; }
  .mbtn { flex: none; min-height: 36px; padding: 0 12px; border-radius: 10px; border: 1px solid var(--ac-line);
    background: var(--card-background-color); color: var(--primary-text-color); font: inherit; font-size: 0.95em; font-weight: 600; cursor: pointer; }
  .mbtn:hover { background: var(--ac-surface-2); }
  .mchev { flex: none; width: 7px; height: 7px; margin: 0 6px 0 2px; border-right: 2px solid var(--ac-muted);
    border-bottom: 2px solid var(--ac-muted); transform: rotate(-45deg); }
  .details.devices div.dev { display: flex; align-items: center; gap: 10px; padding: 6px 10px; }
  .details.devices div.dev ha-icon { --mdc-icon-size: 20px; color: var(--ac-muted); flex: none; }
  .details.devices .dname { flex: 1; min-width: 0; display: flex; flex-direction: column; }
  .details.devices .dname span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .details.devices .dname small { color: var(--ac-muted); font-size: 0.75em; }
  .details.devices .dval { flex: none; font-variant-numeric: tabular-nums; font-weight: 500; }
  .details.devices div.dev.bad { box-shadow: inset 3px 0 0 var(--ac-warn); }
  .details.devices div.dev.bad .dval, .details.devices div.dev.bad ha-icon { color: var(--ac-warn); }
  .alertbox { border-radius: 12px; box-shadow: inset 0 0 0 1px var(--ac-line); overflow: hidden; }
  .ahead { display: flex; align-items: center; gap: 8px; padding: 10px 12px; font-weight: 600; border-bottom: 1px solid var(--ac-line); }
  .acount { min-width: 22px; height: 22px; padding: 0 6px; box-sizing: border-box; border-radius: 999px; font-size: 0.78em; font-weight: 700;
    display: inline-flex; align-items: center; justify-content: center; color: var(--ac-err-fg);
    background: color-mix(in srgb, var(--ac-err) 16%, transparent); }
  ul.alerts { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; }
  ul.alerts li { --t: var(--ac-warn-fg); display: flex; gap: 12px; align-items: flex-start; padding: 12px; font-size: 0.9em; }
  ul.alerts li + li { border-top: 1px solid var(--ac-line); }
  ul.alerts li.error { --t: var(--ac-err-fg); }
  ul.alerts .micon { width: 28px; height: 28px; }
  ul.alerts .micon ha-icon { --mdc-icon-size: 16px; }
  ul.alerts .atext { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
  ul.alerts .atext span { color: var(--ac-muted); line-height: 1.45; overflow-wrap: anywhere; }
  ul.alerts .mchev { align-self: center; }
  .chart-card { border-radius: 14px; background: var(--ac-surface); padding: 12px 12px 10px;
    box-shadow: inset 0 0 0 1px var(--ac-line); display: flex; flex-direction: column; gap: 4px; }
  .hchart.with-out { height: 210px; }
  dialog.chartpop { width: min(960px, calc(100vw - 24px)); max-width: none; max-height: calc(100vh - 24px);
    padding: 12px 14px 14px; border: none; border-radius: 18px; color: var(--primary-text-color);
    background: var(--ha-card-background, var(--card-background-color, var(--primary-background-color, #1c1c1c)));
    background-image: none; backdrop-filter: none; opacity: 1; box-sizing: border-box;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.45); overflow: auto; }
  dialog.chartpop::backdrop { background: rgba(0, 0, 0, 0.55); }
  dialog.chartpop .pophead { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
  dialog.chartpop .pophead .name { font-size: 1.15em; font-weight: 600; }
  dialog.chartpop .popclose { background: none; border: none; color: inherit; cursor: pointer; padding: 6px;
    border-radius: 50%; display: inline-flex; }
  dialog.chartpop .popclose:hover { background: var(--ac-surface-2); }
  dialog.chartpop .hchart { height: min(55vh, 420px); }
  dialog.chartpop .hchart.with-out { height: min(62vh, 480px); }
  .hchart { position: relative; height: 170px; margin-left: 32px; touch-action: pan-y; cursor: crosshair; user-select: none; }
  .hchart svg { width: 100%; height: 100%; display: block; overflow: hidden; }
  .hchart.zoomed { cursor: grab; }
  .hchart.zoomed:active { cursor: grabbing; }
  .zoombar { display: flex; justify-content: space-between; align-items: center; gap: 8px; margin: -2px 0 10px; }
  .zrange { font-size: 0.78em; color: var(--ac-muted); font-variant-numeric: tabular-nums; }
  .zbtns { display: inline-flex; gap: 2px; padding: 2px; border-radius: 9px; background: var(--ac-surface-2); }
  .zbtn { font: inherit; font-size: 0.78em; min-width: 30px; height: 26px; padding: 0 8px; border: none; border-radius: 7px;
    background: none; color: var(--primary-text-color); cursor: pointer; font-variant-numeric: tabular-nums; }
  .zbtn:hover { background: var(--card-background-color); }
  .zbtn.active { background: var(--card-background-color); color: var(--ac-accent); font-weight: 600;
    box-shadow: 0 1px 2px rgba(0,0,0,.15); }
  .hchart .grid { stroke: var(--ac-line); stroke-width: 1; vector-effect: non-scaling-stroke; }
  .hchart .futurebg { fill: var(--primary-text-color); opacity: 0.03; }
  .hchart .oband { fill: var(--primary-text-color); opacity: 0.03; }
  .hchart .sunarea { fill: var(--ac-sun); opacity: 0.3; }
  .hchart .oline { fill: none; stroke: var(--ac-out); stroke-width: 1.6; vector-effect: non-scaling-stroke; stroke-linejoin: round; }
  .hchart .oline.future { stroke-dasharray: 4 4; opacity: 0.8; }
  .hchart .ocut { stroke: var(--ac-hot); stroke-width: 1; stroke-dasharray: 2 3; opacity: 0.6; vector-effect: non-scaling-stroke; }
  .hchart .optband { opacity: 0.08; }
  .hchart .optline { stroke-width: 1.5; stroke-dasharray: 3 3; vector-effect: non-scaling-stroke; }
  .optlab { position: absolute; transform: translate(4px, calc(-100% - 4px)); font-size: 0.68em; white-space: nowrap; padding: 1px 6px;
    border-radius: 6px; color: var(--primary-text-color); background: color-mix(in srgb, var(--c) 18%, var(--card-background-color)); }
  .optlab.end { transform: translate(calc(-100% - 4px), calc(-100% - 4px)); }
  .optlab.below { transform: translate(4px, 4px); }
  .optlab.end.below { transform: translate(calc(-100% - 4px), 4px); }
  .ylabels .olab { color: var(--ac-out); }
  .lg-out { background: var(--ac-out); }
  .hchart .heatlane { fill: var(--primary-text-color); opacity: 0.05; }
  .hchart .heatbar { fill: var(--ac-hot); opacity: 0.9; }
  .hchart .heatbar.future { opacity: 0.35; }
  .lg-heat.future { opacity: 0.35 !important; }
  .hchart .daysep { stroke: var(--primary-text-color); stroke-width: 1; opacity: 0.18; vector-effect: non-scaling-stroke; }
  .hchart .tline { stroke-width: 2.5; vector-effect: non-scaling-stroke; stroke-linecap: round; }
  .hchart .tline.future { stroke-dasharray: 6 5; opacity: 0.75; }
  .hchart .tstep { stroke: var(--primary-text-color); opacity: 0.25; stroke-width: 1; stroke-dasharray: 2 3; vector-effect: non-scaling-stroke; }
  .hchart .templine { fill: none; stroke: var(--ac-accent); stroke-width: 2.25; vector-effect: non-scaling-stroke;
    stroke-linejoin: round; stroke-linecap: round; }
  .hchart .predline { fill: none; stroke: var(--ac-accent); stroke-width: 2; stroke-dasharray: 2 4; opacity: 0.85;
    vector-effect: non-scaling-stroke; stroke-linejoin: round; stroke-linecap: round; }
  .lg-pred { background: repeating-linear-gradient(90deg, var(--ac-accent) 0 3px, transparent 3px 6px); }
  .hchart .now { stroke: var(--primary-text-color); stroke-width: 1.25; opacity: 0.55; stroke-dasharray: 3 3; vector-effect: non-scaling-stroke; }
  .overlay { position: absolute; inset: 0; pointer-events: none; }
  .overlay .lvl { position: absolute; transform: translate(4px, calc(-100% - 4px)); font-size: 0.7em; white-space: nowrap;
    padding: 1px 6px; border-radius: 6px; background: color-mix(in srgb, var(--card-background-color) 88%, transparent);
    color: var(--primary-text-color); display: inline-flex; align-items: center; gap: 5px; }
  .overlay .lvl.end { transform: translate(-4px, calc(-100% - 4px)); }
  .overlay .lvl::before { content: ""; width: 7px; height: 7px; border-radius: 50%; background: var(--c); }
  .overlay .lvl.future { color: var(--ac-muted); }
  .ylabels span { position: absolute; right: calc(100% + 6px); transform: translateY(-50%); font-size: 0.68em;
    color: var(--ac-muted); font-variant-numeric: tabular-nums; white-space: nowrap; }
  .nowlabel { position: absolute; top: -2px; transform: translate(-50%, -100%); font-size: 0.65em; color: var(--ac-muted);
    text-transform: uppercase; letter-spacing: 0.06em; }
  .nowdot { position: absolute; width: 9px; height: 9px; border-radius: 50%; background: var(--ac-accent);
    transform: translate(-50%, -50%); box-shadow: 0 0 0 3px color-mix(in srgb, var(--ac-accent) 25%, transparent); }
  .cross { position: absolute; top: 0; bottom: 0; width: 0; border-left: 1px solid var(--primary-text-color); opacity: 0.45; }
  .ticks { position: relative; height: 14px; margin-left: 32px; font-size: 0.68em; color: var(--ac-muted); }
  .cross[hidden], .tip[hidden] { display: none; }
  .navbar { position: relative; height: 18px; margin: 6px 0 2px 32px; border-radius: 6px; background: var(--ac-surface-2);
    cursor: pointer; touch-action: none; user-select: none; overflow: hidden;
    opacity: 0; transition: opacity 0.25s ease; }
  /* Shown while the mouse is over the chart or a finger is on it, then hidden
     (still there to be dragged: a finger on its place shows it). */
  @media (hover: hover) { .chart-card:hover .navbar { opacity: 1; } }
  .chart-card.touching .navbar, .chart-card.navigating .navbar { opacity: 1; }
  .details small.warn { color: var(--ac-warn); font-weight: 600; }
  .navbar i { position: absolute; top: 0; bottom: 0; display: block; }
  .navbar .navheat { top: auto; height: 4px; bottom: 0; background: var(--ac-hot); opacity: 0.7; }
  .navbar .navnow { width: 0; border-left: 1px dashed var(--primary-text-color); opacity: 0.5; }
  .navbar .navwin { border-radius: 6px; cursor: grab; background: color-mix(in srgb, var(--ac-accent) 22%, transparent);
    box-shadow: inset 0 0 0 1.5px var(--ac-accent); min-width: 6px; }
  .navbar:active .navwin { cursor: grabbing; }
  .ticks span { position: absolute; transform: translateX(-50%); white-space: nowrap; }
  .readout { display: flex; gap: 14px; flex-wrap: wrap; align-items: center; font-size: 0.78em; color: var(--ac-muted);
    min-height: 20px; font-variant-numeric: tabular-nums; }
  .tip { position: absolute; top: 4px; display: flex; flex-direction: column; gap: 2px; padding: 6px 9px; border-radius: 10px;
    font-size: 0.75em; white-space: nowrap; font-variant-numeric: tabular-nums; color: var(--primary-text-color);
    background: var(--ac-opaque, var(--card-background-color, #fff)); box-shadow: 0 2px 10px rgba(0,0,0,.18);
    border: 1px solid var(--ac-line); z-index: 3; }
  .tip span { display: inline-flex; align-items: center; gap: 6px; }
  .tip i { display: inline-block; width: 10px; height: 3px; border-radius: 2px; }
  .tip .hotword { color: var(--ac-hot); font-weight: 600; }
  .tip .optword { font-weight: 600; }
  .lg { display: inline-flex; align-items: center; gap: 6px; font: inherit; color: inherit; background: none; border: none;
    padding: 2px 4px; margin: -2px -4px; border-radius: 6px; cursor: pointer; }
  .lg:hover, .lg:focus-visible { background: var(--ac-surface-2); }
  .lg.off { opacity: 0.45; text-decoration: line-through; }
  .lg-sun { background: color-mix(in srgb, var(--ac-sun) 55%, transparent); height: 8px !important; }
  .lg i { display: inline-block; width: 14px; height: 3px; border-radius: 2px; }
  .lg-temp { background: var(--ac-accent); }
  .lg-target { background: linear-gradient(90deg, #f08c00, #5f6fd1); }
  .lg-heat { background: var(--ac-hot); height: 8px !important; opacity: 0.8; }
  .meta { display: flex; justify-content: space-between; gap: 8px; flex-wrap: wrap; font-size: 0.85em; margin-top: 4px; }
  .presets { display: flex; flex-wrap: wrap; gap: 4px 12px; }
  .preset { display: inline-flex; align-items: center; gap: 5px; font: inherit; font-size: 0.85em; padding: 4px 8px;
    border-radius: 999px; cursor: pointer; background: none; color: var(--primary-text-color); border: none; }
  .preset:hover, .preset:focus-visible { background: var(--ac-surface-2); }
  .preset small { color: var(--ac-muted); }
  .preset .dot { background: var(--c); }
  .dot { width: 10px; height: 10px; border-radius: 50%; background: var(--c); display: inline-block; flex: none; }

  /* folds */
  .fold { border-top: 1px solid var(--ac-line); padding-top: 8px; }
  .fold summary { cursor: pointer; display: flex; justify-content: space-between; gap: 8px; align-items: center;
    list-style: none; font-weight: 500; padding: 2px 0; }
  .fold summary::-webkit-details-marker { display: none; }
  .fold summary::after { content: ""; width: 7px; height: 7px; border-right: 2px solid var(--ac-muted);
    border-bottom: 2px solid var(--ac-muted); transform: rotate(45deg); margin-right: 4px; transition: transform .15s; flex: none; }
  .fold[open] summary::after { transform: rotate(-135deg); }
  .fold summary .muted { margin-left: auto; font-weight: 400; }
  .fold-body { display: flex; flex-direction: column; gap: 10px; padding-top: 10px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 8px; }
  .details { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 8px; margin: 0; }
  .details div { background: var(--ac-surface); border-radius: 10px; padding: 8px 10px; }
  .details div.wide { grid-column: 1 / -1; }
  .details div.learn { display: flex; gap: 8px; align-items: center; justify-content: space-between; padding: 0; background: none; }
  .details div.learn > div.link { flex: 1; min-width: 0; }
  .details div.learn .btn { flex: none; min-width: 7.5em; justify-content: center; }
  .details div.ltile dd { font-size: 1.05em; }
  .lbar { display: block; margin-top: 6px; font-weight: 400; font-size: 0.85em; }
  .lbar-text { display: block; color: var(--ac-muted); }
  .lbar-track { display: block; height: 6px; margin-top: 3px; border-radius: 3px; background: var(--ac-line); overflow: hidden; }
  .lbar-track span { display: block; height: 100%; border-radius: 3px; background: var(--ac-accent); }
  .lbar + small.sub, .lbar ~ small.sub { margin-top: 6px; }
  .sublabel { font-size: 0.75em; color: var(--ac-muted); margin: 6px 0 -2px; }
  .details dt { font-size: 0.75em; color: var(--ac-muted); }
  .details dd { margin: 2px 0 0; font-variant-numeric: tabular-nums; font-weight: 500; }
  .levels-line { display: flex; gap: 12px; flex-wrap: wrap; font-size: 0.85em; align-items: center; }
  .lv { display: inline-flex; gap: 5px; align-items: center; padding: 2px 8px; border-radius: 999px; }
  .lv.active { background: var(--ac-surface-2); font-weight: 600; }

  /* schedule */
  .profiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 10px; }
  .profile { border-radius: 12px; padding: 10px 12px; background: var(--ac-surface); display: flex; flex-direction: column; gap: 6px; }
  .profile.today { box-shadow: inset 0 0 0 1.5px var(--ac-accent); }
  .phead { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
  .phead .muted { flex: 1 1 100%; }
  .profile.edit .phead .muted { flex: 1; }
  .intervals { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 4px; }
  .intervals li { display: grid; grid-template-columns: 10px auto 1fr; gap: 8px; align-items: center; font-size: 0.9em; }
  .intervals .range { font-variant-numeric: tabular-nums; }
  .intervals .pname { text-align: right; color: var(--ac-muted); }
  small { font-size: 0.8em; color: var(--ac-muted); }
  .editor { border-radius: 14px; background: var(--ac-surface); padding: 12px; display: flex; flex-direction: column; gap: 12px; }
  .ehead { font-size: 1em; }
  .slot-head, .slot-row { display: grid; grid-template-columns: 10px minmax(130px, 150px) minmax(90px, auto) 1fr auto; gap: 8px; align-items: center; }
  .slot-head { font-size: 0.75em; color: var(--ac-muted); }
  .slot-row .until { font-variant-numeric: tabular-nums; color: var(--ac-muted); font-size: 0.9em; }
  .profile.edit { background: var(--card-background-color); }
  /* A narrow room (a phone, or a narrow column of a dashboard on a big screen):
     the level under the time. By the width of the room, not of the screen. */
  @media (max-width: 480px) {
    .slot-head { display: none; }
    .slot-row { grid-template-columns: 10px 1fr auto; }
    .slot-row .until { grid-column: 2 / 4; order: 5; }
    .slot-row select { grid-column: 2 / 3; }
  }
  @container (max-width: 460px) {
    .slot-head { display: none; }
    .slot-row { grid-template-columns: 10px 1fr auto; }
    .slot-row .until { grid-column: 2 / 4; order: 5; }
    .slot-row select { grid-column: 2 / 3; }
  }
  /* schedule bars */
  .sbar { position: relative; height: 26px; border-radius: 8px; background: var(--ac-surface-2); overflow: visible; touch-action: none; }
  .sbar.ro { height: 10px; border-radius: 5px; overflow: hidden; }
  .sseg { position: absolute; top: 0; bottom: 0; background: color-mix(in srgb, var(--c) 70%, transparent);
    display: flex; align-items: center; justify-content: center; overflow: hidden; }
  .sseg:first-child { border-radius: 8px 0 0 8px; }
  .sseg span { font-size: 0.7em; color: #fff; text-shadow: 0 1px 1px rgba(0,0,0,.35); white-space: nowrap; }
  .handle { position: absolute; top: -5px; bottom: -5px; width: 22px; transform: translateX(-50%); cursor: ew-resize;
    display: flex; justify-content: center; z-index: 2; outline: none; }
  .handle::before { content: ""; width: 6px; border-radius: 3px; background: var(--card-background-color);
    box-shadow: 0 0 0 1.5px var(--primary-text-color), 0 1px 4px rgba(0,0,0,.3); }
  .handle .htime { position: absolute; bottom: calc(100% + 4px); font-size: 0.72em; padding: 2px 6px; border-radius: 6px;
    background: var(--primary-text-color); color: var(--ac-opaque, var(--card-background-color, #fff)); white-space: nowrap; opacity: 0;
    transition: opacity .12s; pointer-events: none; font-variant-numeric: tabular-nums; }
  .handle:hover .htime, .handle:focus-visible .htime, .handle.dragging .htime { opacity: 1; }
  .handle:focus-visible::before, .handle.dragging::before { box-shadow: 0 0 0 2px var(--ac-accent), 0 1px 6px rgba(0,0,0,.35); }
  .bar-ticks { display: flex; justify-content: space-between; font-size: 0.66em; color: var(--ac-muted); margin-top: -2px; }
  .copysel { font-size: 0.85em; min-height: 32px; padding: 4px 8px; }

  /* compact */
  ha-card.compact { gap: 8px; }
  .crow { display: flex; align-items: center; gap: 8px; width: 100%; font: inherit; color: var(--primary-text-color);
    background: var(--ac-surface); border: none; border-radius: 16px; padding: 8px 12px 8px 14px; cursor: pointer; text-align: left;
    transition: background .15s; min-height: 56px; box-sizing: border-box; }
  .crow:hover { background: var(--ac-surface-2); }
  .crow ha-icon { --mdc-icon-size: 20px; color: var(--ac-muted); }
  .crow .cbar { width: 4px; align-self: stretch; border-radius: 2px; background: var(--c); flex: none; }
  .crow .ctext { display: flex; flex-direction: column; min-width: 0; flex: 1 1 auto; }
  .crow .cname { font-weight: 600; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .house-row .cname { flex: 0 1 auto; }
  .crow .crule { font-size: 0.78em; color: var(--ac-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .crow .ctemp { margin-left: auto; display: inline-flex; align-items: baseline; gap: 5px; font-variant-numeric: tabular-nums; white-space: nowrap; }
  .crow .cnow { font-size: 1.15em; font-weight: 300; }
  .crow .carrow { color: var(--ac-muted); font-size: 0.85em; }
  .crow .chev { margin-left: 2px; }
  .house-row .pill { flex: none; }
  .house-row .ctemp { font-size: 1em; font-weight: 600; }
  .house-row .ctemp ha-icon { --mdc-icon-size: 18px; align-self: center; }
  @media (max-width: 420px) { .house-row .pill.mode { display: none; } }

  /* house */
  .block.house { gap: 16px; }
  .house-head { display: flex; flex-direction: column; align-items: stretch; gap: 16px; }
  .who { display: flex; align-items: center; gap: 8px 12px; min-width: 0; flex-wrap: wrap; flex: 1 1 auto; }
  .avatars { display: flex; gap: 8px; flex: none; padding: 4px; flex-wrap: wrap; row-gap: 10px; }
  .avatars.overlap { gap: 9px; row-gap: 9px; }
  .avatars.overlap .avatar { width: 30px; height: 30px; font-size: 0.82em; }
  .avatar.more { font-size: 0.75em; color: var(--ac-muted); }
  .avatar { --r: var(--ac-line); width: 36px; height: 36px; border-radius: 50%; background: var(--ac-surface-2); display: inline-flex;
    align-items: center; justify-content: center; font-weight: 500; font-size: 0.9em; overflow: hidden; flex: none;
    box-shadow: 0 0 0 2px var(--card-background-color), 0 0 0 4px var(--r); }
  .avatar img { width: 100%; height: 100%; object-fit: cover; }
  .avatar.home { --r: #f08c00; }
  .avatar.nearby { --r: #2f9e8f; }
  .avatar.far { --r: #8a96a3; }
  .avatars.sm { gap: 6px; padding: 3px; }
  .avatars.sm .avatar { width: 24px; height: 24px; font-size: 0.72em; }
  .avatars.sm.overlap { gap: 7px; flex-wrap: nowrap; }
  .avatars.sm.overlap .avatar { width: 24px; height: 24px; font-size: 0.72em; }
  .whotext { min-width: 0; flex: 1 1 150px; font-size: 0.85em; }
  .htitle-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; min-width: 0; }
  .htitle { display: inline-flex; align-items: center; gap: 8px; min-width: 0; }
  .htitle .name { font-weight: 600; font-size: 1.15em; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .htitle ha-icon { --mdc-icon-size: 22px; color: var(--ac-muted); flex: none; }
  .house-row .htitle .name { font-size: 1em; }
  .house-row .htitle ha-icon { --mdc-icon-size: 20px; }
  .pill.presence-state ha-icon { --mdc-icon-size: 15px; }
  .pill.presence-state.home ha-icon { color: #f08c00; }
  .pill.presence-state.nearby ha-icon { color: #2f9e8f; }
  .hname { font-weight: 600; }

  .block.house { container-type: inline-size; }
  /* Two by two on a narrow card, all in one row on a wide one. */
  /* Values as a table with thin lines: two by two on a narrow card, all in one row on a wide one. */
  .stats { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0; border-top: 1px solid var(--ac-line); }
  .stats.three { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .stat, button.stat.period { display: flex; flex-direction: column; gap: 2px; background: none; border: none; border-radius: 0;
    border-bottom: 1px solid var(--ac-line); padding: 12px 12px 12px 0; text-align: left; min-width: 0; font: inherit; color: inherit; }
  .stats > :nth-child(2n) { border-left: 1px solid var(--ac-line); padding-left: 12px; }
  .stats.three > * { border-left: 1px solid var(--ac-line); padding-left: 12px; }
  .stats.three > :first-child { border-left: none; padding-left: 0; }
  @container (min-width: 440px) {
    .stats, .stats.three { grid-template-columns: none; grid-auto-flow: column; grid-auto-columns: minmax(0, 1fr); }
    .stats > * { border-left: 1px solid var(--ac-line); padding-left: 12px; }
    .stats > :first-child { border-left: none; padding-left: 0; }
  }
  .stat .k { display: flex; align-items: center; gap: 6px; font-size: 0.75em; color: var(--ac-muted); min-width: 0; }
  .stat .k ha-icon { --mdc-icon-size: 14px; flex: none; }
  .stat .v { font-variant-numeric: tabular-nums; font-size: 1.25em; font-weight: 600; }
  .stat.hot .v { color: var(--ac-hot); }
  .stat.warn .v { color: var(--ac-warn); }
  .hactions { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 8px; }
  .abtn { --t: var(--ac-accent); grid-column: span var(--span, 2); display: flex; align-items: center; justify-content: center; gap: 8px;
    min-height: 48px; padding: 0 12px; box-sizing: border-box; border-radius: 12px; border: 1px solid var(--ac-line); background: transparent;
    color: var(--primary-text-color); font: inherit; font-size: 0.9em; font-weight: 500; cursor: pointer; min-width: 0;
    transition: background .15s, border-color .15s; }
  .abtn span { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  /* On a narrow card the icon goes above the name, so the name keeps its room. */
  @container (max-width: 400px) {
    .abtn { flex-direction: column; gap: 2px; min-height: 56px; padding: 4px; font-size: 0.82em; }
  }
  .abtn ha-icon { --mdc-icon-size: 20px; }
  .abtn:hover { background: var(--ac-surface-2); }
  .abtn.warn { --t: var(--warning-color, #f0ad4e); }
  .abtn.teal { --t: #2f9e8f; }
  .abtn.blue { --t: #4a78b5; }
  .abtn.on, .abtn.open { border-color: color-mix(in srgb, var(--t) 60%, transparent); background: color-mix(in srgb, var(--t) 16%, transparent); font-weight: 600; }
  .abtn.on ha-icon { color: var(--t); }
  .panel { --t: var(--ac-accent); display: flex; flex-direction: column; gap: 10px; padding: 12px; border-radius: 12px;
    background: color-mix(in srgb, var(--t) 8%, transparent); box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--t) 40%, transparent); }
  .panel.teal { --t: #2f9e8f; }
  .panel.blue { --t: #4a78b5; }
  .panel-head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
  .panel-head > :last-child { margin-left: auto; }
  .pill.state.on, .pill.teal { background: #2f9e8f; color: #fff; }

  /* rooms */
  /* Neutral rooms: the level colour only on the arc and its dot; the outline only for an alert. */
  .block.room { gap: 16px; }
  .block.room.al-error, .tile.al-error { border-color: color-mix(in srgb, var(--ac-err) 50%, transparent); }
  .block.room.al-warn, .tile.al-warn { border-color: color-mix(in srgb, var(--warning-color, #f0ad4e) 55%, transparent); }
  .room-head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
  .rh-left { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; min-width: 0; flex: 1 1 auto; }
  .room-head .decision { flex: none; }
  .room-title .name { font-size: 1.15em; }
  .pill.rule .dot { width: 8px; height: 8px; }
  .pill ha-icon { --mdc-icon-size: 15px; }
  .pulse { animation: shc-pulse 1.8s ease-out infinite; }
  @keyframes shc-pulse {
    0% { box-shadow: 0 0 0 0 color-mix(in srgb, var(--ac-hot) 55%, transparent); }
    70% { box-shadow: 0 0 0 8px color-mix(in srgb, var(--ac-hot) 0%, transparent); }
    100% { box-shadow: 0 0 0 0 color-mix(in srgb, var(--ac-hot) 0%, transparent); }
  }
  .block.room.open { container-type: inline-size; }
  .hero { display: flex; gap: 16px; align-items: center; }
  .hero .chips { flex: 1 1 0; }
  @container (max-width: 400px) {
    .hero { gap: 12px; }
    .hero .gauge { width: 136px !important; height: 136px !important; --gs: 136px; }
    .hero .gauge svg { width: 100%; height: 100%; }
  }
  .gauge { position: relative; display: inline-block; flex: none; }
  .gauge svg { display: block; }
  .gauge .gtrack { fill: none; stroke: var(--ac-line); stroke-linecap: round; }
  .gauge .gvalue { fill: none; stroke: var(--c); stroke-linecap: round; }
  .gauge .gmark { fill: var(--primary-text-color); stroke: var(--ac-opaque, var(--card-background-color)); }
  .gcenter { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; }
  /* In the opening of the arc, under the number. */
  .gtrend { position: absolute; left: 50%; bottom: 0; transform: translateX(-50%); display: inline-flex; line-height: 0; }
  .gtrend ha-icon { --mdc-icon-size: max(14px, calc(var(--gs) * 0.13)); }
  .gtrend.up { color: var(--ac-hot); }
  .gtrend.down { color: var(--state-climate-cool-color, #2b9af9); }
  .gnum { font-size: max(15px, calc(var(--gs) * 0.26)); font-weight: 600; line-height: 1; letter-spacing: -0.03em; font-variant-numeric: tabular-nums; }
  .gsub { font-size: 0.8em; color: var(--ac-muted); margin-top: 6px; }
  .chips { display: flex; flex-direction: column; gap: 12px; min-width: 0; }
  .chip { display: inline-flex; align-items: flex-start; gap: 7px; font-size: 0.9em; line-height: 1.35; }
  .chip.line { display: flex; flex-direction: column; gap: 2px; }
  .chip.line .clabel { font-size: 0.82em; color: var(--ac-muted); }
  .chip.line .cval { font-weight: 500; display: inline-flex; align-items: baseline; gap: 6px; }
  .chip.line .cval .dot { width: 8px; height: 8px; align-self: center; }
  .chip.line .csub { font-size: 0.88em; color: var(--ac-muted); }
  .chip ha-icon { --mdc-icon-size: 17px; color: var(--c); flex: none; }
  .chip small { display: block; }
  .chip.soft { align-self: flex-start; align-items: center; padding: 4px 10px; border-radius: 999px; font-size: 0.82em;
    background: color-mix(in srgb, var(--c) 16%, transparent); }
  .chip.soft.on { box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--c) 55%, transparent); }
  .chip.soft.neutral { background: var(--ac-surface-2); }
  .chip.neutral ha-icon { color: var(--ac-muted); }
  .chip.guest ha-icon { color: #2f9e8f; }
  .today { display: flex; flex-direction: column; gap: 4px; }
  .tlabel { font-size: 0.78em; color: var(--ac-muted); }
  .tbar { position: relative; height: 14px; border-radius: 7px; background: var(--ac-surface-2); }
  .tbar i { position: absolute; top: 0; bottom: 0; background: color-mix(in srgb, var(--c) 85%, transparent); }
  .tbar i:first-child { border-radius: 7px 0 0 7px; }
  .tbar i:last-of-type { border-radius: 0 7px 7px 0; }
  .tbar b { position: absolute; top: -3px; bottom: -3px; width: 3px; margin-left: -1.5px; border-radius: 2px; background: var(--primary-text-color);
    box-shadow: 0 0 0 2px var(--ac-opaque, var(--card-background-color)); }
  .tticks { display: flex; justify-content: space-between; font-size: 0.68em; color: var(--ac-muted); }
  .sbtns { display: grid; grid-template-columns: repeat(var(--cols, 3), minmax(0, 1fr)); gap: 8px; }
  .sbtn { display: flex; align-items: center; justify-content: center; gap: 6px; min-height: 48px; padding: 4px 8px; border-radius: 12px;
    border: 1px solid var(--ac-line); background: transparent; color: var(--primary-text-color); font: inherit;
    font-size: 0.9em; font-weight: 500; cursor: pointer; min-width: 0; box-sizing: border-box; transition: background .15s, border-color .15s; }
  .sbtn span { text-align: center; line-height: 1.2; overflow-wrap: break-word; hyphens: auto; min-width: 0; }
  .sbtn ha-icon { --mdc-icon-size: 18px; flex: none; }
  @container (max-width: 400px) {
    .sbtn { flex-direction: column; gap: 2px; min-height: 56px; padding: 4px; font-size: 0.85em; }
  }
  .sbtn.back { border-color: var(--ac-active-line); background: var(--ac-active-bg); color: var(--ac-active-fg); font-weight: 600; }
  .sbtn.lock.on { border-color: var(--warning-color, #f0ad4e); background: color-mix(in srgb, var(--warning-color, #f0ad4e) 16%, var(--card-background-color)); }
  .sbtn.lock.on ha-icon { color: var(--warning-color, #f0ad4e); }
  .sbtn:hover { background: var(--ac-surface-2); }
  .sbtn.on { border-color: var(--c); background: color-mix(in srgb, var(--c) 18%, transparent); }
  .section { display: flex; flex-direction: column; gap: 4px; padding: 12px; border-radius: 12px; background: var(--ac-surface);
    box-shadow: inset 0 0 0 1px var(--ac-line); }
  .section-head { font-weight: 500; }
  .section .fold-body { padding-top: 6px; }
  .block.room.folded { padding: 8px 12px 8px 8px; }
  .frow { display: flex; align-items: center; gap: 12px; width: 100%; font: inherit; color: inherit; background: none; border: none;
    padding: 0; cursor: pointer; text-align: left; min-height: 60px; }
  .ftext { display: flex; flex-direction: column; gap: 4px; flex: 1; min-width: 0; }
  .ftext .name { font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .freason { display: flex; align-items: flex-start; gap: 6px; font-size: 0.85em; line-height: 1.35; color: var(--ac-muted); min-width: 0; }
  .freason .dot { width: 8px; height: 8px; margin-top: 5px; }
  .freason > span:last-child { min-width: 0; overflow-wrap: anywhere; }
  .ficons { display: inline-flex; gap: 6px; flex: none; }
  /* A narrow folded room (a small phone with big text, a narrow column): the icons
     in a column, so the name and the line keep their room. */
  .block.room.folded { container-type: inline-size; }
  @container (max-width: 340px) { .ficons { flex-direction: column; gap: 4px; } }

  /* compact tiles */
  .rooms-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px; }
  .rooms-list > .block { grid-column: 1 / -1; }
  .tile { display: flex; flex-direction: column; gap: 12px; font: inherit; color: inherit; text-align: left; cursor: pointer; padding: 14px;
    border-radius: 16px; border: 1px solid transparent; background: var(--ac-surface); min-width: 0; box-sizing: border-box; }
  .tile:hover, .crow:hover, .frow:hover { background: var(--ac-surface-2); }
  .tile > .pill.preset { align-self: flex-start; max-width: 100%; min-height: 28px; padding: 0 12px; }
  .tile-head { display: flex; justify-content: space-between; align-items: center; gap: 6px; min-height: 28px; }
  .tile .cname { font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  /* Status icons: all 28 px circles, tinted by meaning. */
  .tstat, .cicon, .alerticon { width: 28px; height: 28px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center;
    flex: none; background: var(--ac-surface-2); color: var(--primary-text-color); }
  .tstat ha-icon, .cicon ha-icon, .alerticon ha-icon { --mdc-icon-size: 16px; }
  .tstat.warn, .cicon.warn { background: color-mix(in srgb, var(--warning-color, #f0ad4e) 18%, transparent); color: var(--ac-warn-fg); }
  .tstat.teal, .cicon.teal { background: color-mix(in srgb, var(--ac-teal) 18%, transparent); color: color-mix(in srgb, var(--ac-teal) 75%, var(--primary-text-color)); }
  .alerticon { background: color-mix(in srgb, var(--ac-err) 16%, transparent); color: var(--ac-err-fg); }
  .alerticon.warn { background: color-mix(in srgb, var(--warning-color, #f0ad4e) 18%, transparent); color: var(--ac-warn-fg); }
  .flame { width: 28px; height: 28px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; flex: none;
    color: var(--secondary-text-color); background: color-mix(in srgb, var(--secondary-text-color) 10%, transparent);
    box-shadow: inset 0 0 0 1.5px var(--secondary-text-color); }
  .flame ha-icon { --mdc-icon-size: 16px; }
  .flame.on { background: var(--ac-hot); color: #fff; box-shadow: none; }
  .flame.on ha-icon { animation: shc-flicker 1.6s ease-in-out infinite; transform-origin: 50% 85%; }
  .flame.on.glow { animation: shc-pulse 2s ease-out infinite; }

  @keyframes shc-flicker {
    0%, 100% { transform: scale(1) rotate(0deg); }
    30% { transform: scale(1.1, 1.18) rotate(-4deg); }
    60% { transform: scale(0.94, 1.04) rotate(3deg); }
  }
  .tstats { display: inline-flex; gap: 4px; flex: none; }
  .tile-body { display: flex; align-items: center; gap: 12px; min-width: 0; }
  .gcol { display: flex; flex-direction: column; align-items: center; gap: 6px; flex: none; }
  .pill.preset { background: color-mix(in srgb, var(--c) 22%, transparent); font-weight: 500; }
  .pill.preset .dot, .pill.rule .dot { width: 8px; height: 8px; }
  .fname, .tname { display: flex; align-items: center; gap: 6px; min-width: 0; flex-wrap: wrap; }
  .tname { flex-wrap: nowrap; flex: 1; }
  .tname .cname { flex: 0 1 auto; }
  .tname .pill { min-width: 0; flex: 0 1 auto; overflow: hidden; text-overflow: ellipsis; }
  .tile-info { display: flex; flex-direction: column; gap: 2px; min-width: 0; align-items: flex-start; }
  .tile-info .tsub { font-size: 0.75em; color: var(--ac-muted); }
  .tile-info .tval { font-size: 1.15em; font-weight: 600; }
  .tile-info .muted { font-size: 0.8em; line-height: 1.35; overflow-wrap: anywhere; max-width: 100%; }

  :host([offscreen]) .pulse, :host([offscreen]) .flame.on ha-icon, :host([offscreen]) .flame.glow { animation-play-state: paused; }
  @media (prefers-reduced-motion: reduce) { .pulse, .flame.on ha-icon, .flame.glow { animation: none; } * { transition: none !important; } }
`;
