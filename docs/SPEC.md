# Smart Heating Control – specification

**English** | [Română](SPEC.ro.md)

*Step-by-step guide for every setting: [guide/README.md](guide/README.md).*

Smart Heating Control computes **one target per room** from the schedule, presence,
windows, weather and manual changes, and applies it to the heating devices.
Everything is configured from the UI (config flow, options flow and room
subentries); no YAML is needed.

The integration is built around **Generic Thermostat (GT)**: it uses the same
preset names and never changes how GT works – it only selects the preset that
fits. Rooms heated by other thermostats, TRVs or plain relays are supported too.

## Principles

- **One decision per room, recalculated continuously.** Any relevant change
  (person, zone, window, time, weather) triggers a reevaluation, not only the
  start of a time slot. A periodic check (default every 5 minutes) catches
  anything missed.
- **A fixed and explicit rule hierarchy** (section 12), so two rules never fight.
- **Every decision has a visible reason**: the *Decision* sensor of the room
  shows the winning rule and a text explaining it.
- **State survives restarts**: manual changes, vacation, learned heating and cooling.
- **Safe defaults**: without extra configuration the integration can neither let
  the house freeze nor overheat it.
- **Advanced options are optional** and stay off until enabled.

## 1. What is controlled

The unit is the **room** (heating zone). The configuration has two levels: one
entry for the **house** (people, zones, global mode, shared settings) and one
**room subentry** per room (devices, sensors, windows, schedule).

| Option | Default | Description |
| --- | --- | --- |
| Temperature unit | unit of Home Assistant | °C or °F per house, chosen first at setup and changed with *Reconfigure* (the values are converted). Inside, everything is kept in °C; each device is read and commanded in its own unit, so the house unit may differ from the one of Home Assistant |
| Heated by | Generic Thermostat | Generic Thermostat, other `climate` entities (TRVs, thermostats) or `switch` / `input_boolean` relays |
| Command (other thermostats) | temperature | Temperature / preset / on-off via `hvac_mode` |
| TRV boost | off | Temperature command only. The heat demand comes from the room sensors (required) with the hysteresis; while it lasts the TRVs get the boost temperature (empty = maximum of the house; never below the target, never above the maximum of the house or of the TRVs), otherwise the target. Applies to every heat demand, frost protection included; not to the valve exercise or to devices turned off. A pause takes a boost left on the TRVs back to the target once |
| External temperature sensors | none | Used instead of the device sensor; several sensors → mean, minimum or median |
| TRV calibration | off | Offset calculated from the external sensor, or the external temperature written to the TRV input (in the unit of the TRV entity) |
| Thermostat tolerance | GT: cold tolerance; relays: hysteresis; others: 0 | How far below the target the thermostat lets the room fall before heating; heating episodes are learned from this far below the target |
| Heat demand | `hvac_action` | Thermostats without `hvac_action` are handled like relays: they count as heating from the hysteresis below their set temperature to the hysteresis above it, and the optimal stop uses the hysteresis as its comfort; the hysteresis is asked for when a thermostat does not report `hvac_action` or is unavailable during the setup |
| Heat source | none | The boiler (or the relay that starts the heat source) when the rooms cannot start it themselves (TRVs, zone valves); switched on when enough rooms ask for heat (with minimum on/off times). A `climate` heat source runs while its `hvac_action` is heating, when it reports one |
| Heating | heat source running | A room heats (learning, heating time) only while its heat source runs: GT heating, the relay or on / off thermostat on, and the *Heat source* too when set; with TRVs and no heat source, the demand of the TRV. While the heat source state is unknown no episode is used. With TRVs and a boiler started by a thermostat outside Home Assistant the learning is not reliable |
| Rooms needed | 1 | Number of rooms that must ask for heat to start the heat source. It has priority over optimal start: with more than 1, a room in optimal start waits until enough rooms ask for heat, so it may reach its target later |
| Reference room | none | Only this room decides for the heat source |
| Room difference alert | off | Alert when a room stays colder than the target while others are warm |

