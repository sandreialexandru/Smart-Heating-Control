# Smart Heating Control – reference

*[Română](reference.ro.md) · [README](../README.md) · [Guide](guide/README.md)*

Everything the integration does, in technical detail: what every rule, sensor, service and card option does. For a step by step introduction see the [guide](guide/README.md).

## Features

- **Presence in three states**: *home*, *nearby* (e.g. somewhere in your city)
  and *far*. Nearby zones are evaluated from coordinates too, so a zone such as
  "Office" inside the city counts as nearby and stale `not_home` states are
  corrected.
- **Schedules** with `workday` / `weekend` / weekday / custom profiles, holidays
  from the Workday integration, profiles chosen from a calendar, a day boundary
  for night shifts, or an existing Schedule helper.
- **Optimal start / stop** with a thermal model learned per room: heating,
  heat loss and thermal inertia (see *Learning* and *Optimal stop*).
  Once an optimal start begins it continues until the scheduled time, even if
  the room is warm early; the rules above the schedule can still override it.
- **Windows**: open/close delays, frost protection or off, detection from a
  sudden temperature drop, windows of neighbouring rooms, alerts.
- **Weather**: outdoor cutoff with averaging and hysteresis (the averaging time
  is also how long an outdoor value stays valid when the sensor or weather is
  unavailable; after it the outdoor temperature is unknown), heating season
  (dates or automatic), outdoor compensation, forecast, solar gain per room (needs the weather
  entity of the house; the setting is shown only when one is set). The measured
  average of the last *Average over* hours turns the heating off when it
  reaches the cutoff; the heating may run again when that average falls to the
  resume temperature (cutoff − hysteresis). With *Use the forecast* the mean
  forecast of the next *Forecast hours* also counts (never a single forecast
  hour):
  - heating off by the measured average, forecast mean at or below the resume
    temperature: the heating may run (a warm afternoon does not keep it off in
    a cold evening); forecast mean above the resume temperature: it stays off;
  - heating running, forecast mean at or above the cutoff: the heating is
    turned off earlier and stays off until that mean falls to the resume
    temperature (the same hysteresis as the measured average); a mean below
    the cutoff does not turn it off. More *Forecast hours* turn it off earlier
    before a warm period.

  In the mean each forecast value holds for its hour; until the next forecast
  hour the measured value counts. Cutoff, hysteresis, *Average over* and
  *Forecast hours* all come from the options. Without a forecast only the
  measured average decides.
- **Manual changes**: detected automatically and kept for a fixed time or until
  the next reevaluation (schedule, presence, window or mode change). A device
  that only reports, later, the values the integration sent it (e.g. a sleepy
  Zigbee TRV) is not a manual change. If a higher rule (window, frost
  protection) changes the devices meanwhile, the manual value is set again
  afterwards. Child lock, pause and per-room / global clear buttons.
- **Global modes**: Auto, Vacation (with dates, preheating before the return and
  automatic vacation), Off (frost protection) and Summer. During the preheating
  hours before the end of a vacation the schedule applies even while everyone
  is still far. Only an end date: the vacation starts now. The automatic
  vacation ends when someone is on the way home (*arriving*), so the house
  preheats; it comes back only when everyone has been far again for the
  time set in *Automatic vacation after everyone is far for*.
- **Energy**: dynamic tariff, PV surplus, control of the heat source (boiler)
  from the heat demand of the rooms, heating time statistics.
- **Safety**: frost protection always (once it starts heating it continues
  until the device stops asking for heat; a room in frost protection starts
  the heat source on its own, also while paused; with a room sensor it is
  decided from the room and the TRVs are boosted to open), maximum temperature, command
  verification with retry, alerts for unavailable devices, failed sensors, low
  batteries and open windows, valve exercise for TRVs.
- **Mold risk alert** for a room with a humidity sensor (and an outdoor
  temperature of the house): the humidity at the coldest wall, by the method
  of DIN 4108-2 (wall at outdoor + 0.70 × (room − outdoor), Magnus formula),
  80 % or more for an hour raises it, below 75 % it ends.
- **Visibility**: a *Decision* sensor per room with the winning rule and the
  reason, an event on every change, diagnostics with the last 100 decisions and
  a Lovelace card with an editable schedule.

