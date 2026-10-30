# 9. Windows, manual changes and safety

*[Română](09-ferestre-manual-siguranta.ro.md) · [Contents](README.md)*

## Windows and doors

When a window opens, there is no point heating the outdoors. The integration
reacts per room.

**What happens:**

1. The window opens. If it stays open for the *Open delay* (60 seconds by
   default), the room uses *When a window is open*:
   - **Frost protection** (default): the room keeps the minimum temperature;
   - **Turn off**: the heating stops (devices that cannot be turned off get the
     frost protection temperature).
2. The window closes. After the *Close delay* (30 seconds by default), the room
   returns to what the rules say at that moment (schedule, presence, a manual
   change that was active).

Airing shorter than the open delay is ignored.

**Several sources of "window open":**

- the room's **window sensors**: any open = open;
- **windows of other rooms**: e.g. the living room balcony door also cools the
  hall;
- **detection from the temperature**: a drop of *Temperature drop* (1 °C by
  default) *Within* (3 minutes by default) counts as an open window for 15
  minutes. For rooms without sensors. A jump of the room temperature because a
  temperature sensor stopped or came back, or because the room fell back to the
  sensor of its device or one of its TRVs stopped, is not a drop: the detection starts again from the new
  value.

**When warm outside**: with *Ignore windows above* (house options), an open
window does not lower the heating when the outdoor temperature is at that value
or above.

**Alert**: if a window stays open longer than *Alert when a window is open longer
than* (30 minutes by default) while heating is needed, you get an alert.

Learning episodes with an open window are not used.

## Manual changes

A **manual change** is any change made by a person: on the thermostat, on the
TRV, in its app, in Home Assistant, from the card or with the `set_override`
service. The integration keeps it for a while, then takes over again.

**How it recognises them.** Commands sent by the integration carry their own
"context" in Home Assistant, so the integration knows which are its own. A
device that only reports later what the integration sent it (e.g. a battery
Zigbee TRV that wakes up rarely) is not a manual change, also when it reports
an older value after a newer one was sent: the values sent in the last 5
minutes and the temperature or preset the device showed before each command are
recognised too,
until the device has shown the last value for 1 minute (some TRVs show the new
value at once and then report the old one once more); after that any other value
is a manual change.

**Limits of the device.** Some TRVs have their own *Max temperature* /
*Min temperature* on the device, narrower than the range of their entity (e.g.
25 °C on a Tuya TRV whose entity goes to 35 °C). When a TRV reports less than a
boost or the valve exercise sent (but at least the target), or more than frost
protection / off sent (but below the lowest level), that is its limit, not a
manual change: the next commands stay within it, and an alert tells it. A TRV
that already held its limit (so it reports nothing) is recognised by the command
check: after the command was sent again and the TRV still holds it. The
limit is tried again after a day, so a new setting on the device is seen.

**How long** (*Manual changes are kept*, in the house options):

| Choice | Ends |
| --- | --- |
| **Fixed duration** (default, 2 hours) | after *Fixed duration* hours |
| **Until next reevaluation** | when something important changes: the schedule level, the profile, the presence, someone on the way home, the vacation or its preheating, a window, the mode, the warm-outside cutoff, the season. The periodic check does not end it. |

**Example with *Until next reevaluation*.** It is 20:00, the schedule asks for
`home` 21 °C until 22:00, and you set 23 °C on the thermostat. The change holds
until 22:00, when the schedule goes to `sleep`; then the room goes to `sleep`.

**What it applies to** (*Manual change applies to*): **Only that room**
(default) or **Whole house** (a change in one room is copied to every room;
only when every room has its own valves).

**If a more important rule steps in.** If a window opens during a manual change
(or frost protection steps in, or the mode changes), the devices follow that
rule. When it ends, the manual value is set again: the value from the card /
service, or what you set on the device (mode, preset, temperature, relay on /
off). For a relay, setting it again respects the minimum on / off time. The card
shows *returns after: …* while it is interrupted.

**From the card or the service.** A level or a temperature set from the card
(*Set for a while*) or with `set_override` is sent only while the manual change
applies (not in a pause, not with an open window, not in mode Off or Summer) and
stays on the devices for its whole duration. While a rule above keeps it away,
the card shows *applies after: …*. The temperature is always between the frost
protection and the maximum.

**Clearing**: the room's *Clear manual change* button, *Back to automatic* in
the card, the house button for every room, or the `clear_override` service.

## Child lock

The room's *Child lock* switch (also in the card, under *Set for a while*): any
manual change on the device is undone at once, and the room returns to the
integration's decision. Useful for a TRV within reach of children.

## Pause

The house's *Pause* switch stops every command of the integration: nothing
changes on the devices and no TRV calibration is done. These stay on, for
safety:

- **frost protection**: a room that is too cold gets heat (and the heat source
  is started for it, then stopped);
- **maximum temperature**: a set temperature above the maximum is lowered, and a
  relay or on / off room is turned off while at the maximum or above;
- **TRV boost**: a boost left on the TRVs when the pause starts is taken back to
  the target once (see [chapter 3](03-rooms.md)).

