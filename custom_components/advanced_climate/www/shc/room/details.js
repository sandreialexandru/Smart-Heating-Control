// Details of a room: humidity, devices, what it learned.

import { PRESET_COLORS } from "../core/constants.js";
import { esc, num } from "../core/format.js";

// The icon of each role of an entity of a room.
const DEVICE_ICONS = {
  thermostat: "thermostat",
  switch: "power-socket-eu",
  temperature: "thermometer",
  humidity: "water-percent",
  window: "window-closed-variant",
  window_linked: "window-closed-variant",
  occupancy: "motion-sensor",
  calibration: "tune-vertical",
};

export const DetailsMixin = (Base) =>
  class extends Base {
    /** Details: temperatures, heating rate and time, device preset, adjustments, levels. */
    _detailsHtml(a, e) {
      const runtime = this._state(e.heating_runtime);
      const offsets =
        (a.offsets || []).map(([label, delta]) => `${this._offsetName(label)} ${delta > 0 ? "+" : ""}${delta}°`).join(", ") ||
        this._t("none");
      const active = a.device_level !== undefined ? a.device_level : a.device_preset;
      const fromDevice = a.custom_levels ? a.device_levels || [] : [];
      const levelTemps = Object.entries(a.levels || {})
        .filter(([, t]) => t !== null && t !== undefined)
        .map(
          ([p, t]) =>
            `<span class="lv ${p === active ? "active" : ""}"><span class="dot" style="--c:${PRESET_COLORS[p]}"></span>${esc(
              this._presetName(a, p)
            )} ${t}°${fromDevice.includes(p) ? ` <small>${this._t("from_device")}</small>` : ""}${
              p === active ? ` <small>${this._t("active")}</small>` : ""
            }</span>`
        )
        .join("");
      const rawPreset = a.device_preset;
      const devicePreset =
        a.climate_entities && a.climate_entities.length
          ? !rawPreset || rawPreset === "none"
            ? this._t("no_preset")
            : rawPreset
          : null;
      const dl = (k, v) => `<div><dt>${esc(k)}</dt><dd>${v}</dd></div>`;
      const group = (title, body) => (body.trim() ? `<div class="label">${esc(title)}</div>${body}` : "");
      const estimate = a.next_estimate
        ? `<div class="wide link" ${this._more(e.decision)}><dt>${esc(this._t("est_label"))}</dt><dd>${esc(
            this._estimate(a)
          )}${
            a.next_estimate.kind === "optimal_start" && !a.next_estimate.learned && this._heatDefault(e)
              ? `<small class="sub">${esc(this._heatDefault(e))}</small>`
              : ""
          }</dd></div>`
        : "";
      const runtimeHtml = runtime ? `<div>${this._runtimeButton(e.heating_runtime, "dt")}</div>` : "";
      const temps = `<dl class="details">
          ${dl(this._t("room_temp"), esc(this._temp(a.current_temperature)))}
          ${dl(
            this._t("target"),
            `${esc(this._temp(a.target_temperature))}${num(a.held_at) !== null ? `<small class="sub">${esc(this._heldAt(a))}</small>` : ""}`
          )}
          ${devicePreset !== null ? dl(this._t("device_preset"), esc(devicePreset)) : ""}
          ${
            a.trv_boost
              ? dl(
                  this._t("trv_boost"),
                  esc(
                    this._t(a.trv_boost.active ? "trv_boost_on" : "trv_boost_off").replace(
                      "{temp}",
                      this._temp(a.trv_boost.temperature)
                    )
                  )
                )
              : ""
          }
          ${this._humidityHtml(a, dl)}
          ${dl(this._t("adjustments"), esc(offsets))}
        </dl>
        ${
          levelTemps
            ? `<div class="sublabel">${a.custom_levels ? this._t("levels") : this._t("level_temps_gt")}</div>
               <div class="levels-line">${levelTemps}</div>`
            : ""
        }`;
      const program = estimate ? `<dl class="details">${estimate}</dl>` : "";
      const heating = `<dl class="details">${this._heatingHtml(a, dl)}${runtimeHtml}</dl>`;
      const learning = this._learnHtml(e, a);
      const html = `${group(this._t("grp_temps"), temps)}
        ${group(this._t("grp_heating"), heating)}
        ${group(this._t("grp_program"), program)}
        ${group(this._t("grp_learning"), learning ? `<dl class="details">${learning}</dl>` : "")}
        ${group(this._t("grp_devices"), this._devicesHtml(a))}
        ${a.schedule_error ? `<p class="error">${esc(a.schedule_error)}</p>` : ""}`;
      return this._fold(`details-${a.room_id}`, this._t("details"), html);
    }

    /**
     * The heat demand of the room: since when it asks for heat and heats (or
     * stopped), and the heat source of the house it waits for: running or not,
     * since when, and how long its minimum on / off time still holds it.
     */
    _heatingHtml(a, dl) {
      const since = (iso) => {
        const t = Date.parse(iso || "");
        if (Number.isNaN(t)) return "";
        const minutes = Math.max(1, (Date.now() - t) / 60000);
        return ` · ${this._t("hd_since").replace("{time}", this._fmtTime(iso)).replace("{d}", this._duration(minutes))}`;
      };
      const yesNo = (on) => this._t(on ? "hd_yes" : "hd_no");
      const onOff = (on) => this._t(on ? "on" : "off");
      let html =
        dl(this._t("asks_heat"), esc(`${yesNo(a.heat_demand)}${since(a.demand_since)}`)) +
        dl(this._t("heating"), esc(`${yesNo(a.heating)}${since(a.heating_since)}`));
      const src = a.heat_source;
      if (src && src.entity_id) {
        let text = src.on === null || src.on === undefined ? this._t("hd_unknown") : `${onOff(src.on)}${since(src.since)}`;
        const left = (Date.parse(src.until || "") - Date.now()) / 60000;
        if (src.waiting && Number.isFinite(left) && left > 0) {
          text += ` · ${this._t(`hd_held_${src.waiting}`).replace("{d}", this._duration(Math.max(1, left)))}`;
        }
        html += `<div class="wide link" ${this._more(src.entity_id)}><dt>${esc(this._t("heat_source"))}</dt><dd>${esc(text)}</dd></div>`;
      }
      return html;
    }

    /** Humidity of the room and at its coldest wall (with a humidity sensor). */
    _humidityHtml(a, dl) {
      const air = num(a.humidity);
      if (air === null) return "";
      const wall = num(a.surface_humidity);
      const text =
        wall === null
          ? this._t("humidity_air").replace("{air}", Math.round(air))
          : this._t("humidity_value").replace("{air}", Math.round(air)).replace("{wall}", Math.round(wall));
      // 80 % at the coldest wall is where mold can grow (DIN 4108-2).
      const risk = wall !== null && wall >= 80 ? ` <small class="warn">${esc(this._t("humidity_risk"))}</small>` : "";
      return dl(this._t("humidity"), `${esc(text)}${risk}`);
    }

    /**
     * The learned thermal model, each value linked to its sensor: the state of
     * the learning (with the reset; two bars while learning), then one tile for
     * the heating, its inertia, the weather curve, the sun and the heat loss.
     */
    _learnHtml(e, a = {}) {
      const heat = this._state(e.heating_rate);
      const cool = this._state(e.cooling_rate);
      const learned = !!(heat && heat.attributes.learned);
      const fill = (u, n) => (u ? String(n).split("{u}").join(u) : n);
      const tile = (entityId, label, text, sub) =>
        `<div class="link ltile" ${this._more(entityId)}><dt>${esc(label)}</dt><dd>${esc(text)}${
          sub ? `<small class="sub">${esc(sub)}</small>` : ""
        }</dd></div>`;
      let html = "";
      if (heat) {
        const unit = heat.attributes.unit_of_measurement || "min/°C";
        const deg = unit.replace(/^min\//, "");
        const value = num(heat.state);
        const tau = num(heat.attributes.inertia_minutes) ?? 0;
        const need = num(heat.attributes.hours_needed) ?? 4;
        const err = num(heat.attributes.error_per_hour);
        const resetId = e.reset_learning;
        const confirming = this._confirmReset === resetId;
        const reset =
          resetId && this._state(resetId)
            ? this._btn(this._t(confirming ? "reset_confirm" : "reset"), `data-action="reset-learning" data-entity="${esc(resetId)}"`, {
                icon: "refresh",
                kind: confirming ? "soft-warn" : "",
              })
            : "";
        let body;
        if (learned) {
          body = esc(
            err === null ? this._t("learn_state_done_short") : this._t("learn_state_done").replace("{err}", `${err.toFixed(2)} ${deg}`)
          );
        } else {
          // The hours seen so far, of the hours needed with and without heating.
          const bar = (key, hours) => {
            const v = Math.min(need, num(hours) ?? 0);
            const pct = need > 0 ? Math.round((100 * v) / need) : 0;
            const text = this._t(key).replace("{v}", String(v)).replace("{need}", String(need));
            return `<span class="lbar"><span class="lbar-text">${esc(text)}</span><span class="lbar-track" role="progressbar"
              aria-valuemin="0" aria-valuemax="${need}" aria-valuenow="${v}" aria-label="${esc(text)}"><span style="width:${pct}%"></span></span></span>`;
          };
          const sub = this._heatDefault(e);
          body = `${esc(this._t("learn_progress"))}${bar("learn_bar_heat", heat.attributes.hours_heating)}${bar(
            "learn_bar_idle",
            heat.attributes.hours_idle
          )}${sub ? `<small class="sub">${esc(sub)}</small>` : ""}`;
        }
        html += `<div class="wide learn"><div class="link" ${this._more(e.heating_rate)}><dt>${esc(
          this._t("learn_state")
        )}</dt><dd>${body}</dd></div>${reset}</div>`;
        if (learned) {
          html += tile(e.heating_rate, this._t("learn_heat"), value === null ? "–" : `${Math.round(value)} ${unit}`, this._t("learn_heat_sub"));
          html += tile(e.heating_rate, this._t("learn_inertia"), `${Math.round(tau)} min`, this._t("learn_inertia_sub"));
          // The curve is °C/h per °C, the same number in °F/h per °F.
          const c = num(heat.attributes.weather_curve) ?? 0;
          html +=
            Math.abs(c) < 0.0005
              ? tile(e.heating_rate, this._t("learn_curve"), this._t("learn_curve_none"), this._t("learn_curve_none_sub"))
              : tile(
                  e.heating_rate,
                  this._t("learn_curve"),
                  fill(deg, this._t("learn_curve_value").replace("{value}", `${c > 0 ? "+" : "−"}${Math.abs(c).toFixed(3)}`)),
                  fill(deg, this._t("learn_curve_sub"))
                );
          // The sun gain, only once it is seen: per unit of the sun signal and now.
          const sunGain = num(heat.attributes.sun_gain) ?? 0;
          if (sunGain > 0) {
            const signal = num(this._state(a.house_entities?.outdoor_average)?.attributes?.sun_forecast?.[0]?.[1]) ?? 0;
            html += tile(
              e.heating_rate,
              this._t("learn_sun"),
              fill(deg, this._t("learn_sun_value").replace("{value}", sunGain.toFixed(2))),
              fill(deg, this._t("learn_sun_sub").replace("{now}", (sunGain * signal).toFixed(2)))
            );
          }
        }
      }
      if (cool && learned) {
        const value = num(cool.state);
        const unit = cool.attributes.unit_of_measurement || "°C/h";
        html += tile(e.cooling_rate, this._t("learn_cool"), value === null ? "–" : `${value.toFixed(2)} ${unit}`, this._t("learn_cool_sub"));
      }
      return html;
    }

    /** One entity of a room: its name, icon, its state now in words and whether it is unavailable. */
    _deviceInfo(entityId, role) {
      const st = this._state(entityId);
      const name = st?.attributes?.friendly_name || entityId;
      let value;
      let bad = false;
      if (!st) {
        value = this._t("dev_missing");
        bad = true;
      } else if (st.state === "unavailable" || st.state === "unknown") {
        value = this._t(st.state === "unavailable" ? "dev_unavailable" : "dev_unknown");
        bad = true;
      } else if (role === "thermostat") {
        const at = st.attributes || {};
        const parts = [];
        if (num(at.current_temperature) !== null) parts.push(this._temp(at.current_temperature));
        if (num(at.temperature) !== null) parts.push(`→ ${this._temp(at.temperature)}`);
        if (st.state === "off") parts.push(this._t("off").toLowerCase());
        else if (at.hvac_action === "heating") parts.push(this._t("dev_heating"));
        else if (at.hvac_action === "idle") parts.push(this._t("dev_idle"));
        value = parts.join(" ") || st.state;
      } else if (role === "window" || role === "window_linked") {
        value = this._t(st.state === "on" ? "dev_open" : "dev_closed");
      } else if (role === "occupancy") {
        value = this._t(st.state === "on" ? "dev_present" : "dev_clear");
      } else if (role === "switch") {
        value = this._t(st.state === "on" ? "on" : "off");
      } else {
        const unit = st.attributes?.unit_of_measurement || "";
        value = `${st.state}${unit ? ` ${unit}` : ""}`;
      }
      return { st, name, value, bad, icon: DEVICE_ICONS[role] || "devices" };
    }

    /** The entities of the room with their state now; an unavailable one stands out (opens its dialog). */
    _devicesHtml(a) {
      const list = Array.isArray(a.devices) ? a.devices : [];
      if (!list.length) return "";
      const rows = list
        .map(([entityId, role]) => {
          const { name, value, bad, icon } = this._deviceInfo(entityId, role);
          return `<div class="wide dev link ${bad ? "bad" : ""}" ${this._more(entityId)}>
              ${this._icon(icon)}
              <span class="dname"><span>${esc(name)}</span><small>${esc(this._t(`dev_${role}`))}</small></span>
              <span class="dval">${esc(value)}</span>
            </div>`;
        })
        .join("");
      return `<dl class="details devices">${rows}</dl>`;
    }
  };
