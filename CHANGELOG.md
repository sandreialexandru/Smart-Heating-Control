# Changelog

What changed for the users, version by version. The notes of each GitHub
release (and of each beta pre-release) are taken from here: a beta shows the
*Unreleased* section, a release its own section. Older versions: see the
GitHub releases.

## Unreleased

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
  by the command verification too, instead of being sent the value again and
  again and told as not accepted.

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
