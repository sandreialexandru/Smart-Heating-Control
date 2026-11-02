# Changelog

What changed for the users, version by version. The notes of each GitHub
release (and of each beta pre-release) are taken from here: a beta shows the
*Unreleased* section, a release its own section. Older versions: see the
GitHub releases.

## Unreleased

Alpha: the code split in smaller parts, and a more robust learning of the
heating. Install it only to help test.

### Integration

- **Heating learning: episodes far from the others are left out.** A door left
  open, cooking or a sensor that jumped made one heating much longer (or
  shorter) and pulled the learned time towards it. With at least 8 episodes, an
  episode more than 3.5 times the usual difference from the others is left out
  of the fit (it stays kept and comes back when it fits again). Checked in
  simulations: about the same in steady houses, clearly closer after a change
  of the house. The *Heating rate* sensor shows `episodes_left_out`. The
  cooling learning is unchanged.

- The code of a room is split: what was sent to the devices and their limits
  (`device_echo.py`), open windows (`window.py`), alerts and notifications
  (`notifier.py`); the evaluation of a room runs in named steps.
- The log lines of the notifications come from
  `custom_components.advanced_climate.notifier` (before: `.house`).

### Development

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
