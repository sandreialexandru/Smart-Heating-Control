# 2. Installation and the house

*[Română](02-instalare-si-casa.ro.md) · [Contents](README.md)*

## What you need

- Home Assistant **2026.6.0** or newer.
- Your heating devices in Home Assistant: a Generic Thermostat, TRVs, other
  thermostats or relays.
- Recommended: the Home Assistant app on the phone of every person (so the
  integration knows who is home), an outdoor temperature sensor or a weather
  entity.

## Installing

**With HACS (recommended):**

1. HACS → ⋮ menu → **Custom repositories** → add
   `https://github.com/sandreialexandru/Smart-Heating-Control`, type
   **Integration**.
2. Search **Smart Heating Control**, install it and restart Home Assistant.
3. **Settings → Devices & services → Add integration → Smart Heating
   Control**.

**By hand:** copy the folder `custom_components/advanced_climate` to
`config/custom_components` and restart Home Assistant.

The Lovelace card is added to the dashboard resources by itself (see
[chapter 10](10-card.md)).

## Creating the house

The forms show only the fields that apply. If a field does not appear, it does
not make sense for your choices.

### Step 1: the house

| Field | What to do |
| --- | --- |
| **Temperature unit** | °C or °F. Every temperature of the house is entered and shown in it. It can be changed later (see below). |
| **Name** | The name of the house, e.g. "Home". Shown on the devices and in the card. |
| **People** | The `person` entities of the people who live there. Their location decides whether the house is *home*, *nearby* or *far*. Left empty, the house is always *home* and only the schedule decides. |
| **Nearby zones** | Zones where the house counts as *nearby* (`eco`) instead of *far* (`away`), e.g. the zone of your city. Left empty, there is only *home* and *far*. |
| **The house is home when** | *At least one person is home* (right for almost every home) or *Everybody is home* (the heating goes down as soon as someone leaves). |

**Example.** Andrei and Maria live in Bucharest. You pick `person.andrei` and
`person.maria`, and a zone "Bucharest" as nearby zone (made in Home Assistant
under *Settings → Areas, labels & zones → Zones*). When both are at work in
town, the house is *nearby* and goes to `eco`. When they leave town, the house
is *far* and goes to `away`.

### Step 2: the heating of the whole house

**Heated by** picks what heats the whole house:

| Choice | When to use it |
| --- | --- |
| **Generic Thermostat** | A Generic Thermostat starts the boiler (the most common case). |
| **Other thermostats / TRVs** | A smart thermostat that is not Generic Thermostat (e.g. a Zigbee or Wi-Fi thermostat). |
| **Switch (relay)** | A relay turns the heating on directly, without a thermostat. |
| **No heating devices yet** | Nothing heats the whole house as one zone; every room is added with its own heating: TRVs or valves on the radiators, electric heaters, a heat pump or air conditioner, underfloor heating. |

What you pick becomes the zone **Whole house**, which behaves like a room and
uses every option of the house.

**Step 3: devices.** Depending on the choice:

- **Thermostats**: the thermostat that controls the boiler, e.g. the Generic
  Thermostat entity.