The card shows a band at the top while the house is paused. A manual change
made in a pause is kept and applies after the pause: one from the card or a
service is sent then, one made on the device stays as it is (the child lock does
not undo it during the pause).

## The house modes

The house's *Mode* select:

| Mode | What it does |
| --- | --- |
| **Auto** | Every rule: schedule, presence, windows, weather… |
| **Vacation** | `away` in every room (see [chapter 5](05-presence.md#vacation)) |
| **Off** | Only frost protection |
| **Summer** | Heating off (frost protection stays as safety). With the automatic or between-dates season, heating stops by itself outside the season. |

## Frost protection

The lowest temperature a room ever gets:

- the *Frost protection* value of the house options (7 °C by default, between 3
  and 15 °C);
- for rooms with Generic Thermostat, the minimum temperature of GT
  (`min_temp`).

It **always** applies: in mode Off, in a pause, over a manual change, with an
open window. Once a room heats for frost protection, it continues until the
device stops asking for heat (it does not switch on and off around the limit).
A level set below frost protection (e.g. in Generic Thermostat) is raised to it,
and the decision shows *Frost protection (sleep is below 7°)*.

No level can be set below frost protection in the integration: the fields, the
card and the services have it as their minimum.

**TRVs with a room sensor.** A TRV measures next to the radiator, warmer than
the room: with the room at 5 °C and the TRV reading 8 °C (example values), a
TRV set to 7 °C would not open. So in a TRV room with its own temperature
sensors, frost protection is decided from the room sensor: below the frost
protection the room asks for heat (the heat source starts) and the TRVs get the
maximum temperature of the house (or the boost temperature of the room with the
TRV boost), until the room reaches frost protection + hysteresis. Then they get
the frost protection temperature again. The hysteresis is the room setting; when
the earlier steps did not ask for it, the *Sensors: details* step asks for it
as *Frost protection hysteresis*.

## Maximum temperature

*Maximum temperature* (25 °C by default, between 15 and 35 °C). No target goes
above it:

- a higher level is sent as the maximum;
- a temperature set on a thermostat above the maximum (manual change, pause) is
  lowered to it;
- a relay or on / off room is **turned off** while the room is at the maximum or
  above; below it, it is not turned on again to heat back up;
- a thermostat that rounds to its step gets the step just below the maximum.

The decision then shows the rule *Maximum temperature*.

## Failed sensors

If the room temperature sensors are unavailable:

1. the device sensor (thermostat, TRV) is used, if it has one;
2. if that does not work either, the room goes to `eco`, but never above the
   schedule: if the schedule asks for a lower level (e.g. `away`), that stays.

In both cases you get an alert. A sensor value that is not a number (`nan`,
`inf`) counts as unavailable.

## Command checks

With *Verify commands* (on by default), 2 minutes after a command the
integration checks that the device accepted it (also for a manual change from
the card). If not, it sends it again once; if it still fails, it raises the alert
*… did not accept …*. Turn the check off only if a device reports its state very
slowly.

## Valve exercise

For TRVs (*Valve exercise*, in the room's *Extras* step): once a week, on the
chosen day and time (Sunday at 10:00 by default), the TRVs open fully for 5
minutes, against limescale. It runs in every mode, in summer and outside the
season too. A pause, a manual change or an open window postpones it to later
the same day. It does not ask the boiler for heat, and its period is not
learned.

## The alerts

Alerts appear as Home Assistant notifications or through the *Notification
service* and, in the card language, in the room *Details*. An alert is not
repeated often.

| Alert | When |
| --- | --- |
| A window has been open for more than … min | the window open longer than the alert threshold, while heat is needed |
| … has been unavailable for more than … min | a thermostat or sensor unavailable longer than the alert threshold |
| The heat source … has been unavailable | then nothing heats, not even frost protection |
| No outdoor temperature from … | no configured source (sensor, weather) gives a temperature for longer than the alert threshold |
| On but not working without an outdoor temperature sensor or a weather entity | weather functions on without the source they need |
| The temperature sensors are unavailable | the device sensor or `eco` is used |
| Low battery on … | below *Low battery below* (20 % by default) |
| … did not accept … | the command check failed twice |
| … accepts at most / at least … | the TRV keeps its own *Max / Min temperature* set on the device (above, *Limits of the device*) |
| Some rooms stay cold while others are warm | with *Alert when a room stays colder than* |
| The level … is not available on … | a preset chosen for a level is missing on the thermostat and its temperature is unknown |
| The schedule is invalid | the default schedule is used |
| No active schedule profile: … | days without an active profile (frost protection) |
| Rooms needed to start the heat source is … | more rooms needed than the house has (rooms were removed): the heat source starts only for frost protection |

## Restart of Home Assistant

Kept: manual changes, the vacation and the automatic vacation, the mode, the
pause, the guests, the heating and cooling learning (also the heating episode in
progress), the outdoor averages
(including the daily means for the season), the forecast cutoff, the times of
the last switches of the boiler and relays, and whether the boiler was started
for frost protection. After a restart the integration continues where it left
off.

Not kept (on a restart or a reload of the integration): the limits learned
from what the TRVs apply on the device (their own Max / Min temperature). They
are learned again at the first boost or command that meets them, so a restart
or a reload is also the way to forget them before the day is over.
