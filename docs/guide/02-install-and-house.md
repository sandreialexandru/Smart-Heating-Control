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

1. In HACS (the **Marketplace** from Home Assistant 2026.11) search
   **Smart Heating Control**, install it and restart Home Assistant.
2. Not found in the search? Add it as a custom repository: ⋮ menu →
   **Custom repositories** → `https://github.com/sandreialexandru/Smart-Heating-Control`,
   type **Integration**, then install it as above.
3. **Settings → Devices & services → Add integration → Smart Heating
   Control**.

**By hand:** copy the folder `custom_components/advanced_climate` to
`config/custom_components` and restart Home Assistant.

The Lovelace card is added to the dashboard resources by itself (see
[chapter 10](10-card.md)).

## Which setup for my house?

Before creating the house, answer two questions: **what heats it** and **who
can start the boiler**. The configuration has three pieces:

1. **Heating of the whole house** (the zone *Whole house*): one thermostat or
   relay that heats the whole home. It gets the schedule of the house, like a
   room.
2. **Rooms**: radiators or zones with their own device (TRV, thermostat,
   relay, electric heater) and, ideally, their own sensor. Each one is a room
   with its own schedule.
3. **Heat source**: the boiler (its relay, or the thermostat that starts it)
   when the rooms cannot start it themselves. Only needed with **TRVs** or zone
   valves: a TRV only opens or closes its radiator valve; if nobody starts the
   boiler, the radiator stays cold.

**The rule.** With TRV rooms, the integration needs **its own way to the
boiler**: a relay of the boiler, or the thermostat that starts it, as *Heat
source*. A device already used by the *Whole house* zone or by a room cannot
also be the *Heat source* (one device, one role: two parts of the integration
would otherwise command the same device).

| Your home | Heating of the whole house | Rooms | Heat source |
| --- | --- | --- | --- |
| **One thermostat or relay for the whole home, no TRVs** (e.g. a flat with a Generic Thermostat on the boiler) | Generic Thermostat, Another thermostat for the whole home or Switch (relay) | – | – (not offered with Generic Thermostat or a relay) |
| **TRVs on the radiators, the boiler has a relay in Home Assistant** | Each room heats separately | one per room with TRVs | **the boiler relay** |
| **TRVs on the radiators, the boiler is started by a thermostat in Home Assistant** (Hive, Nest, Tado, Netatmo) | Each room heats separately | one per room with TRVs | **that thermostat**, with *Start and stop the source by its temperature* on |
| **TRVs on only some radiators, a thermostat starts the boiler** (e.g. a hallway thermostat) | Each room heats separately | the rooms with TRVs | **that thermostat**, with *Start and stop the source by its temperature* on and a *Heat source idle temperature* (e.g. 17.5 °C) for the radiators without TRVs |
| **Electric heaters, air conditioners, a heat pump per room** | Each room heats separately | one per room, with its relay or thermostat | – (each room heats by itself) |
| **A single electric heater or air conditioner for the whole home** | Switch (relay) or Another thermostat for the whole home | – | – |
| **A thermostat or relay on the whole house and TRVs in some rooms** | the thermostat or relay | the rooms with TRVs | ⚠️ none possible: see below |

**Why the last case is limited.** The whole-house zone starts the boiler only
by its own sensor. When that sensor is warm and a TRV room is cold, the TRV
opens but the boiler does not start, so the radiator stays cold. The device of
the whole house cannot also be the heat source (it already has a role). The
ways out: the **boiler relay as *Heat source*** instead of on the whole house
(with a thermostat that also starts the boiler, a relay wired in parallel with
it); or the thermostat as *Heat source* instead of on the whole house (the rows
above), with an idle temperature for the radiators without TRVs.

**With TRVs on every radiator**, the installation must let the water through
when they all close: an automatic bypass, a boiler with an internal bypass, or
one radiator without a TRV (often in the bathroom).

**Examples.**

- *A flat, a Generic Thermostat switches the boiler relay, no TRVs*: Heating of
  the whole house = Generic Thermostat. Nothing else; the *Heat source* page
  is not even offered.
- *A house, a Shelly relay on the boiler, TRVs in every room*: *Each room
  heats separately*; one room per TRV room (*Other thermostats / TRVs*, with
  *Heat by the room sensor* when the room has its own sensor); *Heat source* = the Shelly
  relay.
