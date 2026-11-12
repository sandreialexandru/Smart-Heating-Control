# Changelog

What changed for the users, version by version. The notes of each GitHub
release (and of each beta pre-release) are taken from here: a beta shows the
*Unreleased* section, a release its own section. Older versions: see the
GitHub releases.

## Unreleased

### ⚠️ Before you update: the *Reference room* is removed

If you set a *Reference room* (*Heat source* options), it is no longer used
after the update: **every room of the heat source can then start the boiler**.
To keep only that room starting it, open every other room (⋮ → *Reconfigure*)
and turn off *Can start the house heat source* on the page after its devices:
those rooms become secondary rooms. They take heat while the boiler runs for
the room that starts it, as with the reference room, and frost protection still
starts the boiler for any room. Secondary rooms also allow more than one room
to start the boiler (the living room and the bedroom, the rest secondary),
which the reference room could not.

### New

- 🏠 **Secondary rooms**: *Can start the house heat source* (per room, on by
  default, asked only for a room that heats from the heat source of the house).
  Off: the room never starts the boiler for itself and does not count for
  *Rooms needed*; its TRVs, valves or relays still open while it is below its
  target, so it takes heat only while the boiler runs for another room
  (enclosed balconies, a guest room, a hall). Frost protection still starts the
  boiler for it. A secondary room is never the cold room of the *Alert when a
  room stays colder than*. They replace the *Reference room* (see above). The card says *a
  secondary room: it takes heat when another room starts the heat source*.
- 🔀 **Heating circuits** (#10): *Circuit relays* (house option, at the heat
  source; empty by default) and a *Circuit* per room on the boiler, for houses
  with several circuits on one boiler, each with its own pump or zone valve
  relay (floor heating and radiators, two floors). The relay of a room's
  circuit is turned on before the boiler starts and off after the boiler
  stops; while another circuit keeps the boiler running, a circuit no longer
  needed closes at once. The boiler is not started for a room whose circuit is
  off or unavailable (the card says *its circuit (…) is off*). A secondary room
  does not open its circuit; frost protection does. A room waiting for *Rooms
  needed* does not open its circuit, and *Keep the last TRV open* closes it
  once the boiler is off (no pump running all night). In a pause the circuit
  relays are not switched, except for frost protection.
- 🚨 **Circuit relay unavailable** (important alert): a circuit relay
  unavailable longer than *Alert when a device is unavailable longer than*.
  The rooms of its circuit get no heat, and with *Rooms needed* above 1 the
  boiler may not start for the other rooms either: repair the relay or change
  the circuits of the house.

- ♨️ **Top up while the boiler runs** (room option, off by default; TRVs or
  relays of the heat source): while the boiler runs for other rooms, a room
  only a little below its target (inside its hysteresis, so not asking yet)
  heats up to its target, so the boiler starts less often. It never starts
  nor holds the boiler, does not count for *Rooms needed*, needs its circuit
  already open, and skips a manual change, an open window, the pause and the
  optimal stop; its learning skips that time. A room kept open (*Keep the
  last TRV open*) that another room releases goes on topped up at once, its
  TRVs not closed in between. Its band is the hysteresis of the room, now
  asked also for a TRV that reports whether it heats when the room is topped
  up; *Keep the last TRV open* is asked only when a room with TRVs heats from
  the heat source. For a secondary room, which never starts the boiler, it
  catches the heat while the boiler runs for other rooms, so the room does not
  stay below its target until the next start.

- 🌍 **German, Dutch, French and Italian** for the integration (settings,
  entities, services, the notifications and the Repairs details) and the card
  (also its editor), besides English and Romanian;
  the documentation stays in English and Romanian. Help review them in #12.
  The READMEs are in the six languages, with the card demo playing on top.

### Fixed

- ⏸️ A change made on the devices in a pause (a heat pump making hot water,
  an automation) is no longer a manual change: in a pause something else
  controls the heating, so when the pause ends the decision is sent again. A
  manual change from the card or a service in a pause is still kept.

