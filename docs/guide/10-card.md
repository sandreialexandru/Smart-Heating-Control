# 10. The card

*[Română](10-card.ro.md) · [Contents](README.md)*

The integration has a Lovelace card with every control: the house, the rooms,
the chart, the editable schedule and the details.

## Adding the card

The integration adds the card to the dashboard resources by itself (the address
`/advanced_climate/smart-heating-control-card.js?v=<version>`, changed with every
version, so the browser and the app load the new one). With YAML-mode
dashboards, add the address yourself as a resource of type `module`.

In a dashboard: **Add card → Smart Heating Control**. It has a visual editor.
Without any option it shows every house and room:

```yaml
type: custom:smart-heating-control-card
```

## Card options

| Option | Default | What it does |
| --- | --- | --- |
| `title` | Heating | The card title (an empty text hides it). |
| `rooms` | all | The list of the room *Decision* sensors to show. |
| `show_house` | `true` | The house part (see below). |
| `show_rooms` | `true` | The rooms. |
| `show_timeline` | `true` | The chart of every room. |
| `show_quick_override` | `true` | *Set for a while*. |
| `show_levels` | `true` | The level temperatures. |
| `show_details` | `true` | The room *Details*. |
| `show_schedule_editor` | `true` | The schedule editor. |
| `collapsed` | `false` | Rooms start folded (one row: a small arc, the name, the time to target, the state icons, the level and the target); tap it to open the room. |
| `compact` | `false` | One tile per room (the name, the state icons, arc with the temperature, level, target) and one row for the house; tap to open. |
| `runtime_period` | `day` | The heating time per `day`, `week` or `month` (calendar periods, from the long-term statistics); also changed by tapping the value in the card. |

**Example**: a card only for the bedroom, folded, without the schedule editor:

```yaml
type: custom:smart-heating-control-card
title: Bedroom
show_house: false
rooms:
  - sensor.bedroom_decision
show_schedule_editor: false
collapsed: true
```

## The house part

- The **flame** next to the presence (see below) while the house asks for heat;
  it flickers while a room of the house really heats.
- **Presence**, with every person as a round badge (the photo or the initial)
  in the colour of where they are: orange home, green nearby, grey far.
- Tiles for **the outdoor average** (over the *Average over* hours), the
  **season**, the **heat demand** and the **heating time**.
- The **mode** (Auto / Vacation / Off / Summer).
- A row of buttons: **Pause** and **Guests** (on / off), **Vacation** (opens
  the vacation dates), **Reevaluate** and **Automatic** (clears all manual
  changes). A button stays coloured while its mode is on.
- **Warm outside**, while the heating is off because it is warm, with the reason
  (measured average or forecast) or when the forecast lets the heating run (see
  [chapter 6](06-weather.md)). Not shown where it cannot act: mode Off or Summer,
  outside the season, in a pause.
- A **pause band** at the top while the house is paused, and a **guest band**
  while guest mode is on (with its end, when it has one).
- In the compact card the folded house row shows the people, the presence
  (Home / Nearby / Away), the mode, the outdoor temperature and a flame while
  there is heat demand.

## A room

The header shows the name, the decision (e.g. *Nearby*, *Schedule*; in the
colour of the level) and the flame, open window and manual change badges.

A **flame** shows the heat everywhere (house, open room, folded row, compact
tile): an outlined circle while there is a demand for heat (*Asks for heat*), a
full one that flickers while the heat source really runs (*Heating*); the words
appear when it is touched or hovered.
 A folded room (row or compact tile) shows only the **level** (e.g. *Eco*) and
small icons: heating (flame), window open, manual change and guest mode while
it is on; the decision appears when the room is open, with the level next to
the arc. Below the
header:

- an **arc** with the room temperature and the target under it; the arc is
  empty at the frost protection and full at the maximum temperature of the room
  (it only shows the temperature, it does not change anything);
- next to it the **reason** (in the card language), the **time to target**
  (e.g. *~35 min*) or, during an optimal stop, the **expected temperature at
  the change** (*~21.5° at 22:00*), guest mode while it is on, the **TRV boost** when it is on for the
  room, and what the device itself measures (rooms with TRVs / climate
  devices);
- **Today**: the profile of the day as a bar from 00 to 24, with the time now.
If a room below its target does not heat, the card says why (*Not heating: …*,
see [chapter 8](08-heat-source-and-energy.md#when-a-room-below-its-target-does-not-heat)).
The *Back to automatic* button clears a manual change.

Under the chart, buttons open the sections **Set for a while**, **Schedule**,
**Levels** and **Details**, each on its own (several can be open at once); an
open section's button stays coloured. The chart and the sections:

### The chart

The last 24 hours and the next 12:

- the room temperature;
- the target, as a step line, coloured by level;
- the planned levels;
- the periods the room heated, in a lane of their own;
- the outdoor temperature in its own band (measured, then the hourly forecast
  dashed) and the cutoff as a dotted line;
- the next optimal start / stop, as a shaded period.

Values are read with the mouse, by tapping or by dragging on the chart. Zoom
with the buttons (1h, 6h, −, +), double click, pinch or Ctrl + wheel, down to 20
minutes; when zoomed, move in time by dragging the window in the bar below the
chart.

The planned part shows what will happen: the schedule; a manual change with a
duration until its end; a planned vacation until the preheating; a calendar
event until its end. A window, frost protection or the valve exercise appear
only for now. Mode Off / Summer, the pause, being away, failed sensors and *Warm
outside* appear as they are now, for the whole period.

### Set for a while

Set a level or a temperature for a number of hours: *[Set] [21] °C for [2] h*.
Empty hours = the configured rule for manual changes. The **Child lock** switch
is here too.

### Levels

The level temperatures (rooms without Generic Thermostat) and the fixed nearby
temperature. Changed right from the card, between the frost protection and the
maximum.

### Schedule

Every profile with its days and an on / off switch:

- **start times** are dragged on the day bar, in 5-minute steps;
- the **days** are chosen in the editor (all, workdays, weekend, chosen days);
- a profile can be **copied** over another;
- the card warns before turning a profile on or off would leave days without a
  profile (which would stay on frost protection).

### Details

In groups:

- the **alerts** of the room and the house, first;
- **Temperatures**: the room, the target, the thermostat preset, the active
  adjustments, the level temperatures;
- **Schedule**: the next optimal start / stop, the heating time;
- **Learning**: heating (episodes, the fixed part and the minutes per degree now)
  and cooling (episodes and how fast the room falls now), each with a **Reset**
  button (with a second click to confirm), then the last heating episode.

With a manual change, the card shows where it was made (card / service or on the
device), until when, *applies after: …* or *returns after: …*.

Almost every value, state or badge opens the entity's more-info dialog when
tapped.

## Language

The card is in English and Romanian, following the Home Assistant language. The
decision reason and the adjustment names are translated (the *Decision* sensor
has them as `reason_key` and `reason_params`; `reason` stays the English text).
