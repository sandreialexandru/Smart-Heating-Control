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
 *   compact: false               # one row per room (and the house); tap a row to open it
 *   runtime_period: day          # heating time shown for: day | week | month (tap to change)
 */

const CARD_VERSION = "2.3.25";

// Decisions that last only a while: the planned part of the chart shows the schedule.
const TEMPORARY_RULES = ["window_open", "frost_protection", "valve_exercise"];
// Decisions that hold until something changes: the plan keeps them.
const FLAT_RULES = [
  "mode_off", "summer", "out_of_season", "pause", "presence_far", "presence_nearby",
  "sensor_fallback", "outdoor_cutoff", "vacation",
];
// A target that is only a temperature (no level): neutral.
const TEMP_COLOR = "var(--ac-fixed)";
const PRESET_COLORS = {
  comfort: "#d9480f",
  home: "#f08c00",
  activity: "#e0a030",
  eco: "#2f9e8f",
  sleep: "#5f6fd1",
  away: "#8a96a3",
  frost: "#74a9cf",
};

const MIN_ZOOM_SPAN = 20 * 60 * 1000; // closest zoom: 20 minutes

const WEEKDAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];

/** True when two active profiles cannot be on together (as the integration checks). */
function profileOverlap(a, b) {
  const la = Array.isArray(a);
  const lb = Array.isArray(b);
  if (la && lb) return a.some((d) => b.includes(d));
  if (la || lb) return false; // chosen weekdays are above the other kinds of days
  if (a === "all" || b === "all") return true;
  return a === b;
}

/** Days without an active profile (as the integration reports them). */
function uncoveredDays(meta) {
  const active = Object.values(meta || {}).filter((m) => m && m.enabled).map((m) => m.days);
  const specific = new Set(active.filter(Array.isArray).flat());
  const all = active.includes("all");
  const work = all || active.includes("workday");
  const free = all || active.includes("weekend");
  return {
    days: WEEKDAY_KEYS.filter((d, i) => !specific.has(d) && !(i < 5 ? work : free)),
    free_days: !free && WEEKDAY_KEYS.slice(0, 5).some((d) => !specific.has(d)),
    workdays: !work && WEEKDAY_KEYS.slice(5).some((d) => !specific.has(d)),
  };
}

/** Days a new profile is for, from its name (it starts off). */
function guessDays(name) {
  if (name === "workday" || name === "weekend") return name;
  if (WEEKDAY_KEYS.includes(name)) return [name];
  return "all";
}

/** Turn a profile on or off; the active profiles that overlap it are turned off. */
function switchProfile(meta, name, on) {
  const next = JSON.parse(JSON.stringify(meta || {}));
  if (!next[name]) next[name] = { days: guessDays(name), enabled: false };
  next[name].enabled = on;
  if (on) {
    for (const [other, m] of Object.entries(next)) {
      if (other !== name && m.enabled && profileOverlap(m.days, next[name].days)) m.enabled = false;
    }
  }
  return next;
}

const DEFAULTS = {
  show_house: true,
  show_rooms: true,
  show_timeline: true,
  show_quick_override: true,
  show_levels: true,
  show_details: true,
  show_schedule_editor: true,
  collapsed: false,
  compact: false,
  runtime_period: "day",
};

const RUNTIME_PERIODS = ["day", "week", "month"];

const TEXT = {
  en: {
    title: "Heating",
    now_tag: "Now",
    target_tag: "Target",
    arriving: "On the way home",
    vacation_none: "not planned",
    vacation_hint: "During the vacation every room uses away. A few hours before the end the schedule applies again, so the house is warm when you return. Without a start date the vacation starts now.",
    today: "Today",
    quick_hint: "Keeps a level or a temperature as a manual change. Empty duration = the rule from the options.",
    days_workday: "Monday–Friday, except holidays",
    days_weekend: "Saturday, Sunday and holidays",
    days_all: "All days",
    days_label: "Days",
    days_opt_all: "All days",
    days_opt_workday: "Workdays",
    days_opt_weekend: "Weekend and holidays",
    days_opt_days: "Chosen days",
    profile_on: "On",
    profile_off: "Off",
    frost_level: "frost protection",
    gap_free_days: "free days (holidays)",
    gap_weekend_workdays: "workdays on the weekend",
    gap_warning: "No active profile: {days}. On those days the room keeps its frost protection.",
    gap_confirm: "{days} will have no active profile (frost protection). Continue?",
    confirm: "Confirm",
    schedule_help: "Each time starts a level that lasts until the next time; the last one lasts until the first time of the next day. The schedule is used while someone is home; windows, manual changes, vacation, presence (nearby = eco, far = away) and the house mode come first.",
    schedule_active: "The schedule decides right now.",
    schedule_not_active: "Right now {rule} decides; the schedule applies again when that ends.",
    next_day: "next day",
    starts: "From",
    ends: "Until",
    level: "Level",
    remove_profile: "Delete profile",
    presence: "Presence",
    outdoor: "Outdoor average",
    outdoor_hours: "Outdoor average ({h} h)",
    season: "Heating season",
    cutoff: "Warm outside",
    demand: "Heat demand",
    runtime: "Heating time",
    mode: "Mode",
    pause: "Pause",
    guests: "Guests",
    vacation: "Vacation",
    from: "From",
    to: "To",
    set_vacation: "Save vacation",
    clear_vacation: "Clear vacation",
    reevaluate: "Reevaluate",
    clear_all: "Clear manual changes",
    child_lock: "Child lock",
    next: "Next",
    quick: "Set for a while",
    for_hours: "for",
    hours: "h",
    apply: "Set",
    clear_override: "Back to automatic",
    override: "Manual change",
    until: "until",
    until_change: "until the next change",
    until_reeval: "until the next reevaluation",
    at_latest: "at the latest",
    reeval_help: "Ends when the schedule moves to another level, presence or the house mode changes, a window opens, the profile changes or the outdoor cutoff / heating season changes. The periodic check does not end it.",
    window: "Window open",
    heating: "Heating",
    details: "Details",
    levels: "Level temperatures",
    schedule: "Schedule",
    edit: "Edit schedule",
    save: "Save schedule",
    cancel: "Cancel",
    add_slot: "Add time",
    add_profile: "Add profile",
    profile_name: "New profile name",
    remove: "Remove",
    room_temp: "Room temperature",
    target: "Target",
    rate: "Heating rate",
    adjustments: "Adjustments",
    none: "none",
    not_editable: "This room follows a Schedule helper; edit the helper instead.",
    no_rooms: "No heating devices yet. Add them in Settings → Devices & services → Smart Heating Control → Configure → Heating of the whole house (or add rooms).",
    error: "Could not save",
    persons: "People",
    on: "On",
    off: "Off",
    level_temps_gt: "Preset temperatures (set in Generic Thermostat)",
    from_device: "thermostat",
    device_preset: "Thermostat preset now",
    trv_boost: "TRV boost",
    trv_boost_on: "on • {temp}",
    trv_boost_off: "{temp} while heating",
    no_preset: "none (manual temperature)",
    active: "active",
    chart_label: "Last 24 hours and the next 12",
    legend_temp: "Temperature",
    legend_target: "Target / plan",
    legend_heat: "Heating",
    planned: "Planned",
    tip_early_start: "Early start",
    tip_early_stop: "Early stop",
    loading: "loading history…",
    drag_hint: "Drag the handles on the bar to move a start time in 5-minute steps (arrow keys: 5 min, Shift: 1 h). Levels are chosen in the list.",
    copy_to: "Copy over…",
    new_profile: "new",
    period_day: "today",
    period_week: "this week",
    period_month: "this month",
    period_hint: "Tap to change the period (today, this week, this month).",
    eta_learning: "learning…",
    heat_default: "default {value}",
    grp_temps: "Temperatures",
    grp_program: "Schedule",
    grp_learning: "Learning",
    reset: "Reset",
    reset_confirm: "Confirm?",
    last_episode: "Last heating episode",
    last_episode_value: "+{rise} in {minutes} min, outdoor {outdoor}, {time}",
    last_episode_value_no_out: "+{rise} in {minutes} min, {time}",
    eta_help: "Time until the target, as learned from the heating episodes for the current outdoor temperature.",
    stop_at: "~{temp} at {time}",
    stop_help: "Optimal stop: expected room temperature at the scheduled change, from the learned cooling and the outdoor temperature expected until then.",
    est_label: "Optimal start / stop",
    est_start: "Start for {target} at {time}",
    est_stop: "Stop for {target} at {time}",
    est_preset: "preset {preset}",
    est_temperature: "temperature {temp}",
    est_begins: "begins ~{time}",
    est_running: "running since {time}",
    est_not_needed: "not needed",
    est_out_forecast: "outdoor forecast {temp}",
    est_out_now: "outdoor now {temp}",
    zoom_in: "Zoom in",
    zoom_out: "Zoom out",
    zoom_reset: "Whole period",
    zoom_1h: "Last hour",
    zoom_6h: "Last 6 hours",
    nav_help: "Drag the window (or tap a place) to move the zoomed chart.",
    cutoff_on: "on • heating is off until the average falls to {temp}",
    cutoff_forecast: "on (forecast) • heating is off: the forecast mean for {h} h is {temp}",
    cutoff_cancelled: "cancelled (forecast) • it gets cold: the forecast mean for {h} h is {temp}, rooms heat when they need it",
    no_heat: "Not heating",
    nh_tolerance: "the room is within the thermostat tolerance",
    nh_hysteresis: "within the hysteresis of {value}°",
    nh_relay_min_on: "the relay waits for its minimum on time",
    nh_relay_min_off: "the relay waits for its minimum off time",
    nh_source_min_on: "the heat source waits for its minimum on time",
    nh_source_min_off: "the heat source waits for its minimum off time",
    nh_rooms_needed: "waiting for other rooms: {count} of {needed} ask for heat",
    nh_reference_room: "waiting for the reference room {room}",
    nh_source_off: "the heat source is off",
    nh_source_unknown: "the state of the heat source is unknown",
    nh_device_off: "the thermostat is off",
    legend_outdoor: "Outdoor",
    legend_forecast: "forecast",
    est_mark_start: "start ~{time}",
    est_mark_stop: "stop ~{time}",
    paused_banner: "Pause: only frost protection, the maximum temperature and taking a TRV boost back to the target are sent",
    learn_heat: "Heating learned",
    learn_cool: "Cooling learned",
    learn_none: "learning…",
    learn_heat_value: "{n} episodes · {fixed} min + {rate} now",
    learn_heat_value_1: "1 episode · {fixed} min + {rate} now",
    learn_cool_value: "{n} episodes · falls {rate} now",
    learn_cool_value_1: "1 episode · falls {rate} now",
    origin_card: "card / service",
    origin_device: "on the device",
    back_after: "comes back after: {rule}",
    applied_after: "applies after: {rule}",
    alerts: "Alerts",
    al_source_unavailable: "The heat source {entity} has been unavailable for more than {minutes} min: no heating, not even frost protection.",
    al_room_difference: "Some rooms stay cold while others are warm: {rooms}.",
    al_preset_missing: "The level {level} is not available on {entity} and its temperature is unknown.",
    al_not_accepted: "{entities} did not accept {target}.",
    al_window_long: "A window has been open for more than {minutes} min.",
    al_device_unavailable: "{entity} has been unavailable for more than {minutes} min.",
    al_sensor_unavailable_device: "The temperature sensors are unavailable; the device sensor is used.",
    al_sensor_unavailable_eco: "The temperature sensors are unavailable; eco is used.",
    al_schedule_invalid: "The schedule is invalid ({error}); the default schedule is used.",
    al_schedule_gap: "No active schedule profile: {days}; the room keeps its frost protection on those days.",
    al_battery_low: "Low battery on {device} ({level}%).",
    al_weather_without_source: "On but not working without an outdoor temperature sensor or a weather entity: {features}.",
    al_boiler_min_rooms: "Rooms needed to start the heat source is {needed}, but the house has {rooms} rooms: the heat source starts only for frost protection.",
    al_outdoor_unavailable: "No outdoor temperature from {entities} for more than {minutes} min: the cutoff, the automatic season, the compensation and the optimal stop cannot use it.",
    wf_cutoff: "turn heating off when warm",
    wf_season_auto: "automatic season",
    wf_compensation: "outdoor compensation",
    wf_window_ignore: "ignore windows above",
    wf_forecast: "use the forecast (needs a weather entity and the cutoff)",
    open_entity: "Open the entity",
    r_pause: "Paused: only safety commands are sent",
    r_valve_exercise: "Valve exercise: valves fully open for a few minutes",
    r_mode_off: "Mode off: frost protection only",
    r_summer: "Summer mode: heating off",
    r_out_of_season: "Outside the heating season: heating off",
    r_window_off: "Window open: heating off",
    r_window_frost: "Window open: frost protection",
    r_override: "Manual change is respected",
    r_vacation: "Vacation",
    r_far: "Everyone is far (outside the nearby zones)",
    r_nearby: "Nobody home, someone nearby",
    r_nearby_temperature: "Nobody home, someone nearby: {temperature}",
    r_nearby_schedule: "Nobody home, someone nearby: the schedule ({preset}) is lower",
    r_no_schedule: "No schedule available",
    r_no_profile: "No active profile for this day: frost protection",
    r_sensor_fallback: "Temperature sensors unavailable: eco until they recover",
    r_sensor_fallback_schedule: "Temperature sensors unavailable: the schedule ({preset}), lower than eco",
    r_unoccupied: "Room unoccupied (schedule: {preset})",
    r_schedule: "Schedule: {preset}",
    r_optimal_start: "Optimal start: heating early for {preset}",
    r_optimal_stop: "Optimal stop: lowering early to {preset}",
    r_cutoff: "Warm outside: heating off (would be {would})",
    r_max_level: "Maximum temperature ({preset} is above {max})",
    r_frost_level: "Frost protection ({preset} is below {frost})",
    r_max_device: "Maximum temperature: {value} is above {max}",
    r_max_room: "Maximum temperature: the room is {current}, at {max} or above",
    r_frost_below: "Frost protection: {current} is below {frost}",
    r_frost_holding: "Frost protection: heating up to {frost}",
    rs_arriving: "someone is on the way home",
    rs_vacation_preheat: "vacation ends soon: preheating",
    rs_limited: "limited to {limited}",
    rs_stop_cancelled: "optimal stop cancelled: the room got colder than expected",
    off_compensation: "outdoor compensation",
    off_tariff_high: "high tariff",
    off_tariff_low: "low tariff",
    off_pv_surplus: "solar surplus",
    off_solar_gain: "solar gain",
    guests_banner: "Guest mode: the house counts as Home even if none of the people is home",
    auto_short: "Automatic",
    device_temp: "Device {temp}",
    trv_boost_chip: "TRV boost · {temp}",
    trv_boost_chip_off: "TRV boost {temp} while heating",
  },
  ro: {
    title: "Încălzire",
    now_tag: "Acum",
    target_tag: "Țintă",
    arriving: "Pe drum spre casă",
    vacation_none: "neplanificată",
    vacation_hint: "În vacanță toate camerele folosesc away. Cu câteva ore înainte de sfârșit se aplică iar programul, ca să găsești casa caldă. Fără dată de început, vacanța începe acum.",
    today: "Azi",
    quick_hint: "Păstrează un nivel sau o temperatură ca modificare manuală. Durată goală = regula din opțiuni.",
    days_workday: "Luni–vineri, fără sărbători",
    days_weekend: "Sâmbătă, duminică și sărbători",
    days_all: "Toate zilele",
    days_label: "Zile",
    days_opt_all: "Toate zilele",
    days_opt_workday: "Zile lucrătoare",
    days_opt_weekend: "Weekend și sărbători",
    days_opt_days: "Zile anume",
    profile_on: "Pornit",
    profile_off: "Oprit",
    frost_level: "antiîngheț",
    gap_free_days: "zilele libere (sărbători)",
    gap_weekend_workdays: "zilele lucrătoare din weekend",
    gap_warning: "Fără profil activ: {days}. În acele zile camera rămâne pe antiîngheț.",
    gap_confirm: "{days} vor rămâne fără profil activ (antiîngheț). Continui?",
    confirm: "Confirmă",
    schedule_help: "Fiecare oră pornește un nivel care ține până la ora următoare; ultimul ține până la prima oră din ziua următoare. Programul se folosește cât timp e cineva acasă; ferestrele, modificările manuale, vacanța, prezența (aproape = eco, departe = away) și modul casei au prioritate.",
    schedule_active: "Acum decide programul.",
    schedule_not_active: "Acum decide {rule}; programul se aplică din nou după ce se termină.",
    next_day: "a doua zi",
    starts: "De la",
    ends: "Până la",
    level: "Nivel",
    remove_profile: "Șterge profilul",
    presence: "Prezență",
    outdoor: "Medie afară",
    outdoor_hours: "Medie afară ({h} h)",
    season: "Sezon de încălzire",
    cutoff: "Cald afară",
    demand: "Cerere de căldură",
    runtime: "Timp de încălzire",
    mode: "Mod",
    pause: "Pauză",
    guests: "Oaspeți",
    vacation: "Vacanță",
    from: "De la",
    to: "Până la",
    set_vacation: "Salvează vacanța",
    clear_vacation: "Șterge vacanța",
    reevaluate: "Reevaluează",
    clear_all: "Anulează modificările manuale",
    child_lock: "Blocare modificări",
    next: "Următor",
    quick: "Setează temporar",
    for_hours: "pentru",
    hours: "h",
    apply: "Setează",
    clear_override: "Înapoi la automat",
    override: "Modificare manuală",
    until: "până la",
    until_change: "până la următoarea schimbare",
    until_reeval: "până la următoarea reevaluare",
    at_latest: "cel târziu",
    reeval_help: "Se termină când programul trece la alt nivel, se schimbă prezența sau modul casei, se deschide o fereastră, se schimbă profilul ori pragul exterior / sezonul. Verificarea periodică nu o încheie.",
    window: "Fereastră deschisă",
    heating: "Încălzește",
    details: "Detalii",
    levels: "Temperaturile nivelurilor",
    schedule: "Program",
    edit: "Editează programul",
    save: "Salvează programul",
    cancel: "Renunță",
    add_slot: "Adaugă oră",
    add_profile: "Adaugă profil",
    profile_name: "Numele profilului nou",
    remove: "Șterge",
    room_temp: "Temperatura camerei",
    target: "Țintă",
    rate: "Viteză de încălzire",
    adjustments: "Ajustări",
    none: "niciuna",
    not_editable: "Camera urmează un helper de program; editează helperul.",
    no_rooms: "Încă nu sunt dispozitive de încălzire. Adaugă-le din Setări → Dispozitive și servicii → Smart Heating Control → Configurează → Încălzirea întregii case (sau adaugă camere).",
    error: "Nu s-a putut salva",
    persons: "Persoane",
    on: "Pornit",
    off: "Oprit",
    level_temps_gt: "Temperaturile preseturilor (setate în Generic Thermostat)",
    from_device: "din termostat",
    device_preset: "Preset în termostat acum",
    trv_boost: "Forțare TRV",
    trv_boost_on: "activă • {temp}",
    trv_boost_off: "{temp} cât încălzește",
    no_preset: "niciunul (temperatură manuală)",
    active: "activ",
    chart_label: "Ultimele 24 de ore și următoarele 12",
    legend_temp: "Temperatură",
    legend_target: "Țintă / program",
    legend_heat: "Încălzire",
    planned: "Programat",
    tip_early_start: "Pornire anticipată",
    tip_early_stop: "Oprire anticipată",
    loading: "se încarcă istoricul…",
    drag_hint: "Trage de mânerele de pe bară ca să muți o oră de început din 5 în 5 minute (săgeți: 5 min, Shift: 1 h). Nivelurile se aleg în listă.",
    copy_to: "Copiază peste…",
    new_profile: "nou",
    period_day: "azi",
    period_week: "săptămâna aceasta",
    period_month: "luna aceasta",
    period_hint: "Apasă ca să schimbi perioada (azi, săptămâna aceasta, luna aceasta).",
    eta_learning: "se învață…",
    heat_default: "implicit {value}",
    grp_temps: "Temperaturi",
    grp_program: "Program",
    grp_learning: "Învățare",
    reset: "Resetează",
    reset_confirm: "Confirmi?",
    last_episode: "Ultimul episod de încălzire",
    last_episode_value: "+{rise} în {minutes} min, afară {outdoor}, {time}",
    last_episode_value_no_out: "+{rise} în {minutes} min, {time}",
    eta_help: "Timpul până la țintă, după cât a durat încălzirea în episoadele învățate, la temperatura de afară de acum.",
    stop_at: "~{temp} la {time}",
    stop_help: "Oprire anticipată: temperatura estimată a camerei la schimbarea din program, după răcirea învățată și temperatura de afară prognozată până atunci.",
    est_label: "Pornire / oprire anticipată",
    est_start: "Pornire pentru {target} la {time}",
    est_stop: "Oprire pentru {target} la {time}",
    est_preset: "presetul {preset}",
    est_temperature: "temperatura {temp}",
    est_begins: "începe pe la {time}",
    est_running: "în curs din {time}",
    est_not_needed: "nu e nevoie",
    est_out_forecast: "afară prognozat {temp}",
    est_out_now: "afară acum {temp}",
    zoom_in: "Mărește",
    zoom_out: "Micșorează",
    zoom_reset: "Toată perioada",
    zoom_1h: "Ultima oră",
    zoom_6h: "Ultimele 6 ore",
    nav_help: "Trage fereastra (sau atinge un loc) ca să muți graficul mărit.",
    cutoff_on: "pornit • încălzirea e oprită până media scade la {temp}",
    cutoff_forecast: "pornit (prognoză) • încălzirea e oprită: media prognozei pe {h} h este {temp}",
    cutoff_cancelled: "anulat (prognoză) • vine frigul: media prognozei pe {h} h este {temp}, camerele încălzesc la nevoie",
    no_heat: "Nu încălzește",
    nh_tolerance: "camera e în toleranța termostatului",
    nh_hysteresis: "în histerezisul de {value}°",
    nh_relay_min_on: "releul așteaptă timpul minim pornit",
    nh_relay_min_off: "releul așteaptă timpul minim oprit",
    nh_source_min_on: "sursa de căldură așteaptă timpul minim pornit",
    nh_source_min_off: "sursa de căldură așteaptă timpul minim oprit",
    nh_rooms_needed: "așteaptă alte camere: {count} din {needed} cer căldură",
    nh_reference_room: "așteaptă camera de referință {room}",
    nh_source_off: "sursa de căldură e oprită",
    nh_source_unknown: "starea sursei de căldură e necunoscută",
    nh_device_off: "termostatul e oprit",
    legend_outdoor: "Afară",
    legend_forecast: "prognoză",
    est_mark_start: "pornire ~{time}",
    est_mark_stop: "oprire ~{time}",
    paused_banner: "Pauză: se trimit doar antiînghețul, temperatura maximă și readucerea forțării TRV la țintă",
    learn_heat: "Învățare încălzire",
    learn_cool: "Învățare răcire",
    learn_none: "se învață…",
    learn_heat_value: "{n} episoade · {fixed} min + {rate} acum",
    learn_heat_value_1: "1 episod · {fixed} min + {rate} acum",
    learn_cool_value: "{n} episoade · scade {rate} acum",
    learn_cool_value_1: "1 episod · scade {rate} acum",
    origin_card: "card / serviciu",
    origin_device: "pe dispozitiv",
    back_after: "revine după: {rule}",
    applied_after: "se aplică după: {rule}",
    alerts: "Alerte",
    al_source_unavailable: "Sursa de căldură {entity} e indisponibilă de peste {minutes} min: nu se încălzește, nici pentru antiîngheț.",
    al_room_difference: "Unele camere rămân reci, altele sunt calde: {rooms}.",
    al_preset_missing: "Nivelul {level} nu există pe {entity} și temperatura lui e necunoscută.",
    al_not_accepted: "{entities} nu a acceptat {target}.",
    al_window_long: "O fereastră e deschisă de peste {minutes} min.",
    al_device_unavailable: "{entity} e indisponibil de peste {minutes} min.",
    al_sensor_unavailable_device: "Senzorii de temperatură sunt indisponibili; se folosește senzorul dispozitivului.",
    al_sensor_unavailable_eco: "Senzorii de temperatură sunt indisponibili; se folosește eco.",
    al_schedule_invalid: "Programul e invalid ({error}); se folosește programul implicit.",
    al_schedule_gap: "Fără profil activ în program: {days}; în acele zile camera rămâne pe antiîngheț.",
    al_battery_low: "Baterie descărcată la {device} ({level}%).",
    al_weather_without_source: "Pornite, dar nu funcționează fără senzor de temperatură exterioară sau entitate meteo: {features}.",
    al_boiler_min_rooms: "Camere necesare pentru pornirea sursei de căldură: {needed}, dar casa are {rooms} camere: sursa de căldură pornește doar pentru antiîngheț.",
    al_outdoor_unavailable: "Nicio temperatură de afară de la {entities} de peste {minutes} min: oprirea când e cald, sezonul automat, compensarea și oprirea anticipată nu o pot folosi.",
    wf_cutoff: "oprirea când e cald",
    wf_season_auto: "sezonul automat",
    wf_compensation: "compensarea exterioară",
    wf_window_ignore: "ignorarea ferestrelor peste",
    wf_forecast: "prognoza (cere o entitate meteo și oprirea când e cald)",
    open_entity: "Deschide entitatea",
    r_pause: "Pauză: se trimit doar comenzile de siguranță",
    r_valve_exercise: "Mișcarea robinetelor: robinetele complet deschise câteva minute",
    r_mode_off: "Mod oprit: doar antiîngheț",
    r_summer: "Mod vară: încălzire oprită",
    r_out_of_season: "În afara sezonului de încălzire: încălzire oprită",
    r_window_off: "Fereastră deschisă: încălzire oprită",
    r_window_frost: "Fereastră deschisă: antiîngheț",
    r_override: "Modificarea manuală e respectată",
    r_vacation: "Vacanță",
    r_far: "Toți sunt departe (în afara zonelor apropiate)",
    r_nearby: "Nimeni acasă, cineva în apropiere",
    r_nearby_temperature: "Nimeni acasă, cineva în apropiere: {temperature}",
    r_nearby_schedule: "Nimeni acasă, cineva în apropiere: programul ({preset}) e mai jos",
    r_no_schedule: "Niciun program disponibil",
    r_no_profile: "Niciun profil activ pentru ziua de azi: antiîngheț",
    r_sensor_fallback: "Senzorii de temperatură indisponibili: eco până revin",
    r_sensor_fallback_schedule: "Senzorii de temperatură indisponibili: programul ({preset}), mai jos decât eco",
    r_unoccupied: "Cameră neocupată (program: {preset})",
    r_schedule: "Program: {preset}",
    r_optimal_start: "Pornire anticipată: încălzește mai devreme pentru {preset}",
    r_optimal_stop: "Oprire anticipată: coboară mai devreme la {preset}",
    r_cutoff: "Cald afară: încălzire oprită (ar fi {would})",
    r_max_level: "Temperatura maximă ({preset} e peste {max})",
    r_frost_level: "Antiîngheț ({preset} e sub {frost})",
    r_max_device: "Temperatura maximă: {value} e peste {max}",
    r_max_room: "Temperatura maximă: camera are {current}, la {max} sau peste",
    r_frost_below: "Antiîngheț: {current} e sub {frost}",
    r_frost_holding: "Antiîngheț: încălzește până la {frost}",
    rs_arriving: "cineva e pe drum spre casă",
    rs_vacation_preheat: "vacanța se termină curând: preîncălzire",
    rs_limited: "limitat la {limited}",
    rs_stop_cancelled: "oprire anticipată anulată: camera s-a răcit mai repede decât se aștepta",
    off_compensation: "compensare exterioară",
    off_tariff_high: "tarif ridicat",
    off_tariff_low: "tarif redus",
    off_pv_surplus: "surplus solar",
    off_solar_gain: "câștig solar",
    guests_banner: "Mod oaspeți: casa e considerată Acasă chiar dacă nu e acasă nimeni dintre persoane",
    auto_short: "Automat",
    device_temp: "Dispozitiv {temp}",
    trv_boost_chip: "Forțare TRV · {temp}",
    trv_boost_chip_off: "Forțare TRV {temp} cât încălzește",
  },
};