## 2. Levels (presets)

The integration uses the **Generic Thermostat preset names**, each with a fixed
role in the rules:

| Preset | Applied automatically when |
| --- | --- |
| `home` | Someone is home and the schedule says `home` |
| `sleep` | Sleep slot of the schedule with someone home |
| `eco` | Nobody home, at least one person in the nearby zone |
| `away` | Everyone outside the nearby zones, or vacation |
| `comfort`, `activity` | No automatic role in the rules |
| `min_temp` of GT (not a preset) | Frost protection: window open, mode Off |

All GT presets remain available as presets: they can be chosen manually or used
in the schedule. The integration only selects the preset; it does not change any
functionality of GT.

For *nearby* the default is the `eco` preset. Instead of the preset a **fixed
temperature** can be configured; the integration sends it to GT, which switches
to preset `none` by itself. With *Not above the schedule* (per room, unchecked
by default) the lower of the nearby level / temperature and the schedule
applies, so being in town at night does not heat more than being home.

Without Generic Thermostat the roles in the rules stay the same and the room
settings depend on the command:

| Command | Levels in the room settings |
| --- | --- |
| Preset | Each level picks one of the **thermostat's own presets** (read from the device). The thermostat keeps that temperature; the integration learns it for display. A level without a preset is reached by sending its temperature. |
| Temperature | Configurable **names** and a **temperature** per level; the temperature is sent to the device. |
| On / off (`hvac_mode`) | Configurable **names** and a **temperature** per level; the device presets are not used, the integration switches it on and off around the level temperature. |

The temperatures set in the room settings can also be changed later from the
card or the number entities (one per level the integration controls). They are
set between the frost protection and the maximum temperature of the house.

## 3. Schedule

The schedule says which level is wanted while someone is home. Presence and the
other rules can lower it but never raise it.

```
workday: 00:00 sleep, 06:00 home, 22:00 sleep
weekend: 00:00 sleep, 08:00 home, 23:00 sleep
fri:     00:00 sleep, 06:00 home, 23:30 sleep
home_office: 00:00 sleep, 07:00 comfort, 23:00 sleep
```