- *A house, a Hive in the hallway wired to the boiler, TRVs in three rooms*:
  *Each room heats separately*; three TRV rooms; *Heat source* = the Hive,
  *Start and stop the source by its temperature* on, *Heat source idle temperature* 17.5 °C. The Hive
  keeps the rest of the house at about 17.5 °C and gets the maximum when a TRV
  room asks.
- *Electric heaters on smart plugs*: *Each room heats separately*; one room per
  room (*Switch (relay)*, with its temperature sensor); no heat source.

## Creating the house

The forms show only the fields that apply. If a field does not appear, it does
not make sense for your choices.

### Step 1: the house

| Field | What to do |
| --- | --- |
| **Temperature unit** | °C or °F. Every temperature of the house is entered and shown in it. It can be changed later (see below). |
| **Name** | The name of the house, e.g. "Home". Shown on the devices and in the card. |
| **People** | The `person` entities of the people who live there. Their location decides whether the house state is *home*, *nearby* or *far*. Left empty, the house state is always *home* and only the schedule decides. |
| **Nearby zones** | Zones where the house state is *nearby* (`eco`) instead of *far* (`away`), e.g. the zone of your city. Left empty, there is only *home* and *far*. |
| **The house state is Home when** | *At least one person is home* (right for almost every home) or *Everybody is home* (the heating goes down as soon as someone leaves). |

**Example.** Andrei and Maria live in Bucharest. You pick `person.andrei` and
`person.maria`, and a zone "Bucharest" as nearby zone (made in Home Assistant
under *Settings → Areas, labels & zones → Zones*). When both are at work in
town, the house state is *nearby* and the rooms go to `eco`. When they leave town, the house state
is *far* and the rooms go to `away`.

### Step 2: the heating of the whole house

**Heated by** picks what heats the whole house:

| Choice | When to use it |
| --- | --- |
| **Generic Thermostat** | A Generic Thermostat starts the boiler (the most common case). |
| **Another thermostat for the whole home** | One smart thermostat that is not Generic Thermostat heats the whole home (e.g. Nest, Tado, Hive, a Zigbee or Wi-Fi thermostat). |
| **Switch (relay)** | A relay turns the heating on directly, without a thermostat. |
| **Each room heats separately** | Nothing heats the whole house as one zone; every room is added with its own heating: TRVs or valves on the radiators, electric heaters, a heat pump or air conditioner, underfloor heating. |

What you pick becomes the zone **Whole house**, which behaves like a room and
uses every option of the house.

**Step 3: devices.** Depending on the choice:

- **Thermostats**: the thermostat that controls the boiler, e.g. the Generic
  Thermostat entity.
