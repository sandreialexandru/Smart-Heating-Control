# Changelog

What changed for the users, version by version. The notes of each GitHub
release (and of each beta pre-release) are taken from here: a beta shows the
*Unreleased* section, a release its own section. Older versions: see the
GitHub releases.

## Unreleased

Beta: relays and on / off thermostats start and stop by the inertia the room
has learned, so slow radiators and floor heating no longer overshoot.

### Integration and card

- 🔥 **Use the learned inertia** (new option of the *On / off control* step,
  on by default): for a relay or a thermostat commanded *On / off*, once the
  room has learned its model, the heating stops a little early when the heat
  still in the radiators or the floor would take the room to the top of the
  hysteresis band, and starts a little early when the room would fall to its
  bottom before the heat arrives. The band and the minimum on / off times stay
  the limits; until the room has learned, only the band decides. In
  simulations the mean distance from the target fell from 0.33 to 0.27 °C
  with cast iron radiators (no more time above target + 0.5 °C, before
  14 %) and from 0.9 to 0.45 °C with floor heating; little changes for
  ordinary radiators. The card says *stopped early: the heat still in the
  radiators takes the room to ~21.3°* while it waits (`no_heat_reason`
  `inertia`). See [the guide](docs/guide/07-optimal-start-stop-and-learning.md#starting-and-stopping-by-the-inertia).
- 🏠 Clearer words for the presence of the house: *the house state is Home*
  instead of *the house is home* (*starea casei e „acasă”* in Romanian), in
  the setup forms and in the guest mode banner of the card, so it is not
  mistaken for the level *home*.

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
