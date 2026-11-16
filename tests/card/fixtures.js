// Fake Home Assistant for the Smart Heating Control card (shapes from sensor.py).
(function () {
  const HOUR = 3600e3;
  const iso = (t) => new Date(t).toISOString();
  window.makeHass = function (o = {}) {
    const now = o.now ?? Date.now();
    const unit = o.unit || "°C";
    const F = unit === "°F";
    const T = (c) => (c === null || c === undefined ? c : F ? +(c * 1.8 + 32).toFixed(1) : c);
    const D = (c) => (F ? +(c * 1.8).toFixed(2) : c);
    const entry = o.entry || "e1";
    const house = o.houseName || "Home";
    const hp = o.prefix || "home";
    const he = {
      mode: `select.${hp}_mode`, presence: `sensor.${hp}_presence`, outdoor_average: `sensor.${hp}_outdoor_average`,
      heating_runtime: `sensor.${hp}_heating_runtime`, heating_season: `binary_sensor.${hp}_heating_season`,
      outdoor_cutoff: `binary_sensor.${hp}_outdoor_cutoff`, heat_demand: `binary_sensor.${hp}_heat_demand`,
      pause: `switch.${hp}_pause`, guest_mode: `switch.${hp}_guest_mode`, vacation_start: `datetime.${hp}_vacation_start`,
      vacation_end: `datetime.${hp}_vacation_end`, clear_overrides: `button.${hp}_clear_overrides`,
      reevaluate: `button.${hp}_reevaluate`, clear_vacation: `button.${hp}_clear_vacation`,
      ...(o.scenarios ? { scenario: `select.${hp}_scenario` } : {}),
      ...(o.source ? { heat_source: `select.${hp}_heat_source` } : {}),
    };
    const states = {};
    const st = (id, state, attributes = {}) => {
      states[id] = { entity_id: id, state: String(state), attributes, last_updated: iso(now) + (o.tick || 0), last_changed: iso(now), context: {} };
    };
    st(he.presence, o.presence || "home", { advanced_climate_house: true, entry_id: entry, house_name: house, house_entities: he,
      temperature_unit: unit, persons: { "person.andrei": "home" }, arriving: false, guest_mode: false, vacation_active: false });
    st(he.mode, o.mode || "auto", { options: ["auto", "away", "vacation", "off", "summer"] });
    if (o.scenarios) st(he.scenario, o.scenario || "unknown", { options: o.scenarios });
    if (o.source) st(he.heat_source, o.source.state, { primary_name: "Boiler", secondary_name: "Heat pump", active: "primary", ...o.source });
    const fc = Array.from({ length: 12 }, (_, i) => [iso(Math.ceil(now / HOUR) * HOUR + i * HOUR), T(o.outdoor ?? 5) - i * 0.3]);
    st(he.outdoor_average, T(o.outdoor ?? 5), { latest: o.noOutdoor ? null : T(o.outdoor ?? 5), cutoff_enabled: true, cutoff_temperature: T(17),
      forecast: o.noOutdoor ? [] : fc, unit_of_measurement: unit, heating_season: true,
      sun_forecast: o.sun === undefined ? [] : Array.from({ length: 49 }, (_, i) => [iso(Math.floor(now / 60000) * 60000 + i * 900e3), o.sun]) });
    st(he.heating_runtime, 2.5, { unit_of_measurement: "h" });
    st(he.heating_season, "on"); st(he.outdoor_cutoff, "off"); st(he.heat_demand, "on");
    st(he.pause, o.pause ? "on" : "off"); st(he.guest_mode, o.guest ? "on" : "off");
    st(he.vacation_start, "unknown"); st(he.vacation_end, "unknown");
    for (const b of ["clear_overrides", "reevaluate", "clear_vacation"]) st(he[b], "unknown");

    const sched = { workday: [{ time: "00:00", preset: "sleep" }, { time: "06:00", preset: "home" }, { time: "22:00", preset: "sleep" }],
      weekend: [{ time: "00:00", preset: "sleep" }, { time: "08:00", preset: "home" }, { time: "23:00", preset: "sleep" }] };
    const rooms = o.rooms || [{ id: "r1", name: "Bedroom" }];
    for (const r of rooms) {
      const p = r.prefix || r.name.toLowerCase().replace(/\W+/g, "_");
      const e = {};
      for (const k of ["decision", "target_temperature", "room_temperature", "next_change", "heating_rate", "cooling_rate", "heating_runtime"]) e[k] = `sensor.${p}_${k}`;
      e.heat_demand = `binary_sensor.${p}_heat_demand`; e.window_open = `binary_sensor.${p}_window_open`;
      e.manual_override = `binary_sensor.${p}_manual_override`; e.child_lock = `switch.${p}_child_lock`;
      e.clear_override = `button.${p}_clear_override`; e.reset_learning = `button.${p}_reset_learning`;
      for (const lv of ["home", "eco", "away", "sleep", "comfort", "activity", "nearby"]) e[`level_${lv}`] = `number.${p}_level_${lv}`;
      const cur = r.current === undefined ? 20.2 : r.current;
      const plan = [{ at: iso(now), preset: r.preset || "home" }, { at: iso(now + 3 * HOUR), preset: "sleep" }, { at: iso(now + 10 * HOUR), preset: "home" }];
      const learned = r.learned !== false;
      const a = {
        room_id: r.id, entry_id: entry, room_name: r.name, reason: "Schedule", reason_key: r.reasonKey || "schedule", reason_params: r.reasonParams || {},
        target_kind: "preset", preset: r.preset || "home", temperature_unit: unit, target_temperature: T(r.target ?? 21),
        current_temperature: cur === null ? null : T(cur), offsets: r.offsets || [], presence: "home", window_open: !!r.window,
        override: r.override || null, profile: "workday", next_change: plan[1].at, next_preset: "sleep", plan,
        schedule: sched, profile_days: { workday: { days: "workday", enabled: true }, weekend: { days: "weekend", enabled: true } }, schedule_error: null, schedule_editable: true,
        presets: ["home", "eco", "away", "sleep", "comfort", "activity"], preset_names: {},
        levels: { home: T(21), eco: T(18), away: T(16), sleep: T(18.5), comfort: T(22), activity: T(19) },
        min_temperature: T(7), max_temperature: T(25), climate_entities: r.climates || [], device_preset: null, trv_boost: null,
        device_level: null, time_to_target: learned ? 35 : null, stop_forecast: null, next_estimate: r.estimate || null,
        no_heat_reason: null, hold_until: r.holdUntil || null, alerts: r.alerts || [], optimal_stop_cancelled: false,
        rate_learned: learned, humidity: r.humidity ?? null, surface_humidity: r.wall ?? null, device_levels: [],
        heat_demand: r.demand ?? true, heating: r.heating ?? true, temperature_trend: r.trend ?? 0, day_boundary: 0, source: r.source || "switch",
        custom_levels: true, house_name: house, entities: e, house_entities: he, devices: r.devices || [], held_at: r.heldAt ?? null,
      };
      if (r.dropAttrs) for (const k of r.dropAttrs) delete a[k];
      st(e.decision, r.state || "schedule", a);
      st(e.target_temperature, T(r.target ?? 21), { unit_of_measurement: unit, preset: r.preset || "home" });
      st(e.room_temperature, cur === null ? "unavailable" : T(cur), { unit_of_measurement: unit });
      st(e.next_change, plan[1].at, { next_preset: "sleep" });
      st(e.heating_rate, learned ? (F ? 22.2 : 40) : (F ? 33.3 : 60), {
        unit_of_measurement: `min/${unit}`, learned, heating_per_hour: D(2), weather_curve: r.curve ?? 0.05, sun_gain: r.sunGain ?? 0,
        loss_per_hour: 0.05, constant_loss: false, inertia_minutes: 30, heat_reaching_now: 0.3, error_per_hour: learned ? D(0.12) : null,
        minutes_per_degree: {}, hours_heating: learned ? 4 : 1.5, hours_idle: learned ? 4 : 0.5, hours_needed: 4,
        model: learned ? { band: r.band ?? null, inertia_control: !!r.inertia, tau: r.tau ?? 30, h: 2, c: r.curve ?? 0.05, k: 0.05, s: r.sunGain ?? 0, q: 0.3, constant_loss: false, outdoor_mean: 5 } : null });
      st(e.cooling_rate, learned ? D(0.75) : "unknown", { unit_of_measurement: `${unit}/h`, learned, loss_per_hour: 0.05, inertia_minutes: 30 });
      st(e.heating_runtime, 1.2, { unit_of_measurement: "h" });
      st(e.heat_demand, (r.demand ?? true) ? "on" : "off", { heating: r.heating ?? true });
      st(e.window_open, r.window ? "on" : "off"); st(e.manual_override, r.override ? "on" : "off");
      st(e.child_lock, "off"); st(e.clear_override, "unknown"); st(e.reset_learning, "unknown");
      for (const lv of ["home", "eco", "away", "sleep", "comfort", "activity", "nearby"]) st(e[`level_${lv}`], T(19), { min: T(7), max: T(25), step: 0.5, unit_of_measurement: unit });
    }
    // Other entities (the devices of a room): [entity_id, state, attributes].
    for (const [id, state, attributes] of o.extra || []) st(id, state, attributes || {});
    window.calls = window.calls || { ws: [], service: [] };
    return {
      states, user: { name: "Andrei", is_admin: true }, themes: { darkMode: !!o.dark }, language: o.lang || "en",
      locale: { language: o.lang || "en", time_format: o.timeFormat || "24", time_zone: "local" },
      config: { time_zone: o.tz || "Europe/Bucharest", unit_system: { temperature: unit } },
      callService: async (domain, service, data) => { window.calls.service.push({ domain, service, data }); if (o.serviceFails) throw new Error("boom"); },
      callWS: async (msg) => {
        window.calls.ws.push(msg);
        if (o.historyFails) throw new Error("history down");
        if (msg.type === "recorder/statistic_during_period") return { change: 1.5 };
        if (msg.type === "recorder/statistics_during_period") {
          if (o.statsFail) throw new Error("statistics down");
          // One row a period from the start to now: a changing heating time per sensor.
          const len = { day: 864e5, week: 7 * 864e5, month: 30 * 864e5 }[msg.period] || 864e5;
          const out = {};
          msg.statistic_ids.forEach((id, k) => {
            const rows = [];
            // The temperatures (outdoor, room, target) have a mean, minimum and maximum instead.
            const base = id.endsWith("_outdoor_average") ? 4 : id.endsWith("_room_temperature") ? 20.4 : id.endsWith("_target_temperature") ? 21 : null;
            for (let t = Date.parse(msg.start_time), i = 0; t < now; t += len, i++) {
              if (base === null) rows.push({ start: t, end: t + len, change: ((i + k) % 5) * 0.75 + (id.startsWith("sensor.home") ? 2 : 0.5) });
              else if (!o.noTempStats) rows.push({ start: t, end: t + len, mean: T(base + ((i + k) % 3) * 0.5), min: T(base - 3 + (i % 2)), max: T(base + 4 - (i % 2)) });
            }
            out[id] = rows;
          });
          return out;
        }
        if (msg.type === "advanced_climate/history") {
          if (o.historyLogFails) throw new Error("history log down");
          // Each room: three decisions; the house: an alert that ended and one that still applies.
          const at = (h) => iso(now - h * HOUR);
          return { houses: [{ entry_id: entry, name: house, temperature_unit: unit,
            rooms: rooms.map((r) => ({ room_id: r.id, name: r.name, decisions: [
              { time: at(26), rule: "schedule", target: { kind: "preset", preset: "sleep", temperature: null }, description: "Schedule: sleep", reason_key: "schedule", reason_params: { preset: "sleep" } },
              { time: at(5), rule: "window_open", target: { kind: "off" }, description: "Window open", reason_key: "window_open", reason_params: {} },
              { time: at(1), rule: "schedule", target: { kind: "preset", preset: "home", temperature: null }, description: "Schedule: home", reason_key: "schedule", reason_params: { preset: "home" } },
            ] })),
            alerts: [
              { key: "dev", code: "device_unavailable", params: { entity: "climate.trv", minutes: 15 }, room: rooms[0]?.id, start: at(30), end: at(29.25) },
              { key: "mold", code: "mold_risk", params: { surface: 84, humidity: 62 }, room: rooms[0]?.id, start: at(3), end: null },
              { key: "out", code: "outdoor_unavailable", params: {}, room: null, start: at(50), end: at(49), restart: true },
            ] }] };
        }
        if (msg.type !== "history/history_during_period") return {};
        const s = Date.parse(msg.start_time), en = Date.parse(msg.end_time), out = {};
        const step = (o.historyStepMin || 15) * 60e3;
        const pts = (f) => { const r = []; for (let t = s; t <= en; t += step) r.push(f(t)); return r; };
        for (const id of msg.entity_ids) {
          if (o.emptyHistory) { out[id] = []; continue; }
          if (id.endsWith("_room_temperature")) out[id] = pts((t) => ({ s: String(T(19.5 + 1.5 * Math.sin(t / HOUR / 24 * 2 * Math.PI))), lu: t / 1000 }));
          else if (id.endsWith("_target_temperature")) out[id] = [{ s: String(T(21)), a: { preset: "home" }, lu: s / 1000 }];
          else if (id.endsWith("_heat_demand")) out[id] = pts((t) => ({ s: Math.floor(t / HOUR) % 3 === 0 ? "on" : "off", a: { heating: true }, lu: t / 1000 }));
          else if (id.endsWith("_outdoor_average")) out[id] = pts((t) => ({ s: "5", a: { latest: T(5 + 3 * Math.sin(t / HOUR)) }, lu: t / 1000 }));
        }
        return out;
      },
    };
  };
})();