**The complete guide**, step by step and in plain words (every setting, every
kind of heating, examples): [docs/guide/README.md](guide/README.md).
The full specification is in [docs/SPEC.md](SPEC.md) ([Română](SPEC.ro.md)).

## Installation

### HACS

1. HACS → ⋮ → **Custom repositories** → add
   `https://github.com/sandreialexandru/Smart-Heating-Control` as **Integration**.
2. Install **Smart Heating Control** and restart Home Assistant.
3. **Settings → Devices & services → Add integration → Smart Heating Control**.

### Manual

Copy `custom_components/advanced_climate` into your `config/custom_components`
folder and restart Home Assistant.

Requires Home Assistant **2026.6.0** or newer (the oldest version the tests run on;
they also run on the newest one).

## Configuration

> **Interactive configurator:** [docs/configurator.html](configurator.html) walks through
> every form step by step, in English or Romanian, explains each choice and
> gives a summary of what to set. Download the file and open it in a browser.

1. **Create the house**: first the **temperature unit** (°C or °F), then the name, people, nearby zones and the home rule, then the
   **heating of the whole house** (e.g. your Generic Thermostat). That is enough
   for a house heated by one thermostat: it becomes the zone *Whole house*
   and uses every option. It can be changed later in *Configure → Heating of the
   whole house*.
2. Optionally **add rooms** with *Add room* on the integration page, for rooms
   with their own valves or thermostats. Each room has its own devices,
   sensors, windows and schedule. The zone *Whole house* is changed the same
   way (*⋮ → Reconfigure* on the integration page).
3. Everything else is in the integration **options** (presence, workdays and
   calendar, weather and season, energy, heat source, manual changes and vacation,
   alerts).

### Temperature unit

Each house has one temperature unit, °C or °F, for all its rooms. Every
temperature of the house is entered and shown in it: the settings, the level
temperatures, the sensors, the card and the `set_override` service. It is
chosen first when the house is created and changed with **Reconfigure** on the
integration page; the values are converted, nothing has to be entered again.
The integration keeps its values in °C and converts the readings and commands
of the thermostats and sensors from their own unit, so the unit of the house
does not have to match the one of Home Assistant.

Every form shows only what applies. The choices come first; a second form
then asks only for the values they need, and is skipped when nothing applies:

- **Heating**: the source, then its devices (and the command for other
  thermostats), then the command settings: hysteresis, minimum times and
  *Use the learned inertia* for relays and on / off control (relays also need a room temperature sensor),
  the hysteresis for temperature / preset commands only when the thermostat
  does not report `hvac_action`, nothing for Generic Thermostat.
- **Rooms**: TRV calibration and valve exercise only for TRVs; the fixed
  *nearby* temperature only with that choice; aggregation only with several
  temperature sensors; occupancy time only with occupancy sensors; window
  delays only with window sensors or the temperature-drop detection; the
  Schedule helper fields only for a helper; optimal start / stop limits only
  when turned on.
- **Options**: preheat distances only with a Proximity / travel time sensor,
  cutoff / forecast / season / compensation values only for what is turned
  on, price and PV thresholds only with their sensors, heat source times only
  with a heat source, the fixed duration only for that kind of manual change.

### Schedule format

One profile per line, each slot is `HH:MM preset`:

```
workday: 00:00 sleep, 06:00 home, 22:00 sleep
weekend: 00:00 sleep, 08:00 home, 23:00 sleep
```

Each profile has its **days** and is **on or off** (set in the card, *Schedule*):
all days, workdays, weekend days and holidays, or chosen weekdays. A day uses,
in this order: a calendar event titled with a profile name (also a profile that
is off; an event that covers part of the day selects it for the whole day,
today and the coming days alike, so the plan and the optimal start of tomorrow
match what happens tomorrow) → the active profile of that weekday (e.g. a profile for Wednesday is
above the workday profile on Wednesdays only) → the active profile of workdays
or of weekend days → the active profile of all days. Turning a profile on turns
off the active ones it overlaps (all days overlaps workdays and weekend days;
chosen weekdays overlap when they share a day), so a day never has two.

A day **no active profile covers keeps the frost protection**; the room shows an
alert (*No active schedule profile: …*) and the card warns before turning a
profile on or off leaves such days. Profiles saved before 2.2 keep their days:
`mon` … `sun` for their day, `workday` and `weekend` for their kind of day (for
all days when the other one is missing), and when none of these exists the first
profile is for all days; other profiles start off. The *Profile* select of the
rooms was removed in 2.2.

