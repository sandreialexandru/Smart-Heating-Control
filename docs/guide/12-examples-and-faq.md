# 12. Examples and questions

*[Română](12-exemple-si-intrebari.ro.md) · [Contents](README.md)*

## Complete setups

### A. Flat with a boiler and one Generic Thermostat

**What you have:** a gas boiler started by a relay, a Generic Thermostat in the
living room, two people with the Home Assistant app on their phones.

1. Create the house: the people, the city zone as *nearby zone*, *At least one
   person is home*.
2. *Heating of the whole house*: Generic Thermostat, its entity.
3. In Generic Thermostat set the presets (e.g. `home_temp` 21, `sleep_temp` 18,
   `eco_temp` 17, `away_temp` 15).
4. Options → *Weather and season*: the weather entity, *Turn heating off when it
   is warm outside*, the season *Between dates*.
5. The *Whole house* zone → *Reconfigure room*: the window sensor, the schedule,
   *Optimal start*.

**What happens on a workday** (with the default schedule
`workday: 00:00 sleep, 06:00 home, 22:00 sleep`):

| Time | What happens |
| --- | --- |
| 04:50 | The optimal start turns the boiler on (e.g. with 70 learned minutes before 06:00) |
| 06:00 | `home`, the living room is already at 21 °C |
| 08:10 | The last person leaves at 08:00; after the 10-minute delay the house is *nearby* (in town): `eco` |
| 17:30 | Someone comes home: `home` |
| 22:00 | `sleep` |

Leave *Heat source* empty: Generic Thermostat already starts the boiler.

### B. House with TRVs in every room

**What you have:** a boiler with a Shelly relay in Home Assistant, Zigbee TRVs
in the bedroom, the living room and the office, window sensors.

1. Create the house, *Heating of the whole house*: *No heating devices yet*.
2. Add one room each: *Other thermostats / TRVs*, command *Temperature*, the
   levels, the window sensor; optionally a wall sensor with *Offset*
   calibration; the valve exercise.
3. Options → *Heat source and heat demand*: *Heat source* = the Shelly relay of
   the boiler; *Rooms needed* 1.

Now, when a TRV asks for heat, the integration starts the boiler; when none asks
any more, it stops it (with the 5-minute minimum times).

### C. Electric heating with smart plugs and PV

**What you have:** electric heaters on smart plugs, temperature sensors in every
room, solar panels with an exported power sensor.

1. Every room: *Switch (relay)*, the plug, hysteresis 0.3 °C, minimum times 0,
   the room sensor (required).
2. Options → *Energy*: the surplus sensor, *Surplus from* 1000 W, *Adjustment
   with surplus* +1 °C.

During the day, with sun, the rooms go 1 °C higher (e.g. 21 + 1 = 22 °C) on your
own energy, and use less in the evening.

### D. Night shifts

You work nights from Monday to Thursday and sleep in the morning.

1. Options → *Workdays and calendar*: *Schedule day starts at* 05:00.
2. The schedule: `workday: 05:00 sleep, 14:00 home` and `weekend: 05:00 home`.

The schedule day now starts at 05:00. On Friday between 00:00 and 05:00 (still at
work) Thursday is used, i.e. the `workday` profile with `home` from 14:00. At
05:00 Friday begins: you sleep (`sleep`) until 14:00.

## Frequent questions

**Do I have to add rooms?**
No, if you have one thermostat. The *Whole house* zone is enough. Add rooms only
for rooms with their own valves or thermostats.

**Can I change the temperature by hand?**
Yes. The integration recognises it as a manual change and keeps it (2 hours by
default). With *Child lock* on, the change is undone at once.

**Why does the heating not start?**
Look at the room decision in the card. If it is below the target and does not
heat, the card says why (*Not heating: …*). Common reasons: an open window, warm
outside, pause, mode Summer, outside the season, the minimum time, other rooms
needed.

**Why is the room on `eco` although I am home?**
Check the *Presence* sensor: maybe the phone reports wrongly (then the house is
*nearby*). Or the room has occupancy sensors that did not detect you for *Eco
after no occupancy for* minutes.

**I set a very low level in Generic Thermostat, but the room stays warmer.**
No target can be below the frost protection. For Generic Thermostat the frost
protection is its `min_temp`; lower it there if you want less.

**The optimal start begins too early or too late.**
In the first days the room learns (until then it uses 60 minutes per degree). If
you changed something in the heating, reset the learning. If the source waits for
other rooms, the wait is not learned (see
[chapter 7](07-optimal-start-stop-and-learning.md)).

**The optimal stop is often cancelled.**
The room cools faster than learned (e.g. a door left open). Lower *Maximum early
stop*.

**The heating stopped on a sunny autumn day.**
That is the warm-outside cutoff: the average over *Average over* hours reached
the cutoff. Raise *Average over* or the cutoff, or turn on *Use the forecast*, so
the heating may start when the cold comes.

**The house is on frost protection and I do not see why.**
Maybe it is a day without an active profile in the schedule (the room shows the
alert *No active schedule profile*), mode Off, an open window or a window
detected from a temperature drop.

**What happens when Home Assistant restarts?**
Almost everything is kept; only the TRV limits learned from the device are not
(see [chapter 9](09-windows-manual-safety.md#restart-of-home-assistant)).

**Does it work with several houses?**
Yes, every house is a separate entry of the integration. The house services then
need `config_entry_id`.

**Does it work for cooling (air conditioning)?**
No. The integration is for heating.

## When something does not work

1. **Read the decision** of the room in the card (the rule and the reason).
2. **Open the room *Details***: the alerts come first.
3. **Check the entities**: the temperature sensors, the thermostat, the people,
   the heat source; an unavailable one explains a lot.
4. **Press *Reevaluate*** (house) to work out the decision again at once.
5. **Download the diagnostics** (integration page, ⋮) and attach them when you
   report a problem on GitHub: they hold the configuration and the last 100
   decisions.
