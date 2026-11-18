// The house: presence, mode, heat source, outdoor, pause, guests, vacation, heating time, messages.

import { RUNTIME_PERIODS } from "../core/constants.js";
import { esc, num } from "../core/format.js";

export const HouseMixin = (Base) =>
  class extends Base {
    /** House block: presence, outdoor, mode, pause, guests, vacation and buttons. */
    _houseHtml(house) {
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

      const { avatars, overlap, who } = this._people(house);

      const modeOptions = mode?.attributes?.options || ["auto", "away", "vacation", "off", "summer"];
      const modeCount = modeOptions.length;
      const modes = modeOptions
        .map(
          (opt) => `<button class="seg ${mode?.state === opt ? "active" : ""}" data-action="mode" aria-pressed="${mode?.state === opt}"
            data-entity="${esc(e.mode)}" data-option="${esc(opt)}">${esc(this._label(mode, opt))}</button>`
        )
        .join("");
      const scenarios = this._scenariosHtml(house);

      const stat = (icon, label, value, extra = "", entityId = null) =>
        `<div class="stat ${extra} ${entityId ? "link" : ""}" ${this._more(entityId)}><span class="k">${this._icon(icon)}<span>${esc(
          label
        )}</span></span><span class="v">${esc(value)}</span></div>`;
      const onOff = (s) => (s ? (s.state === "on" ? this._t("on") : this._t("off")) : "–");

      // The same title in every view: house icon and name, presence, flame.
      const presenceIcon0 =
        { home: "home-outline", nearby: "map-marker-radius-outline", far: "map-marker-distance" }[presence?.state] ||
        "home-search-outline";
      const titleHtml = `<span class="htitle">${this._icon("home-thermometer-outline")}<span class="name">${esc(
        house.name || this._t("title")
      )}</span></span>`;
      const presencePill = (link) =>
        `<span class="pill presence-state ${esc(presence?.state)} ${link ? "link" : ""}" ${link ? this._more(e.presence) : ""}>${this._icon(
          presenceIcon0
        )}${esc(this._label(presence))}</span>`;
      const houseKey = `house-${house.id}`;
      if (this._config.compact && !this._open[houseKey]) {
        return `<button class="crow house-row" data-action="fold" data-key="${esc(houseKey)}" aria-expanded="false">
            ${titleHtml}
            ${presencePill(false)}
            ${demand?.state === "on" ? this._flame(this._houseHeating(house), null, true) : ""}
            <span class="pill mode active">${esc(this._label(mode))}</span>
            <span class="ctemp muted">${this._icon("weather-partly-cloudy")} ${esc(this._temp(outdoor?.state))}</span>
            <span class="chev"></span>
          </button>`;
      }
      const foldBack = this._config.compact
        ? `<button class="room-title" data-action="fold" data-key="${esc(houseKey)}" aria-expanded="true" aria-label="${esc(
            house.name || ""
          )}"><span class="chev open"></span></button>`
        : "";

      const actions = this._houseActions(house);
      // On 6 columns: 5 buttons as 3 + 2, 4 as 2 + 2, else one row.
      const spans = { 1: [6], 2: [3, 3], 3: [2, 2, 2], 4: [3, 3, 3, 3], 5: [2, 2, 2, 3, 3] }[actions.length] || actions.map(() => 2);
      const actionsHtml = actions.map((html, i) => html.replace("<button ", `<button style="--span:${spans[i]}" `)).join("");
      const vacPanel = this._vacPanelHtml(house);

      return `
        <section class="block house">
          <div class="house-head">
            <div class="htitle-row">
              ${foldBack}${titleHtml}
              ${presencePill(true)}
              ${presence?.attributes?.arriving ? `<span class="pill arriving">${this._icon("arrow-right")}${esc(this._t("arriving"))}</span>` : ""}
              ${demand?.state === "on" ? this._flame(this._houseHeating(house), e.heat_demand) : ""}
            </div>
            <div class="segmented ${modeCount > 4 ? "many" : ""}" style="--n:${modeCount}" role="group" aria-label="${esc(this._t("mode"))}">${modes}</div>
            ${scenarios}
            ${source ? this._sourceHtml(source, e.heat_source) : ""}
          </div>
          ${
            avatars
              ? `<div class="who"><div class="avatars ${overlap}">${avatars}</div>${
                  who ? `<span class="whotext muted">${esc(who)}</span>` : ""
                }</div>`
              : ""
          }
          <div class="stats ${runtime ? "" : "three"}">
            ${stat("weather-partly-cloudy", this._outdoorLabel(outdoor), this._temp(outdoor?.state), "", e.outdoor_average)}
            ${stat("calendar-range", this._t("season"), onOff(season), "", e.heating_season)}
            ${stat("fire", this._t("demand"), onOff(demand), demand?.state === "on" ? "hot" : "", e.heat_demand)}
            ${runtime ? this._runtimeStat(e.heating_runtime) : ""}
          </div>
          ${this._cutoffHtml(outdoor, cutoff, e.outdoor_cutoff, mode, season, pause)}
          <div class="hactions">${actionsHtml}</div>
          ${vacPanel}
        </section>`;
    }

    /**
     * The people of the house: their avatars (a ring in the colour of where the
     * person is: home, nearby, far; the photo when there is one), linked to their
     * entity, and the words "Mark home · Anna nearby".
     */
    _people(house) {
      const presence = this._state(house.entities.presence);
      const persons = Object.entries(presence?.attributes?.persons || {}).map(([id, cls]) => {
        const p = this._hass.states[id];
        return { id, cls: cls || "unknown", name: p?.attributes?.friendly_name || id.split(".")[1], picture: p?.attributes?.entity_picture };
      });
      // Several people overlap a little; the compact row shows a few and "+N" for the rest.
      const avatarList = (links, max = persons.length) =>
        persons
          .slice(0, persons.length > max ? max - 1 : max)
          .map((p) => {
            const title = `${p.name}: ${this._label(presence, p.cls)}`;
            return `<span class="avatar ${esc(p.cls)} ${links ? "link" : ""}" ${links ? this._more(p.id, title) : `title="${esc(title)}"`}>${
              p.picture ? `<img src="${esc(p.picture)}" alt="">` : esc((String(p.name).trim()[0] || "?").toUpperCase())
            }</span>`;
          })
          .join("") +
        (persons.length > max
          ? `<span class="avatar more" title="${esc(persons.slice(max - 1).map((p) => p.name).join(", "))}">+${persons.length - max + 1}</span>`
          : "");
      return {
        avatars: avatarList(true),
        list: avatarList,
        count: persons.length,
        overlap: persons.length > 3 ? "overlap" : "",
        who: persons.map((p) => `${p.name} ${String(this._label(presence, p.cls)).toLowerCase()}`).join(" · "),
      };
    }

    /** The scenarios of the house: one button each, the active one marked. */
    _scenariosHtml(house) {
      const e = house.entities;
      const scenario = this._state(e.scenario);
      const scenarioOptions = scenario?.attributes?.options || [];
      // Three per row, the same shape as the mode buttons (two when there are only two or four).
      const scenCols = [2, 4].includes(scenarioOptions.length) ? 2 : 3;
      return scenarioOptions.length
        ? `<div class="scenarios">
            <span class="sclabel">${this._icon("playlist-check")}<span>${esc(this._t("scenario"))}</span></span>
            <div class="segmented scen-grid" style="--n:${scenCols}" role="group" aria-label="${esc(this._t("scenario"))}">${scenarioOptions
              .map(
                (opt) => `<button class="seg scen ${scenario.state === opt ? "active" : ""}" data-action="mode" title="${esc(opt)}"
                  aria-pressed="${scenario.state === opt}" data-entity="${esc(e.scenario)}" data-option="${esc(opt)}">${esc(opt)}</button>`
              )
              .join("")}</div>
          </div>`
        : "";
    }

    /** The buttons of the house: Pause, Guests, Vacation (opens its panel), Reevaluate, Automatic. */
    _houseActions(house, titled = false) {
      const e = house.entities;
      const guest = this._state(e.guest_mode);
      const pause = this._state(e.pause);
      const guestOn = guest?.state === "on";
      const vacationSet = this._vacationSet(house);
      // Action buttons: an icon and a short name; Guests and Vacation open their own panel.
      const vacKey = `vac-${house.id}`;
      // ``titled``: every button says its name on hover (only its icon is shown).
      const abtn = (icon, label, attrs, cls = "", title = titled ? label : "") =>
        `<button class="abtn ${cls}" ${attrs} ${title ? `title="${esc(title)}" aria-label="${esc(title)}"` : ""}>${this._icon(
          icon
        )}<span>${esc(label)}</span></button>`;
      const fold = (key) => `data-action="fold" data-key="${esc(key)}" aria-expanded="${!!this._open[key]}"`;
      return [
        pause
          ? abtn("pause", this._t("pause"), `data-action="toggle" data-entity="${esc(e.pause)}" role="switch" aria-checked="${pause.state === "on"}"`, pause.state === "on" ? "warn on" : "warn")
          : "",
        guest
          ? abtn("account-group-outline", this._t("guests"), `data-action="toggle" data-entity="${esc(e.guest_mode)}" role="switch" aria-checked="${guestOn}"`, `teal ${guestOn ? "on" : ""}`)
          : "",
        abtn("airplane", this._t("vacation"), fold(vacKey), `blue ${vacationSet ? "on" : ""} ${this._open[vacKey] ? "open" : ""}`),
        e.reevaluate ? abtn("refresh", this._t("reevaluate"), `data-action="press" data-entity="${esc(e.reevaluate)}"`) : "",
        e.clear_overrides
          ? abtn("restore", this._t("auto_short"), `data-action="press" data-entity="${esc(e.clear_overrides)}"`, "", this._t("clear_all"))
          : "",
      ].filter(Boolean);
    }

    /** True while a vacation is set (a start or an end). */
    _vacationSet(house) {
      const isDate = (s) => s && !Number.isNaN(Date.parse(s.state));
      return isDate(this._state(house.entities.vacation_start)) || isDate(this._state(house.entities.vacation_end));
    }

    /** The vacation panel of the house, while it is open. */
    _vacPanelHtml(house) {
      const e = house.entities;
      const vacKey = `vac-${house.id}`;
      if (!this._open[vacKey]) return "";
      const vStart = this._state(e.vacation_start);
      const vEnd = this._state(e.vacation_end);
      const isDate = (s) => s && !Number.isNaN(Date.parse(s.state));
      const vacationSet = isDate(vStart) || isDate(vEnd);
      const vacationSummary = vacationSet
        ? `${isDate(vStart) ? esc(this._fmtTime(vStart.state)) : this._t("now_tag")} – ${
            isDate(vEnd) ? esc(this._fmtTime(vEnd.state)) : "…"
          }`
        : this._t("vacation_none");
      return `<div class="panel blue">
            <div class="panel-head"><b>${esc(this._t("vacation"))}</b><span class="muted">${vacationSummary}</span></div>
            <div class="dates">
              <label class="datefield"><span>${this._t("from")}</span>
                <input type="datetime-local" data-vac="start" data-house="${esc(house.id)}"
                  value="${esc(this._toInput(vStart?.state))}"></label>
              <label class="datefield"><span>${this._t("to")}</span>
                <input type="datetime-local" data-vac="end" data-house="${esc(house.id)}"
                  value="${esc(this._toInput(vEnd?.state))}"></label>
            </div>
            <p class="hint">${this._t("vacation_hint")}</p>
            <div class="row wrap">
              ${this._btn(this._t("set_vacation"), `data-action="vacation" data-house="${esc(house.id)}"`, {
                icon: "content-save",
                kind: "primary",
              })}
              ${
                e.clear_vacation && vacationSet
                  ? this._btn(this._t("clear_vacation"), `data-action="press" data-entity="${esc(e.clear_vacation)}"`, {
                      icon: "close",
                    })
                  : ""
              }
            </div>
            ${this._error[vacKey] ? `<p class="error">${esc(this._error[vacKey])}</p>` : ""}
          </div>`;
    }

    /** The heat source of the house: Automatic (with a criterion), the primary and the secondary one, by their names. */
    _sourceHtml(s, entityId) {
      const at = s.attributes || {};
      const name = (k) => at[`${k}_name`] || this._label(s, k);
      const label = (opt) => (opt === "auto" ? this._t("source_auto") : name(opt));
      const options = at.options || [];
      const active = at.active === "secondary" ? "secondary" : "primary";
      let info = `${this._t("heat_source")}: ${name(active)}`;
      if (at.switch_at) {
        // Automatic changes the source once the criterion has stayed changed long enough.
        const next = active === "primary" ? "secondary" : "primary";
        const time = this._fmt(at.switch_at, { hour: "2-digit", minute: "2-digit" });
        info += ` · ${this._t("source_switch").replace("{name}", name(next)).replace("{time}", time)}`;
      }
      const buttons = options
        .map(
          (opt) => `<button class="seg ${s.state === opt ? "active" : ""}" data-action="mode" title="${esc(label(opt))}"
            aria-pressed="${s.state === opt}" data-entity="${esc(entityId)}" data-option="${esc(opt)}">${esc(label(opt))}</button>`
        )
        .join("");
      return `<div class="scenarios sources">
          <span class="sclabel">${this._icon("fire-circle")}<span>${esc(info)}</span></span>
          <div class="segmented" style="--n:${options.length}" role="group" aria-label="${esc(this._t("heat_source"))}">${buttons}</div>
        </div>`;
    }

    /** "Warm outside: on • heating is off until the average falls to 17°", or why the forecast changes it. */
    _cutoffHtml(outdoor, cutoff, entityId, mode, season, pause) {
      const a = outdoor?.attributes || {};
      if (!cutoff || a.cutoff_enabled === false) return "";
      // Only where the cutoff can act: not in mode Off / Summer, outside the
      // heating season or in a pause (vacation keeps it: away still heats).
      if (["off", "summer"].includes(mode?.state) || season?.state === "off" || pause?.state === "on") return "";
      // Shown while the heating is off because it is warm, or while the forecast lets it run.
      const reason = a.cutoff_reason ?? (cutoff.state === "on" ? (a.forecast_cutoff ? "forecast_warm" : "measured") : null);
      if (!reason) return "";
      const hours = String(num(a.forecast_hours) ?? "");
      let text;
      if (reason === "forecast_cold") {
        text = this._t("cutoff_cancelled").replace("{h}", hours).replace("{temp}", this._temp(a.forecast_mean));
      } else if (reason === "forecast_warm") {
        text = this._t("cutoff_forecast").replace("{h}", hours).replace("{temp}", this._temp(a.forecast_mean));
      } else {
        text = this._t("cutoff_on").replace("{temp}", this._temp(a.cutoff_resume_temperature));
      }
      return this._msg({
        kind: reason === "forecast_cold" ? "info cutoffline" : "warn cutoffline on",
        icon: reason === "forecast_cold" ? "weather-cloudy" : "weather-sunny",
        lead: `${this._t("cutoff")}:`,
        text,
        link: entityId,
      });
    }

    /** Banner while guest mode is on (the Guests button turns it off), with its end when it has one. */
    _guestBanner(house) {
      const guest = this._state(house.entities?.guest_mode);
      if (guest?.state !== "on") return "";
      const name = this._houses().length > 1 && house.name ? `${house.name}: ` : "";
      const until = guest.attributes?.until ? ` (${this._t("until")} ${this._fmtTime(guest.attributes.until)})` : "";
      // While a vacation or the away mode waits for the guests, the band says so.
      const suspended = this._state(house.entities?.presence)?.attributes?.vacation_suspended;
      const away = this._state(house.entities?.mode)?.state === "away";
      const key = suspended ? "guests_banner_vacation" : away ? "guests_banner_away" : "guests_banner";
      const [lead, rest] = this._split(this._t(key));
      return this._msg({
        kind: "teal banner",
        icon: "account-group-outline",
        lead: name + lead,
        text: rest + until,
        link: house.entities.guest_mode,
        action: { label: this._t("end_guests"), attrs: `data-action="toggle" data-entity="${esc(house.entities.guest_mode)}"` },
      });
    }

    /** Banner while the house is paused (the switch stays the only control). */
    _pauseBanner(house) {
      const pause = this._state(house.entities?.pause);
      if (pause?.state !== "on") return "";
      const name = this._houses().length > 1 && house.name ? `${house.name}: ` : "";
      const [lead, rest] = this._split(this._t("paused_banner"));
      return this._msg({
        kind: "warn banner",
        icon: "pause",
        lead: name + lead,
        text: rest,
        action: { label: this._t("resume"), attrs: `data-action="toggle" data-entity="${esc(house.entities.pause)}"` },
      });
    }

    /**
     * One shape for every message: a tinted band, the icon in a circle, the subject
     * in bold, the text; on the right its action (a button) or a chevron when the
     * text opens an entity. ``kind``: warn, teal, info, error or plain (outlined).
     */
    _msg({ kind = "info", icon, lead = "", text = "", link = null, action = null }) {
      // With a button the text opens the entity, else the whole band does.
      const textLink = link && action ? link : null;
      const bandLink = link && !action ? link : null;
      const body = `<span class="mtext ${textLink ? "link" : ""}" ${this._more(textLink)}>${lead ? `<b>${esc(lead)}</b> ` : ""}${esc(
        text
      )}</span>`;
      const right = action
        ? `<button class="mbtn" ${action.attrs}>${esc(action.label)}</button>`
        : bandLink
          ? `<span class="mchev" aria-hidden="true"></span>`
          : "";
      return `<div class="msg ${kind} ${bandLink ? "link" : ""}" ${bandLink ? this._more(bandLink) : 'role="status"'}><span class="micon">${this._icon(
        icon
      )}</span>${body}${right}</div>`;
    }

    /** Label of the outdoor temperature: it is the average of the last hours. */
    _outdoorLabel(outdoor) {
      const h = num(outdoor?.attributes?.average_hours);
      return h === null ? this._t("outdoor") : this._t("outdoor_hours").replace("{h}", String(h));
    }

    /** True while a room of the house heats (every room of it, also those not on this card). */
    _houseHeating(house) {
      return this._discover().rooms.some((id) => {
        const at = this._hass.states[id]?.attributes;
        return at && at.entry_id === house.id && at.heating;
      });
    }

    // ------------------------------------------------------------------ heating time per period
    _period() {
      const p = this._runtimePeriod || this._config.runtime_period || "day";
      return RUNTIME_PERIODS.includes(p) ? p : "day";
    }

    /** Heating time as hours and minutes. */
    _runtimeText(entityId) {
      const value = this._runtimeValue(entityId);
      if (value === null) return "–";
      const h = Math.floor(value);
      const m = Math.round((value - h) * 60);
      return h ? `${h} h ${String(m).padStart(2, "0")} min` : `${m} min`;
    }

    /** "Heating time · today" that changes the period when tapped. */
    _runtimeButton(entityId, kind) {
      // Every period label takes the same place, so the text does not move when it changes.
      const current = this._period();
      const label = RUNTIME_PERIODS.map(
        (p) =>
          `<span class="${p === current ? "on" : ""}" ${p === current ? "" : 'aria-hidden="true"'}>${esc(
            `${this._t("runtime")} · ${this._t(`period_${p}`)}`
          )}</span>`
      ).join("");
      const value = esc(this._runtimeText(entityId));
      const title = esc(this._t("period_hint"));
      if (kind === "dt") {
        return `<button class="period" data-action="period" title="${title}"><dt class="stack">${label}</dt><dd>${value}</dd></button>`;
      }
      return `<button class="stat period" data-action="period" title="${title}"><span class="k">${this._icon(
        "timer-outline"
      )}<span class="stack">${label}</span></span><span class="v">${value}</span></button>`;
    }

    /** Heating time of the house, as a stat that changes the period when tapped. */
    _runtimeStat(entityId) {
      return this._runtimeButton(entityId, "stat");
    }
  };