### How a room decides

Rules are evaluated from the top; the first one that applies wins:

1. Safety (frost protection, maximum temperature) – always applied, also to a
   manual change and in pause (a level above the maximum is sent as the
   maximum); frost protection starts the heat source on its own
2. Pause – only safety is sent (and a TRV boost is taken back to the target)
3. Valve exercise – in every mode, not with a window open
4. Mode Off / Summer / outside the heating season
5. Window open
6. Manual change
7. Vacation (on a day without an active profile: frost protection)
8. Presence: far → `away` (on a day without an active profile: frost
   protection), nearby → `eco` (or a fixed temperature; with *Not above the
   schedule* the lower of it and the schedule)
9. Schedule (optimal start / stop, room occupancy)

Then the adjustments (outdoor cutoff, compensation, tariff, PV, solar gain) and
the safety limits.

## Entities

House: *Mode* (select), *Presence* (home / nearby / far), *Pause* and *Guest
mode* (switches), *Vacation start / end* (datetime), *Heating season*, *Outdoor
cutoff* and *Heat demand* (binary sensors), *Outdoor average*, *Heating time*,
buttons to clear manual changes, clear the vacation and reevaluate.

Room: *Decision* (enum with the reason in the attributes), *Target temperature*,
*Room temperature*, *Next change*, *Heating rate*, *Cooling rate*, *Heating time*, *Heat
demand*, *Window open*, *Manual change*, *Child lock*
(switch), *Clear manual change*, *Reset learning* (buttons) and, for rooms without Generic
Thermostat, the level temperatures (numbers).

## Learning

*The full explanation, with worked examples and simulations: [docs/learning.md](learning.md).*

Each room learns a small physical model of itself, continuously, with and
without heating:

**rise per hour = (heating − curve × outdoor) × q − loss × (room − outdoor) + sun gain × sun**

- **Heating** (`heating_per_hour`): °C per hour the heating adds at full heat,
  at 0 °C outdoors.
- **Weather curve** (`weather_curve`): how many °C per hour more the heating
  adds for each °C colder outdoors: positive for a boiler with outdoor
  compensation, negative for a heat pump that gives less in the cold, 0 for a
  fixed water temperature or an electric heater. Learned once the room has
  heated at outdoor temperatures at least 1 °C apart (standard deviation);
  0 until then and in a house without an outdoor temperature.
- **Heat loss** (`loss_per_hour`): the part of the inside / outside difference
  lost per hour (colder outside, faster).
- **Sun gain** (`sun_gain`): °C per hour the sun adds at a sun signal of 1.
  The signal is sin(sun elevation) × (1 − 0.75 × cloud cover^3.4), from the
  time, the location of Home Assistant and the clouds of the weather entity
  (0 at night, 1 with the sun overhead in a clear sky). Learned only with a
  weather entity and only when clearly seen (at least 5 standard errors from
  0); 0 otherwise. No orientation to set.
- **Inertia** (`inertia_minutes`): q, the part of the heating that reaches the
  room, follows the heating on / off with this delay: the boiler, the water,
  the radiators or the floor warm up first after a start and keep giving heat
  after a stop. It is learned, not set: ten candidates (0 – 240 minutes) are
  learned together and the one that predicts the room best is used.
- Every **30 minutes** of measurements is one equation; heating, curve, loss
  and sun gain are its **least squares** fit. Older stretches count less (half after 7 days),
  so the model follows a room that changes; a stretch far from what the model
  expects (more than 2.5 times the usual difference: a door left open,
  cooking) counts less.
- Not used: stretches with a **window or door sensor** of the room (or a
  linked one) open, with the state of the heat source unknown, during the
  valve exercise, with the outdoor temperature unknown in a house that has
  one, or outside the **cold season** (mode Off or Summer, outside the heating
  season).
- The model is used after **4 hours with heating and 4 without** (usually
  within the first day); until then 60 minutes per degree, no inertia.
- Without an outdoor temperature in the house the loss is learned as a constant
  (°C per hour).