const esc = (value) =>
  String(value ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]
  );

const toMinutes = (hhmm) => {
  const [h, m] = String(hhmm).split(":").map((x) => parseInt(x, 10));
  return (h || 0) * 60 + (m || 0);
};

const hhmm = (minutes) =>
  `${String(Math.floor(minutes / 60)).padStart(2, "0")}:${String(minutes % 60).padStart(2, "0")}`;

const num = (value) => {
  const n = parseFloat(value);
  return Number.isFinite(n) ? n : null;
};

/** ISO datetime -> value for <input type="datetime-local"> in local time. */
const toLocalInput = (iso) => {
  if (!iso || iso === "unknown" || iso === "unavailable") return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(
    d.getHours()
  )}:${pad(d.getMinutes())}`;
};

/** <input type="datetime-local"> value -> "YYYY-MM-DD HH:MM:SS" in local time. */
const fromLocalInput = (value) => (value ? `${value.replace("T", " ")}:00` : null);

class SmartHeatingControlCard extends HTMLElement {
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

  /** Visual editor of the card (Home Assistant form). */
  static getConfigForm() {
    const lang = (document.querySelector("home-assistant")?.hass?.locale?.language || navigator.language || "en").slice(0, 2);
    const labels = EDITOR_LABELS[lang] || EDITOR_LABELS.en;
    return {
      schema: EDITOR_SCHEMA,
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
    this.style.colorScheme = hass?.themes?.darkMode ? "dark" : "light";
    if (this._editing || this._pan) return;
    const active = this.shadowRoot.activeElement;
    if (active && ["INPUT", "SELECT"].includes(active.tagName)) return;
    const key = this._watched()
      .map((id) => {
        const s = hass.states[id];
        return s ? `${id}:${s.state}:${s.last_updated}` : id;
      })
      .join("|");
    if (key !== this._lastKey) {
      this._lastKey = key;
      this._render();
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

  // ------------------------------------------------------------------ data
  _t(key) {
    const lang = (this._hass?.locale?.language || this._hass?.language || "en").slice(0, 2);
    return (TEXT[lang] || TEXT.en)[key] ?? TEXT.en[key] ?? key;
  }

  /** Language of the user, for dates and times. */
  _lang() {
    return this._hass?.locale?.language || "en";
  }

  /**
   * Entity ids of the rooms (Decision sensors) and houses (Presence sensors).
   * Looking through every entity of Home Assistant is done at most every 30 s,
   * not on every state change.
   */
  _discover() {
    const states = this._hass.states;
    const cache = this._found;
    const fresh =
      cache &&
      Date.now() - cache.at < 30000 &&
      [...cache.rooms, ...cache.houses].every((id) => states[id]);
    if (fresh) return cache;
    const rooms = [];
    const houses = [];
    for (const [id, s] of Object.entries(states)) {
      const a = s.attributes;
      if (!a || !a.entry_id) continue;
      if (a.room_id && a.schedule) rooms.push(id);
      else if (a.advanced_climate_house) houses.push(id);
    }
    this._found = { at: Date.now(), rooms, houses };
    return this._found;
  }

  /** Decision sensors of the rooms shown, sorted by name. */
  _rooms() {
    if (!this._hass) return [];
    const wanted = this._config?.rooms;
    if (Array.isArray(wanted) && wanted.length) {
      return wanted.map((id) => this._hass.states[id]).filter(Boolean);
    }
    return this._discover()
      .rooms.map((id) => this._hass.states[id])
      .filter(Boolean)
      .sort((a, b) => String(a.attributes.room_name).localeCompare(String(b.attributes.room_name)));
  }

  /** Houses with their entities and rooms (computed once per update). */
  _houses() {
    if (this._housesMemo) return this._housesMemo;
    const houses = new Map();
    const filtered = Array.isArray(this._config?.rooms) && this._config.rooms.length;
    for (const id of this._discover().houses) {
      const s = this._hass.states[id];
      const a = s?.attributes || {};
      if (!a.advanced_climate_house || !a.entry_id) continue;
      houses.set(a.entry_id, {
        id: a.entry_id,
        name: a.house_name,
        entities: a.house_entities || {},
        rooms: [],
        standalone: true,
      });
    }
    for (const room of this._rooms()) {
      const a = room.attributes;
      if (!houses.has(a.entry_id)) {
        houses.set(a.entry_id, {
          id: a.entry_id,
          name: a.house_name,
          entities: a.house_entities || {},
          rooms: [],
        });
      }
      const house = houses.get(a.entry_id);
      house.standalone = false;
      house.rooms.push(room);
    }
    // With an explicit room list, only the houses of those rooms are shown.
    this._housesMemo = [...houses.values()].filter((h) => !filtered || h.rooms.length);
    return this._housesMemo;
  }

  /** Entities whose change redraws the card. */
  _watched() {
    const ids = [];
    for (const house of this._houses()) {
      ids.push(...Object.values(house.entities));
      for (const room of house.rooms) {
        ids.push(room.entity_id, ...Object.values(room.attributes.entities || {}));
        ids.push(...(room.attributes.climate_entities || []));
      }
    }
    return ids;
  }

  /** State object of an entity, if any. */
  _state(id) {
    return id ? this._hass.states[id] : undefined;
  }

  /** State or option as Home Assistant shows it (translated). */
  _label(stateObj, value) {
    if (!stateObj) return value ?? "";
    if (this._hass.formatEntityState) {
      try {
        return this._hass.formatEntityState(stateObj, value);
      } catch (e) {
        /* older frontends */
      }
    }
    return value ?? stateObj.state;
  }

  /** Name of a level for the user (custom names included). */
  _presetName(attrs, preset) {
    const name = preset === "frost" ? this._t("frost_level") : (attrs.preset_names && attrs.preset_names[preset]) || preset;
    // Shown as a name: the first letter capital (Home, Eco, Antiîngheț).
    const text = String(name ?? "");
    return text ? text.charAt(0).toLocaleUpperCase(this._lang()) + text.slice(1) : text;
  }

  /** Time of a moment; with the weekday when it is not today. */
  _fmtTime(iso) {
    if (!iso) return "–";
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return "–";
    const sameDay = new Date().toDateString() === d.toDateString();
    const opts = sameDay
      ? { hour: "2-digit", minute: "2-digit" }
      : { weekday: "short", hour: "2-digit", minute: "2-digit" };
    return d.toLocaleString(this._lang(), opts);
  }

  /** Temperature with one decimal, or a dash. */
  _temp(value) {
    const n = num(value);
    return n === null ? "–" : `${n.toFixed(1)}°`;
  }

  // ------------------------------------------------------------------ render
  _render() {
    if (!this._config) return;
    const cfg = this._config;
    const houses = this._hass ? this._houses() : [];
    const title = cfg.title ?? this._t("title");
    let body = "";
    if (!houses.length) {
      body = `<p class="empty">${this._t("no_rooms")}</p>`;
    } else {
      body = houses
        .map(
          (house) =>
            this._pauseBanner(house) +
            this._guestBanner(house) +
            (cfg.show_house ? this._houseHtml(house) : "") +
            (cfg.show_rooms
              ? house.rooms.length
                ? cfg.compact
                  ? `<div class="rooms-list">${house.rooms.map((r) => this._roomHtml(r)).join("")}</div>`
                  : house.rooms.map((r) => this._roomHtml(r)).join("")
                : `<p class="empty">${this._t("no_rooms")}</p>`
              : "")
        )
        .join("");
    }
    this.shadowRoot.innerHTML = `<style>${STYLE}</style>
      <ha-card class="${cfg.compact ? "compact" : ""}">
        ${title ? `<h2 class="title">${esc(title)}</h2>` : ""}
        ${body}
      </ha-card>`;
  }

  /** Material Design icon. */
  _icon(name) {
    return name ? `<ha-icon icon="mdi:${name}"></ha-icon>` : "";
  }

  /** Button with an optional icon. */
  _btn(label, attrs, { icon = "", kind = "" } = {}) {
    return `<button class="btn ${kind}" ${attrs}>${this._icon(icon)}<span>${esc(label)}</span></button>`;
  }

  /** On / off switch for an entity. */
  _toggle(entityId, label) {
    const s = this._state(entityId);
    if (!s) return "";
    const on = s.state === "on";
    return `<button class="toggle ${on ? "on" : ""}" role="switch" aria-checked="${on}"
      data-action="toggle" data-entity="${esc(entityId)}"><span class="knob"></span><span>${esc(
      label
    )}</span></button>`;
  }

  /** Label of the outdoor temperature: it is the average of the last hours. */
  _outdoorLabel(outdoor) {
    const h = num(outdoor?.attributes?.average_hours);
    return h === null ? this._t("outdoor") : this._t("outdoor_hours").replace("{h}", String(h));
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
    const m = Math.round(a.time_to_target);
    if (m < 60) return `~${m} min`;
    const h = Math.floor(m / 60);
    const r = Math.round((m % 60) / 5) * 5;
    return r ? `~${h} h ${r} min` : `~${h} h`;
  }

  /** "default 60 min/1°C": the heating used until the first episode (empty once learned). */
  _heatDefault(e) {
    const s = e && e.heating_rate ? this._state(e.heating_rate) : null;
    if (s && (num(s.attributes.episodes) ?? 0) > 0) return "";
    const unit = ((s && s.attributes.unit_of_measurement) || "min/°C").replace(/^min\//, "");
    const value = s ? num(s.state) : null;
    return this._t("heat_default").replace("{value}", `${Math.round(value ?? 60)} min/1${unit}`);
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

  /**
   * Arc of the room temperature: full at the maximum temperature, empty at the
   * frost protection (the limits of the targets). Tapping it opens the sensor.
   */
  _gauge(a, e, size, withTarget = true) {
    const cur = num(a.current_temperature);
    const tgt = num(a.target_temperature);
    let lo = num(a.min_temperature) ?? 5;
    let hi = num(a.max_temperature) ?? 30;
    if (!(hi > lo)) {
      lo = 5;
      hi = 30;
    }
    const f = cur === null ? 0 : Math.min(1, Math.max(0, (cur - lo) / (hi - lo)));
    const sw = size >= 120 ? 11 : size >= 80 ? 8 : 5;
    const r = size / 2 - sw / 2 - 1;
    const c = 2 * Math.PI * r;
    const arc = c * 0.75;
    const mid = size / 2;
    const ring = (cls, len) =>
      `<circle cx="${mid}" cy="${mid}" r="${r.toFixed(2)}" class="${cls}" stroke-width="${sw}" stroke-dasharray="${len.toFixed(
        1
      )} ${c.toFixed(1)}" transform="rotate(135 ${mid} ${mid})"></circle>`;
    const label = `${this._t("room_temp")} ${this._temp(cur)}, ${this._t("target_tag")} ${this._temp(tgt)}`;
    const link = e && e.room_temperature ? this._more(e.room_temperature) : "";
    return `<span class="gauge ${link ? "link" : ""}" style="width:${size}px;height:${size}px;--gs:${size}px" ${link}
        role="img" aria-label="${esc(label)}">
        <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" aria-hidden="true">
          ${ring("gtrack", arc)}${cur !== null ? ring("gvalue", Math.max(0.1, arc * f)) : ""}
        </svg>
        <span class="gcenter"><span class="gnum">${this._temp(cur)}</span>${
          withTarget
            ? `<span class="gsub ${e && e.target_temperature ? "link" : ""}" ${
                e && e.target_temperature ? this._more(e.target_temperature) : ""
              }>${esc(this._t("target_tag"))} ${this._temp(tgt)}</span>`
            : ""
        }</span>
      </span>`;
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

  /** Lines next to the arc: the reason, the time to target, the TRV boost, the device reading. */
  _chipsHtml(a, e, stateObj, eta) {
    const chips = [
      `<span class="chip">${this._icon(this._ruleIcon(stateObj.state))}<span>${esc(this._reasonText(a))}</span></span>`,
    ];
    if (eta) {
      const sub = eta === this._t("eta_learning") ? this._heatDefault(e) : "";
      chips.push(
        `<span class="chip" title="${esc(this._t(a.stop_forecast ? "stop_help" : "eta_help"))}">${this._icon(
          a.stop_forecast ? "thermometer-chevron-down" : "clock-outline"
        )}<span>${esc(eta)}${sub ? ` <small>${esc(sub)}</small>` : ""}</span></span>`
      );
    }
    if (!this._config.show_timeline && a.next_change) {
      chips.push(
        `<span class="chip">${this._icon("calendar-arrow-right")}<span>${this._t("next")}: ${esc(
          this._fmtTime(a.next_change)
        )} → ${esc(this._presetName(a, a.next_preset))}</span></span>`
      );
    }
    if (a.trv_boost) {
      chips.push(
        `<span class="chip soft ${a.trv_boost.active ? "on" : ""}">${this._icon("lightning-bolt-outline")}<span>${esc(
          this._t(a.trv_boost.active ? "trv_boost_chip" : "trv_boost_chip_off").replace("{temp}", this._temp(a.trv_boost.temperature))
        )}</span></span>`
      );
    }
    // What the device itself measures (a Generic Thermostat reads the room sensor).
    if (a.source !== "generic_thermostat") {
      const dev = (a.climate_entities || [])
        .map((id) => this._state(id))
        .find((s) => s && num(s.attributes.current_temperature) !== null);
      if (dev) {
        chips.push(
          `<span class="chip soft neutral link" ${this._more(dev.entity_id)}>${this._icon("thermostat")}<span>${esc(
            this._t("device_temp").replace("{temp}", this._temp(dev.attributes.current_temperature))
          )}</span></span>`
        );
      }
    }
    return chips.join("");
  }

  /** Today's profile as a bar from 00 to 24, with the time now. */
  _todayHtml(a) {
    const slots = a.profile && a.schedule ? a.schedule[a.profile] : null;
    if (!slots || !slots.length) return "";
    const segs = this._segments(slots)
      .map(
        (sg) =>
          `<i style="left:${(sg.start / 1440) * 100}%;width:${((sg.end - sg.start) / 1440) * 100}%;--c:${
            PRESET_COLORS[sg.preset] || TEMP_COLOR
          }" title="${esc(`${this._presetName(a, sg.preset)} ${hhmm(sg.start)}–${hhmm(sg.end % 1440)}`)}"></i>`
      )
      .join("");
    const d = new Date();
    const now = ((d.getHours() * 60 + d.getMinutes()) / 1440) * 100;
    return `<div class="today">
        <span class="tlabel">${esc(this._t("today"))} · ${esc(a.profile)}</span>
        <div class="tbar">${segs}<b style="left:${now}%"></b></div>
        <div class="tticks"><span>00</span><span>06</span><span>12</span><span>18</span><span>24</span></div>
      </div>`;
  }

  /** Buttons that open the room sections (independently), then the open sections in a fixed order. */
  _sectionsHtml(a, e, stateObj) {
    const cfg = this._config;
    const id = a.room_id;
    const defs = [];
    if (cfg.show_quick_override) defs.push([`quick-${id}`, "quick", "timer-edit-outline", () => this._quickHtml(a, e)]);
    if (cfg.show_schedule_editor) defs.push([`sched-${id}`, "schedule", "calendar-edit", () => this._scheduleHtml(a, stateObj)]);
    if (cfg.show_levels && Object.keys(e).some((k) => k.startsWith("level_"))) {
      defs.push([`levels-${id}`, "levels", "tune-variant", () => this._levelsHtml(a, e)]);
    }
    if (cfg.show_details) defs.push([`details-${id}`, "details", "information-outline", () => this._detailsHtml(a, e)]);
    if (!defs.length) return "";
    const open = (k) => !!this._open[k] || (k === `sched-${id}` && this._editing === id);
    const buttons = defs
      .map(
        ([k, label, icon]) => `<button class="sbtn ${open(k) ? "on" : ""}" data-action="fold" data-key="${esc(k)}"
          aria-expanded="${open(k)}">${this._icon(icon)}<span>${esc(this._t(label))}</span></button>`
      )
      .join("");
    const bodies = defs
      .filter(([k]) => open(k))
      .map(([, , , html]) => html())
      .join("");
    return `<div class="sbtns" style="--n:${defs.length}">${buttons}</div>${bodies}`;
  }

  /** House block: presence, outdoor, mode, pause, guests, vacation and buttons. */
  _houseHtml(house) {
    const e = house.entities;
    const presence = this._state(e.presence);
    const mode = this._state(e.mode);
    const outdoor = this._state(e.outdoor_average);
    const season = this._state(e.heating_season);
    const cutoff = this._state(e.outdoor_cutoff);
    const demand = this._state(e.heat_demand);
    const runtime = this._state(e.heating_runtime);
    const guest = this._state(e.guest_mode);
    const pause = this._state(e.pause);
    const vStart = this._state(e.vacation_start);
    const vEnd = this._state(e.vacation_end);

    const persons = Object.entries(presence?.attributes?.persons || {}).map(([id, cls]) => {
      const p = this._hass.states[id];
      return { id, cls: cls || "unknown", name: p?.attributes?.friendly_name || id.split(".")[1], picture: p?.attributes?.entity_picture };
    });
    // A ring in the colour of where the person is (home, nearby, far); the photo when there is one.
    const avatarList = (links) =>
      persons
        .map((p) => {
          const title = `${p.name}: ${this._label(presence, p.cls)}`;
          return `<span class="avatar ${esc(p.cls)} ${links ? "link" : ""}" ${links ? this._more(p.id, title) : `title="${esc(title)}"`}>${
            p.picture ? `<img src="${esc(p.picture)}" alt="">` : esc((String(p.name).trim()[0] || "?").toUpperCase())
          }</span>`;
        })
        .join("");
    const avatars = avatarList(true);
    const who = persons.map((p) => `${p.name} ${String(this._label(presence, p.cls)).toLowerCase()}`).join(" · ");

    const modes = (mode?.attributes?.options || ["auto", "vacation", "off", "summer"])
      .map(
        (opt) => `<button class="seg ${mode?.state === opt ? "active" : ""}" data-action="mode"
          data-entity="${esc(e.mode)}" data-option="${esc(opt)}">${esc(this._label(mode, opt))}</button>`
      )
      .join("");

    const stat = (icon, label, value, extra = "", entityId = null) =>
      `<div class="stat ${extra} ${entityId ? "link" : ""}" ${this._more(entityId)}><span class="k">${this._icon(icon)}<span>${esc(
        label
      )}</span></span><span class="v">${esc(value)}</span></div>`;
    const onOff = (s) => (s ? (s.state === "on" ? this._t("on") : this._t("off")) : "–");
    const guestOn = guest?.state === "on";
    const isDate = (s) => s && !Number.isNaN(Date.parse(s.state));
    const vacationSet = isDate(vStart) || isDate(vEnd);
    const vacationSummary = vacationSet
      ? `${isDate(vStart) ? esc(this._fmtTime(vStart.state)) : this._t("now_tag")} – ${
          isDate(vEnd) ? esc(this._fmtTime(vEnd.state)) : "…"
        }`
      : this._t("vacation_none");

    const houseKey = `house-${house.id}`;
    if (this._config.compact && !this._open[houseKey]) {
      return `<button class="crow house-row" data-action="fold" data-key="${esc(houseKey)}" aria-expanded="false">
          ${persons.length ? `<span class="avatars sm" aria-hidden="true">${avatarList(false)}</span>` : this._icon("home-thermometer-outline")}
          <span class="cname">${esc(house.name || "")}</span>
          <span class="pill">${esc(this._label(mode))}</span>
          ${demand?.state === "on" ? `<span class="cicon hot" title="${esc(this._t("heating"))}">${this._icon("fire")}</span>` : ""}
          <span class="ctemp muted">${this._icon("weather-partly-cloudy")} ${esc(this._temp(outdoor?.state))}</span>
          <span class="chev"></span>
        </button>`;
    }
    const foldBack = this._config.compact
      ? `<button class="room-title" data-action="fold" data-key="${esc(houseKey)}" aria-expanded="true" aria-label="${esc(
          house.name || ""
        )}"><span class="chev open"></span></button>`
      : "";
    const presenceIcon =
      { home: "home-outline", nearby: "map-marker-radius-outline", far: "map-marker-distance" }[presence?.state] ||
      "home-search-outline";

    // Action buttons: an icon and a short name; Guests and Vacation open their own panel.
    const vacKey = `vac-${house.id}`;
    const abtn = (icon, label, attrs, cls = "", title = "") =>
      `<button class="abtn ${cls}" ${attrs} ${title ? `title="${esc(title)}" aria-label="${esc(title)}"` : ""}>${this._icon(
        icon
      )}<span>${esc(label)}</span></button>`;
    const fold = (key) => `data-action="fold" data-key="${esc(key)}" aria-expanded="${!!this._open[key]}"`;
    const actions = [
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

    const vacPanel = this._open[vacKey]
      ? `<div class="panel blue">
          <div class="panel-head"><b>${esc(this._t("vacation"))}</b><span class="muted">${vacationSummary}</span></div>
          <div class="dates">
            <label class="datefield"><span>${this._t("from")}</span>
              <input type="datetime-local" data-vac="start" data-house="${esc(house.id)}"
                value="${esc(toLocalInput(vStart?.state))}"></label>
            <label class="datefield"><span>${this._t("to")}</span>
              <input type="datetime-local" data-vac="end" data-house="${esc(house.id)}"
                value="${esc(toLocalInput(vEnd?.state))}"></label>
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
        </div>`
      : "";

    return `
      <section class="block house">
        <div class="house-head">
          <div class="who">
            ${foldBack}
            ${avatars ? `<div class="avatars">${avatars}</div>` : ""}
            <div class="whotext">
              ${this._houses().length > 1 && house.name ? `<span class="hname">${esc(house.name)}</span>` : ""}
              <span class="pstate">
                <span class="presence-state link ${esc(presence?.state)}" ${this._more(e.presence)}>${this._icon(presenceIcon)}${esc(
                  this._label(presence)
                )}</span>
                ${presence?.attributes?.arriving ? `<span class="pill">${this._t("arriving")}</span>` : ""}
                ${demand?.state === "on" ? `<span class="tstat hot pulse link" ${this._more(e.heat_demand, this._t("demand"))}>${this._icon("fire")}</span>` : ""}
              </span>
              ${who ? `<span class="muted">${esc(who)}</span>` : ""}
            </div>
          </div>
          <div class="segmented" role="group" aria-label="${esc(this._t("mode"))}">${modes}</div>
        </div>
        <div class="stats">
          ${stat("weather-partly-cloudy", this._outdoorLabel(outdoor), this._temp(outdoor?.state), "", e.outdoor_average)}
          ${stat("calendar-range", this._t("season"), onOff(season), "", e.heating_season)}
          ${stat("fire", this._t("demand"), onOff(demand), demand?.state === "on" ? "hot" : "", e.heat_demand)}
          ${runtime ? this._runtimeStat(e.heating_runtime) : ""}
        </div>
        ${this._cutoffHtml(outdoor, cutoff, e.outdoor_cutoff, mode, season, pause)}
        <div class="hactions" style="--n:${actions.length}">${actions.join("")}</div>
        ${vacPanel}
      </section>`;
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
    return `<div class="cutoffline ${reason === "forecast_cold" ? "" : "on"} link" ${this._more(entityId)}>
        <b>${esc(this._t("cutoff"))}:</b> ${esc(text)}</div>`;
  }

  /** Banner while guest mode is on (the Guests button turns it off), with its end when it has one. */
  _guestBanner(house) {
    const guest = this._state(house.entities?.guest_mode);
    if (guest?.state !== "on") return "";
    const name = this._houses().length > 1 && house.name ? `${house.name}: ` : "";
    const until = guest.attributes?.until ? ` (${this._t("until")} ${this._fmtTime(guest.attributes.until)})` : "";
    return `<div class="banner teal link" ${this._more(house.entities.guest_mode)}>${this._icon("account-group-outline")}<span>${esc(
      name + this._t("guests_banner") + until
    )}</span></div>`;
  }

  /** Banner while the house is paused (the switch stays the only control). */
  _pauseBanner(house) {
    const pause = this._state(house.entities?.pause);
    if (pause?.state !== "on") return "";
    const name = this._houses().length > 1 && house.name ? `${house.name}: ` : "";
    return `<div class="banner">${this._icon("pause-circle-outline")}<span>${esc(name + this._t("paused_banner"))}</span></div>`;
  }

  /** Room block (or one compact tile / folded row); the sections are shown when it is open. */
  _roomHtml(stateObj) {
    const cfg = this._config;
    const a = stateObj.attributes;
    const e = a.entities || {};
    const key = a.room_id;
    const folded =
      this._open[`room-${key}`] === undefined ? cfg.collapsed || cfg.compact : !this._open[`room-${key}`];
    const color = PRESET_COLORS[a.preset] || "var(--secondary-text-color)";
    if (cfg.compact && folded) return this._compactRow(stateObj, color);
    if (folded) return this._foldedRow(stateObj, color);

    const badges = [];
    if (a.heating ?? a.heat_demand)
      badges.push(`<span class="pill hot pulse link" ${this._more(e.heat_demand)}>${this._icon("fire")}${this._t("heating")}</span>`);
    if (a.window_open)
      badges.push(`<span class="pill warn link" ${this._more(e.window_open)}>${this._icon("window-open-variant")}${this._t("window")}</span>`);
    if (a.override) {
      const until = this._overrideUntil(a);
      const prefix = stateObj.state === "manual_override" ? "" : `${this._t("override")} `;
      const origin = a.override.origin ? ` · ${this._t(`origin_${a.override.origin}`)}` : "";
      // While a higher rule wins: not sent yet, or set again once it ends.
      // (The maximum temperature limits the manual value for good.)
      const blocked = !["manual_override", "maximum_temperature"].includes(stateObj.state);
      const back = !blocked
        ? ""
        : a.override.applied === false
          ? ` · ${this._t("applied_after").replace("{rule}", this._label(stateObj))}`
          : a.override.interrupted
            ? ` · ${this._t("back_after").replace("{rule}", this._label(stateObj))}`
            : "";
      badges.push(`<span class="pill link wrap" ${this._more(
        e.manual_override,
        a.override.until ? null : this._t("reeval_help")
      )}>${this._icon("hand-back-right-outline")}${esc(prefix + until + origin + back)}</span>`);
    }

    const head = `
      <div class="room-head">
        <div class="rh-left">
          <button class="room-title" data-action="fold" data-key="room-${esc(key)}" aria-expanded="true">
            <span class="chev open"></span><span class="name">${esc(a.room_name)}</span>
          </button>
          <span class="pill rule link" ${this._more(e.decision)}><span class="dot"></span>${esc(this._label(stateObj))}</span>
        </div>
        ${badges.length ? `<div class="decision">${badges.join("")}</div>` : ""}
      </div>`;
    const hero = `<div class="hero">${this._gauge(a, e, 140)}<div class="chips">${this._presetPill(a)}${this._chipsHtml(
      a,
      e,
      stateObj,
      this._eta(a)
    )}</div></div>`;

    const parts = [
      head,
      hero,
      this._noHeatHtml(a),
      this._todayHtml(a),
      cfg.show_timeline ? this._timelineHtml(a) : "",
      this._controlsHtml(a, e),
      this._sectionsHtml(a, e, stateObj),
    ];
    return `<section class="block room open" style="--c:${color}">${parts.join("")}</section>`;
  }

  /** The level the room is at (its colour and name); a temperature without a level shows only the value. */
  _presetPill(a, withTarget = false) {
    const target = withTarget ? ` ${this._temp(a.target_temperature)}` : "";
    if (!a.preset) return withTarget ? `<span class="pill preset">${this._temp(a.target_temperature)}</span>` : "";
    return `<span class="pill preset"><span class="dot"></span>${esc(this._presetName(a, a.preset))}${target}</span>`;
  }

  /** Small icons of a folded room: heating, window open, manual change. */
  _statusIcons(a) {
    const icons = [];
    if (a.heating ?? a.heat_demand) icons.push(`<span class="cicon hot" title="${esc(this._t("heating"))}">${this._icon("fire")}</span>`);
    if (a.window_open) icons.push(`<span class="cicon warn" title="${esc(this._t("window"))}">${this._icon("window-open-variant")}</span>`);
    if (a.override) icons.push(`<span class="cicon" title="${esc(`${this._t("override")} ${this._overrideUntil(a)}`)}">${this._icon("hand-back-right-outline")}</span>`);
    if (this._guestOn(a)) icons.push(`<span class="cicon teal" title="${esc(this._t("guests_banner"))}">${this._icon("account-group-outline")}</span>`);
    return icons.join("");
  }

  /** True while the guest mode of the room's house is on. */
  _guestOn(a) {
    return this._state(a.house_entities?.guest_mode)?.state === "on";
  }

  /** A folded room: small arc, name, reason, target; a tap opens it. */
  _foldedRow(stateObj, color) {
    const a = stateObj.attributes;
    const eta = this._eta(a);
    return `<section class="block room folded" style="--c:${color}">
        <button class="frow" data-action="fold" data-key="room-${esc(a.room_id)}" aria-expanded="false">
          ${this._gauge(a, null, 54, false)}
          <span class="ftext"><span class="fname"><span class="name">${esc(a.room_name)}</span></span>
            ${eta ? `<span class="freason">${esc(eta)}</span>` : ""}</span>
          ${this._statusIcons(a)}
          ${this._presetPill(a, true)}
          <span class="chev"></span>
        </button>
      </section>`;
  }

  /** One tile per room in the compact card: arc, level, target; a tap opens the room. */
  _compactRow(stateObj, color) {
    const a = stateObj.attributes;
    const heating = a.heating ?? a.heat_demand;
    // Every state that applies, as small round icons (heating pulses).
    const status = [
      heating ? `<span class="tstat hot pulse" title="${esc(this._t("heating"))}">${this._icon("fire")}</span>` : "",
      a.window_open ? `<span class="tstat warn" title="${esc(this._t("window"))}">${this._icon("window-open-variant")}</span>` : "",
      a.override ? `<span class="tstat" title="${esc(this._t("override"))}">${this._icon("hand-back-right-outline")}</span>` : "",
      this._guestOn(a) ? `<span class="tstat teal" title="${esc(this._t("guests_banner"))}">${this._icon("account-group-outline")}</span>` : "",
    ].join("");
    const eta = this._eta(a);
    const line = a.override
      ? `${this._t("override")} ${this._overrideUntil(a)}`
      : a.window_open
        ? this._t("window")
        : eta || (a.next_change ? `${this._presetName(a, a.next_preset)} · ${this._fmtTime(a.next_change)}` : "");
    return `<button class="tile" data-action="fold" data-key="room-${esc(a.room_id)}" aria-expanded="false" style="--c:${color}"
        aria-label="${esc(`${a.room_name}, ${this._temp(a.current_temperature)}, ${this._label(stateObj)}`)}">
        <span class="tile-head"><span class="tname"><span class="cname">${esc(a.room_name)}</span></span>${
          status ? `<span class="tstats">${status}</span>` : ""
        }</span>
        <span class="tile-body">${this._gauge(a, null, 64, false)}
          <span class="tile-info">${this._presetPill(a)}
            <span class="tsub">${esc(this._t("target_tag"))} ${this._temp(a.target_temperature)}</span>
            ${line ? `<span class="muted">${esc(line)}</span>` : ""}</span>
        </span>
      </button>`;
  }

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
    return text;
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
      .replace("{room}", r.room ?? "");
    return `<p class="reason noheat">${this._icon("information-outline")}<span><b>${esc(
      this._t("no_heat")
    )}:</b> ${esc(text)}</span></p>`;
  }

  /** When a manual change ends, in words. */
  _overrideUntil(a) {
    if (!a.override) return "";
    if (a.override.until) return `${this._t("until")} ${this._fmtTime(a.override.until)}`;
    const latest = a.next_change
      ? ` (${this._t("at_latest")} ${this._fmtTime(a.next_change)}${
          a.next_preset ? `, ${this._presetName(a, a.next_preset)}` : ""
        })`
      : "";
    return `${this._t("until_reeval")}${latest}`;
  }

  /** Segments of a profile over one day (the last slot continues past midnight). */
  _segments(slots) {
    const sorted = [...slots].sort((x, y) => toMinutes(x.time) - toMinutes(y.time));
    const segments = [];
    const last = sorted[sorted.length - 1];
    if (toMinutes(sorted[0].time) > 0) {
      segments.push({ start: 0, end: toMinutes(sorted[0].time), preset: last.preset });
    }
    sorted.forEach((slot, i) => {
      const end = i + 1 < sorted.length ? toMinutes(sorted[i + 1].time) : 1440;
      segments.push({ start: toMinutes(slot.time), end, preset: slot.preset });
    });
    return segments.filter((s) => s.end > s.start);
  }

  /** Intervals as people read them: from a slot to the next one; the last one ends at the first slot of the next day. */
  _intervals(slots) {
    const sorted = [...slots].sort((x, y) => toMinutes(x.time) - toMinutes(y.time));
    return sorted.map((slot, i) => {
      if (i + 1 < sorted.length) {
        return { from: slot.time, to: sorted[i + 1].time, preset: slot.preset, nextDay: false };
      }
      const first = sorted[0];
      if (sorted.length > 1 && toMinutes(first.time) === 0) {
        return { from: slot.time, to: "24:00", preset: slot.preset, nextDay: false };
      }
      return { from: slot.time, to: first.time, preset: slot.preset, nextDay: true };
    });
  }

  // ------------------------------------------------------------------ history chart
  /** Cached history of the room (fetched in the background, refreshed every 5 minutes). */
  _history(a) {
    const key = a.room_id;
    this._hist = this._hist || {};
    const cached = this._hist[key];
    if (!cached || (!cached.loading && Date.now() - cached.at > 5 * 60 * 1000)) {
      this._fetchHistory(a);
    }
    return cached && cached.temp ? cached : null;
  }

  /** Fetch the last 24 h of room temperature, target and heat demand. */
  async _fetchHistory(a) {
    const key = a.room_id;
    const e = a.entities || {};
    const outdoorId = a.house_entities?.outdoor_average;
    const ids = [e.room_temperature, e.target_temperature, e.heat_demand, outdoorId].filter(Boolean);
    const previous = this._hist[key];
    if (!ids.length || !this._hass?.callWS) {
      this._hist[key] = { at: Date.now(), loading: false, temp: [], target: [], heat: [], outdoor: [] };
      return;
    }
    this._hist[key] = { ...(previous || {}), at: Date.now(), loading: true };
    const end = new Date();
    const start = new Date(end.getTime() - 24 * 3600 * 1000);
    try {
      const res = await this._hass.callWS({
        type: "history/history_during_period",
        start_time: start.toISOString(),
        end_time: end.toISOString(),
        entity_ids: ids,
        minimal_response: false,
        no_attributes: false,
        significant_changes_only: false,
      });
      const rows = (id) =>
        ((id && res[id]) || [])
          .map((p) => ({ t: (p.lu ?? p.lc) * 1000, s: p.s, a: p.a || {} }))
          .filter((p) => Number.isFinite(p.t));
      this._hist[key] = {
        at: Date.now(),
        loading: false,
        temp: rows(e.room_temperature)
          .map((p) => [p.t, num(p.s)])
          .filter((p) => p[1] !== null),
        target: rows(e.target_temperature).map((p) => ({ t: p.t, v: num(p.s), preset: p.a.preset })),
        // Heated: the heat source ran (older history without the attribute: the demand).
        heat: rows(e.heat_demand).map((p) => [p.t, p.s === "on" && p.a.heating !== false]),
        // Measured outdoor temperature (the latest value of the house).
        outdoor: rows(outdoorId)
          .map((p) => [p.t, num(p.a.latest)])
          .filter((p) => p[1] !== null),
      };
    } catch (err) {
      this._hist[key] = { at: Date.now(), loading: false, temp: [], target: [], heat: [], outdoor: [], failed: true };
    }
    const active = this.shadowRoot.activeElement;
    if (this._editing || this._drag || (active && ["INPUT", "SELECT"].includes(active.tagName))) return;
    this._lastKey = "";
    this._render();
  }

  /** Everything drawn by the chart, in time order. */
  _chartData(a) {
    const HOUR = 3600 * 1000;
    const now = Date.now();
    const t0 = now - 24 * HOUR;
    const t1 = now + 12 * HOUR;
    const hist = this._history(a);
    // A day without an active profile keeps the frost protection.
    const levels = { ...(a.levels || {}), frost: a.min_temperature };

    // Target: history for the past, the plan for the future.
    const segs = [];
    if (hist && hist.target.length) {
      const points = hist.target.filter((p) => p.v !== null);
      points.forEach((p, i) => {
        const s = Math.max(t0, p.t);
        const e = i + 1 < points.length ? Math.min(points[i + 1].t, now) : now;
        if (e > s) segs.push({ s, e, v: p.v, preset: p.preset, future: false });
      });
    }
    const plan = (a.plan || [])
      .map((p) => ({ t: Date.parse(p.at), preset: p.preset }))
      .filter((p) => Number.isFinite(p.t))
      .sort((x, y) => x.t - y.t);
    let upcoming = plan.filter((p) => p.t > now && p.t < t1);
    let cursor = now;
    let preset = a.preset;
    let value = num(a.target_temperature);
    const rule = this._rooms().find((r) => r.attributes.room_id === a.room_id)?.state;
    // Hold a value until a known moment, then the schedule of that moment.
    const holdThen = (until) => {
      const end = Math.min(until, t1);
      if (value !== null) segs.push({ s: now, e: end, v: value, preset, future: true });
      cursor = end;
      const atEnd = plan.filter((p) => p.t <= until).at(-1);
      preset = atEnd ? atEnd.preset : a.preset;
      value = atEnd ? num(levels[preset]) : null;
      upcoming = plan.filter((p) => p.t > until && p.t < t1);
    };
    const ovUntil = a.override?.until ? Date.parse(a.override.until) : NaN;
    const hold = a.hold_until ? Date.parse(a.hold_until) : NaN;
    const holdKnown = Number.isFinite(hold) && hold > now;
    if (FLAT_RULES.includes(rule) && !(rule === "vacation" && holdKnown)) {
      // Lasts until something changes (mode, presence, pause, sensors, warm
      // outside): the schedule does not apply meanwhile.
      upcoming = [];
    } else if (a.override && Number.isFinite(ovUntil) && ovUntil > now) {
      // A manual change for a set time keeps its value until it ends (also while
      // a window or frost protection interrupts it), limited by the maximum.
      const held = num(a.override.temperature);
      if (held !== null) {
        const max = num(a.max_temperature);
        value = max !== null ? Math.min(held, max) : held;
        preset = a.override.preset ?? null;
      }
      holdThen(ovUntil);
    } else if (holdKnown) {
      // A planned vacation (until its preheating) or a calendar event (until its end).
      holdThen(hold);
    } else if (TEMPORARY_RULES.includes(rule) && plan.length && plan[0].t <= now + 60000) {
      // A window open, frost protection or the valve exercise last only a while:
      // ahead the plan shows the schedule (they are seen in the past and now).
      preset = plan[0].preset;
      value = num(levels[preset]);
    }
    for (const change of upcoming) {
      if (value !== null) segs.push({ s: cursor, e: change.t, v: value, preset, future: true });
      cursor = change.t;
      preset = change.preset;
      value = num(levels[preset]);
    }
    if (value !== null && cursor < t1) segs.push({ s: cursor, e: t1, v: value, preset, future: true });
    // Optimal start / stop: from its beginning the target is already the next
    // level (the shaded period of the chart, limited by the room settings).
    const est = a.next_estimate;
    if (est && (est.started_at || num(est.minutes))) {
      const b0 = Math.max(Date.parse(est.started_at || est.starts_at), now);
      const b1 = Date.parse(est.at);
      const bv = num(est.temperature) ?? num(levels[est.preset]);
      if (Number.isFinite(b0) && Number.isFinite(b1) && b1 > b0 && b0 < t1 && bv !== null) {
        // The planned parts in that period give way to the next level.
        const split = [];
        for (const sg of segs) {
          if (!sg.future || sg.e <= b0 || sg.s >= b1) {
            split.push(sg);
            continue;
          }
          if (sg.s < b0) split.push({ ...sg, e: b0 });
          if (sg.e > b1) split.push({ ...sg, s: b1 });
        }
        split.push({ s: b0, e: Math.min(b1, t1), v: bv, preset: est.preset, future: true, opt: est.kind });
        split.sort((p, q) => p.s - q.s);
        segs.length = 0;
        segs.push(...split);
      }
    }
    // Neighbours with the same level form one segment.
    const merged = [];
    for (const sg of segs) {
      const prev = merged[merged.length - 1];
      if (
        prev &&
        prev.v === sg.v &&
        prev.preset === sg.preset &&
        prev.future === sg.future &&
        prev.opt === sg.opt &&
        prev.e >= sg.s - 1000
      ) {
        prev.e = sg.e;
      } else {
        merged.push({ ...sg });
      }
    }
    segs.length = 0;
    segs.push(...merged);

    const temp = hist ? hist.temp.filter((p) => p[0] >= t0 - HOUR) : [];
    const current = num(a.current_temperature);
    if (current !== null) temp.push([now, current]);

    const heat = [];
    if (hist) {
      let on = null;
      for (const [t, state] of hist.heat) {
        if (state && on === null) on = Math.max(t, t0);
        if (!state && on !== null) {
          heat.push([on, t]);
          on = null;
        }
      }
      if (on !== null) heat.push([on, now]);
    } else if (a.heating ?? a.heat_demand) {
      heat.push([now - 5 * 60 * 1000, now]);
    }

    const values = [...segs.map((x) => x.v), ...temp.map((p) => p[1])].filter((v) => v !== null);
    let lo = values.length ? Math.floor(Math.min(...values) - 0.5) : 15;
    let hi = values.length ? Math.ceil(Math.max(...values) + 0.5) : 23;
    if (hi - lo < 4) {
      const mid = (hi + lo) / 2;
      lo = Math.floor(mid - 2);
      hi = lo + 4;
    }
    // Outdoor: measured for the past, the hourly forecast ahead.
    const outdoorState = this._state(a.house_entities?.outdoor_average);
    const outdoor = hist ? (hist.outdoor || []).filter((p) => p[0] >= t0 - HOUR) : [];
    const latest = num(outdoorState?.attributes?.latest);
    if (latest !== null) outdoor.push([now, latest]);
    const forecast = (outdoorState?.attributes?.forecast || [])
      .map(([at, v]) => [Date.parse(at), num(v)])
      .filter(([t, v]) => Number.isFinite(t) && v !== null && t < t1)
      .sort((p, q) => p[0] - q[0]);
    const outValues = [...outdoor.map((p) => p[1]), ...forecast.map((p) => p[1])];
    let olo = outValues.length ? Math.floor(Math.min(...outValues)) : null;
    let ohi = outValues.length ? Math.ceil(Math.max(...outValues)) : null;
    if (olo !== null && ohi - olo < 4) {
      const mid = (olo + ohi) / 2;
      olo = Math.floor(mid - 2);
      ohi = olo + 4;
    }
    const cutoffAt = outdoorState?.attributes?.cutoff_enabled ? num(outdoorState.attributes.cutoff_temperature) : null;
    return { t0, t1, now, segs, temp, heat, lo, hi, outdoor, forecast, olo, ohi, cutoffAt, loading: !hist };
  }

  /** Visible time window of a chart (zoom); the whole range when not zoomed. */
  _viewOf(room, d) {
    const v = this._view?.[room];
    if (!v) return { v0: d.t0, v1: d.t1, zoomed: false };
    const span = Math.min(d.t1 - d.t0, Math.max(MIN_ZOOM_SPAN, v.v1 - v.v0));
    const v0 = Math.min(d.t1 - span, Math.max(d.t0, v.v0));
    return { v0, v1: v0 + span, zoomed: span < d.t1 - d.t0 - 1000 };
  }

  /** Show the time window v0 … v1 (limited to the chart range); the whole range resets the zoom. */
  _setView(room, v0, v1) {
    const d = this._charts?.[room];
    if (!d) return;
    this._view = this._view || {};
    const span = Math.min(d.t1 - d.t0, Math.max(MIN_ZOOM_SPAN, v1 - v0));
    if (span >= d.t1 - d.t0 - 1000) {
      delete this._view[room];
    } else {
      const start = Math.min(d.t1 - span, Math.max(d.t0, v0));
      this._view[room] = { v0: start, v1: start + span };
    }
    this._redrawChart(room);
  }

  /** Zoom by ``factor`` (< 1 = closer) keeping ``center`` in place. */
  _zoom(room, factor, center) {
    const d = this._charts?.[room];
    if (!d) return;
    const { v0, v1 } = this._viewOf(room, d);
    const c = center ?? (Math.min(Math.max(d.now, v0), v1) === d.now ? d.now : (v0 + v1) / 2);
    this._setView(room, c - (c - v0) * factor, c + (v1 - c) * factor);
  }

  /** Redraw only the chart of a room (zoom and pan), not the whole card. */
  _redrawChart(room) {
    const card = this.shadowRoot.querySelector(`[data-chartcard="${CSS.escape(room)}"]`);
    const stateObj = this._rooms().find((s) => s.attributes.room_id === room);
    if (!card || !stateObj) return;
    card.innerHTML = this._timelineHtml(stateObj.attributes, true);
  }

  /** Chart of the room: past temperature, target and heating, the plan ahead, zoom bar. */
  _timelineHtml(a, innerOnly = false) {
    const d = this._chartData(a);
    if (!d.segs.length && !d.temp.length) return "";
    this._charts = this._charts || {};
    this._charts[a.room_id] = d;
    const view = this._viewOf(a.room_id, d);
    d.v0 = view.v0;
    d.v1 = view.v1;
    if (view.zoomed) {
      // Zoomed in: the temperature scale follows what is visible, for detail.
      const vis = [
        ...d.temp.filter(([t]) => t >= view.v0 - 3600000 && t <= view.v1 + 3600000).map((p) => p[1]),
        ...d.segs.filter((sg) => sg.e >= view.v0 && sg.s <= view.v1).map((sg) => sg.v),
      ].filter((v) => v !== null);
      if (vis.length) {
        let lo = Math.floor((Math.min(...vis) - 0.3) * 2) / 2;
        let hi = Math.ceil((Math.max(...vis) + 0.3) * 2) / 2;
        if (hi - lo < 1) hi = lo + 1;
        d.lo = lo;
        d.hi = hi;
      }
    }
    const W = 1000;
    const H = 100;
    const TOP = 6;
    // The plot ends above a band for the outdoor temperature (when known)
    // and a separate lane for the heating periods.
    const LANE = 7;
    const hasOut = d.olo !== null;
    const OBOT = H - LANE - 5;
    const OTOP = hasOut ? OBOT - 19 : OBOT;
    const BOTTOM = hasOut ? OTOP - 11 : H - LANE - 4;
    const x = (t) => ((t - view.v0) / (view.v1 - view.v0)) * W;
    const y = (v) => BOTTOM - ((v - d.lo) / (d.hi - d.lo)) * (BOTTOM - TOP);
    const pct = (t) => (x(t) / W) * 100;
    const gid = `g-${String(a.room_id).replace(/[^a-z0-9]/gi, "")}`;
    const nowX = x(d.now);

    const range = d.hi - d.lo;
    const gstep = range > 8 ? 2 : range > 3 ? 1 : 0.5;
    const gridValues = [];
    for (let v = Math.ceil(d.lo / gstep) * gstep; v <= d.hi + 1e-9; v += gstep) gridValues.push(+v.toFixed(1));
    const grid = gridValues
      .map((v) => `<line x1="0" x2="${W}" y1="${y(v)}" y2="${y(v)}" class="grid"></line>`)
      .join("");
    const heat = `<rect x="0" y="${H - LANE}" width="${W}" height="${LANE}" class="heatlane"></rect>${d.heat
      .map(
        ([s, e]) =>
          `<rect x="${x(s)}" y="${H - LANE}" width="${Math.max(2, x(e) - x(s))}" height="${LANE}" class="heatbar"></rect>`
      )
      .join("")}`;
    const segs = d.segs
      .map((sg) => {
        const c = PRESET_COLORS[sg.preset] || TEMP_COLOR;
        const x0 = x(sg.s);
        const x1 = x(sg.e);
        const yy = y(sg.v);
        return `<line x1="${x0}" x2="${x1}" y1="${yy}" y2="${yy}" stroke="${c}" class="tline ${sg.future ? "future" : ""}"></line>`;
      })
      .join("");
    const steps = d.segs
      .slice(1)
      .map((sg, i) => {
        const prev = d.segs[i];
        return `<line x1="${x(sg.s)}" x2="${x(sg.s)}" y1="${y(prev.v)}" y2="${y(sg.v)}" class="tstep"></line>`;
      })
      .join("");
    let tempPath = "";
    let tempArea = "";
    if (d.temp.length > 1) {
      const pts = d.temp.map(([t, v]) => `${x(Math.max(t, d.t0)).toFixed(1)} ${y(v).toFixed(1)}`);
      tempPath = `M${pts.join(" L")}`;
      tempArea = `${tempPath} L${x(d.temp[d.temp.length - 1][0]).toFixed(1)} ${BOTTOM} L${x(
        Math.max(d.temp[0][0], d.t0)
      ).toFixed(1)} ${BOTTOM} Z`;
    }
    const last = d.temp.length ? d.temp[d.temp.length - 1] : null;

    // Outdoor band: its own scale, measured line and the forecast (dashed steps).
    let outdoorSvg = "";
    let outLabels = "";
    if (hasOut) {
      const oy = (v) => OBOT - ((v - d.olo) / (d.ohi - d.olo)) * (OBOT - OTOP);
      const path = (pts) =>
        pts.length > 1 ? `M${pts.map(([t, v]) => `${x(Math.max(t, d.t0)).toFixed(1)} ${oy(v).toFixed(1)}`).join(" L")}` : "";
      const measured = path(d.outdoor);
      const steps = [];
      const start = d.outdoor.length ? d.outdoor[d.outdoor.length - 1] : null;
      if (start) steps.push(start);
      // The measured value stands until the next forecast hour (as for the optimal start / stop).
      for (const [t, v] of d.forecast.filter(([ft]) => ft > d.now)) {
        if (steps.length) steps.push([t, steps[steps.length - 1][1]]);
        steps.push([t, v]);
      }
      if (steps.length) steps.push([Math.min(d.t1, (d.forecast.at(-1)?.[0] ?? d.now) + 3600000), steps[steps.length - 1][1]]);
      const cutoff =
        d.cutoffAt !== null && d.cutoffAt >= d.olo && d.cutoffAt <= d.ohi
          ? `<line x1="0" x2="${W}" y1="${oy(d.cutoffAt)}" y2="${oy(d.cutoffAt)}" class="ocut"></line>`
          : "";
      outdoorSvg = `<rect x="0" y="${OTOP}" width="${W}" height="${OBOT - OTOP}" class="oband"></rect>${cutoff}
        ${measured ? `<path d="${measured}" class="oline"></path>` : ""}
        ${steps.length > 1 ? `<path d="${path(steps.filter(([t]) => t >= d.now - 1))}" class="oline future"></path>` : ""}`;
      outLabels = [d.olo, d.ohi]
        .map((v) => `<span class="olab" style="top:${(oy(v) / H) * 100}%">${v}°</span>`)
        .join("");
      d.oy = oy;
    }

    // The next optimal start / stop: from when it begins to the change.
    let optimal = "";
    let optimalLabel = "";
    const est = a.next_estimate;
    if (est && (est.started_at || num(est.minutes))) {
      const s0 = Date.parse(est.started_at || est.starts_at);
      const s1 = Date.parse(est.at);
      if (Number.isFinite(s0) && Number.isFinite(s1) && s1 > view.v0 && s0 < view.v1) {
        const c = PRESET_COLORS[est.preset] || TEMP_COLOR;
        const xa = Math.max(0, x(s0));
        const xb = Math.min(W, x(s1));
        optimal = `<rect x="${xa}" y="${TOP}" width="${Math.max(1, xb - xa)}" height="${BOTTOM - TOP}" fill="${c}" class="optband"></rect>
          <line x1="${x(s0)}" x2="${x(s0)}" y1="${TOP}" y2="${BOTTOM}" stroke="${c}" class="optline"></line>`;
        const text = this._t(est.kind === "optimal_start" ? "est_mark_start" : "est_mark_stop").replace(
          "{time}",
          this._fmtTime(est.started_at || est.starts_at)
        );
        if (x(s0) >= 0 && x(s0) <= W) {
          optimalLabel = `<span class="optlab ${x(s0) > W * 0.7 ? "end" : ""}" style="left:${(x(s0) / W) * 100}%;--c:${c}">${esc(
            text
          )}</span>`;
        }
      }
    }

    // Labels of the levels (HTML, so the text is not stretched).
    const visible = (sg) => [Math.max(0, x(sg.s)), Math.min(W, x(sg.e))];
    // A label for each level wide enough, not over another label.
    const placed = [];
    const labels = d.segs
      .filter((sg, i) => {
        // The rest of the same level after an optimal start / stop has no second label.
        const before = d.segs[i - 1];
        if (before && before.opt && before.v === sg.v && before.preset === sg.preset && before.e >= sg.s - 1000) return false;
        const [xs, xe] = visible(sg);
        const yy = y(sg.v);
        const wide = sg.preset ? 190 : 90;
        // Where the label starts: near the right edge it ends with the segment.
        const lx = xs > W * 0.7 ? xe - wide : xs;
        if (xe - xs < (sg.preset ? 110 : 60) || placed.some(([px, py, pw]) => Math.abs(lx - px) < Math.max(wide, pw) && Math.abs(yy - py) < 14)) {
          return false;
        }
        placed.push([lx, yy, wide]);
        return true;
      })
      .map((sg) => {
        const [xs, xe] = visible(sg);
        // Near the right edge the label ends with the segment, so it stays inside.
        const place =
          xs > W * 0.7 ? `right:${100 - (xe / W) * 100}%` : `left:${(xs / W) * 100}%`;
        const name = sg.preset ? `${esc(this._presetName(a, sg.preset))} ` : "";
        return `<span class="lvl ${sg.future ? "future" : ""} ${xs > W * 0.7 ? "end" : ""}" style="${place};top:${
          (y(sg.v) / H) * 100
        }%;--c:${PRESET_COLORS[sg.preset] || TEMP_COLOR}">${name}${sg.v}°</span>`;
      })
      .join("");
    const yLabels = gridValues
      .map((v) => `<span style="top:${(y(v) / H) * 100}%">${v}°</span>`)
      .join("");

    // Ticks adapt to the zoom: from every 6 hours down to every 5 minutes.
    const span = view.v1 - view.v0;
    const stepMin = [5, 10, 15, 30, 60, 120, 180, 360].find((m) => span / (m * 60000) <= 7) || 360;
    const ticks = [];
    const first = new Date(view.v0);
    first.setSeconds(0, 0);
    first.setMinutes(Math.ceil(first.getMinutes() / Math.min(stepMin, 60)) * Math.min(stepMin, 60));
    for (let t = first.getTime(); t <= view.v1; t += 60000 * Math.min(stepMin, 60)) {
      const dt = new Date(t);
      const minutes = dt.getHours() * 60 + dt.getMinutes();
      if (minutes % stepMin !== 0) continue;
      const label =
        minutes === 0
          ? dt.toLocaleDateString(this._lang(), { weekday: "short" })
          : dt.toLocaleTimeString(this._lang(), { hour: "2-digit", minute: "2-digit" });
      ticks.push(`<span style="left:${pct(t)}%">${esc(label)}</span>`);
    }
    const fmt = (t) => new Date(t).toLocaleTimeString(this._lang(), { hour: "2-digit", minute: "2-digit" });
    const zoomBtn = (zoom, label, title, active = false) =>
      `<button class="zbtn ${active ? "active" : ""}" data-action="zoom" data-zoom="${zoom}" data-room="${esc(
        a.room_id
      )}" title="${esc(title)}" aria-label="${esc(title)}">${label}</button>`;
    const spanH = Math.round(span / 3600000);
    const zoombar = `<div class="zoombar">
        <span class="zrange">${view.zoomed ? `${esc(fmt(view.v0))} – ${esc(fmt(view.v1))}` : esc(this._t("chart_label"))}</span>
        <span class="zbtns">
          ${zoomBtn("1h", "1h", this._t("zoom_1h"), view.zoomed && spanH === 1)}
          ${zoomBtn("6h", "6h", this._t("zoom_6h"), view.zoomed && spanH === 6)}
          ${zoomBtn("out", "−", this._t("zoom_out"))}
          ${zoomBtn("in", "+", this._t("zoom_in"))}
          ${view.zoomed ? zoomBtn("reset", "⤢", this._t("zoom_reset")) : ""}
        </span>
      </div>`;

    const next = a.next_change
      ? `<span>${this._t("next")}: <b>${esc(this._fmtTime(a.next_change))}</b> → ${esc(
          this._presetName(a, a.next_preset)
        )}</span>`
      : "";
    const nowIn = d.now >= view.v0 && d.now <= view.v1;
    const inner = `
        ${zoombar}
        <div class="hchart ${view.zoomed ? "zoomed" : ""} ${hasOut ? "with-out" : ""}" data-chart="${esc(a.room_id)}">
          <svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" role="img" aria-label="${esc(this._t("chart_label"))}">
            <defs><linearGradient id="${gid}" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0" stop-color="var(--ac-accent)" stop-opacity="0.14"></stop>
              <stop offset="1" stop-color="var(--ac-accent)" stop-opacity="0"></stop>
            </linearGradient></defs>
            <rect x="${Math.min(W, Math.max(0, nowX))}" y="0" width="${W - Math.min(W, Math.max(0, nowX))}" height="${BOTTOM}" class="futurebg"></rect>
            ${grid}${optimal}${heat}${segs}${steps}${outdoorSvg}
            ${tempArea ? `<path d="${tempArea}" fill="url(#${gid})" class="tempfill"></path>` : ""}
            ${tempPath ? `<path d="${tempPath}" class="templine"></path>` : ""}
            <line x1="${nowX}" x2="${nowX}" y1="0" y2="${BOTTOM}" class="now"></line>
          </svg>
          <div class="overlay">
            ${labels}
            <div class="ylabels">${yLabels}${outLabels}</div>
            ${optimalLabel}
            ${nowIn ? `<span class="nowlabel" style="left:${pct(d.now)}%">${this._t("now_tag")}</span>` : ""}
            ${
              last && last[0] >= view.v0 && last[0] <= view.v1
                ? `<span class="nowdot" style="left:${pct(last[0])}%;top:${(y(last[1]) / H) * 100}%"></span>`
                : ""
            }
            <div class="cross" hidden></div>
            <div class="tip" hidden></div>
          </div>
        </div>
        <div class="ticks">${ticks.join("")}</div>
        ${view.zoomed ? this._navHtml(a.room_id, d, view) : ""}
        <div class="readout">
          <span class="lg"><i class="lg-temp"></i>${this._t("legend_temp")}</span>
          <span class="lg"><i class="lg-target"></i>${this._t("legend_target")}</span>
          <span class="lg"><i class="lg-heat"></i>${this._t("legend_heat")}</span>
          ${hasOut ? `<span class="lg"><i class="lg-out"></i>${this._t("legend_outdoor")}</span>` : ""}
          ${d.loading ? `<span class="muted">${this._t("loading")}</span>` : ""}
        </div>
        <div class="meta"><span>${this._t("today")}: <b>${esc(a.profile || (a.profile_days && a.schedule ? this._t("frost_level") : "–"))}</b></span>${next}</div>`;
    if (innerOnly) return inner;
    return `<div class="chart-card" data-chartcard="${esc(a.room_id)}">${inner}</div>`;
  }

  /** Bar of the whole period with the visible window (only when zoomed). */
  _navHtml(room, d, view) {
    const total = d.t1 - d.t0;
    const pc = (t) => (((Math.min(d.t1, Math.max(d.t0, t)) - d.t0) / total) * 100).toFixed(2);
    const heat = d.heat
      .map(([s, e]) => `<i class="navheat" style="left:${pc(s)}%;width:${Math.max(0.3, pc(e) - pc(s))}%"></i>`)
      .join("");
    return `<div class="navbar" data-nav="${esc(room)}" role="scrollbar" aria-label="${esc(this._t("nav_help"))}"
        title="${esc(this._t("nav_help"))}">
        ${heat}<i class="navnow" style="left:${pc(d.now)}%"></i>
        <i class="navwin" style="left:${pc(view.v0)}%;width:${(pc(view.v1) - pc(view.v0)).toFixed(2)}%"></i>
      </div>`;
  }

  /** Crosshair and values under the pointer (the legend stays visible). */
  _chartHover(ev) {
    const chart = ev.target.closest?.(".hchart");
    if (!chart) return;
    const room = chart.dataset.chart;
    const d = this._charts?.[room];
    const cross = chart.querySelector(".cross");
    const tip = chart.querySelector(".tip");
    if (!d || !cross || !tip) return;
    if (ev.type === "pointerleave" && ev.target !== chart) return;
    if (ev.type === "pointerleave") {
      cross.hidden = true;
      tip.hidden = true;
      return;
    }
    const stateObj = this._rooms().find((s) => s.attributes.room_id === room);
    const a = stateObj?.attributes || {};
    const rect = chart.getBoundingClientRect();
    const f = Math.min(1, Math.max(0, (ev.clientX - rect.left) / rect.width));
    const t = d.v0 + f * (d.v1 - d.v0);
    let temp = null;
    for (const [pt, v] of d.temp) {
      if (pt <= t) temp = v;
      else break;
    }
    const seg = d.segs.find((sg) => sg.s <= t && t < sg.e);
    const heating = d.heat.some(([s, e]) => s <= t && t <= e);
    let out = null;
    let outForecast = false;
    if (t <= d.now) {
      for (const [pt, v] of d.outdoor || []) {
        if (pt <= t) out = v;
        else break;
      }
    } else {
      for (const [pt, v] of (d.forecast || []).filter(([ft]) => ft > d.now)) {
        if (pt <= t) {
          out = v;
          outForecast = true;
        } else break;
      }
      if (out === null && d.outdoor?.length) out = d.outdoor[d.outdoor.length - 1][1];
    }
    const time = new Date(t).toLocaleString(this._lang(), { weekday: "short", hour: "2-digit", minute: "2-digit" });
    const rows = [`<b>${esc(time)}</b>`];
    if (t <= d.now && temp !== null) rows.push(`<span><i class="lg-temp"></i>${temp.toFixed(1)}°</span>`);
    if (seg && seg.opt) {
      rows.push(`<span class="optword">${esc(this._t(seg.opt === "optimal_start" ? "tip_early_start" : "tip_early_stop"))}</span>`);
    }
    if (seg) {
      rows.push(
        `<span><i style="background:${PRESET_COLORS[seg.preset] || TEMP_COLOR}"></i>${
          seg.future ? this._t("planned") : this._t("target_tag")
        } ${seg.v}° · ${esc(this._presetName(a, seg.preset) || "")}</span>`
      );
    }
    if (heating) rows.push(`<span class="hotword"><i class="lg-heat"></i>${this._t("heating")}</span>`);
    if (out !== null) {
      rows.push(
        `<span><i class="lg-out"></i>${esc(this._t("legend_outdoor"))} ${out.toFixed(1)}°${
          outForecast ? ` · ${esc(this._t("legend_forecast"))}` : ""
        }</span>`
      );
    }
    cross.hidden = false;
    cross.style.left = `${f * 100}%`;
    tip.hidden = false;
    tip.innerHTML = rows.join("");
    tip.style.left = `${f * 100}%`;
    tip.style.transform = f > 0.6 ? "translateX(calc(-100% - 10px))" : "translateX(10px)";
  }

  /** Back to automatic (while there is a manual change). */
  _controlsHtml(a, e) {
    if (!a.override) return "";
    return `<div class="row wrap controls">${this._btn(this._t("clear_override"), `data-action="clear" data-room="${esc(a.room_id)}"`, {
      icon: "autorenew",
      kind: "primary",
    })}</div>`;
  }

  /** Quick manual change: a level or a temperature, for an optional number of hours. */
  _quickHtml(a, e = {}) {
    const presets = (a.presets || Object.keys(PRESET_COLORS).filter((p) => p !== "frost"))
      .map(
        (p) => `<button class="preset" style="--c:${PRESET_COLORS[p] || "var(--primary-color)"}"
          data-action="quick-preset" data-room="${esc(a.room_id)}" data-preset="${esc(p)}"><span class="dot"></span>${esc(
          this._presetName(a, p)
        )}${num(a.levels?.[p]) !== null ? ` <small>${num(a.levels[p])}°</small>` : ""}</button>`
      )
      .join("");
    const unit = a.temperature_unit || "°C";
    const fahrenheit = unit === "°F";
    const target = num(a.target_temperature) ?? (fahrenheit ? 70 : 21);
    return this._fold(
      `quick-${a.room_id}`,
      this._t("quick"),
      `<p class="hint">${this._t("quick_hint")}</p>
        <div class="presets">${presets}</div>
        ${e.child_lock ? `<div class="lockrow">${this._toggle(e.child_lock, this._t("child_lock"))}</div>` : ""}
        <div class="quickset">
          ${this._btn(this._t("apply"), `data-action="quick-temp" data-room="${esc(a.room_id)}"`, {
            icon: "thermometer-check",
            kind: "soft-accent",
          })}
          <label class="numfield"><input type="number" step="0.5" min="${
            num(a.min_temperature) ?? (fahrenheit ? 41 : 5)
          }" max="${num(a.max_temperature) ?? (fahrenheit ? 86 : 30)}" aria-label="${esc(this._t("target_tag"))}"
            data-quick="temp" data-room="${esc(a.room_id)}" value="${target}"><em>${esc(unit)}</em></label>
          <label class="numfield"><span>${this._t("for_hours")}</span><input type="number" step="0.5" min="0.5" max="72"
            data-quick="hours" data-room="${esc(a.room_id)}" placeholder="auto"><em>${this._t("hours")}</em></label>
        </div>`
    );
  }

  /** Temperatures of the levels the integration sets (number entities). */
  _levelsHtml(a, e) {
    const numbers = Object.entries(e).filter(([k]) => k.startsWith("level_"));
    if (!numbers.length) return "";
    const rows = numbers
      .map(([k, id]) => {
        const s = this._state(id);
        if (!s) return "";
        const preset = k.replace("level_", "");
        const name = s.attributes.friendly_name?.replace(`${a.room_name} `, "") || this._presetName(a, preset);
        return `<label class="numfield level"><span class="dot" style="--c:${
          PRESET_COLORS[preset] || "var(--divider-color)"
        }"></span><span class="lname">${esc(name)}</span><input type="number" step="${s.attributes.step || 0.5}" min="${
          s.attributes.min ?? 5
        }" max="${s.attributes.max ?? 30}" data-action="number" data-entity="${esc(id)}" value="${esc(
          s.state
        )}"><em>${esc(s.attributes.unit_of_measurement || "°C")}</em></label>`;
      })
      .join("");
    return this._fold(`levels-${a.room_id}`, this._t("levels"), `<div class="grid">${rows}</div>`);
  }

  /** Details: temperatures, heating rate and time, device preset, adjustments, levels. */
  _detailsHtml(a, e) {
    const rate = this._state(e.heating_rate);
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
        ${dl(this._t("target"), esc(this._temp(a.target_temperature)))}
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
        ${dl(this._t("adjustments"), esc(offsets))}
      </dl>
      ${
        levelTemps
          ? `<div class="sublabel">${a.custom_levels ? this._t("levels") : this._t("level_temps_gt")}</div>
             <div class="levels-line">${levelTemps}</div>`
          : ""
      }`;
    const program = estimate || runtimeHtml ? `<dl class="details">${estimate}${runtimeHtml}</dl>` : "";
    const learning = this._learnHtml(e);
    const html = `${this._alertsHtml(a)}
      ${group(this._t("grp_temps"), temps)}
      ${group(this._t("grp_program"), program)}
      ${group(this._t("grp_learning"), learning ? `<dl class="details">${learning}</dl>` : "")}
      ${a.schedule_error ? `<p class="error">${esc(a.schedule_error)}</p>` : ""}`;
    return this._fold(`details-${a.room_id}`, this._t("details"), html);
  }

  /** What the room learned (heating and cooling), each linked to its sensor, with its reset. */
  _learnHtml(e) {
    const row = (entityId, label, valueKey, resetId) => {
      const s = this._state(entityId);
      if (!s) return "";
      const n = num(s.attributes.episodes) ?? 0;
      const unit = s.attributes.unit_of_measurement || "°C/h";
      const value = num(s.state);
      // Heating: minutes per degree (whole minutes) plus the fixed part.
      const heating = valueKey === "learn_heat_value";
      const fixed = num(s.attributes.fixed_minutes);
      const text = n
        ? this._t(n === 1 ? `${valueKey}_1` : valueKey)
            .replace("{n}", String(n))
            .replace("{fixed}", fixed === null ? "–" : String(Math.round(fixed)))
            .replace(
              "{rate}",
              value === null ? "–" : `${heating ? Math.round(value) : value.toFixed(2)} ${unit}`
            )
        : this._t("learn_none");
      const sub = heating && !n ? this._heatDefault({ heating_rate: entityId }) : "";
      const confirming = this._confirmReset === resetId;
      const reset =
        resetId && this._state(resetId)
          ? this._btn(this._t(confirming ? "reset_confirm" : "reset"), `data-action="reset-learning" data-entity="${esc(resetId)}"`, {
              icon: "refresh",
              kind: confirming ? "soft-warn" : "",
            })
          : "";
      return `<div class="wide learn"><div class="link" ${this._more(entityId)}><dt>${esc(label)}</dt><dd>${esc(text)}${
        sub ? `<small class="sub">${esc(sub)}</small>` : ""
      }</dd></div>${reset}</div>`;
    };
    return (
      row(e.heating_rate, this._t("learn_heat"), "learn_heat_value", e.reset_heating_learning) +
      row(e.cooling_rate, this._t("learn_cool"), "learn_cool_value", e.reset_cooling_learning) +
      this._lastEpisodeHtml(e)
    );
  }

  /** The last heating episode learned: rise, minutes, outdoor temperature and time. */
  _lastEpisodeHtml(e) {
    const s = this._state(e.heating_rate);
    const list = s && Array.isArray(s.attributes.last_episodes) ? s.attributes.last_episodes : [];
    const last = list[list.length - 1];
    if (!last || num(last.rise) === null || num(last.minutes) === null) return "";
    const outdoor = num(last.outdoor);
    const text = this._t(outdoor === null ? "last_episode_value_no_out" : "last_episode_value")
      .replace("{rise}", this._temp(last.rise))
      .replace("{minutes}", String(Math.round(last.minutes)))
      .replace("{outdoor}", outdoor === null ? "" : this._temp(outdoor))
      .replace("{time}", last.at ? this._fmtTime(last.at) : "–");
    return `<div class="wide link" ${this._more(e.heating_rate)}><dt>${esc(this._t("last_episode"))}</dt><dd>${esc(
      text
    )}</dd></div>`;
  }

  /** Alerts of the room and of the whole house, in the language of the card. */
  _alertsHtml(a) {
    const alerts = a.alerts || [];
    if (!alerts.length) return "";
    const items = alerts
      .map((al) => {
        const p = al.params || {};
        const code = al.code === "sensor_unavailable" ? `sensor_unavailable_${p.fallback || "device"}` : al.code;
        let text = code ? this._t(`al_${code}`) : "";
        if (!text || text === `al_${code}`) text = al.message || "";
        const values = {
          ...p,
          entities: Array.isArray(p.entities) ? p.entities.join(", ") : p.entities,
          rooms: Array.isArray(p.rooms) ? p.rooms.map(([n, g]) => `${n} (−${g}°)`).join(", ") : p.rooms,
        };
        if (al.code === "schedule_gap") values.days = this._gapText(p);
        if (Array.isArray(p.features)) values.features = p.features.map((f) => this._t(`wf_${f}`)).join(", ");
        text = text.replace(/\{(\w+)\}/g, (m, k) => (values[k] !== undefined ? String(values[k]) : m));
        const entity = p.entity || (Array.isArray(p.entities) ? p.entities[0] : null);
        return `<li class="${entity ? "link" : ""}" ${this._more(entity)}>${this._icon("alert-outline")}<span>${esc(
          text
        )}</span></li>`;
      })
      .join("");
    return `<div class="label">${esc(this._t("alerts"))}</div><ul class="alerts">${items}</ul>`;
  }

  /** Which days a profile is for, in words. */
  _profileDays(meta) {
    const days = meta ? meta.days : "all";
    if (days === "workday") return this._t("days_workday");
    if (days === "weekend") return this._t("days_weekend");
    if (Array.isArray(days)) return days.map((d) => this._weekdayName(WEEKDAY_KEYS.indexOf(d), "short")).join(", ");
    return this._t("days_all");
  }

  /** On / off switch of a profile (in the schedule and in the editor). */
  _profileSwitch(room, name, on, action) {
    return `<button class="toggle sm ${on ? "on" : ""}" role="switch" aria-checked="${on}" aria-label="${esc(
      this._t(on ? "profile_on" : "profile_off")
    )}" title="${esc(this._t(on ? "profile_on" : "profile_off"))}" data-action="${action}" data-room="${esc(room)}" data-profile="${esc(
      name
    )}"><span class="knob"></span><span>${esc(this._t(on ? "profile_on" : "profile_off"))}</span></button>`;
  }

  /** Days without an active profile, in words ("" when every day has one). */
  _gapText(gap) {
    if (!gap) return "";
    const parts = (gap.days || []).map((d) => this._weekdayName(WEEKDAY_KEYS.indexOf(d)));
    if (gap.free_days) parts.push(this._t("gap_free_days"));
    if (gap.workdays) parts.push(this._t("gap_weekend_workdays"));
    return parts.join(", ");
  }

  /** Weekday name in the language of the user (0 = Monday). */
  _weekdayName(index, style = "long") {
    // 2024-01-01 was a Monday.
    return new Date(2024, 0, 1 + index).toLocaleDateString(this._lang(), { weekday: style });
  }

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

  /** Start a pan or pinch on the chart; True when the pointer is on a chart. */
  _chartPointerDown(ev) {
    const chart = ev.target.closest?.(".hchart");
    if (!chart) return false;
    const room = chart.dataset.chart;
    this._ptrs = this._ptrs || new Map();
    this._ptrs.set(ev.pointerId, ev.clientX);
    const d = this._charts?.[room];
    if (!d) return true;
    const card = chart.closest(".chart-card");
    try {
      card.setPointerCapture(ev.pointerId);
    } catch (err) {
      /* ignore */
    }
    const xs = [...this._ptrs.values()];
    this._pan = {
      room,
      card,
      startX: xs.length > 1 ? (xs[0] + xs[1]) / 2 : ev.clientX,
      dist: xs.length > 1 ? Math.abs(xs[0] - xs[1]) : 0,
      v0: d.v0,
      v1: d.v1,
      moved: false,
    };
    return true;
  }

  /** Pan with one finger or mouse, pinch zoom with two; True when handled. */
  _chartPointerMove(ev) {
    const p = this._pan;
    if (!p || !this._ptrs?.has(ev.pointerId)) return false;
    this._ptrs.set(ev.pointerId, ev.clientX);
    const d = this._charts?.[p.room];
    const chart = p.card.querySelector(".hchart");
    if (!d || !chart) return true;
    const rect = chart.getBoundingClientRect();
    const span = p.v1 - p.v0;
    const xs = [...this._ptrs.values()];
    if (xs.length > 1 && p.dist > 10) {
      // Pinch: zoom around the middle of the two fingers.
      const dist = Math.abs(xs[0] - xs[1]);
      const factor = p.dist / Math.max(dist, 10);
      const center = p.v0 + ((p.startX - rect.left) / rect.width) * span;
      p.moved = true;
      this._setView(p.room, center - (center - p.v0) * factor, center + (p.v1 - center) * factor);
      return true;
    }
    // One finger or the mouse moves the values cursor (the bar under the chart pans).
    if (Math.abs(ev.clientX - p.startX) > 4) p.moved = true;
    return false;
  }

  /** Bar under a zoomed chart: drag the window (or tap a place) to move the chart. */
  _navPointerDown(ev) {
    const nav = ev.target.closest?.(".navbar");
    if (!nav) return false;
    const room = nav.dataset.nav;
    const d = this._charts?.[room];
    if (!d) return true;
    ev.preventDefault();
    const card = nav.closest(".chart-card");
    try {
      card.setPointerCapture(ev.pointerId);
    } catch (err) {
      /* ignore */
    }
    const rect = nav.getBoundingClientRect();
    const at = d.t0 + ((ev.clientX - rect.left) / rect.width) * (d.t1 - d.t0);
    const span = d.v1 - d.v0;
    // On the window: keep where it was grabbed; elsewhere: centre the window there.
    const grab = at >= d.v0 && at <= d.v1 ? at - d.v0 : span / 2;
    this._nav = { room, card, grab, span, pointer: ev.pointerId };
    this._navAt = Date.now();
    this._setView(room, at - grab, at - grab + span);
    return true;
  }

  _navPointerMove(ev) {
    const n = this._nav;
    if (!n || ev.pointerId !== n.pointer) return false;
    const d = this._charts?.[n.room];
    const nav = n.card.querySelector(".navbar");
    if (!d || !nav) return true;
    const rect = nav.getBoundingClientRect();
    const at = d.t0 + ((ev.clientX - rect.left) / rect.width) * (d.t1 - d.t0);
    this._setView(n.room, at - n.grab, at - n.grab + n.span);
    return true;
  }

  /** End a pan or pinch; a tap without moving shows the values under it. */
  _chartPointerUp(ev) {
    if (!this._ptrs) return;
    this._ptrs.delete(ev.pointerId);
    const p = this._pan;
    if (!this._ptrs.size) this._pan = null;
    else if (p) {
      // One finger left after a pinch: start a new pan from here.
      const d = this._charts?.[p.room];
      const [x] = [...this._ptrs.values()];
      this._pan = { ...p, startX: x, dist: 0, v0: d?.v0 ?? p.v0, v1: d?.v1 ?? p.v1 };
    }
    const chart = p?.card?.querySelector(".hchart");
    if (p && !p.moved && chart) this._chartHover({ type: "pointermove", clientX: ev.clientX, target: chart });
  }

  /** Ctrl + wheel or touchpad pinch zooms the chart around the pointer. */
  _chartWheel(ev) {
    const chart = ev.target.closest?.(".hchart");
    // Only pinch on a touchpad or Ctrl + wheel zoom, so the page still scrolls normally.
    if (!chart || !(ev.ctrlKey || ev.metaKey)) return;
    ev.preventDefault();
    const d = this._charts?.[chart.dataset.chart];
    if (!d) return;
    const rect = chart.getBoundingClientRect();
    const center = d.v0 + ((ev.clientX - rect.left) / rect.width) * (d.v1 - d.v0);
    this._zoom(chart.dataset.chart, ev.deltaY > 0 ? 1.25 : 0.8, center);
  }

  /** Double click zooms in around the pointer. */
  _chartDblClick(ev) {
    // With the pointer captured by the chart card the event target is the card itself.
    const chart = ev.target.closest?.(".hchart") || ev.target.closest?.(".chart-card")?.querySelector(".hchart");
    if (ev.target.closest?.(".zoombar")) return;
    // Two taps on the bar under the chart move it; they do not zoom.
    if (ev.target.closest?.(".navbar") || Date.now() - (this._navAt || 0) < 700) return;
    if (!chart) return;
    const d = this._charts?.[chart.dataset.chart];
    if (!d) return;
    const rect = chart.getBoundingClientRect();
    const center = d.v0 + ((ev.clientX - rect.left) / rect.width) * (d.v1 - d.v0);
    this._zoom(chart.dataset.chart, 0.4, center);
  }

  /** Pointer pressed: chart pan, or dragging a handle of the schedule editor. */
  _pointerDown(ev) {
    if (this._navPointerDown(ev)) return;
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
    if (this._nav && (!ev || ev.pointerId === this._nav.pointer)) {
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

  // ------------------------------------------------------------------ heating time per period
  _period() {
    const p = this._runtimePeriod || this._config.runtime_period || "day";
    return RUNTIME_PERIODS.includes(p) ? p : "day";
  }

  /** Hours of heating in the current day / week / month, from the long-term statistics. */
  _runtimeValue(entityId) {
    const period = this._period();
    const key = `${entityId}|${period}`;
    this._runtime = this._runtime || {};
    const cached = this._runtime[key];
    if (!cached || (!cached.loading && Date.now() - cached.at > 5 * 60 * 1000)) {
      this._fetchRuntime(entityId, period, key);
    }
    return cached && !cached.failed ? cached.value : null;
  }

  /** Fetch the heating time of the period from the long-term statistics. */
  async _fetchRuntime(entityId, period, key) {
    this._runtime[key] = { ...(this._runtime[key] || {}), at: Date.now(), loading: true };
    if (!this._hass?.callWS) return;
    let value = null;
    let failed = false;
    try {
      const res = await this._hass.callWS({
        type: "recorder/statistic_during_period",
        statistic_id: entityId,
        calendar: { period },
        types: ["change"],
      });
      value = num(res?.change) ?? 0;
    } catch (err) {
      failed = true;
    }
    this._runtime[key] = { at: Date.now(), loading: false, value, failed };
    const active = this.shadowRoot.activeElement;
    if (this._editing || this._drag || this._pan || (active && ["INPUT", "SELECT"].includes(active.tagName))) return;
    this._lastKey = "";
    this._render();
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

  /** Call a service; the error is shown under the section when it fails. */
  async _call(domain, service, data, errorKey) {
    try {
      await this._hass.callService(domain, service, data);
      if (errorKey) delete this._error[errorKey];
      return true;
    } catch (err) {
      if (errorKey) this._error[errorKey] = `${this._t("error")}: ${err?.message || err}`;
      this._lastKey = "";
      this._render();
      return false;
    }
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
      this._render();
    }
  }

  /** Temperature and duration entered in the quick manual change. */
  _quickValues(room) {
    const temp = this.shadowRoot.querySelector(`input[data-quick="temp"][data-room="${CSS.escape(room)}"]`);
    const hours = this.shadowRoot.querySelector(`input[data-quick="hours"][data-room="${CSS.escape(room)}"]`);
    const data = {};
    const h = num(hours?.value);
    if (h !== null) data.duration_hours = h;
    return { temp: num(temp?.value), data };
  }

  /** Attributes that open the more-info dialog of an entity on click. */
  _more(entityId, title = null) {
    if (!entityId) return title ? `title="${esc(title)}"` : "";
    return `data-action="more" data-entity="${esc(entityId)}" role="link" tabindex="0" title="${esc(
      title || this._t("open_entity")
    )}"`;
  }

  /** Every button of the card (data-action). */
  async _onClick(ev) {
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
        break;
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
        else if (z === "reset") this._setView(room, d.t0, d.t1);
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
        if (start?.value) data.start = fromLocalInput(start.value);
        if (end?.value) data.end = fromLocalInput(end.value);
        await this._call("advanced_climate", "set_vacation", data, `vac-${house}`);
        break;
      }
      case "clear":
        await this._call("advanced_climate", "clear_override", { room });
        return;
      case "quick-preset": {
        const { data } = this._quickValues(room);
        await this._call("advanced_climate", "set_override", { room, preset: el.dataset.preset, ...data });
        return;
      }
      case "quick-temp": {
        const { temp, data } = this._quickValues(room);
        if (temp === null) return;
        await this._call("advanced_climate", "set_override", { room, temperature: temp, ...data });
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
        const name = (input?.value || "")
          .trim()
          .toLowerCase()
          .replace(/[,:#]/g, "")
          .replace(/\s+/g, "_");
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

const STYLE = `
  :host {
    --ac-surface: color-mix(in srgb, var(--primary-text-color) 4%, transparent);
    --ac-surface-2: color-mix(in srgb, var(--primary-text-color) 7%, transparent);
    --ac-line: color-mix(in srgb, var(--primary-text-color) 12%, transparent);
    --ac-muted: var(--secondary-text-color);
    --ac-accent: var(--primary-color);
    --ac-fixed: color-mix(in srgb, var(--primary-text-color) 65%, transparent);
    --ac-out: #7d8ea8;
    --ac-hot: #d9480f;
    --ac-warn: #c98a12;
    color: var(--primary-text-color);
  }
  ha-card { padding: 16px; color: var(--primary-text-color); display: flex; flex-direction: column; gap: 12px; }
  .title { margin: 0; font-size: 1.35em; font-weight: 500; letter-spacing: -0.01em; }
  .empty { margin: 0; color: var(--ac-muted); }
  .muted { color: var(--ac-muted); font-size: 0.85em; }
  .block { border: 1px solid var(--ac-line); border-radius: 16px; padding: 14px; display: flex; flex-direction: column; gap: 10px; }
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
  .pill.rule { background: color-mix(in srgb, var(--c) 18%, transparent); color: var(--primary-text-color);
    box-shadow: inset 0 0 0 1.5px var(--c); font-weight: 500; }
  .pill.hot { background: var(--ac-hot); color: #fff; }
  .pill.warn { background: var(--ac-warn); color: #fff; }
  .presence-state.home { background: color-mix(in srgb, #f08c00 22%, transparent); }
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
  .segmented { display: grid; grid-template-columns: repeat(4, 1fr); padding: 3px; gap: 3px; border-radius: 12px;
    background: var(--ac-surface-2); }
  .seg { border: none; background: none; padding: 8px 6px; border-radius: 9px; font: inherit; font-size: 0.9em;
    color: var(--primary-text-color); cursor: pointer; }
  .seg.active { background: var(--card-background-color); box-shadow: 0 1px 2px rgba(0,0,0,.18); font-weight: 600; color: var(--ac-accent); }
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
  input, select { font: inherit; color: var(--primary-text-color); background: var(--card-background-color);
    border: 1px solid var(--ac-line); border-radius: 10px; padding: 7px 10px; min-height: 36px; box-sizing: border-box; }
  input:hover, select:hover { border-color: color-mix(in srgb, var(--primary-text-color) 30%, transparent); }
  input:focus, select:focus { border-color: var(--ac-accent); outline: none; }
  .dates { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 10px; }
  .datefield, .selectfield, .textfield { display: flex; flex-direction: column; gap: 4px; font-size: 0.8em; color: var(--ac-muted); }
  .datefield input, .selectfield select, .textfield input { font-size: 1.1em; }
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
  .quickset .btn { padding: 7px 12px; }
  .quickset .numfield { gap: 4px; white-space: nowrap; }
  .quickset .numfield input { width: 4em; }
  .quickset .numfield input[data-quick="hours"] { width: 4.6em; }
  .lockrow { display: flex; align-items: center; background: var(--ac-surface); border-radius: 10px; padding: 4px 10px; }
  .lockrow .toggle { width: 100%; justify-content: space-between; flex-direction: row-reverse; font-size: 0.9em; }
  .lockrow .toggle .knob { background: var(--ac-line); }
  .lockrow .toggle.on .knob { background: var(--ac-accent); }
  .profile.off > .sbar, .profile.off > .intervals { opacity: 0.45; }
  .confirmbox { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; padding: 8px 10px; border-radius: 10px;
    background: color-mix(in srgb, var(--ac-warn) 14%, transparent); }
  .confirmbox > span { flex: 1 1 200px; }
  .daychecks { display: flex; flex-wrap: wrap; gap: 6px 10px; align-items: center; font-size: 0.9em; }
  .daychecks label { display: inline-flex; gap: 4px; align-items: center; }
  dd small.sub { display: block; font-size: 0.8em; color: var(--ac-muted); }
  .decision { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }
  .reason { margin: 0; color: var(--ac-muted); font-size: 0.9em; }
  .pill.wrap { white-space: normal; text-align: left; }
  .reason.noheat { display: flex; gap: 6px; align-items: flex-start; color: var(--primary-text-color); }
  .reason.noheat ha-icon { --mdc-icon-size: 18px; color: var(--ac-muted); flex: none; }
  .link { cursor: pointer; }
  .link:hover { filter: brightness(0.96); }
  .link:focus-visible { outline: 2px solid var(--ac-accent); outline-offset: 2px; }
  .banner { display: flex; gap: 8px; align-items: center; padding: 10px 12px; border-radius: 12px;
    background: color-mix(in srgb, var(--warning-color, #f0ad4e) 18%, transparent);
    border: 1px solid color-mix(in srgb, var(--warning-color, #f0ad4e) 55%, transparent); font-size: 0.9em; }
  .banner ha-icon { --mdc-icon-size: 20px; color: var(--warning-color, #f0ad4e); flex: none; }
  .cutoffline { font-size: 0.85em; color: var(--ac-muted); padding: 6px 10px; border-radius: 10px; background: var(--ac-surface); }
  .cutoffline b { color: var(--primary-text-color); font-weight: 500; }
  .cutoffline.on { background: color-mix(in srgb, var(--warning-color, #f0ad4e) 14%, transparent); }
  ul.alerts { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
  ul.alerts li { display: flex; gap: 8px; align-items: flex-start; font-size: 0.85em; padding: 8px 10px; border-radius: 10px;
    background: color-mix(in srgb, var(--error-color, #db4437) 10%, transparent); }
  ul.alerts ha-icon { --mdc-icon-size: 18px; color: var(--error-color, #db4437); flex: none; }
  .chart-card { border-radius: 14px; background: var(--ac-surface); padding: 12px 12px 10px;
    box-shadow: inset 0 0 0 1px var(--ac-line); display: flex; flex-direction: column; gap: 4px; }
  .hchart.with-out { height: 210px; }
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
  .hchart .oline { fill: none; stroke: var(--ac-out); stroke-width: 1.6; vector-effect: non-scaling-stroke; stroke-linejoin: round; }
  .hchart .oline.future { stroke-dasharray: 4 4; opacity: 0.8; }
  .hchart .ocut { stroke: var(--ac-hot); stroke-width: 1; stroke-dasharray: 2 3; opacity: 0.6; vector-effect: non-scaling-stroke; }
  .hchart .optband { opacity: 0.08; }
  .hchart .optline { stroke-width: 1.5; stroke-dasharray: 3 3; vector-effect: non-scaling-stroke; }
  .optlab { position: absolute; top: 2px; transform: translateX(4px); font-size: 0.68em; white-space: nowrap; padding: 1px 6px;
    border-radius: 6px; color: var(--primary-text-color); background: color-mix(in srgb, var(--c) 18%, var(--card-background-color)); }
  .optlab.end { transform: translateX(calc(-100% - 4px)); }
  .ylabels .olab { color: var(--ac-out); }
  .lg-out { background: var(--ac-out); }
  .hchart .heatlane { fill: var(--primary-text-color); opacity: 0.05; }
  .hchart .heatbar { fill: var(--ac-hot); opacity: 0.9; }
  .hchart .tline { stroke-width: 2.5; vector-effect: non-scaling-stroke; stroke-linecap: round; }
  .hchart .tline.future { stroke-dasharray: 6 5; opacity: 0.75; }
  .hchart .tstep { stroke: var(--primary-text-color); opacity: 0.25; stroke-width: 1; stroke-dasharray: 2 3; vector-effect: non-scaling-stroke; }
  .hchart .templine { fill: none; stroke: var(--ac-accent); stroke-width: 2.25; vector-effect: non-scaling-stroke;
    stroke-linejoin: round; stroke-linecap: round; }
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
    cursor: pointer; touch-action: none; user-select: none; overflow: hidden; }
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
    background: color-mix(in srgb, var(--card-background-color) 92%, transparent); box-shadow: 0 2px 10px rgba(0,0,0,.18);
    border: 1px solid var(--ac-line); z-index: 3; }
  .tip span { display: inline-flex; align-items: center; gap: 6px; }
  .tip i { display: inline-block; width: 10px; height: 3px; border-radius: 2px; }
  .tip .hotword { color: var(--ac-hot); font-weight: 600; }
  .tip .optword { font-weight: 600; }
  .lg { display: inline-flex; align-items: center; gap: 6px; }
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
  @media (max-width: 480px) {
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
    background: var(--primary-text-color); color: var(--card-background-color); white-space: nowrap; opacity: 0;
    transition: opacity .12s; pointer-events: none; font-variant-numeric: tabular-nums; }
  .handle:hover .htime, .handle:focus-visible .htime, .handle.dragging .htime { opacity: 1; }
  .handle:focus-visible::before, .handle.dragging::before { box-shadow: 0 0 0 2px var(--ac-accent), 0 1px 6px rgba(0,0,0,.35); }
  .bar-ticks { display: flex; justify-content: space-between; font-size: 0.66em; color: var(--ac-muted); margin-top: -2px; }
  .copysel { font-size: 0.85em; min-height: 32px; padding: 4px 8px; }

  /* compact */
  ha-card.compact { gap: 8px; }
  .crow { display: flex; align-items: center; gap: 10px; width: 100%; font: inherit; color: var(--primary-text-color);
    background: var(--ac-surface); border: none; border-radius: 12px; padding: 10px 12px; cursor: pointer; text-align: left;
    transition: background .15s; min-height: 48px; box-sizing: border-box; }
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
  .cicon ha-icon { --mdc-icon-size: 18px; }
  .cicon.hot ha-icon { color: var(--ac-hot); }
  .cicon.warn ha-icon { color: var(--ac-warn); }
  .house-row .pill { flex: none; }
  .house-row .ctemp { font-size: 0.85em; }
  @media (max-width: 420px) { .house-row .pill + .pill { display: none; } }

  /* house */
  .house-head { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
  .who { display: flex; align-items: center; gap: 12px; min-width: 0; }
  .avatars { display: flex; gap: 8px; flex: none; padding: 4px; }
  .avatar { --r: var(--ac-line); width: 36px; height: 36px; border-radius: 50%; background: var(--ac-surface-2); display: inline-flex;
    align-items: center; justify-content: center; font-weight: 500; font-size: 0.9em; overflow: hidden; flex: none;
    box-shadow: 0 0 0 2px var(--card-background-color), 0 0 0 4px var(--r); }
  .avatar img { width: 100%; height: 100%; object-fit: cover; }
  .avatar.home { --r: #f08c00; }
  .avatar.nearby { --r: #2f9e8f; }
  .avatar.far { --r: #8a96a3; }
  .avatars.sm { gap: 6px; padding: 3px; }
  .avatars.sm .avatar { width: 24px; height: 24px; font-size: 0.72em; }
  .whotext { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
  .hname { font-weight: 600; }
  .pstate { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
  .pstate .presence-state { display: inline-flex; align-items: center; gap: 6px; font-weight: 500; font-size: 1.05em; background: none; }
  .pstate .presence-state ha-icon { --mdc-icon-size: 19px; color: var(--ac-muted); }
  .pstate .presence-state.home ha-icon { color: #f08c00; }
  .pstate .presence-state.nearby ha-icon { color: #2f9e8f; }
  .house-head .segmented { flex: 0 1 280px; min-width: 220px; }
  .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(105px, 1fr)); gap: 8px; }
  .stat, button.stat.period { display: flex; flex-direction: column; gap: 3px; background: var(--ac-surface-2); border-radius: 10px;
    padding: 8px 10px; text-align: left; min-width: 0; }
  .stat .k { display: flex; align-items: center; gap: 5px; font-size: 0.72em; color: var(--ac-muted); min-width: 0; }
  .stat .k ha-icon { --mdc-icon-size: 14px; flex: none; }
  .stat .v { font-variant-numeric: tabular-nums; font-size: 1.15em; font-weight: 500; }
  .stat.hot { background: color-mix(in srgb, var(--ac-hot) 16%, transparent); }
  .stat.hot .k, .stat.hot .v { color: var(--ac-hot); }
  .stat.warn .v { color: var(--ac-warn); }
  .hactions { display: grid; grid-template-columns: repeat(var(--n, 5), minmax(0, 1fr)); gap: 6px; }
  @media (max-width: 420px) { .hactions { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
  .abtn { --t: var(--ac-accent); display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 4px;
    min-height: 56px; padding: 6px 4px; border-radius: 12px; border: 1px solid var(--ac-line); background: var(--card-background-color);
    color: var(--primary-text-color); font: inherit; font-size: 0.75em; cursor: pointer; min-width: 0; transition: background .15s, border-color .15s; }
  .abtn span { max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .abtn ha-icon { --mdc-icon-size: 20px; }
  .abtn:hover { background: var(--ac-surface-2); }
  .abtn.warn { --t: var(--warning-color, #f0ad4e); }
  .abtn.teal { --t: #2f9e8f; }
  .abtn.blue { --t: #4a78b5; }
  .abtn.on, .abtn.open { border-color: var(--t); background: color-mix(in srgb, var(--t) 16%, var(--card-background-color)); }
  .abtn.on ha-icon { color: var(--t); }
  .panel { --t: var(--ac-accent); display: flex; flex-direction: column; gap: 10px; padding: 12px; border-radius: 12px;
    background: color-mix(in srgb, var(--t) 8%, transparent); box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--t) 40%, transparent); }
  .panel.teal { --t: #2f9e8f; }
  .panel.blue { --t: #4a78b5; }
  .panel-head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
  .panel-head > :last-child { margin-left: auto; }
  .pill.state.on, .pill.teal { background: #2f9e8f; color: #fff; }

  /* rooms */
  .block.room { background: color-mix(in srgb, var(--c) 6%, var(--card-background-color));
    border-color: color-mix(in srgb, var(--c) 32%, var(--ac-line)); gap: 14px; }
  .room-head { display: flex; justify-content: space-between; align-items: center; gap: 8px; flex-wrap: wrap; }
  .rh-left { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; min-width: 0; }
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
  .hero .chips .pill.preset { align-self: flex-start; }
  @container (max-width: 440px) {
    .hero { gap: 12px; }
    .hero .gauge { width: 112px !important; height: 112px !important; --gs: 112px; }
    .hero .gauge svg { width: 100%; height: 100%; }
    .hero .chip { font-size: 0.85em; }
  }
  .gauge { position: relative; display: inline-block; flex: none; }
  .gauge svg { display: block; }
  .gauge .gtrack { fill: none; stroke: color-mix(in srgb, var(--c) 20%, var(--ac-line)); stroke-linecap: round; }
  .gauge .gvalue { fill: none; stroke: var(--c); stroke-linecap: round; }
  .gcenter { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; }
  .gnum { font-size: max(13px, calc(var(--gs) * 0.24)); font-weight: 300; line-height: 1; letter-spacing: -0.02em; font-variant-numeric: tabular-nums; }
  .gsub { font-size: 0.8em; color: var(--ac-muted); margin-top: 5px; }
  .chips { display: flex; flex-direction: column; gap: 9px; min-width: 0; }
  .chip { display: inline-flex; align-items: flex-start; gap: 7px; font-size: 0.9em; line-height: 1.35; }
  .chip ha-icon { --mdc-icon-size: 17px; color: var(--c); flex: none; }
  .chip small { display: block; }
  .chip.soft { align-self: flex-start; align-items: center; padding: 4px 10px; border-radius: 999px; font-size: 0.82em;
    background: color-mix(in srgb, var(--c) 16%, transparent); }
  .chip.soft.on { box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--c) 55%, transparent); }
  .chip.soft.neutral { background: var(--ac-surface-2); }
  .chip.neutral ha-icon { color: var(--ac-muted); }
  .today { display: flex; flex-direction: column; gap: 4px; }
  .tlabel { font-size: 0.72em; color: var(--ac-muted); text-transform: uppercase; letter-spacing: 0.06em; }
  .tbar { position: relative; height: 12px; border-radius: 6px; overflow: hidden; background: var(--ac-surface-2); }
  .tbar i { position: absolute; top: 0; bottom: 0; background: color-mix(in srgb, var(--c) 80%, transparent); }
  .tbar b { position: absolute; top: 0; bottom: 0; width: 2px; margin-left: -1px; background: var(--primary-text-color); }
  .tticks { display: flex; justify-content: space-between; font-size: 0.68em; color: var(--ac-muted); }
  .sbtns { display: grid; grid-template-columns: repeat(var(--n, 3), minmax(0, 1fr)); gap: 8px; }
  @media (max-width: 420px) { .sbtns { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
  .sbtn { display: flex; align-items: center; justify-content: center; gap: 6px; min-height: 44px; padding: 6px 8px; border-radius: 12px;
    border: 1px solid var(--ac-line); background: var(--card-background-color); color: var(--primary-text-color); font: inherit;
    font-size: 0.85em; font-weight: 500; cursor: pointer; min-width: 0; transition: background .15s, border-color .15s; }
  .sbtn span { text-align: center; line-height: 1.2; overflow-wrap: anywhere; }
  .sbtn ha-icon { --mdc-icon-size: 18px; flex: none; }
  .sbtn:hover { background: var(--ac-surface-2); }
  .sbtn.on { border-color: var(--c); background: color-mix(in srgb, var(--c) 18%, var(--card-background-color)); }
  .section { display: flex; flex-direction: column; gap: 4px; padding: 12px; border-radius: 12px; background: var(--ac-surface);
    box-shadow: inset 0 0 0 1px var(--ac-line); }
  .section-head { font-weight: 500; }
  .section .fold-body { padding-top: 6px; }
  .block.room.folded { padding: 8px 12px; }
  .frow { display: flex; align-items: center; gap: 12px; width: 100%; font: inherit; color: inherit; background: none; border: none;
    padding: 0; cursor: pointer; text-align: left; min-height: 54px; }
  .ftext { display: flex; flex-direction: column; gap: 2px; flex: 1; min-width: 0; }
  .ftext .name { font-weight: 600; }
  .freason { font-size: 0.82em; color: var(--ac-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .frow .gnum, .tile .gnum { font-weight: 400; }
  .frow ha-icon, .frow .cicon ha-icon { --mdc-icon-size: 18px; }

  /* compact tiles */
  .rooms-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); gap: 10px; }
  .rooms-list > .block { grid-column: 1 / -1; }
  .tile { display: flex; flex-direction: column; gap: 10px; font: inherit; color: inherit; text-align: left; cursor: pointer; padding: 12px;
    border-radius: 16px; border: 1px solid color-mix(in srgb, var(--c) 32%, var(--ac-line));
    background: color-mix(in srgb, var(--c) 7%, var(--card-background-color)); min-width: 0; }
  .tile:hover { background: color-mix(in srgb, var(--c) 12%, var(--card-background-color)); }
  .tile-head { display: flex; justify-content: space-between; align-items: center; gap: 6px; min-height: 28px; }
  .tile .cname { font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .tstat { width: 28px; height: 28px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; flex: none;
    background: color-mix(in srgb, var(--c) 22%, transparent); }
  .tstat ha-icon { --mdc-icon-size: 16px; }
  .tstat.hot { background: var(--ac-hot); color: #fff; }
  .tstat.warn { background: var(--ac-warn); color: #fff; }
  .tstat.teal { background: #2f9e8f; color: #fff; }
  .tstats { display: inline-flex; gap: 4px; flex: none; }
  .cicon.teal ha-icon { color: #2f9e8f; }
  .tile-body { display: flex; align-items: center; gap: 10px; min-width: 0; }
  .gcol { display: flex; flex-direction: column; align-items: center; gap: 6px; flex: none; }
  .pill.preset { background: color-mix(in srgb, var(--c) 22%, transparent); font-weight: 500; }
  .pill.preset .dot, .pill.rule .dot { width: 8px; height: 8px; }
  .fname, .tname { display: flex; align-items: center; gap: 6px; min-width: 0; flex-wrap: wrap; }
  .tname { flex-wrap: nowrap; flex: 1; }
  .tname .cname { flex: 0 1 auto; }
  .tname .pill { min-width: 0; flex: 0 1 auto; overflow: hidden; text-overflow: ellipsis; }
  .banner.teal { background: color-mix(in srgb, #2f9e8f 18%, transparent); border-color: color-mix(in srgb, #2f9e8f 55%, transparent); }
  .banner.teal ha-icon { color: #2f9e8f; }
  .tile-info { display: flex; flex-direction: column; gap: 4px; min-width: 0; font-size: 0.85em; align-items: flex-start; }
  .tile-info .muted { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 100%; }

  @media (prefers-reduced-motion: reduce) { .pulse { animation: none; } * { transition: none !important; } }
`;

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
          { value: "day", label: "Day / Zi" },
          { value: "week", label: "Week / Săptămână" },
          { value: "month", label: "Month / Lună" },
        ],
      },
    },
  },
];

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
    compact: "Compact: one row per room, tap to open",
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
    compact: "Compact: un rând pe cameră, se deschide la atingere",
    runtime_period: "Timpul de încălzire afișat pentru (se schimbă și apăsând valoarea în card)",
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