| Option | Default | Description |
| --- | --- | --- |
| Profiles | workday + weekend | Any names; each with its days (all, workdays, weekend days and holidays, or chosen weekdays) and on / off, set in the card. Active profiles do not overlap (chosen weekdays only among themselves) |
| Profile selection | auto | Calendar event → active profile of the weekday → active profile of workdays / weekend days → active profile of all days → none: frost protection, with an alert |
| Workdays | Workday integration | Holidays come from the Workday integration (including future days) |
| Calendar | none | An event titled with a profile name selects that profile for the whole schedule day it covers part of (today and the next 7 days alike; read from the start of today, every hour and when the calendar changes); a preset name selects that level while the event runs |
| Schedule source | internal | Internal schedule or an existing HA **Schedule helper** |
| Optimal start | off | Start heating early so the next level is reached on time |
| Learned heating | on with optimal start | Minutes per room = fixed part + degrees × (minutes per degree at 0 °C + change per degree outdoors × outdoor), the least squares fit of the last 25 small (< 1 °C) and 25 large (≥ 1 °C) heating episodes, each with its degrees, minutes and mean outdoor temperature. The fixed part needs episodes at least 1 °C apart in size, the outdoor term episodes at least 1 °C apart outdoors; impossible terms (negative fixed part or minutes) are set to zero and the rest is fitted again; unseen outdoor temperatures extend the line (the maximum early start still limits it). An episode starts at least the thermostat tolerance below the target and is used when the heat demand lasted at least 10 minutes and the temperature rose, however little; episodes with an open window sensor are not used. Until the first episode 60 minutes per degree. Learning saved before 2.0 (a rate per episode) is discarded. Heating and cooling are learned in the cold season only (not in mode Off or Summer, nor outside the season) |
| Maximum early start | 2 h (10 min – 24 h) | Limit of the optimal start. Once started, the optimal start continues until the change (the other rules can still override it) |
| Learned cooling | on with optimal stop | One coefficient per room of the inside / outside difference (mean of the last 30 episodes). An episode lasts from the end to the start of the heat demand and is used when it lasted at least 10 minutes and the temperature fell, however little; episodes with an open window sensor are not used |
| Optimal stop tolerance | GT: cold tolerance; relays, TRV boost and thermostats without `hvac_action`: hysteresis; others: 0 | The comfort kept by the optimal stop: how far below the current level the room may fall before the change |
| Maximum early stop | 30 min (5 min – 24 h) | Limit of the optimal stop; until the cooling is learned the lower level starts this early |
| Outdoor temperature of the optimal start / stop | automatic | With an hourly forecast of the weather entity: the time-weighted mean forecast of the period the start / stop runs (each value holds for its hour, the measured value until the next forecast hour), worked out again 3 times from the period found before; without a forecast covering the period: the outdoor temperature of now. The forecast is read every 30 minutes when the forecast cutoff or a room with optimal start / stop uses it |
| Optimal stop | off | Needs an outdoor temperature (sensor or weather; without one the saved outdoor values are dropped). Lower the level as early as the room can cool and stay in the comfort of the current level (the tolerance above); the cooling is learned from periods without heat demand, as a coefficient of the inside / outside difference; limited by a maximum; continues once started, cancelled (current level until the change) if the room falls below the comfort |
| Day boundary | 00:00 | For night shifts: when the schedule day changes |

## 4. Presence

The house presence has three states: **home / nearby / far**, plus optional
per-room occupancy.

| Option | Default | Description |
| --- | --- | --- |
| People | – | Which `person` entities count |
| Home rule | at least one | "At least one" or "everybody" home |
| Nearby zones | none | Zones (e.g. Bucharest) where the house is *nearby* instead of *far* |
| Zones inside a nearby zone | automatic | A zone in the city (e.g. Office) also counts as nearby, computed from coordinates |
| Proximity | off | Distance and direction; preheat only when someone is coming home |
| Arrival threshold | 10 km or 20 min | Distance or travel time from which preheating starts |
| Departure delay | 10 min | Wait before the house counts as empty |
| Arrival delay | 0 min | Wait before someone counts as arrived |
| Presence sensors | none | mmWave / motion / switches keep the house *home* |
| Room occupancy | off | The room goes to eco after X minutes without occupancy |
| Guest mode | off | Forces *home*, with optional automatic expiry |

`unknown` / `unavailable` person states are treated as "no change", never as a
departure.

## 5. Windows and doors

An open window lowers the room to frost protection or turns it off; when it
closes the room returns to whatever the rules say at that moment.

| Option | Default | Description |
| --- | --- | --- |
| Window sensors | none | Any of them open = open |
| Open delay | 60 s | Ignore very short airing |
| Close delay | 30 s | Wait before resuming |
| Action | frost protection | Frost protection or off |
| Detect from temperature | off | A quick drop (e.g. 1 °C in 3 min) counts as an open window |
| Windows of other rooms | none | e.g. the balcony door of the living room also affects the hall |
| Alert after | 30 min | Notification while heating is relevant |
| Ignore above outdoor temperature | off | In spring/autumn airing does not lower heating |

## 6. Weather and season

Weather can turn heating off or adjust the target; it can never raise it above
what the schedule asks.

