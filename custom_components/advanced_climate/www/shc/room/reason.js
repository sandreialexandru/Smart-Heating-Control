// Why a room has its target, what comes next, why it does not heat, how long until warm.

import { num } from "../core/format.js";

export const ReasonMixin = (Base) =>
  class extends Base {
    /** The reason of the decision in the language of the card (the English text otherwise). */
    _reasonText(a) {
      const key = a.reason_key;
      const base = key ? this._t(`r_${key}`) : null;
      if (!key || base === `r_${key}`) return a.reason || "";
      const p = a.reason_params || {};
      const temp = (v) => (num(v) === null ? "–" : this._temp(v));
      const values = {
        preset: p.preset ? this._presetName(a, p.preset) : "",
        temperature: temp(p.temperature),
        max: temp(p.max),
        frost: temp(p.frost),
        current: temp(p.current),
        value: temp(p.value),
        limited: temp(p.limited),
        would: p.preset ? `${this._presetName(a, p.preset)}${num(p.temperature) !== null ? ` ${this._temp(p.temperature)}` : ""}` : temp(p.temperature),
      };
      const fill = (text) => text.replace(/\{(\w+)\}/g, (m, k) => (values[k] !== undefined ? values[k] : m));
      let text = fill(base);
      if (p.extra) text += ` (${this._t(`rs_${p.extra}`)})`;
      const offsets = (a.offsets || [])
        .map(([label, delta]) => `${this._offsetName(label)} ${delta > 0 ? "+" : ""}${delta}°`)
        .join(", ");
      if (offsets) text += ` (${offsets})`;
      if (p.limited !== undefined) text += ` (${fill(this._t("rs_limited"))})`;
      if (p.stop_cancelled) text += ` (${this._t("rs_stop_cancelled")})`;
      if (num(a.held_at) !== null) text += ` (${this._heldAt(a)})`;
      return text;
    }

    /** The thermostat holds more than the target: its entity goes no lower. */
    _heldAt(a) {
      return this._t("rs_held_at").replace("{temp}", this._temp(a.held_at));
    }

    /** Name of an adjustment of the target. */
    _offsetName(label) {
      const text = this._t(`off_${label}`);
      return text === `off_${label}` ? label : text;
    }

    /** Why a room below its target does not heat. */
    _noHeatHtml(a) {
      const r = a.no_heat_reason;
      if (!r || !r.code) return "";
      let text = this._t(`nh_${r.code}`);
      if (text === `nh_${r.code}`) return "";
      text = text
        .replace("{value}", r.value ?? "")
        .replace("{count}", r.count ?? "")
        .replace("{needed}", r.needed ?? "")
        .replace("{room}", r.room ?? "")
        .replace("{entity}", r.entity ? this._hass?.states?.[r.entity]?.attributes?.friendly_name || r.entity : "");
      return this._msg({ kind: "info noheat", icon: "information-outline", lead: `${this._t("no_heat")}:`, text });
    }

    /** When a manual change ends, in words. */
    _overrideUntil(a) {
      if (!a.override) return "";
      if (a.override.until) {
        // And the time it has left (at least 1 min until it ends).
        const left = (new Date(a.override.until).getTime() - Date.now()) / 60000;
        const rest = Number.isFinite(left) && left > 0 ? ` · ${this._t("time_left").replace("{d}", this._duration(Math.max(1, left)))}` : "";
        return `${this._t("until")} ${this._fmtTime(a.override.until)}${rest}`;
      }
      const latest = a.next_change
        ? ` (${this._t("at_latest")} ${this._fmtTime(a.next_change)}${
            a.next_preset ? `, ${this._presetName(a, a.next_preset)}` : ""
          })`
        : "";
      return `${this._t("until_reeval")}${latest}`;
    }

    /** "~35 min" until the target, from the learned heating. */
    _eta(a) {
      const stop = a.stop_forecast;
      if (stop && num(stop.temperature) !== null) {
        return this._t("stop_at")
          .replace("{temp}", this._temp(stop.temperature))
          .replace("{time}", this._fmtTime(stop.at));
      }
      const current = num(a.current_temperature);
      const target = num(a.target_temperature);
      if (current === null || target === null || target - current <= 0) return "";
      if (a.time_to_target === null || a.time_to_target === undefined) return "";
      if (!a.rate_learned) return this._t("eta_learning");
      return `~${this._duration(a.time_to_target)}`;
    }

    /** The optimal start / stop expected for the next change, in words. */
    _estimate(a) {
      const est = a.next_estimate;
      if (!est) return "";
      const level = num(est.temperature);
      const target =
        est.sent_as === "temperature" && level !== null
          ? this._t("est_temperature").replace("{temp}", this._temp(level))
          : `${this._t("est_preset").replace("{preset}", this._presetName(a, est.preset))}${
              level !== null ? ` (${this._temp(level)})` : ""
            }`;
      const head = this._t(est.kind === "optimal_start" ? "est_start" : "est_stop")
        .replace("{target}", target)
        .replace("{time}", this._fmtTime(est.at));
      let when;
      if (est.started_at) when = this._t("est_running").replace("{time}", this._fmtTime(est.started_at));
      else if (!est.minutes) when = this._t("est_not_needed");
      else when = this._t("est_begins").replace("{time}", this._fmtTime(est.starts_at));
      const parts = [when];
      if (num(est.outdoor) !== null) {
        parts.push(
          this._t(est.outdoor_source === "forecast" ? "est_out_forecast" : "est_out_now").replace(
            "{temp}",
            this._temp(est.outdoor)
          )
        );
      }
      if (!est.learned) parts.push(this._t("eta_learning"));
      return `${head}: ${parts.join(", ")}`;
    }

    /** While heating the time to the target, else the next change ("Sleep at 22:00"), else the time to the target. */
    _roomNext(a) {
      const eta = this._eta(a);
      const next = a.next_change
        ? this._t("next_at").replace("{preset}", this._presetName(a, a.next_preset)).replace("{time}", this._fmtTime(a.next_change))
        : "";
      return (a.heating && eta) || next || eta;
    }

    /** "default 60 min/1°C": the heating used until the model is learned (empty once learned). */
    _heatDefault(e) {
      const s = e && e.heating_rate ? this._state(e.heating_rate) : null;
      if (s && s.attributes.learned) return "";
      const unit = ((s && s.attributes.unit_of_measurement) || "min/°C").replace(/^min\//, "");
      const value = s ? num(s.state) : null;
      return this._t("heat_default").replace("{value}", `${Math.round(value ?? 60)} min/1${unit}`);
    }

    /** Icon of the rule that decides the room. */
    _ruleIcon(rule) {
      const icons = {
        window_open: "window-open-variant",
        manual_override: "hand-back-right-outline",
        schedule: "calendar-clock",
        optimal_start: "calendar-clock",
        optimal_stop: "calendar-clock",
        room_unoccupied: "calendar-clock",
        vacation: "airplane",
        house_away: "home-export-outline",
        presence_far: "map-marker-distance",
        presence_nearby: "map-marker-radius-outline",
        pause: "pause",
        mode_off: "power",
        summer: "weather-sunny",
        out_of_season: "power",
        outdoor_cutoff: "weather-sunny",
        frost_protection: "snowflake",
        maximum_temperature: "thermometer-high",
        sensor_fallback: "thermometer-alert",
        valve_exercise: "valve",
      };
      return icons[rule] || "information-outline";
    }
  };