- All predictions (optimal start, time to target, optimal stop, the expected
  temperature at the change) are a minute by minute simulation of the model,
  from the room temperature and the heat reaching the room now.
- The learning of versions before 2.6 (episodes) does not fit the model and is
  discarded: every room learns again after the update.
- **Heating only while the heat source runs.** The learning (heating and
  cooling) and the heating time count a room as heating only while its heat
  source runs: Generic Thermostat heating (`hvac_action`), the relay or the
  on / off thermostat on, and, when a *Heat source* is set in the options
  (the boiler that TRVs and zone valves wait for), only while it runs too. A
  room that asks for heat while the heat source waits for other rooms cools,
  and is learned as heat loss. While the state of the heat source is unknown,
  nothing is learned. With TRVs and no heat source set the demand of the
  TRV is used; that is right for a boiler that runs all season or by outdoor
  compensation. **With TRVs and a boiler started by a thermostat that is not in
  Home Assistant the learning is not reliable: optimal start and stop are not
  recommended.**
- The **heat demand** comes from `hvac_action` (heating). Thermostats that do
  not report it count as heating from the *hysteresis* below their set
  temperature until the hysteresis above it, like a relay (the optimal stop
  uses the hysteresis as its comfort too); the *Hysteresis*
  setting is shown for them (and for thermostats unavailable during the
  setup, which cannot be checked).

The *Heating time* sensors count the same way: a room while its heat
source runs for it, the house while the heat source runs (without one, while
at least one room heats). The chart of the card shows these periods.

The *Heating rate* sensor shows the **minutes per degree** with the heating on,
at the room and outdoor temperatures of now; its attributes show the model
(`heating_per_hour`, `weather_curve`, `loss_per_hour`, `constant_loss`, `inertia_minutes`,
`heat_reaching_now`, `error_per_hour`), the minutes per degree at
−10 / 0 / 10 / 20 °C outdoors and the learning progress (`hours_heating`,
`hours_idle`, `hours_needed`). Optimal start uses the same model. With *Rooms
needed* higher than 1, a room in optimal start waits until enough rooms ask
for heat, so it may reach its target later.

While a room is below its target the card shows the **time to the target**
(e.g. *~35 min*) under the target temperature, from the model and the current
outdoor temperature; until the model is learned it shows *learning…* with
the default used under it (*default 60 min/1°C*).
The *Decision* sensor has it as the `time_to_target` attribute (minutes).

## Optimal stop

**Optimal stop** needs an outdoor temperature (sensor or weather entity of the
house; without one the option is not shown and no optimal stop is made, and
the outdoor values saved before are dropped). It lowers the level before the next colder one as early as the
room can cool and still stay in the comfort of the current level at the
scheduled time. The comfort is the *tolerance*: the *cold tolerance* of Generic
Thermostat, the *hysteresis* for relays, on / off control and thermostats
that do not report `hvac_action`, and the *Optimal stop tolerance* room setting
for the other thermostats (default 0).
Example: home 22 °C until 22:00, tolerance 0.5 °C, 7 °C outside: if the room
falls from 22 to 21.5 °C in 40 minutes, sleep starts at 21:20.

- The *Maximum early stop* room setting is the limit; until the model is
  learned the lower level starts that early.
- How long the room can go without heat is simulated with the learned heat
  loss and inertia (warm radiators still give heat after the stop).
- Once an optimal stop begins it continues until the scheduled time; the rules
  above the schedule can still override it. If the room falls below the
  comfort of the current level before that time (it cooled faster than
  learned), the optimal stop is cancelled: the current level stays until the
  scheduled time and the stop does not start again for that change. If this
  happens often, lower the *Maximum early stop*.
- The card shows the expected temperature at the change (e.g. *~21.5° at
  22:00*), from the model and the outdoor temperature expected until
  then; the *Decision* sensor has it as the `stop_forecast` attribute.
- The *Cooling rate* sensor shows how fast the room falls now without heating
  (empty until learned); its attributes show the loss, the inertia and the
  tolerance.

## Outdoor forecast for optimal start / stop

With a weather entity that has an hourly forecast, the optimal start and the
optimal stop use the **outdoor temperature expected while they run**, not the
one of now. For a start at 05:00 for 07:00, the heating time is the one
simulated with the mean forecast between 05:00 and 07:00; for a stop, the
cooling uses the mean forecast of the stop period. The period depends on that
temperature, so it is worked out again a few times (3 passes) from the period
found before. Each forecast value holds for its hour; until the next forecast
hour the measured outdoor temperature is used.

