# 11. Entities, services and automations

*[Română](11-entitati-si-servicii.ro.md) · [Contents](README.md)*

Entity names are given as in the English interface. IDs start with the name of
the house or the room, e.g. `sensor.bedroom_decision`.

## House entities

| Entity | Shows / does |
| --- | --- |
| *Mode* (select) | The mode: `auto`, `vacation`, `off`, `summer`. |
| *Presence* (sensor) | `home`, `nearby`, `far`; attributes: the people, `arriving`, `guest_mode`, `vacation_active`, `vacation_suspended`, `vacation_preheating`, `pending`, `pending_since`. |
| *Pause* (switch) | The pause. |
| *Guest mode* (switch) | Guest mode (the house stays *home*). |
| *Vacation start*, *Vacation end* (date and time) | The vacation period. An end before (or equal to) the start is refused, as with `set_vacation`. |
| *Heating season* (binary sensor) | Whether it is the heating season. |
| *Warm outside* (binary sensor) | Whether the heating is off because it is warm. |
| *Heat demand* (binary sensor) | Whether heat is asked for now. |
| *Outdoor average* (sensor) | The outdoor average over *Average over* hours; attributes: the latest value, the cutoff reason (`cutoff_reason`: `measured`, `forecast_warm`, `forecast_cold`), the forecast mean (`forecast_mean`), the thresholds, the forecast. |
| *Heating time* (sensor) | Total heating hours of the house. |
| *Clear manual changes* (button) | Clears the manual changes of every room. |
| *Clear vacation* (button) | Clears the vacation. |
| *Reevaluate* (button) | Works everything out again now. |

## Room entities

| Entity | Shows / does |
| --- | --- |
| *Decision* (sensor) | The rule deciding now (see below), with many attributes. |
| *Target temperature* (sensor) | The target, in the unit of the house. |
| *Room temperature* (sensor) | The room temperature used by the integration. |
| *Next change* (sensor) | The next schedule change; attributes: the next level, the profile. |
| *Heating rate* (sensor) | Learned minutes per degree for the outdoor temperature now (see [chapter 7](07-optimal-start-stop-and-learning.md)). |
| *Cooling rate* (sensor) | How fast the room falls now without heating. |
| *Heating time* (sensor) | Total heating hours of the room. |
| *Heat demand* (binary sensor) | Whether the room asks for heat; the `heating` attribute shows whether its source runs. |
| *Window open* (binary sensor) | Whether a window counts as open now. |
| *Manual change* (binary sensor) | Whether a manual change is active. |
| *Child lock* (switch) | The child lock. |
| *Clear manual change* (button) | Clears the room's manual change. |
| *Reset heating learning*, *Reset cooling learning* (buttons) | Delete the room's learning. |
| *Level Home* … *Level Activity*, *Nearby temperature* (numbers) | The level temperatures, only for rooms without Generic Thermostat. A level with its own name appears as *Level "name"*. |

### States of the *Decision* sensor

| State | Means |
| --- | --- |
| `starting` | The integration is still starting |
| `frost_protection` | Frost protection |
| `maximum_temperature` | Maximum temperature |
| `pause` | Pause |
| `mode_off` | Mode Off |
| `summer` | Mode Summer |
| `out_of_season` | Outside the heating season |
| `valve_exercise` | Valve exercise |
| `window_open` | Window open |
| `manual_override` | Manual change |
| `vacation` | Vacation |
| `presence_far` | Everybody is far |
| `presence_nearby` | Nobody home, someone nearby |
| `room_unoccupied` | Room unoccupied |
| `sensor_fallback` | Temperature sensors unavailable |
| `schedule` | The schedule |
| `optimal_start` | Optimal start |
| `optimal_stop` | Optimal stop |
| `outdoor_cutoff` | Warm outside |

### Useful attributes of the *Decision* sensor

