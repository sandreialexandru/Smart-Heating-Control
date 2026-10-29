# 3. Rooms

*[Română](03-camere.ro.md) · [Contents](README.md)*

A **room** is a heating zone with its devices. It is added on the integration
page with **Add room** and changed with **⋮ → Reconfigure room**. The *Whole
house* zone (made with the house) is changed the same way.

The form has several steps. Steps and fields that do not apply to your kind of
heating are skipped.

## Which kind of heating to pick

| You have… | Pick under *Heated by* | Command |
| --- | --- | --- |
| A **Generic Thermostat** for the room | Generic Thermostat | – (GT keeps its presets, the integration only picks them) |
| **TRVs** (thermostatic radiator valves) | Other thermostats / TRVs | usually *Temperature* |
| A **smart thermostat** with its own presets | Other thermostats / TRVs | *Preset* |
| A thermostat you only want to turn on / off | Other thermostats / TRVs | *On / off (hvac mode)* |
| A **relay** (smart plug, Shelly / Sonoff relay, `input_boolean`) that turns a heater or boiler on directly | Switch (relay) | – (the integration switches it itself) |

## Step 1: Room

| Field | What to do |
| --- | --- |
| **Name** | The name of the room, e.g. "Bedroom". |
| **Area** | Optional, links the room to a Home Assistant area. |
| **Heated by** | The kind of heating, from the table above. |

## Step 2: Devices

| Field | What to do |
| --- | --- |
| **Thermostats** | The thermostats of the room (for Generic Thermostat and other thermostats / TRVs). Several thermostats in one room all get the same command, e.g. two TRVs on two radiators of the living room. |
| **Switches (relays)** | The relays that heat the room (only for *Switch*). |
| **Command** | Only for other thermostats / TRVs, see below. |
| **Boost TRV temperature while heating** | Only for other thermostats / TRVs with the *Temperature* command (otherwise *The TRV boost works only with the Temperature command*), see step 3. |

At least one device must be picked (otherwise *Select at least one device*).

**A device is controlled by one room only.** The form refuses a thermostat or a
relay that another room already controls (in any house), the heat source of a
house, and the relay of a Generic Thermostat used by another room (also the
relay of a Generic Thermostat you pick here, if it is used elsewhere). Two
integrations, or two rooms, sending opposite commands to the same device would
fight. Sensors (temperature, window, occupancy) may be shared by several rooms.

### Command for other thermostats

| Command | What the integration does | Suits |
| --- | --- | --- |
| **Temperature** | Sends the temperature of every level (e.g. 21 °C for `home`). The thermostat keeps it. | Most TRVs |
| **Preset** | Every level uses a preset of the thermostat, with the temperature set in the thermostat. | Thermostats with well set presets |
| **On / off (hvac mode)** | The thermostat is only turned on and off; the integration keeps the temperature, from the room sensor. | Simple thermostats or ones with a badly placed sensor |

## Step 3: the command settings

### Relay or *On / off*: **On / off control**

| Field | Default | What it does |
| --- | --- | --- |
| Hysteresis | 0.3 °C (0.1 – 3) | Starts below target − hysteresis, stops above target + hysteresis. With a chosen target of 21 °C: starts at 20.7 °C, stops at 21.3 °C. |
| Minimum on time | 5 min (0 – 60) | The shortest time it stays on. 0 for heaters that do not mind short cycles. |
| Minimum off time | 5 min (0 – 60) | The shortest pause between two starts. |

The minimum time counts from the last switch, **also one made by hand**. When it
ends, the room is checked again at once. Inside the hysteresis band (in the
example between 20.7 and 21.3 °C) the relay stays as it is: if you turned it
off, it stays off.

### *Temperature* or *Preset*: **Thermostat**

| Field | Default | What it does |
| --- | --- | --- |
| Thermostat tolerance | 0 (0 – 2 °C) | How far below the target the thermostat lets the room fall before heating (its own tolerance). The heating is learned from rises that start at least this far below the target. If unsure, leave 0. |
| Hysteresis | 0.3 °C | Only when the thermostat does not report when it heats (`hvac_action`) or is unavailable during the setup. It then counts as heating from hysteresis below its set temperature to hysteresis above it, like a relay. Used for the heat demand, the boiler, the heating time, the learning and as the tolerance of the optimal stop. |