Without a weather entity, without an hourly forecast or when the forecast
does not reach the change, the outdoor temperature of now is used, as before.
The forecast is read every 30 minutes when the weather entity is set and the
forecast cutoff or a room with optimal start / stop uses it.

The card shows the next optimal start or stop in the room *Details* (e.g.
*Start for preset home (21.0°) at 07:00: begins ~05:10, outdoor forecast 2.4°*, or *Start for temperature 21.0° at …* when the level is sent as a temperature; *running
since …* once it began; *learning…* until something is learned). The
*Decision* sensor has it as the `next_estimate` attribute: `kind`
(`optimal_start` / `optimal_stop`), `at` (the change), `preset`, `minutes`,
`starts_at`, `started_at`, `outdoor`, `outdoor_source` (`forecast` / `now`),
`learned`, `sent_as` (`preset` / `temperature`) and `temperature` (of the level). It is shown only when the option is on for the room and the
next change is warmer (start) or colder (stop); the optimal stop also needs a
known outdoor temperature and not to be cancelled for that change.

## Services

| Service | Description |
| --- | --- |
| `advanced_climate.set_override` | Set a preset or a temperature as a manual change (optional duration) |
| `advanced_climate.clear_override` | Clear manual changes (one room or all) |
| `advanced_climate.set_vacation` | Set or clear the vacation period |
| `advanced_climate.reevaluate` | Evaluate everything now |
| `advanced_climate.set_schedule` | Replace the schedule of a room (text or profiles) |

Rooms are addressed by `room` (name or id) or by any of their entities.

The event `advanced_climate_decision_changed` is fired whenever a room changes
its decision (`room`, `old_rule`, `rule`, `old_target`, `target`, `reason`).

## Lovelace card



The integration adds the card to the dashboard resources automatically
(`/advanced_climate/smart-heating-control-card.js?v=<version>`, updated on every
release, so browsers and the companion app load the new version). With
YAML-mode dashboards add that URL as a `module` resource yourself. The card has
a visual editor. With no options it shows every house and room with every control:

```yaml
type: custom:smart-heating-control-card
```

| Option | Default | Shows |
| --- | --- | --- |
| `title` | Heating | Card title (empty string hides it) |
| `rooms` | all | List of room *Decision* sensors to show |
| `show_house` | `true` | Presence and people (round badges in the colour of where they are), tiles for the outdoor average (over the *Average over* hours), season, heat demand and heating time, mode (Auto / Vacation / Off / Summer), and a row of buttons: Pause and Guests (on / off; guest mode shows a band at the top), Vacation (opens the dates), Reevaluate, Automatic (clears all manual changes) |
| `show_rooms` | `true` | The rooms |
| `show_timeline` | `true` | A **Chart** button in every room that opens, in a window over the dashboard, the chart: 7 days of history and the next 12 hours, opened on the last 24 hours and the next 12: room temperature, the temperature the learned model predicts ahead (the heating switched as the device does: the GT tolerances, the hysteresis, the learned inertia; the target held for thermostats that regulate by themselves), target (colored by level), planned levels and the periods when the room heated. Hover, touch or drag on the chart to read the values (in an opaque box). Zoom with the buttons (1h, 6h, −, +), double-click, pinch or Ctrl + wheel, from 20 minutes up to the 7 days (⤢ goes back); move through the history by dragging the window in the navigation bar under the chart (shown while the mouse is over the chart or a finger is on it) or by scrolling sideways. Under the chart, every legend item hides or shows its series (kept in the browser). Once the room has learned that the sun warms it, the expected sun (`sun_forecast`, 0 to 1) is a faint yellow area in the outdoor band |
| `show_quick_override` | `true` | Set a level or a temperature for a number of hours (empty = the configured rule) |
| `show_levels` | `true` | Level temperatures (rooms without Generic Thermostat, fixed *nearby* temperature) |
| `show_details` | `true` | Room and target temperature, the learning (two progress bars while learning; then one tile each for heating, inertia, weather curve, sun and heat loss), heating time, active adjustments, level temperatures |
| `show_schedule_editor` | `true` | Schedule profiles with an editor: drag the start times on the day bar (5-minute steps), copy a profile over another one |
| `collapsed` | `false` | Rooms start folded (a row with a small arc, the name, the time to target, state icons, the level and the target); tap it to open the room |
| `compact` | `false` | One tile per room (the name, the status icons, arc with the temperature, level, target; under the name the time to target while heating, else the next change) and one row for the house; tap to open |
| `runtime_period` | `day` | Heating time shown for `day`, `week` or `month` (calendar periods, from the long-term statistics; tap the value in the card to change it). The *Heating time* sensors stay cumulative totals |