| Option | Default | Description |
| --- | --- | --- |
| Outdoor temperature | `weather` | Local sensor or the weather entity. The cutoff, the automatic season, the compensation and ignoring windows need one (the options form refuses them otherwise; saved without one: alert, and the automatic season counts as always on); no temperature from any configured source (sensor, else the weather temperature) for longer than the alert time: alert |
| Cutoff | 18 °C | Heating off when the average is at or above it; on again at or below cutoff − hysteresis (hysteresis 1 °C) |
| Average over | 6 h (at least 1 h) | Average, not the instantaneous value. Also how long an outdoor value stays valid: with no new value for this time the outdoor temperature is unknown (no cutoff, compensation or ignored windows, no learning episodes, no optimal stop) until the sensor or weather reports again |
| Heating season | always | Always, between dates (e.g. 10-15 → 04-15) or automatic |
| Automatic season | 3 days / 15 °C | Starts/ends after X consecutive days below/above the threshold (the X days before today; each day a time-weighted mean of the time covered, added up as the values come and saved, so a restart does not change it; a day without any value breaks the run) |
| Outdoor compensation | off | Small adjustment, e.g. +0.5 °C below −5 °C |
| Forecast | off | Needs a weather entity and the cutoff. Only the mean forecast of the next forecast hours (each value for its hour, the measured value until the next forecast hour), never a single hour. Heating off by the measured average and that mean at or below the resume temperature: the heating may run (rooms heat when they need it); above it: the heating stays off. Heating running and that mean at or above the cutoff: the heating is turned off earlier and stays off until the mean falls to the resume temperature (same hysteresis as the measured average; the state is saved) |
| Solar gain per room | off | Negative offset while the sun shines (needs the weather entity) |

## 7. Manual changes

A change made by a person (app, TRV, HA) is respected for a defined time; then
the integration takes control again.

| Option | Default | Description |
| --- | --- | --- |
| Detection | on | Changes made by the integration are told apart by their context, or because the device only reports the values the integration sent |
| Duration | configurable, universal | One rule for every manual change, including turning GT off: **fixed duration** (X hours) or **until the next reevaluation** triggered by a change (slot, presence, window, mode). The periodic check does not end it |
| Scope | room | Whole house only when rooms have their own valves |
| Pause | – | Switch: no commands at all, no TRV calibration (frost protection and the maximum temperature still apply) |
| Child lock | off | Manual changes are reverted immediately |
| Clear | – | Button per room and for the house |
| Card / service | – | A level or temperature set from the card or with `set_override` is sent only while the manual change applies (not in a pause, with a window open, in mode Off / Summer…), and stays on the devices for its whole time |
| After an interruption | – | When a higher rule changed the devices during a manual change (window, frost protection, mode), the manual value is set again once it ends: the card / service value, or what the person set on the device (mode, preset, temperature, relay on / off). The maximum temperature limits it for good |

## 8. Global modes

One select for the house: **Auto / Vacation / Off / Summer**.

| Mode | What it does | Options |
| --- | --- | --- |
| Auto | Schedule + presence + every rule | – |
| Vacation | `away` in every room | Start and end dates (only an end: from now), preheat X hours before the end (default 4 h; the schedule applies even while everyone is far), automatic vacation after Y hours far away (the preheating before the end of a planned vacation wins over it; it ends when someone is arriving and comes back only after another Y hours far away) |
| Off | Frost protection only (`min_temp` of GT) | – |
| Summer | Heating off | Automatic switch with the season (section 6) |

## 9. Energy and heat source protection

| Option | Default | Description |
| --- | --- | --- |
| Hysteresis | 0.3 °C | Relays, on / off control and thermostats without `hvac_action` (not with GT, which has its own tolerances) |
| Minimum on / off time | 5 / 5 min | Relays only (not with GT); counted from the last switch, also one made by hand; the room is evaluated again when it ends (also for the heat source of the house); inside the hysteresis band the relay keeps its real state; a manual value set again after a window also waits for it |
| Dynamic tariff | off | Lower by X °C above a price, preheat below a price |
| PV surplus | off | Raise by X °C with surplus |
| Statistics | on | Heating hours per room and for the house |