### *Temperature* with boost: **TRV boost**

With the boost the *Thermostat* page is not shown: the thermostat tolerance and
the optimal stop tolerance are not used, the hysteresis takes their place.

A TRV measures the temperature next to the radiator, which is warmer than the
room, so it may close before the room is warm. With *Boost TRV temperature while
heating* the room sensor decides instead, and the TRV is kept open while the room
needs heat:

- the room **asks for heat** at target − hysteresis and stops at target +
  hysteresis, measured by the **room temperature sensors** (required, see step 5);
- while it asks for heat, the TRVs get the **Boost temperature**; the rest of
  the time they get the **target**, so the TRV closes by itself and keeps the
  room even when Home Assistant is down.

| Field | Default | What it does |
| --- | --- | --- |
| Boost temperature | empty = the maximum temperature of the house | Sent to the TRVs while the room asks for heat. Between the frost protection and the maximum of the house; never below the target and never above the maximum of the TRVs. |
| Hysteresis | 0.3 °C (0.1 – 3) | The band of the heat demand, as for relays. |

**Example** (the values chosen in the form): target 20 °C, hysteresis 0.2 °C,
maximum of the house 25 °C, boost temperature empty. At 20 − 0.2 = 19.8 °C in
the room the TRVs get 25 °C; at 20 + 0.2 = 20.2 °C they get 20 °C again. Between
19.8 and 20.2 °C it stays as it was.