Every room also shows its decision, a flame (outlined while it asks for heat, full and flickering
while it heats; also on the house and on folded rooms) / window / manual change badges, an arc with the room temperature (empty at the frost protection, full at
the maximum; it only shows the value), an arrow ↑ / ↓ in its opening while the room warms or cools (`temperature_trend`: at least 0.2 °C/h over the last 30 minutes) and the target, the reason, the time to
target, the TRV boost when it is on, what the device itself measures, today's
profile as a bar, and an *Automatic* button (back to automatic) in the row of buttons while there is a manual change. Buttons under the arc open *For a while* (set for
a while; a manual change with an end shows the time it has left), *Schedule* (each profile with its days and an on / off switch; its
days are chosen in the editor), *Chart*, *Levels* (level temperatures) and *Details*, each on its own (several
at once), and a *Lock* button for the child lock of the room.

- **Not heating**: below its target, a room says why it does not heat (within
  the thermostat tolerance or the hysteresis, a minimum on / off time, waiting
  for other rooms or the reference room, the heat source off or unknown, the
  thermostat off). The *Decision* sensor has it as `no_heat_reason`.
- **Warm outside**: while the heating is off because it is warm the house
  shows why, e.g. *Warm outside: on • heating is off until the average falls to
  16°*, *on (forecast) • heating is off: the forecast mean for 3 h is 19.2°*,
  or while the forecast lets the heating run *cancelled (forecast) • it gets cold: the
  forecast mean for 3 h is 12.4°, rooms heat when they need it*; the *Outdoor
  average* sensor has the `cutoff_reason` (`measured`, `forecast_warm`,
  `forecast_cold`) and the `forecast_mean`. It is not shown where the cutoff cannot act: mode
  Off or Summer, outside the heating season and in a pause (in Vacation it
  stays: *away* still heats).
- **Chart**: the planned part follows what will happen: the schedule; a
  manual change for a set time until it ends; a planned vacation until its
  preheating and a calendar event until its end, then the schedule; a window,
  frost protection or the valve exercise only for now (the schedule ahead);
  mode Off / Summer, outside the season, pause, everyone away or nearby, failed
  sensors and warm outside as they are now, for the whole period.
- **Chart**: the outdoor temperature in its own band (measured, then the hourly
  forecast dashed; the cutoff limit as a dotted line) and the next optimal
  start / stop as a shaded period with its start time (never longer than the
  room settings allow); in it the planned target is already the next level, and
  the tooltip shows *Early start* / *Early stop* above it.
- **Pause**: a banner at the top of the card while the house is paused (the
  *Pause* switch stays the only control).
- **Details**, grouped: the alerts of the room and of the house (first, in the
  language of the card); *Temperatures* (room, target, thermostat preset,
  humidity of the air and at the coldest wall with a humidity sensor,
  adjustments, level temperatures); *Schedule* (next optimal start / stop,
  heating time); *Learning* (its state or progress, with a **Reset** button
  that asks to confirm with a second click; once learned the heating: minutes
  per degree now and the inertia; the weather curve; the sun, once seen: its
  gain and what it adds now; the heat loss: how fast the room falls now).
- **Manual change**: where it was made (card / service or on the device), until
  when, *applies after: …* while a higher rule keeps a change from the card off
  the devices, and *comes back after: …* while a higher rule interrupts it.
- The next optimal start / stop is shown only while the room follows its
  schedule; cold rooms are reported only in those rooms.
- **Links**: values, states, badges and details open the more-info dialog of
  their entity.
- **Language**: the reason of the decision and the names of the adjustments are
  shown in the language of the card (the *Decision* sensor has them as
  `reason_key` and `reason_params`; `reason` stays the English text).