## 10. Safety and resilience

| Option | Default | Description |
| --- | --- | --- |
| Frost protection | on | Lower limit, also in Off and Pause (GT: its minimum temperature); once heating, it continues until the device stops asking for heat. A room in frost protection starts the heat source on its own (no rooms needed, no reference room, also while paused). TRV rooms with room sensors: decided from the room sensor (below frost protection until it + hysteresis), the TRVs get the maximum of the house (or the boost temperature) meanwhile |
| Maximum temperature | 25 °C | Upper limit of every target: a level above it is sent as the maximum, a set point above it (manual change, pause) is lowered to it, a relay or hvac_mode room is turned off while the room is at it or above (manual change, pause; it is not turned on again to heat back up), the service and the card stay within it, and a thermostat that rounds to its step gets the step just below the maximum. Shown as the rule *Maximum temperature* |
| Sensor unavailable | device sensor | External sensor down → device sensor → eco (never above the schedule: a lower level, e.g. away, stays), with alert |
| Device unavailable | alert after 15 min | The other rooms keep working; also for the heat source (then not even frost protection can heat) |
| Command verification | on | Retry once after 2 min, then alert |
| Valve exercise | off | Weekly full opening of the TRVs, in every mode (also in summer and outside the season); a pause, a manual change or an open window postpones it to later the same day; it does not ask for heat and its period is not learned |
| Low battery | alert below 20 % | TRVs and sensors of the room |
| Restart | restore | Manual changes, vacation and learned data are kept; the heating episode in progress too (it goes on if the room still heats after the restart, otherwise it is dropped) |
| Periodic reevaluation | 5 min | In addition to events |
| Invalid values | refused | A sensor value, attribute or saved value that is not a number (`nan`, `inf`) counts as unavailable or is dropped; a temperature sensor without a unit is read in the unit of the house. `set_override` refuses a temperature that is not a number and a duration outside 0.25–72 h (as in the form); the vacation entities refuse an end not after the start; a malformed `set_schedule` profile gives a clear error |
| One owner per device | form check | A thermostat or relay is controlled by one room only (in every house); the heat source is not a room device; the relay of a Generic Thermostat used by a room is neither a room device nor a heat source; the outdoor sensor is not a room temperature sensor. Sensors may be shared |
| Rooms needed | ≤ rooms | The form allows at most the number of rooms of the house; an alert when rooms are removed and fewer remain |
| Time | UTC inside | Durations (heating time, learning, manual changes, delays, vacation preheat) are real time, also across a DST change; the schedule, workdays and daily means use the local time. A schedule slot in the hour repeated at the end of summer time applies once (at its first occurrence); one in the hour skipped in spring starts when that hour ends (e.g. 03:30 → 04:00). |

## 11. Visibility