- 🕒 The card shows times in the *Time format* of the user profile of Home
  Assistant (24 h, 12 h, of the language or of the system); before, it always
  used the clock of the language, so English showed 12 h even when 24 h was
  set (#11).

## 2.6.4 – 2026-11-11

### New

- 🔓 **Keep the last TRV open** (house option, at the heat source, off by
  default): when no room asks for heat any more, the TRVs of the last room that
  asked stay open (the maximum of the room; On / off: on; Preset: that
  temperature), so the heat left in the boiler and the pipes has a way through,
  as with a bypass, and the valve does not move again during the night (less
  noise, less battery). Until another room asks for heat, a stronger rule takes
  the room (window, manual change, pause, mode, warm outside) or the room itself
  needs heat. The room asks for no heat meanwhile and keeps its target; it may
  get warmer than it, and its learning skips that time. The card shows *Kept
  open for the heat source*. Suggested by a user.
- 🏠 **Mode away** (#9): a fifth mode of the house, *Away*: nobody home, set by
  hand, without people or location tracking. Every room goes to `away` until
  another mode is chosen. Below a manual change of a room and the vacation,
  above the presence and the schedule; guest mode wins over it. One change for
  the whole house, from an automation, a button or a tablet.
- 📅 **Schedule profile select** (#9) for every room with its own schedule: it shows
  the profile chosen last while it is on (a workday profile on a Saturday too),
  and its *Used today* attribute the profile used today; choosing one does what
  turning it on in the card does (the active profiles of the same days go off),
  until another is chosen.
  An easy way to switch e.g. between `workday` and `home_office` from an
  automation. (Not the select of versions before 2.2, which was removed.)
- 🎬 **Scenarios** (#9): *Add scenario*, next to *Add room*: a name and, for every
  room in it, the profiles to turn on (several per room when they cover
  different days; profiles that share days are refused). The house's
  **Scenario** select and the buttons on the card choose one: it does in every
  room what its profile select does, and shows the scenario whose profiles are
  all on. A deleted room leaves the scenarios; a missing profile, overlapping
  days or a room without its own schedule is skipped and told in Repairs.
  When two scenarios match (one part of the other), the one setting more
  profiles is shown. A room that cannot take its profiles is skipped both when
  a scenario is chosen and when the select shows which one is on. A room
  switched to a schedule helper loses its profile select.

### Integration

- 🌡️ **A TRV left in auto is put in heat** (Temperature command): in *auto* a
  TRV follows its own schedule (e.g. the one stored in Zigbee2MQTT) and changes
  its target by itself, which came back as manual changes. Now, once it took
  the temperature sent and stayed in *auto*, it is put in *heat*. A thermostat
  that leaves *auto* by itself when a temperature is set (Netatmo, Tado; on
  Netatmo *heat* is a boost to the maximum) gets no mode command. A device with
  only *auto* stays in it,
  and the Preset command leaves the mode alone. *Auto* chosen by hand is still
  a manual change; with the child lock it is undone at once.
- 🚗 **Travel time for several people**: *Travel time sensors* takes one Waze
  or Google Travel Time sensor per person; the shortest trip counts, so the
  house preheats for whoever is closest to home (an unavailable sensor is left
  out). The trip of about 0 minutes of a person who is home is not someone on
  the way home (with the rule *Everybody* the heating is lowered when another
  person leaves). A single sensor chosen before keeps working. With Proximity,
  its *nearest* sensors already follow the closest person.
- The guide and the option texts now say plainly that a travel time sensor
  only tells how close someone is, not whether they are coming home, and
  recommend Proximity with its direction sensor for preheating on the way
  home.
- 🛠️ **TRV calibration that cannot work is refused** ([#6](https://github.com/sandreialexandru/Smart-Heating-Control/issues/6)):
  *Offset* or *External temperature input* without a room temperature sensor,
  or without the calibration entities, did nothing and said nothing; the room
  form now asks for them. The guide says which entity to pick and that the
  external input must also be selected on the TRV (Sonoff TRVZB:
  *temperature_sensor_select*).

### Card

- 🐞 *Set for a while*: its fields (the temperature and the hours typed) start
  again from the target of the room once the manual change ends, and the field
  lets go of the focus after *Apply* (while a field has it the card is not
  drawn again, so it could keep showing the old state).
- 🎨 **New look, easier to read** (design only, every value and button stays):
  - rooms are neutral: the level colour is only on the arc and its dot, not on
    the whole room; a room is outlined red for an alert that something does not
    work and amber for a warning (its alert icon in the same colour);
  - the arc ends exactly on the target when the room is within 0.3 °C (0.5 °F)
    of it, and the target is a dot on the arc instead of a mark across it;
    bigger, bolder temperatures;
  - the house: its values as a table with thin lines, the chosen mode and
    scenario tinted with the accent colour, the scenarios three per row in the
    same buttons as the modes, the five buttons as 3 + 2 with the icon next to
    the name (above it on a narrow card);
  - a folded room shows on one line the level, its target and the time to the
    target or the next change (*Home 21.0° · Sleep at 22:00*); a compact tile
    shows the target under *Target*, the next change, and the level below the
    arc;
  - an open room: the level and the rule in its header (*Home · Schedule*),
    *Now* and *Next* next to the arc, the buttons three per row (*Automatic*
    first while there is a manual change);
  - **messages in one shape** (a tinted band, the icon in a circle, the subject
    in bold): the pause band with a **Resume** button, the guest band with an
    **End** button, *Warm outside*, *Not heating* and the manual change with
    its end;
  - **alerts in the open room**, with a title, their number and a tap that
    opens the entity (they were the first item of the *Details*).
- ⏱️ **Set for a while with only the hours** ([#7](https://github.com/sandreialexandru/Smart-Heating-Control/issues/7)):
  with the temperature left empty, *Set* changes how long the current manual
  change lasts, from now (its level or temperature stays). Without a manual
  change, or with nothing typed, the card now says what to fill in instead of
  doing nothing.
- 📈 **Smoother chart on a phone**: a line with many points (a sensor that
  reports every minute, over 7 days) is drawn with only the points that change
  its shape, and while a finger or the mouse moves the chart it is drawn once
  per frame. Zooming and moving through the week no longer makes the card hang
  on a slower phone. A pan that ends outside the card (outside the window, for
  example) now ends properly, so the card keeps following Home Assistant. A
  card removed from the page (e.g. while editing the dashboard) no longer stays
  in memory.
- 👥 **Guest band with the Away mode**: it says the away mode is suspended and
  the rooms follow the schedule, as it does for a vacation.
- 📈 **Optimal start / stop in the chart**: its line and shaded band start at
  the level, like the other changes of the plan, instead of at the top of the
  chart, and the "start ~…" label sits right above the line.

### Alerts

- 🔇 **Silent temperature sensor**: a room temperature sensor that stays
  available but sends nothing at all (not even the same value) for 12 hours is
  told: a flat battery or a lost signal often keeps the last value, and the room
  was heated by an old one. A steady temperature is not silence. Off with 0,
  longer for sensors that report only on a change and for a template or group
  sensor (an average), which writes only when one of its sensors changes
  (*Alerts* options). A silent sensor of the room is left out until it reports
  again, like an unavailable one (the other sensors, else the thermostat, else
  eco); the sensor of a Generic Thermostat is watched too, and only told.
- 🧯 **Heating without effect**: a room that heats for 2 hours, clearly below its
  target, while its temperature rises much less than the learned model expects
  (a third of it) is told: a stuck valve, a heat source that does not start, a
  window open without a sensor. Only once the room has learned its model: before
  that, a slow heating (a floor) could not be told from a stuck one. Not with a
  window open, in frost protection or paused; a heating too weak for the cold
  outside expects little and is not told. Once the room warms up the alert
  ends and a new watch starts. Off with 0.
- The mold risk alert says the coldest wall *reached* its humidity (the value
  when the alert started; the card's humidity row shows the value now), and
  that airing and a warmer room lower *the risk*.

### Documentation

- An automation example for a room that is usually 16 °C and 22 °C while it
  is used, with `set_override` and `clear_override`, and why the integration
  has no climate entity of its own.

## 2.6.3 – 2026-11-05

🔒 The diagnostics no longer contain personal data, and HACS is now the first
way to install.

### Integration

- 🔒 **Diagnostics without personal data**: the alert recipients (phones,
  e-mail addresses), the people and where each of them is, the nearby zones,
  the distance and travel-time sensors and the text of the calendar event are
  replaced by `**REDACTED**`, since diagnostics are often attached to public
  issues.
- 🏷️ The integration has a category in Home Assistant (*Climate →
  Thermostats & heating*).

### Documentation

- The install steps start with searching *Smart Heating Control* in HACS (the
  Marketplace from Home Assistant 2026.11); the custom repository is the
  fallback. New buttons in the README add the repository and start the setup.
- A new demo of the card, with invented people.

## 2.6.2 – 2026-11-04

🔥 A thermostat that starts the boiler (Hive, Nest, Tado, Netatmo) can now be
the heat source of TRV rooms: it gets the maximum to start the boiler and an
idle temperature to stop it. 🔌 The room details list every device with its
state. 🏷️ Clearer setup choices, and a configurator that starts with what
heats your home. 🐛 Fixes in the card: the schedule editor in a dark theme,
typing a time, and the *Set for a while* fields on a narrow card.

### Integration

- 🔥 **Start and stop the source by its temperature** ([#6](https://github.com/sandreialexandru/Smart-Heating-Control/issues/6)):
  a thermostat as the heat source of the house (Hive, Nest, Tado, Netatmo, a
  Generic Thermostat) starts the boiler only by its own target and sensor, so
  switched to *heat* with a low target it never fired it. Now, like a TRV
  heated by the room sensors, it stays in its heat mode and gets the *Maximum temperature* of the
  house to start (not above its own maximum) and the *Frost protection* of the
  house to stop (not below its minimum): the boiler fires when the rooms ask,
  and the thermostat still protects against frost if Home Assistant stops. A
  target set on it by hand is taken back. New option *Start and stop the source by its temperature*
  (Heat source and heat demand → Heat source), **on by default**; off keeps the
  old behaviour (only its mode, heat / off). A thermostat without a target
  temperature is still switched by its mode.
- 🌡️ **Heat source idle temperature** (optional, with *Start and stop the source by its temperature*): what the
  thermostat source gets while no room asks, instead of the frost protection
  (e.g. 17.5 °C for a hallway thermostat that also heats radiators without
  TRVs). Below the maximum of the house.

### Setup

- 🏷️ **Clearer choices for the heating of the whole house.** *Other thermostats
  / TRVs* is now **Another thermostat for the whole home**, and *No heating
  devices yet* is now **Each room heats separately (TRVs, heaters, AC)**: a
  house with TRVs on the radiators picks the second one and adds its rooms.
  Only the labels and the explanations change; existing houses are not
  affected. The guide has a new section, *Which setup for my house?*, with
  every kind of home, and the configurator a new case for a thermostat that
  starts the boiler.
- 🏷️ **No more options called boost.** For the whole-house zone, *Boost TRV
  temperature while heating* is now **Heat by the room sensors** (also for a
  thermostat, not only for TRVs), with its page *Heating by the room sensors*.
  For a room it is now **Heat by the room sensor**, with its page *Heating by
  the room sensor* (was *TRV boost*); *Boost temperature* is now **Temperature
  while heating** in both. For the heat source the new option is **Start and
  stop the source by its temperature**. The explanation of each says when to
  choose the other one. The card shows *By the room sensor* instead of *TRV
  boost*. The explanations of the zone and of the room options now say what
  the devices get while heating: the *Temperature while heating*, by default
  the maximum temperature of the house. Only the labels and the explanations
  change; the settings are kept.

### Card

- 🔌 **Devices in the Details**: every entity of the room (thermostats,
  relays, temperature and humidity sensors, windows, occupancy, calibration)
  with its role and its state now; an unavailable, unknown or missing one is
  marked, a tap opens it. New `devices` attribute of the *Decision* sensor.
- 🐛 **Schedule editor in a dark theme**: the list of levels, the time
  fields and the time shown while dragging a handle were white on white.
  They now use the opaque background of the card, and the native pickers
  follow the dark or light theme.
- 🐛 **Typing a time in the schedule editor**: the field lost the focus after
  the first digit. Now the whole time can be typed; the bar follows at once,
  the rows are sorted again when the field is left, and Save right after
  typing still saves the new time.
- 🐛 **Set for a while on a narrow card** ([#6](https://github.com/sandreialexandru/Smart-Heating-Control/issues/6)):
  the temperature and duration fields cut their values (*17.* for 17.5,
  *aut* for auto) under their up / down arrows. The arrows are gone (the
  value is typed, or changed with the arrow keys) and the fields are a little
  wider. The *Set* button looks like the other buttons of the card.


### Configurator

- 🏠 **Your home** first: one choice (a Generic Thermostat, a smart
  thermostat, TRVs with a boiler relay, TRVs with a thermostat that starts the
  boiler, TRVs on only some radiators, heaters or air conditioners per room…)
  fills in the matching answers on the next pages; each one can still be
  changed.
- *Heated by* is no longer preselected: a page waits until it is answered.
  Its explanation is shorter, with the details under *Why?*.
- The summary flags a thermostat or relay used twice (in two rooms, or in a
  room and as the heat source).
- On a phone the progress shows the current part and step instead of cut
  labels.
### Development

- 🧪 Tests for what mutation testing found unchecked: the coldest wall below
  0 °C outside and the mold thresholds, distances between coordinates and a
  zone without them, far → nearby as an arrival, times like 24:00 or 06:60,
  the start of a schedule day that does not begin at midnight, the highest
  sun of the day in Bucharest in June and November, the clouds of every
  weather condition, and the renaming of a whole-house zone named like the
  house.
- 🧪 Tests from the first full mutation run (Python 62.8 %, card 30.2 % of
  the mutants noticed): the limit of ±3 °C on the adjustments, the levels
  exactly at the maximum or the frost protection, the edges of the band with
  the learned inertia, no optimal stop when it is off and the ones exactly on
  time, the texts in °F, which stretches the learning uses, the time to the
  target and the expected temperature during an optimal stop, every attribute
  of the *Decision* sensor, a preset or an hvac mode set by hand coming back
  after a window, the calibration within the range of its number, the valve
  exercise (5 minutes, after a manual change, only on its day), the alert for
  rooms that stay cold; in the card the history, the prediction and the
  tooltip values, and every button (mode, pause, guests, buttons of the
  house and the room, a temperature for a while, vacation dates, the
  heating time period, the schedule editor and its profiles).
- 🧬 The card's mutation jobs are split by how many mutants their lines have
  (12 jobs of about 400), not by equal lines (from 74 to 919).

## 2.6.1 – 2026-11-04

🔥 Relays, on / off thermostats and TRVs with the boost now start and stop by
the inertia the room has learned, so slow heating no longer overshoots. 📈 The
predicted temperature of the chart follows how each device really switches.
🖼️ The card is easier to read: an arrow shows whether a room warms or cools,
the learning shows as tiles and the chart legend hides or shows each line.
🧪 Many more tests, now also of the card, and a weekly mutation testing.

### 🧠 After the update

- ✅ **The learning is kept**: rooms that learned with 2.6.0 go on from there.
- 🔥 *Use the learned inertia* is **on by default** for relays, on / off
  thermostats and the TRV boost: it acts once the room has learned its model,
  only inside the hysteresis band. It can be turned off in the room options.

### Card

- ↕️ **Warming or cooling**: an arrow in the opening of the arc (also on the
  folded rows and compact tiles) while the room warms (↑) or cools (↓) by at
  least 0.2 °C per hour over the last 30 minutes, that is one step of a usual
  sensor (0.1 °C) in 30 minutes. New `temperature_trend` attribute of the
  *Decision* sensor (1, −1, 0).
- 🧠 **Learning in Details**: while learning, two bars (*with heating 2 of
  4 h*, *without heating 1 of 4 h*); once learned, one tile each for the
  heating, the inertia, the weather curve, the sun and the heat loss.
- 📈 **Chart**: tapping a legend item hides or shows its series (kept in the
  browser); the expected sun is a faint yellow area in the outdoor band, once
  the room has learned that the sun warms it.
- ⏳ A manual change with an end shows the time it has left (*until 15:10 ·
  1 h 30 min left*).
- 🏠 The house tiles are two by two on a narrow card and in one row on a wide
  one; the room buttons have short labels (*For a while*, *Levels*).
- 🔲 The line of a compact tile: the time to the target while the room heats,
  else the next change (the manual change and the open window are shown by
  their icons).

### Integration and card

- 🐛 A level that the thermostat has no preset for and whose temperature is
  unknown (e.g. a Generic Thermostat without that preset) was taken as already
  reached: nothing was sent and the *preset missing* alert never came. Now the
  alert comes.
- 🔥 **Use the learned inertia** (new option of the *On / off control* and
  *TRV boost* steps, on by default): for a relay, a thermostat commanded
  *On / off* or TRVs with the boost, once the room has learned its model, the
  heating stops a little early when the heat already given would take the
  room to the top of the hysteresis band, and starts a little early when the
  room would fall to its bottom before the heat arrives. The band and the
  minimum on / off times stay the limits; until the room has learned, only
  the band decides. In simulations the mean distance from the target fell
  from 0.33 to 0.27 °C with cast iron radiators on a relay (no more time
  above target + 0.5 °C, before 14 %), from 0.9 to 0.45 °C with floor
  heating, and from 0.28 to about 0.24 °C with TRVs with the boost (time
  above target + 0.5 °C from 5 – 7 % to almost 0). The card says *stopped
  early: the heat already given still takes the room to ~21.3°* while it
  waits (`no_heat_reason` `inertia`). See [the guide](docs/guide/07-optimal-start-stop-and-learning.md#starting-and-stopping-by-the-inertia).
- 📈 **The predicted temperature follows the device.** The chart switches the
  heating ahead as the device does: Generic Thermostat by its cold and hot
  tolerance, relays, on / off control and the TRV boost by the hysteresis (and
  the learned inertia), thermostats without `hvac_action` by the hysteresis.
  The line now goes up and down around the target as the room does, instead
  of staying flat with many short heating periods. Thermostats and TRVs that
  regulate by themselves, and a Generic Thermostat set up in YAML (its
  tolerances cannot be read), still hold the target; their heating ahead is
  one period. The *Heating rate* sensor has the `band` in its `model`.
- 🏠 Clearer words for the presence of the house: *the house state is Home*
  instead of *the house is home* (*starea casei e „acasă”* in Romanian), in
  the setup forms and in the guest mode banner of the card, so it is not
  mistaken for the level *home*.

### Development

- 🧪 The tests of the card are in the repository (`tests/card`, 55 checks in
  Chromium with a fake Home Assistant) and run in CI on every push.
- 📊 CI measures the test coverage (on the newest Home Assistant) and shows it
  in the summary of the run; it must stay at least 93 %.
- 🧪 New tests of the rooms as they are used: Generic Thermostat, thermostats
  with their own presets or on / off, TRVs in summer, a relay turned on by
  hand around an open window, the child lock, manual changes for the whole
  house or until the next reevaluation, the valve exercise, a Schedule helper,
  a calendar event, a thermostat as the heat source, tariff and solar
  adjustments, unavailable devices, low batteries, offset calibration, the
  buttons and the services (coverage from 89 % to 93 % or more).
- 🧬 Mutation testing (`tests/mutation`): about 3,700 small changes of the
  Python code, and those of the card with Stryker, each run against the
  tests, to find the mistakes no test would notice. A workflow runs it every
  week in the night to Sunday (and by hand from the Actions tab) and writes a
  report of the survivors.
- 🧩 The room controller is split by job into `room.py` (state, schedule,
  decision) and `room_devices.py`, `room_override.py`, `room_optimal.py`,
  `room_alerts.py`, `room_status.py`. Nothing changes in what it does.

### Documentation

- 📖 A new README that shows what the integration does, with a video of the
  card (40 s, played in the page) and new pictures. The technical
  details that were in it are in the new [Reference](docs/reference.md).
  The same pictures, the GIF and the video are in the card chapter of the
  [guide](docs/guide/10-card.md).
- 🏠 The same wording for the presence of the house in the guide, the
  specification and the configurator.
- 🧭 The configurator explains *Use the learned inertia*, the learned sun and the external temperature
  written again every 30 minutes.

## 2.6.0 – 2026-11-03

🧠 Every room now learns a physical model of itself and uses it for optimal
start and stop. 🌦️ The model follows the weather curve of the boiler and ☀️
the sun. 🍄 A new alert warns about mold risk. 📈 The chart keeps 7 days of
history and draws the temperature the model expects.

### 🧠 About the learning: what to expect after the update

- 🔄 **Coming from 2.5.0 or earlier, the learning starts again.** The old
  heating and cooling episodes do not fit the new model and are discarded.
  The learning of the 2.6.0 alphas (from a4) and betas is kept.
- ⏱️ **About a day until the first model.** A room needs 4 hours with
  heating and 4 hours without, as 8 stretches of 30 minutes each. In a
  lived-in room these usually come within the first day. Until then it uses
  60 minutes per degree, no inertia and the longest optimal stop you set. The
  card shows the progress, e.g. *learning… 2 of 4 h with heating, 1 of 4 h
  without*.
- 📐 **What is learned, with nothing to set:**
  - how fast the heating warms the room;
  - the 🌡️ **weather curve**: how much more a boiler with outdoor compensation
    gives in the cold, or less for a heat pump; 0 when there is none;
  - how fast the room loses heat to the outdoors;
  - the ⏳ **inertia**: how slowly the radiators or a floor heating react;
  - ☀️ how much the **sun** warms the room.
- 🌡️ **The weather curve** is learned once the room has heated at outdoor
  temperatures with a standard deviation of at least 1 °C, for example heating
  by day and by night with the outdoors ±1.5 °C apart. Until then it is 0.
- ☀️ **The sun** is learned only in a house with a weather entity, because it
  needs the clouds. It is used once clearly seen: at least 5 standard errors
  from 0, after enough sun. For example, 12 stretches of 30 minutes at a sun
  signal of 0.3 is enough (12 × 0.3² = 1.08, above the threshold of 1). A room
  without sun keeps 0. In the card *Details* the *Sun* row appears only from
  then on. It starts from 0 also for those coming from a 2.6.0 beta.
- 📉 **It keeps adapting.** Older measurements count half after 7 days, so the
  model follows a house that changes (new radiators, another boiler curve, the
  season). Measurements far from the model, like a door left open or cooking,
  count less. *Reset learning* starts from zero at once.
- 📊 **How good it is**, in simulations of fictional rooms, not measurements:
  - with a weather curve, the mean error of the optimal start fell from
    16 – 42 to 4 – 8 minutes;
  - in a room with a south window, the mean error of a 3 hour prediction fell
    from 1.1 – 1.2 °C to 0.2 °C by day and from 0.9 – 1.0 °C to under
    0.1 °C at night.

  The details, assumptions and every number are in
  [How the integration learns](https://github.com/sandreialexandru/Smart-Heating-Control/blob/main/docs/learning.md).

### 🏠 Integration

- 🧠 **New learning: a physical model of every room.** Instead of heating and
  cooling episodes, each room learns, continuously and with or without
  heating, how fast its heating warms it, how that changes with the outdoor
  temperature (the **weather curve** of a boiler with outdoor compensation, or
  a heat pump that gives less in the cold; 0 when there is none), how fast it
  loses heat to the outdoors and its **thermal inertia** (how slowly the heating reacts: the
  boiler, the radiators or a floor heating warm up first after a start and keep
  giving heat after a stop). The inertia is learned, nothing has to be set.
  Optimal start, optimal stop, the time to target and the expected temperature
  at the change are a minute by minute simulation of that model. Older
  measurements count less (half after 7 days), so the model follows a house
  that changes; measurements far from the model (a door left open, cooking)
  count less. In simulations of houses with a weather curve the mean error of
  the optimal start fell from 16 – 42 to 4 – 8 minutes. See
  [How the integration learns](docs/learning.md).
- ☀️ **The sun is learned too** (in a house with a weather entity): how many °C
  per hour the sun adds to each room, from the sun height (calculated from the
  time and the location of Home Assistant) and the clouds of the weather
  entity (`cloud_coverage`, else its condition). It is used only once clearly
  seen (at least 5 standard errors from 0); a room without sun keeps 0. No new
  setting, no orientation to give. The predictions count the sun of each
  minute with the clouds of the hourly forecast: a sunny morning needs a
  shorter optimal start, a sunny afternoon allows a longer optimal stop. In
  simulations of a room with a south window the mean error of a 3 hour
  prediction fell from 1.1 – 1.2 °C to 0.2 °C by day and from 0.9 – 1.0 °C to
  under 0.1 °C at night. The *Solar gain* room setting is unchanged. The *Heating
  rate* sensor shows `sun_gain`; the *Outdoor average* sensor `sun_forecast`.
- 🔄 **The learning starts again after the update.** The saved episodes do not
  fit the model and are discarded. Until a room has seen 4 hours with heating
  and 4 without (usually within the first day) the default is used: 60 minutes
  per degree, no inertia, the longest optimal stop.
- **One *Reset learning* button per room** replaces *Reset heating learning*
  and *Reset cooling learning*; the old buttons are removed by themselves.
- The *Heating rate* and *Cooling rate* sensors show the model (heating, heat
  loss, inertia, the heat reaching the room now, the learning progress); the
  episode attributes are gone. The card shows *45 min/°C now · inertia 30 min*,
  or the learning progress.
- **The *Thermostat tolerance* field is removed** (thermostats commanded by
  temperature or preset): it only marked where a heating episode started, and
  the new learning has no episodes. The *Thermostat* page now appears only for
  a thermostat that does not report `hvac_action`, to ask for its hysteresis.
- 🚶 **Back from eco after presence of** (new room option, with occupancy
  sensors; 0 minutes by default, as before, at most 60): a room in eco for no occupancy
  follows its schedule again only after someone has been present without a
  break for that long, so a short visit does not start the heating
  ([#4](https://github.com/sandreialexandru/Smart-Heating-Control/issues/4)).
- 🍄 **Mold risk alert** (a warning) for a room with the new optional *Humidity
  sensor* (rooms step *Sensors*): the humidity at the coldest wall, from the
  room temperature and humidity and the outdoor temperature (DIN 4108-2
  method); 80 % or more for an hour raises it, below 75 % it ends. Without a
  humidity sensor or without an outdoor temperature (sensor or weather entity)
  no mold alert is sent; a humidity sensor that measures outdoors (on the
  weather entity's device, or on the outdoor sensor's device when it has no
  other temperature sensor) is refused. The *Decision* sensor shows `surface_humidity`.
- 🐛 **Fix: TRV calibration with the external temperature**
  ([#5](https://github.com/sandreialexandru/Smart-Heating-Control/issues/5)).
  A change of one step was sometimes not written (in floating point
  19.7 − 19.6 is 0.0999…, below the step of 0.1), and an unchanged value was
  never written again, so a Sonoff TRVZB went back to its own sensor after
  about 120 minutes. A one step change is now written, and the external
  temperature is written again every 30 minutes even when unchanged.
- 🐛 **Fix:** after saving the options, the old settings could still wake up
  once (at the next schedule change) and send a command; it no longer does.

- The code of a room is split: what was sent to the devices and their limits
  (`device_echo.py`), open windows (`window.py`), alerts and notifications
  (`notifier.py`); the evaluation of a room runs in named steps.
- The log lines of the notifications come from
  `custom_components.advanced_climate.notifier` (before: `.house`).

### 🖼️ Card

- **The chart opens in a window** over the dashboard, larger, instead of inside
  the room (one room at a time; closes with ✕, a click outside or Esc).
  The window is always opaque, also with themes whose cards are transparent.
  It stays open and in place while the values update, and a click inside it
  (on its margin too) does not close it. Leaving the dashboard closes it (it
  does not pop up again on return); a phone turned keeps it open.
- 📈 **The chart keeps 7 days of history**: it opens on the last 24 hours and the
  next 12, zooms out up to the 7 days and moves through them with the
  navigation bar (shown only while the mouse is over the chart or a finger is
  on it) or a sideways scroll. The values under the pointer are in an opaque
  box. After the first load only what is new is fetched.
- 🔮 **Predicted temperature** in the chart (dotted), once the room has learned:
  the learned model simulated along the planned target, with the forecast and
  the expected sun; the
  periods it heats are shown lighter in the heating lane.
- A fine line at every midnight in the chart, between the days.
- 💧 **A drop icon** (*Mold risk*) on the room, folded or open and in compact
  mode, while its mold risk alert is active.
- **Details**: the state of the learning (with its usual error), the weather
  curve, the learned sun once seen (*+1.50 °C/h with the sun overhead in a clear
  sky · now +0.60 °C/h*), and with a humidity sensor the humidity of the air and at the coldest
  wall (marked *mold risk* from 80 %).

### 🛠️ Development

- CI checks the formatting (`ruff format`) and the types of the plain modules
  (mypy); new unit tests for the split parts and a test of the window timings
  of the guide.

## 2.5.0 – 2026-11-02

### Integration

- Notifications by how much an alert matters: *Important alerts to*,
  *Warnings to* and *Information to* (phones, email or any notify service or
  entity, several each). The texts are in the language of Home Assistant
  (Romanian or English), with the room. Quiet hours send only the important
  alerts; the others follow when they end, if they still apply. The end of an
  alert (a device back, a window closed, a battery replaced) is told too, and on
  a phone it replaces the alert. The start and the end of the automatic vacation
  are sent as information. A *Notification service* of an earlier version keeps
  working until the *Alerts* options are saved again; the form offers it as the
  recipient.
- Email: the addresses can be written after the notify service
  (`notify.me_gmail_com: ana@example.com, ion@example.com`) and go as its
  target, so the Google Mail integration sends the alerts too.
  A recipient written with capitals (e.g. *Notify.* from a phone keyboard) is
  accepted.
- More messages, only for rare events: a room that falls below the frost
  protection temperature (warning, its end told too), a pause left on (warning
  after *Remind when the pause lasts longer than*, 12 h by default, then once a
  day), and as information the start and end of the heating season, a planned
  vacation that starts, the preheating before the return and guest mode that
  ends by itself.
- A room can be set not to heat from the heat source of the house (*Heats from
  the heat source of the house*, in the room's devices step, shown only when the
  house has a heat source; on by default). A room with its own heat (electric
  heater, heat pump, air conditioner) then no longer starts the boiler, does not
  count for the rooms needed, and its heating and learning follow its own device.
- The whole-house heating choice explains better when to pick *No heating
  devices yet*: every room has its own heating (TRVs, electric heaters, a heat
  pump or air conditioner, underfloor heating).
- Rooms with a Generic Thermostat no longer ask for temperature sensors: GT
  keeps the temperature by the sensor of its own configuration, and the
  integration uses that one too, so the card and the learning match what GT does.

  > **Warning – Generic Thermostat rooms with temperature sensors chosen in the
  > integration:** they keep working until the room form is saved again; saving
  > it removes them. To keep another sensor, set it as the sensor of the Generic
  > Thermostat itself.
- The options show only what can apply to the house:
  - *Heat source and heat demand* is no longer in the menu when the *Whole house*
    zone is a Generic Thermostat or a relay;
  - *Alert when a room stays colder than* moved to *Alerts*, shown only with
    more than one room (its value is kept);
  - *Manual change applies to* is shown only with more than one room, the
    *Automatic vacation* only when the house has people;
  - a room's *nearby* choices are shown only when the house has nearby zones.
  A value hidden this way stays saved and works again when it can apply.

  > **Warning – houses with a Generic Thermostat or a relay on the whole house
  > that still have a *Heat source*:** it now goes away when the *Heating of the
  > whole house* is saved (no longer from the heat source form, which is gone
  > for these houses). Check before saving that the Generic Thermostat (or the
  > relay) is the one that starts the boiler.
- The interactive configurator follows the latest forms: the heat source is not
  offered for a Generic Thermostat or relay on the whole house, the colder-room
  alert under Alerts, the room option for the heat source of the house, no temperature sensors for Generic
  Thermostat rooms, the bypass warning and the clearer whole-house choice; its
  Romanian text is impersonal.
- The diagnostics list every kept heating episode (`episode_list`) and cooling
  episode (`cooling_episode_list`) of each room, not only their number.

## 2.4.3 – 2026-10-31

### Integration

- The minimum on / off times are 0 by default (no wait), for the heat source
  and for the relays of the rooms: the heat follows the demand at once, so the
  heat source stops as soon as the last room reached its target. Houses and
  rooms that saved their own values keep them; a few minutes still protect a
  boiler without its own anti-cycling or spare a mechanical relay.
- The *Heat source* is no longer offered when the *Whole house* zone is a Generic
  Thermostat or a relay: that zone already starts the boiler. The form then
  shows only the alert for a room that stays colder.

  > **Warning – houses with a Generic Thermostat or a relay on the whole house:**
  > if a *Heat source* was chosen there, it keeps working until the options form
  > *Heat source and heat demand* is saved again; saving it removes the heat
  > source. Check that the Generic Thermostat (or the relay) is the one that
  > starts the boiler before you save, since nothing else will start it then.
- The heat source form warns that with TRVs on every radiator the installation
  needs a bypass or a radiator without a TRV (also in the guide, chapter 8).

## 2.4.2 – 2026-10-30

### Integration

- A person who turns a TRV down during a boost (after the TRV showed the boost
  value) is a manual change again, not the TRV's own maximum: no false alert,
  and the next boosts are no longer cut to that value for a day. The same for
  turning it up a little during frost protection. A limit is learned only
  within 5 minutes of the command and only while the TRV has not shown the value
  sent.

## 2.4.1 – 2026-10-30

### Card

- The room buttons wrap into even rows (one row up to five buttons) instead of
  breaking their words when there are six.

### Integration

- Guest mode wins over every vacation (the vacation mode, the dates or the
  automatic one): while it is on, the rooms follow the schedule; the vacation
  goes on when it is turned off. The card band says the vacation is suspended.
  The automatic vacation comes back at once after the guests, unless one of the
  people is near or home then.
- A TRV with its own Max / Min temperature on the device (narrower than its
  entity, e.g. 25 °C on a Tuya TRV) is no longer taken for a manual change when it
  holds its limit after a boost, the valve exercise or frost protection; the next
  commands stay within it and an alert tells it (tried again after a day).
  A TRV that already held its limit (so it reports nothing new) is recognised
  by the command verification too (after the value was sent again), instead of
  being told as not accepted.

## 2.4.0 – 2026-10-29

### Card

- The room buttons (Set for a while, Schedule, Chart, Levels, Details, Lock and
  Automatic while there is a manual change) are right under the arc, with the
  sections they open; the day bar comes after them.
- The chart opens with its own **Chart** button and its history is loaded only
  then; while it is closed the next change is shown next to the arc.
- The house has the same title in every view: the house icon and name, the
  presence (Home / Nearby / Away) and the flame.
- The arc ends exactly at the room temperature (it went a little past the target
  mark when both were equal); the target mark is thinner.
- An alert icon on the folded and the open room while the room has alerts; its
  title lists them, the Details explain them.
- A new schedule profile keeps only letters, digits, spaces, "_" and "-" in its
  name (what the integration accepts), instead of being refused at saving.

### Integration

- Window detection from the temperature: a jump of the room temperature because
  a sensor stopped or came back (or the device sensor took over) no longer
  counts as an open window; a real drop still does.
- Window detection from the temperature keeps the readings of the whole window
  (e.g. 30 minutes) however often the temperature is read; before, a busy house
  could shorten a long window and miss a slow drop.
- In a room without a room sensor, a TRV that stops reporting no longer counts
  as an open window (the temperature of the other TRVs is not a drop).
- A thermostat that reports an older command late (e.g. 21 °C after 12 °C was
  already sent), or that shows the new value and then reports the old one once
  more (e.g. Tuya TS0601), is no longer taken for a manual change: the values
  sent in the last 5 minutes and the temperature or preset shown before each
  command are recognised until the device has shown the last value for 1 minute. A change
  from the card keeps its duration.
- A level named like the key of another level (e.g. Eco named "home") no longer
  turns the schedule around; the room settings refuse such a name.
- The heat source and the house checks (rooms left cold, weather alerts) are
  guarded on their own: an error of one does not skip the others.

### Releases

- Beta versions are published as pre-releases (e.g. `2.3.30b1`): HACS shows them
  only to those who turned on the beta versions for this repository.
- The release notes are written here, as text, instead of the list of commits.