- **Switches (relays)**: only when a relay heats directly.
- **Command**: only for thermostats other than Generic Thermostat; see
  [chapter 3](03-rooms.md#command-for-other-thermostats) for the difference
  between *Temperature*, *Preset* and *On / off*.

**Step 4: the command settings.** Only when needed:

- **On / off control** (relay, or a thermostat commanded *On / off*):
  - *Temperature sensors*: the sensors in the room. Required for relays, which
    have no sensor of their own.
  - *Hysteresis* (0.3 °C by default): heating starts below target minus
    hysteresis and stops above target plus hysteresis. Example with a chosen
    target of 21 °C: it starts at 21 − 0.3 = 20.7 °C and stops at
    21 + 0.3 = 21.3 °C.
  - *Minimum on time* and *Minimum off time* (0 by default, no wait): set
    them (e.g. a few minutes) when the relay starts a boiler without its own
    anti-cycling, or to spare a mechanical relay; 0 suits electric heaters.
- **Thermostat** (other thermostats commanded by *Temperature* or *Preset*):
  - *Thermostat tolerance* (0 by default): how far below the target the
    thermostat lets the room fall before heating. Matters for the learning
    ([chapter 7](07-optimal-start-stop-and-learning.md)).
  - *Hysteresis*: only when the thermostat does not report when it heats (no
    `hvac_action`). The integration then counts it as heating from hysteresis
    below its set temperature to hysteresis above it.
- **Generic Thermostat**: no step, GT has its own settings.

After these steps the house exists. For a house with one thermostat you are
done; the rest is optional.

## Changing the temperature unit

On the integration page, at the house: **⋮ → Reconfigure**. Pick another unit,
and every value (settings, levels, card) is converted. Nothing has to be
entered again.

## The options of the house

On the integration page, **Configure** opens a menu with the groups of options.
Every group first asks the choices, then, if needed, a second form with only
the values you need.

### Heating of the whole house

The same steps as when creating the house (source, devices, command settings).
The other settings of the *Whole house* zone (levels, sensors, windows,
schedule) are changed like any room: on the integration page, at the *Whole
house* zone, **⋮ → Reconfigure** (see [chapter 3](03-rooms.md)).

### Presence

| Setting | Default | What it does |
| --- | --- | --- |
| People | – | As when creating the house. |
| The house is home when | at least one | As when creating the house. |
| Nearby zones | none | As when creating the house. |
| Use coordinates for nearby zones | on | Someone in a zone that lies inside a nearby zone (e.g. the "Office" zone in town) counts as *nearby*. Turn off if people have no GPS location. |
| Departure delay | 10 min | How long everybody must be gone before the heating goes down. Avoids reacting to short trips (shop, walking the dog). |
| Arrival delay | 0 min | Usually 0: the heating returns as soon as someone is home. Raise it only if GPS sometimes reports "home" by mistake. |
| Presence sensors | none | Keep the house *home* while on (mmWave, motion, a switch for people without a phone). |
| Guest mode turns off after | 0 h | Guest mode keeps the house *home*; it turns off after this many hours. 0 = only by hand. |
| Proximity distance sensor | – | For preheating on the way home. |
| Proximity direction sensor | – | So preheating starts only when someone comes towards home, not when sitting at an office near home. |
| Travel time sensor | – | Travel time to home (Waze, Google Travel Time). |

With a distance or travel time sensor, a second form appears, **Preheating on
the way home**:

| Setting | Default | What it does |
| --- | --- | --- |
| Preheat below distance | 10 km | Preheating starts when someone is closer than this. |
| Preheat below travel time | 20 min | Preheating starts when someone is less than this many minutes from home. |

Everything about presence: [chapter 5](05-presence.md).

### Workdays and calendar

| Setting | Default | What it does |
| --- | --- | --- |
| Workday sensor | – | The sensor of the Workday integration, so holidays use the profile of weekend days. Without it Mon–Fri are workdays. |
| Calendar | – | Optional. An event titled with a profile name (e.g. `home_office`) or a level name (e.g. `away`) applies it. |
| Schedule day starts at | 00:00 | Leave 00:00. Change it only for night shifts, so a night belongs to the day before. |

Details: [chapter 4](04-schedule.md).

### Weather and season

| Setting | Default | What it does |
| --- | --- | --- |
| Outdoor temperature sensor | – | The outdoor temperature. If empty, the temperature of the weather entity is used. |
| Weather entity | – | For the forecast, the solar gain, and as outdoor temperature without a sensor. |
| Turn heating off when it is warm outside | off | Stops heating when the outdoor average reaches the cutoff. |
| Use the forecast | off | Uses the mean forecast of the next hours to stop / restart. |
| Heating season | Always | *Always*, *Between dates* or *Automatic (outdoor temperature)*. |
| Outdoor compensation | off | Raises the target a little when it is very cold outside. |
| Ignore windows above | – | At or above this outdoor temperature, open windows no longer lower the heating. |

**What every option needs.** The cutoff, the *Automatic* season, the compensation
and *Ignore windows above* need an outdoor temperature sensor or a weather
entity. *Use the forecast* needs a weather entity and the cutoff turned on.
Without them the form is not saved and shows the error next to the option. If
an older setup has them on without a source, the house raises the alert *On but
not working…*, and the *Automatic* season behaves like *Always* (it cannot stay
off).

The second form, **Weather and season values**, shows only what you turned on:

| Setting | Default | Range |
| --- | --- | --- |
| Outdoor cutoff temperature | 18 °C | 5 – 30 °C |
| Cutoff hysteresis | 1 °C | 0 – 5 °C |
| Average over | 6 h | 1 – 48 h |
| Forecast hours | 3 h | 1 – 24 h |
| Season start / end (MM-DD) | 10-15 / 04-15 | month-day |
| Automatic season: consecutive days | 3 | 1 – 14 |
| Automatic season threshold | 15 °C | 0 – 25 °C |
| Compensate below | −5 °C | −30 – 15 °C |
| Compensation | 0.5 °C | −3 – 3 °C |

Everything about the weather: [chapter 6](06-weather.md).

### Energy

| Setting | What it does |
| --- | --- |
| Energy price sensor | The energy price (dynamic tariff). Empty with a fixed price. |
| PV surplus sensor | The power exported to the grid (W). Useful only with electric heating or a heat pump. |

The second form, **Energy thresholds**:

| Setting | Default | What it does |
| --- | --- | --- |
| High price from | – | At or above this price the high-price adjustment applies. |
| Adjustment at high price | −1 °C | Usually negative. |
| Low price up to | – | At or below this price the low-price adjustment applies. |
| Adjustment at low price | +0.5 °C | Usually positive. |
| Surplus from | 1000 W | From this surplus the adjustment applies. |
| Adjustment with surplus | +0.5 °C | Degrees added while there is surplus. |

Details: [chapter 8](08-heat-source-and-energy.md).

### Heat source and heat demand

| Setting | Default | What it does |
| --- | --- | --- |
| Heat source | – | The boiler (or the relay that starts it) when the rooms cannot start it themselves (TRVs, zone valves). Not shown when the *Whole house* zone is a Generic Thermostat or a relay: it already starts the boiler (a heat source saved before is removed when the form is saved). The form refuses a device of a room and the relay of a Generic Thermostat used by a room. |
| Alert when a room stays colder than | 0 (off) | Alert when a room stays this many degrees below its target while others are warm (stuck valve, open window). |

The second form, only with a heat source:

| Setting | Default | What it does |
| --- | --- | --- |
| Rooms needed to start the heat source | 1 | How many rooms must ask for heat to start it. At most the number of rooms of the house; if rooms are removed later and fewer remain, you get an alert. |
| Heat source minimum on / off time | 0 / 0 min | 0 = the source follows the heat demand at once. A larger value protects a boiler without its own anti-cycling from short cycles. |
| Reference room | – | Only this room decides when the source runs; the others only open or close their valves. |

Details: [chapter 8](08-heat-source-and-energy.md).

### Manual changes, vacation and limits

| Setting | Default | What it does |
| --- | --- | --- |
| Manual changes are kept | Fixed duration | *Fixed duration* (the hours below) or *Until next reevaluation* (until the schedule, presence, a window or the mode changes). |
| Manual change applies to | Only that room | *Whole house* copies a manual change to every room; only when every room has its own valves. |
| Preheat before the end of a vacation | 4 h | The schedule returns this many hours before the vacation ends. |
| Automatic vacation after everyone is far for | 0 h (off) | The vacation starts by itself after everybody has been far this long. |
| Frost protection | 7 °C (3 – 15 °C) | The lowest temperature. Rooms with Generic Thermostat use its minimum temperature instead. |
| Maximum temperature | 25 °C (15 – 35 °C) | No target goes above it. |
| Periodic check every | 5 min (1 – 60) | The safety check that resends the decision. Changes are applied at once anyway. |

With *Fixed duration*, **Fixed duration** appears (2 h by default, from 0.25 to
72 h).

Details: [chapter 9](09-windows-manual-safety.md) and
[chapter 5](05-presence.md#vacation).

### Alerts

| Setting | Default | What it does |
| --- | --- | --- |
| Notification service | – | e.g. `notify.mobile_app_phone`. Empty = notifications in Home Assistant only. |
| Alert when a window is open longer than | 30 min | While heating is needed. |
| Alert when a device is unavailable longer than | 15 min | Thermostat or sensor. |
| Low battery below | 20 % | The room devices (TRV, sensors). |
| Verify commands | on | After 2 minutes checks that the device accepted the command, retries once, then alerts. |

The list of alerts: [chapter 9](09-windows-manual-safety.md#the-alerts).