| Entity / interface | Shows |
| --- | --- |
| `sensor.<room>_decision` | Winning rule (enum) + reason, preset, schedule, next change, plan, time to the target, expected temperature at the change during an optimal stop, whether an optimal stop was cancelled, the next optimal start / stop (`next_estimate`: kind, change, preset, sent as preset or temperature, level temperature, minutes, start, outdoor temperature and its source, learned) |
| `sensor.<room>_target_temperature`, `sensor.<room>_room_temperature` | Target and room temperature, in the unit of the house |
| `sensor.<room>_heating_rate` | Learned minutes per degree for the current outdoor temperature (fixed part, estimates, episodes) |
| `sensor.<room>_cooling_rate` | How fast the room falls now without heating (coefficient, episodes, tolerance) |
| `sensor.<room>_heating_time`, `sensor.<house>_heating_time` (`…_heating_runtime` when created before 2.3.18) | Total heating time (total increasing): a room while its heat source runs, the house while the heat source runs (without one, while a room heats) |
| `sensor.<room>_next_change` | Next scheduled change |
| `binary_sensor.<room>_heat_demand` | Whether the room asks for heat; the `heating` attribute tells if its heat source runs |
| `sensor.<house>_presence` | home / nearby / far |
| `select.<house>_mode` | Global mode |
| `number.*`, `button.*`, `switch.*` | Levels, clear overrides, reset heating / cooling learning (per room), guest mode, pause, child lock |
| Services | `set_override`, `clear_override`, `set_vacation`, `reevaluate`, `set_schedule` |
| Events | `advanced_climate_decision_changed` with room, old and new target and reason |
| Lovelace card | Room state and decision; 24 h chart (temperature, target, heating) with the next 12 h planned and zoom to the minute (a bar under the zoomed chart moves it; dragging on the chart reads the values); schedule editable by dragging (5 minutes), copy of a day; time to the target or, during an optimal stop, the expected temperature at the change; the next optimal start / stop in the room details; chart with a degree grid, the target as a step line, the heating in its own lane, the outdoor temperature (measured and forecast) in its own band and the next optimal start / stop; why a room below its target does not heat; why the heating is off because it is warm (measured average or forecast mean), or that the forecast lets it run; a pause banner; learning status and alerts in the details; the origin of a manual change; links to the entities; heating time per day / week / month; compact mode (one tile per room); the room temperature as an arc between the frost protection and the maximum (display only); today's profile as a bar; buttons that open the room sections independently; house buttons (Pause and Guests switch directly, with a band at the top while on; Vacation opens its dates); the decision next to the room name and the level apart, in every view |
| Diagnostics | Configuration and the last 100 decisions |

## 12. Rule hierarchy

Rules are evaluated from the top down for every room; the first rule that
applies sets the level.

1. **Safety** – frost protection and maximum temperature, always applied: also
   to a manual change, in pause, to the `set_override` service and the card,
   and frost protection starts the heat source on its own
2. **Pause**
3. **Valve exercise** – in every mode, not with a window open
4. **Mode Off / Summer / out of season**
5. **Window open**
6. **Manual change**
7. **Vacation** (a day without an active profile: frost protection, above `away`)
8. **Presence** – far → `away` (a day without an active profile: frost protection), nearby → `eco` (or the fixed temperature; with *Not above the schedule* the lower of it and the schedule), home → schedule
9. **Schedule** – with optimal start / stop and room occupancy

Final adjustments (outdoor cutoff, compensation, tariff, PV, solar gain) only
correct a heating target by a few tenths of a degree (never a frost protection:
mode Off or Summer, outside the season, a window, a day without a profile), and
the result always goes through the safety limits. The reason shown by the decision sensor is the
winning rule.

## 13. Glossary RO → EN

| Română | English |
| --- | --- |
| Casă / cameră | house / room |
| Program / profil / interval | schedule / profile / time slot |
| Prezență: acasă / aproape / departe | presence: home / nearby / far |
| Zonă apropiată | nearby zone |
| Fereastră deschisă | window open |
| Intervenție manuală | manual override |
| Durată fixă / până la următoarea reevaluare | fixed duration / until next reevaluation |
| Mod global: Auto / Vacanță / Oprit / Vară | global mode: auto / vacation / off / summer |
| Pauză | pause |
| Antiîngheț | frost protection |
| Pornire / oprire anticipată | optimal start / optimal stop |
| Sezon de încălzire | heating season |
| Prag de oprire (temperatură exterioară) | outdoor cutoff |
| Câștig solar | solar gain |
| Viteză de încălzire / răcire | heating rate / cooling rate |
| Toleranța termostatului | thermostat tolerance |
| Toleranța opririi anticipate | optimal stop tolerance |
| Unitatea de temperatură | temperature unit |
| Sursa de căldură | heat source |
| Cererea către centrală | heat demand |
| Mod oaspeți | guest mode |
| Motiv curent | decision reason |
| Mișcarea robinetelor | valve exercise |
| Reevaluare | reevaluation |