| Attribute | Contains |
| --- | --- |
| `reason`, `reason_key`, `reason_params` | The reason (English text, and the key with parameters for translation) |
| `preset`, `target_temperature`, `current_temperature` | The level, the target, the room temperature |
| `offsets` | The active adjustments |
| `profile`, `next_change`, `next_preset`, `plan` | Today's profile, the next change, the plan of the next hours |
| `time_to_target` | Minutes to the target |
| `next_estimate` | The next optimal start / stop: `kind`, `at`, `preset`, `minutes`, `starts_at`, `started_at`, `outdoor`, `outdoor_source`, `learned`, `sent_as`, `temperature` |
| `stop_forecast` | The expected temperature at the change, during an optimal stop |
| `optimal_stop_cancelled` | Whether the optimal stop was cancelled |
| `no_heat_reason` | Why a room below its target does not heat |
| `override`, `hold_until` | The active manual change and until when the current plan holds |
| `alerts` | The room's alerts |
| `window_open`, `presence`, `heat_demand`, `heating` | The current states |

## Services

The room is picked with `room` (name or id) or with `entity_id` (any entity of
the room or its thermostat). With several houses, the house services need
`config_entry_id`.

### `advanced_climate.set_override`

Sets a level or a temperature as a manual change.

| Field | What it is |
| --- | --- |
| `room` / `entity_id` | The room |
| `preset` | The level (e.g. `comfort`); spaces around it and capitals do not matter |
| `temperature` | The temperature, in the unit of the house |
| `duration_hours` | Hours, between 0.25 and 72 (as in the house options); empty = the configured rule for manual changes |

Give either `preset` or `temperature`. The temperature is limited between the
frost protection and the maximum. A temperature that is not a number (`nan`,
`inf`) and a duration outside 0.25–72 hours (0 or negative included) are
refused with an error.

```yaml
action: advanced_climate.set_override
data:
  room: Living room
  temperature: 23
  duration_hours: 3
```

### `advanced_climate.clear_override`

Back to automatic (every room, when no room is given; a room that does not exist gives an error).

### `advanced_climate.set_vacation`

Sets the vacation period; empty values clear it.

```yaml
action: advanced_climate.set_vacation
data:
  start: "2026-12-20 08:00:00"
  end: "2026-12-27 18:00:00"
```

The end must be after the start.

### `advanced_climate.reevaluate`

Works out every room again now.

### `advanced_climate.set_schedule`

Replaces the schedule of a room: `schedule` (the text) or `profiles` (an object:
profile → list of time and level), optionally `profile_days` (the days and on /
off of every profile). Not for rooms with a Schedule helper (edit the helper
instead). Malformed `profiles` give a clear error, e.g. *Profile "workday":
every slot needs "time" and "preset"*.

`profiles` example:

```yaml
action: advanced_climate.set_schedule
data:
  room: Office
  profiles:
    workday:
      - {time: "00:00", preset: sleep}
      - {time: "07:30", preset: home}
```

```yaml
action: advanced_climate.set_schedule
data:
  room: Office
  schedule: |
    workday: 00:00 sleep, 07:30 home, 18:00 sleep
    weekend: 00:00 sleep
```

## The event `advanced_climate_decision_changed`

Fired every time a room changes its decision, with `room`, `old_rule`, `rule`,
`old_target`, `target`, `reason`.

**Automation example**: a notification when a room goes to open window.

```yaml
triggers:
  - trigger: event
    event_type: advanced_climate_decision_changed
    event_data:
      rule: window_open
actions:
  - action: notify.mobile_app_phone
    data:
      message: "Window open in {{ trigger.event.data.room }}"
```

## More automation examples

**Guests**: guest mode on (it turns off by itself after *Guest mode turns off
after* hours, if you set a value).

```yaml
actions:
  - action: switch.turn_on
    target:
      entity_id: switch.home_guest_mode
```

**Summer mode on 1 May** (if you do not use the between-dates or automatic
season):

```yaml
triggers:
  - trigger: template
    value_template: "{{ now().month == 5 and now().day == 1 }}"
actions:
  - action: select.select_option
    target:
      entity_id: select.home_mode
    data:
      option: summer
```

**Comfort in the bathroom while you shower**, started by a button:

```yaml
actions:
  - action: advanced_climate.set_override
    data:
      room: Bathroom
      preset: comfort
      duration_hours: 1
```

## Diagnostics

On the integration page, **⋮ → Download diagnostics** gives the configuration,
the learning (`learned_heating`) and the last 100 decisions of every room. Useful
when you report a problem.