- **Switches (relays)**: only when a relay heats directly.
- **Command**: only for thermostats other than Generic Thermostat; see
  [chapter 3](03-rooms.md#command-for-other-thermostats) for the difference
  between *Temperature*, *Preset* and *On / off*.
- **Heat by the room sensors**: only with another thermostat and the
  *Temperature* command. While the house asks for heat, by its own
  temperature sensors and the hysteresis, the thermostat gets a higher
  temperature (by default the maximum of the house), so it keeps heating
  until the house is warm; the rest of the time it gets the target. Useful
  when the thermostat measures in the wrong place, e.g. in the hallway. The
  next page asks for the sensors, the temperature, the hysteresis and *Use
  the learned inertia*. Not the same as *Start and stop the source by its
  temperature*, which is for a thermostat that only starts the boiler for
  rooms with their own TRVs (*Each room heats separately*, with the
  thermostat as the *Heat source*).

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
  - *Use the learned inertia* (on by default): once learned, the heating
    stops and starts a little early inside the band, by how slowly it reacts
    (see [chapter 3](03-rooms.md#relay-or-on--off-on--off-control)).
- **Thermostat** (other thermostats commanded by *Temperature* or *Preset*),
  only when the thermostat does not report when it heats (no `hvac_action`):
  - *Hysteresis*. The integration then counts it as heating from hysteresis
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
| The house state is Home when | at least one | As when creating the house. |
| Nearby zones | none | As when creating the house. |
| Use coordinates for nearby zones | on | Someone in a zone that lies inside a nearby zone (e.g. the "Office" zone in town) counts as *nearby*. Turn off if people have no GPS location. |
| Departure delay | 10 min | How long everybody must be gone before the heating goes down. Avoids reacting to short trips (shop, walking the dog). |
| Arrival delay | 0 min | Usually 0: the heating returns as soon as someone is home. Raise it only if GPS sometimes reports "home" by mistake. |
| Presence sensors | none | Keep the house state *home* while on (mmWave, motion, a switch for people without a phone). |
| Guest mode turns off after | 0 h | Guest mode keeps the house state *home*; it turns off after this many hours. 0 = only by hand. |
| Proximity distance sensor | – | For preheating on the way home (recommended, with the direction sensor). |
| Proximity direction sensor | – | So preheating starts only when someone comes towards home, not when sitting at an office near home. |
| Travel time sensors | – | Travel time to home (Waze, Google Travel Time), one sensor per person: the shortest trip counts. It only tells how close someone is, not whether they are coming home: someone staying nearby keeps the house warm. Proximity is recommended instead, because it can tell the direction. |

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

Not in the menu when the *Whole house* zone is a Generic Thermostat or a relay:
that zone already starts the boiler (a heat source saved before is removed when
the whole-house heating is saved).

| Setting | Default | What it does |
| --- | --- | --- |
| Heat source | – | The boiler (or the relay that starts it) when the rooms cannot start it themselves (TRVs, zone valves). The form refuses a device of a room and the relay of a Generic Thermostat used by a room. |

The second form, only with a heat source:

| Setting | Default | What it does |
| --- | --- | --- |
| Rooms needed to start the heat source | 1 | How many rooms must ask for heat to start it. At most the number of rooms of the house; if rooms are removed later and fewer remain, you get an alert. |
| Heat source minimum on / off time | 0 / 0 min | 0 = the source follows the heat demand at once. A larger value protects a boiler without its own anti-cycling from short cycles. |
| Start and stop the source by its temperature | on | Only for a thermostat (`climate`) as the source: the maximum temperature of the house to start it, the frost protection of the house to stop it, always in its heat mode. Off: only its mode is switched. |
| Heat source idle temperature | – (frost protection) | Only with *Start and stop the source by its temperature*: what the thermostat gets while no room asks, e.g. 17.5 °C when it also heats radiators without TRVs. Below the maximum of the house. |
| Reference room | – | Only this room decides when the source runs; the others only open or close their valves. |

Details: [chapter 8](08-heat-source-and-energy.md).

### Manual changes, vacation and limits

| Setting | Default | What it does |
| --- | --- | --- |
| Manual changes are kept | Fixed duration | *Fixed duration* (the hours below) or *Until next reevaluation* (until the schedule, presence, a window or the mode changes). |
| Manual change applies to | Only that room | *Whole house* copies a manual change to every room; only when every room has its own valves. Shown only with more than one room. |
| Preheat before the end of a vacation | 4 h | The schedule returns this many hours before the vacation ends. |
| Automatic vacation after everyone is far for | 0 h (off) | The vacation starts by itself after everybody has been far this long. Shown only when the house has people. |
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
| Important alerts to | – | Phones (`notify.mobile_app_...`), email or other notify services. For email write the addresses after the service: `notify.me_gmail_com: ana@example.com, ion@example.com` (Google Mail needs them). Sent at once, also in the quiet hours. Empty = notifications in Home Assistant. |
| Warnings to | – | The same, for the alerts to look at. Empty = notifications in Home Assistant. |
| Information to | – | What the house did by itself: the heating season started or ended, a planned vacation started, the preheating before your return, the automatic vacation, guest mode ended by itself. Empty = not told. |
| Tell when an alert ends | on | A message when a device works again, a window is closed or a battery was replaced. |
| Remind when the pause lasts longer than | 12 h | A warning when the heating stays paused this long, then once a day. 0 = never. |
| Quiet hours from / until | – | Only the important alerts in this time; the others are sent when it ends, if they still apply. |
| Alert when a window is open longer than | 30 min | While heating is needed. |
| Alert when a device is unavailable longer than | 15 min | Thermostat or sensor. |
| Alert when a temperature sensor sends nothing for | 4 h | A room temperature sensor that stays available but sends no value at all (a flat battery or a lost signal keeps the last one). 0 = off; raise it for sensors that report only when the temperature changes. |
| Alert when heating has no effect for | 2 h | A room that heats this long, clearly below its target, while its temperature rises much less than learned (stuck valve, heat source that does not start, window open without a sensor). 0 = off. |
| Low battery below | 20 % | The room devices (TRV, sensors). |
| Verify commands | on | After 2 minutes checks that the device accepted the command, retries once, then alerts. |
| Alert when a room stays colder than | 0 (off) | Alert when a room stays this many degrees below its target while others are warm (stuck valve, open window). Shown only with more than one room. |

The list of alerts: [chapter 9](09-windows-manual-safety.md#the-alerts).