The boost applies to every heat demand, also to frost protection. Without the
boost, a TRV room with temperature sensors is boosted for frost protection only
(see [chapter 9](09-windows-manual-safety.md#frost-protection)). With the
valve exercise, a window open with *Turn off*, or mode Off with devices that
turn off, there is no boost. In a **pause** nothing is sent, except that a boost
left on the TRVs is taken back to the target once, so no TRV stays boosted while
nothing regulates it. The card shows it in *Details* as *TRV boost*.

### Generic Thermostat

No step: Generic Thermostat has its own tolerances (`cold_tolerance`,
`hot_tolerance`) and its own minimum cycle.

## Step 4: Levels

| Field | What to do |
| --- | --- |
| **When nobody is home but someone is nearby** | *Eco preset* (uses the `eco` level) or *Fixed temperature* (a temperature chosen on the next page; with Generic Thermostat the preset becomes `none`). |
| **Not above the schedule** | Unchecked by default. Checked: when the schedule is lower than the nearby level or temperature, the schedule applies. Example with chosen values: nearby 20 °C, the schedule asks for `sleep` 18 °C at night → 18 °C. Unchecked → 20 °C. |

The rest of the step depends on the kind:

- **Generic Thermostat**: nothing else. The level temperatures are the ones set
  in Generic Thermostat (`home_temp`, `sleep_temp`, `eco_temp`, `away_temp`,
  `comfort_temp`, `activity_temp`).
- **Command *Preset***: for every level you pick the **thermostat preset** (the
  list shows the presets found on the device) and a **temperature**. The
  thermostat keeps the preset's temperature. If the thermostat has no preset
  for a level, leave the field empty and the level's temperature is sent.
- **Command *Temperature*, *On / off* and relays**: for every level a **name**
  (how it appears in the schedule and the card; you may keep the default name)
  and a **temperature**. A name cannot be the internal name of another level
  (`home`, `sleep`, `eco`, `away`, `comfort`, `activity`, `frost`): the schedule
  uses those names, so it would read the wrong level.

Default temperatures: `home` 21, `sleep` 18, `eco` 17, `away` 12, `comfort` 22,
`activity` 20 °C. They can be between the frost protection and the maximum
temperature of the house and can be changed any time from the card or from the
room's number entities. Two levels cannot have the same name. A name may use any
letters (also with accents), digits, spaces, `_` and `-`, but not `,` `:` or `#`,
which the schedule format uses.

**Names example.** For an office you may call `home` "Work" and `sleep`
"Closed". In the schedule you then write `07:00 Work, 19:00 Closed`, and the
roles stay the same: "Work" is still the `home` level.

### The **Nearby** page (only with *Fixed temperature*)

| Field | Default | What it does |
| --- | --- | --- |
| Fixed temperature when nearby | 17 °C | Sent while nobody is home and someone is nearby. Can be changed from the card. |

## Step 5: Sensors

| Field | What to do |
| --- | --- |
| **Temperature sensors** | Sensors in the room, used instead of the thermostat sensor (more accurate when the thermostat sits next to the radiator). Empty = the thermostat sensor. **Required for relays**, which have no sensor (otherwise *Relays need a temperature sensor of the room*), and for the TRV boost (otherwise *The TRV boost needs a temperature sensor of the room*). The outdoor sensor of a house is refused. A sensor that reports no unit is read in the unit of the house. |
| **TRV calibration** | Only for TRVs and only with a room sensor. *Offset*: corrects the TRV sensor. *External temperature input*: writes the room temperature into the TRV (if it has that input). *Off* otherwise. |
| **Occupancy sensors** | Motion / presence sensors of the room: when the room is empty for a while it goes to `eco` even if someone is home. Empty for rooms that should only follow the schedule. |

The second form, **Sensors: details**, appears only when needed:

| Field | Default | When | What it does |
| --- | --- | --- | --- |
| Several sensors | Average | with several temperature sensors | *Average*, *Minimum* (the coldest) or *Median*. |
| Calibration entities | – | with calibration | The TRV number entities (offset or external temperature). The integration finds the TRV of every entity by itself (same device). |
| Eco after no occupancy for | 30 min (1 – 720) | with occupancy sensors | How long the room must be empty before `eco`. |

**Calibration example** (chosen values). The TRV says 22 °C (it sits next to the
radiator), the wall sensor says 20.5 °C, and the TRV offset is 0 now. With
*Offset*, the integration adds the difference 20.5 − 22 = −1.5 °C to the current
offset, so it writes −1.5 °C, and the TRV "sees" the real room temperature. The
offset is adjusted at most every 10 minutes, the external temperature at most
every 5 minutes, and nothing in a pause.

**Room occupancy.** It works only when the schedule asks for a level warmer than
`eco`: an empty room never gets warmer than the schedule would make it.

## Step 6: Windows and doors

| Field | What to do |
| --- | --- |
| **Window sensors** | The windows and doors of the room. Any open = window open. |
| **Windows of other rooms** | Windows that also cool this room, e.g. the living room balcony door for the hall. |
| **Detect open windows from the temperature** | A quick temperature drop counts as an open window for 15 minutes. Useful for rooms without window sensors. |

The second form, **Windows: delays and action**:

| Field | Default | What it does |
| --- | --- | --- |
| Open delay | 60 s (0 – 3600) | How long a window must be open before the heating reacts. Shorter airing is ignored. |
| Close delay | 30 s (0 – 3600) | How long to wait after closing before heating again. |
| When a window is open | Frost protection | *Frost protection* keeps the minimum temperature. *Turn off* stops the heating. |
| Temperature drop | 1 °C (0.2 – 5) | Only with detection from the temperature: the drop that counts as an open window. |
| Within | 3 min (1 – 30) | The time in which the drop must happen. |

Example with the default detection values: if the temperature drops by 1 °C
within 3 minutes, the room uses the open-window action for 15 minutes.

Everything about windows: [chapter 9](09-windows-manual-safety.md).

## Step 7: Schedule

| Field | What to do |
| --- | --- |
| **Schedule source** | *Internal schedule* (written here or edited from the card) or *Schedule helper* (a Home Assistant Schedule helper decides between two levels). |
| **Optimal start** | Starts heating earlier so the next level is reached on time. The heating speed is learned in a few days. |
| **Optimal stop** | Lowers the level earlier before a colder one, as early as the room can cool without leaving the comfort of the current level. Appears only when the house options have an outdoor temperature (sensor or weather). |

Then, depending on the source:

- **Schedule** (internal): the schedule text, one profile per line, e.g.
  `workday: 00:00 sleep, 06:00 home, 22:00 sleep`. Easier to edit from the
  card. A wrong schedule gives the error *Invalid schedule*.
- **Schedule helper**: *Schedule helper* (the `schedule` entity), *Level while
  the helper is on* (`home` by default) and *Level while the helper is off*
  (`sleep` by default).

With optimal start or stop on, **Optimal start / stop** appears:

| Field | Default | What it does |
| --- | --- | --- |
| Maximum early start | 120 min (10 – 1440, i.e. up to 24 h) | The optimal start never begins earlier than this. |
| Maximum early stop | 30 min (5 – 1440, i.e. up to 24 h) | The optimal stop never begins earlier than this. Until the cooling is learned, the lower level starts exactly this early. |
| Optimal stop tolerance | 0 (0 – 2 °C) | Only for thermostats that report `hvac_action`, are not Generic Thermostat and do not use the TRV boost: how far below the current level the room may fall before the change. 0 = the room must not fall below the level, so it stops early only when warmer than the level. |

Details: [chapter 4](04-schedule.md) and
[chapter 7](07-optimal-start-stop-and-learning.md).

## Step 8: Extras

| Field | When | What it does |
| --- | --- | --- |
| **Solar gain** | only with a weather entity in the house options | A negative value (e.g. −1 °C, between −3 and 0) that lowers the target while the sun shines, for rooms that get warm from the sun. 0 = off. |
| **Valve exercise** | only for TRVs not commanded *On / off* | Opens the TRVs fully for 5 minutes once a week, against limescale, in every mode (also in summer). |

With valve exercise on, **Valve exercise** appears: *Day* (Sunday by default)
and *Time* (10:00 by default; best when no heat is needed).

## Complete examples

### Bedroom with Generic Thermostat

1. *Room*: name "Bedroom", *Heated by* Generic Thermostat.
2. *Devices*: `climate.bedroom` (the Generic Thermostat entity).
3. *Levels*: *Eco preset*.
4. *Sensors*: nothing (GT already has its sensor).
5. *Windows*: the bedroom window sensor.
6. *Schedule*: internal, with optimal start.

The temperatures are changed in the Generic Thermostat settings (its presets).

### Living room with two TRVs

1. *Heated by* Other thermostats / TRVs.
2. *Devices*: the two TRVs, *Command* Temperature.
3. *Thermostat*: tolerance 0.
4. *Levels*: the temperatures (e.g. `home` 21.5 °C).
5. *Sensors*: a wall sensor, *TRV calibration* Offset, then in the details the
   offset entities of the two TRVs.
6. *Windows*: the balcony door.
7. *Schedule*: internal, with optimal start and stop.
8. *Extras*: valve exercise on Sunday at 10:00.

With TRVs the boiler must know when to start: in the house options, *Heat
source*, pick the boiler or its relay (see
[chapter 8](08-heat-source-and-energy.md)).

### Bathroom with an electric heater on a smart plug

1. *Heated by* Switch (relay).
2. *Devices*: `switch.bathroom_plug`.
3. *On / off control*: hysteresis 0.3 °C, minimum times 0 (an electric heater
   does not need them).
4. *Levels*: e.g. `home` 23 °C.
5. *Sensors*: the bathroom temperature sensor (required).

### Smart thermostat with its own presets

1. *Heated by* Other thermostats / TRVs, *Command* Preset.
2. *Levels*: for `home` the thermostat preset "Comfort", for `sleep` the preset
   "Night", for `away` the preset "Away"; what is missing stays empty and is
   sent as a temperature.

## The entities of a room

Every room gets a device with its entities: the decision, the target, the room
temperature, the next change, the learning, the heating time, the window, the
heat demand, the manual change, the child lock and, for rooms without Generic
Thermostat, the level temperatures. The full list:
[chapter 11](11-entities-and-services.md).
