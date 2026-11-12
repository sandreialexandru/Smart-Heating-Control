# 8. Heat source and energy

*[Română](08-sursa-si-energie.ro.md) · [Contents](README.md)*

## Do you need a *Heat source*?

It depends on who starts the boiler:

| Your case | *Heat source* |
| --- | --- |
| A **Generic Thermostat** starts the boiler (through its relay) | **None.** GT already starts the boiler; with GT on the *Whole house* zone the form does not offer a heat source. |
| A room **relay** starts the boiler or a heater directly | **None.** The relay is already controlled by the integration; with a relay on the *Whole house* zone the form does not offer a heat source. |
| **TRVs** or zone valves, and the boiler has a relay or a thermostat in Home Assistant | **Pick the boiler** (or its relay). The integration starts it when rooms ask for heat. |
| TRVs, and the boiler is started by a thermostat that is **not in Home Assistant** | Nothing to pick. It works, but the learning is not reliable (see [chapter 7](07-optimal-start-stop-and-learning.md#when-it-is-not-recommended)). |

Why it matters: a TRV only opens or closes the radiator valve. If the boiler
does not start, the radiator stays cold.

The full choice of the setup, with every kind of home, is in
[chapter 2](02-install-and-house.md#which-setup-for-my-house). A device used by
the *Whole house* zone or by a room cannot also be the *Heat source* (one
device, one role).

**A thermostat (Generic Thermostat or another) or a relay on the whole house,
plus rooms with TRVs.** The boiler then runs only when the whole-house zone asks
for heat (after its own sensor). A TRV room that needs heat while that sensor is
warm stays cold: the integration cannot start the boiler for it. The way out:
the boiler relay as *Heat source* instead of on the whole house (with a
thermostat that also starts the boiler, a relay wired in parallel with it), or
the thermostat used as *Heat source* (with *Start and stop the source by its temperature*) instead of on the whole
house.

## How the integration controls the heat source

The source can be a `switch`, an `input_boolean` or a `climate` (e.g. the boiler
thermostat). A `switch` or an `input_boolean` is turned on and off.

A `climate` (a Hive, Nest, Tado or Netatmo thermostat, a Generic Thermostat)
starts the boiler only by its own target and sensor: switched to `heat` with a
low target it would not fire it. So with **Start and stop the source by its
temperature** (on by default) it stays in its heat mode and gets:

- to **start**: the *Maximum temperature* of the house (25 °C by default), not
  above the maximum of the thermostat;
- to **stop**: the *Heat source idle temperature*, by default the *Frost
  protection* temperature of the house (7 °C), not below its minimum. At the
  frost protection it does not heat by its own sensor meanwhile, but still
  protects the house against frost if Home Assistant stops.

**Heat source idle temperature** (optional, only with *Start and stop the source by its temperature*): a higher value,
e.g. 17.5 °C, lets the thermostat keep its own area at that temperature by its
own sensor while no room asks. Useful when it also heats radiators **without
TRVs** (a hallway thermostat, TRVs only in some rooms): those rooms are then
kept at about that temperature, and a TRV room that asks still gets the maximum.
It must be below the maximum of the house. Do not raise the house's *Frost
protection* for this: it is also the temperature of Off mode and of an open
window, and the lowest any level can go.

A target set on it by hand is taken back. Without *Start and stop the source by its temperature*, or for a
thermostat without a target temperature, only its mode is switched: `heat` (or
`auto`, without `heat`) to start and `off` to stop; it then heats by its own
target, which must be above its sensor.

> **Example (a Hive in the hallway, TRVs in the rooms):** the living room asks
> for heat, the Hive gets 25 °C and fires the boiler although the hallway is at
> 20 °C; once the living room is warm it gets 7 °C and the boiler stops.

It **starts** the source when:

- at least *Rooms needed to start the heat source* rooms ask for heat (1 by
  default, i.e. any; [secondary rooms](#when-a-room-heats) do not count), or
- a room is in **frost protection** and needs heat. Frost protection starts the
  source alone, without the rooms needed and even in a pause.

> **Only one room should start the boiler** (e.g. the living room with the
> thermostat it always had): leave *Can start the house heat source* on for
> that room and turn it off for the others, which become secondary rooms. Several
> rooms can start it too (the living room and the bedroom), the rest secondary.
> This replaces the *Reference room* of versions before 2.6.5.

It **stops** the source when the condition is no longer met.

**Minimum times**: *Heat source minimum on time* and *Heat source minimum off
time* (0 by default, that is no wait: the source follows the heat demand at
once). A larger value protects a boiler without its own anti-cycling from
frequent starts and stops. They hold over a Home Assistant restart too. When a minimum time ends,
the integration checks again at once.

> [!WARNING]
> **TRVs on every radiator: a bypass or a radiator without a TRV.**
>
> When the last room stops asking for heat (it reached its target), its TRVs
> get the target and it is up to them: many close fully (their sensor sits next
> to the warm radiator), some keep the valve slightly open. The heat source runs
> on until its minimum on time ends, when one is set, and the heat left in it
> and in the pipes still needs a way through. The installation should give the
> water one, as with plain mechanical TRVs: an automatic bypass, a boiler with
> an internal bypass, or one radiator without a TRV (often in the bathroom).
> Without one, choose a short *Heat source minimum on time* or 0 (the default),
> and consider *Keep the last TRV open* (below).

**Keep the last TRV open** (off by default; only with a *Heat source* and a
room with TRVs on it): when no
room asks for heat any more, the TRVs of the last room that asked stay open, so
the heat left in the source and the pipes has a way through, as with a bypass,
and the valve does not move again during the night (less noise, less battery).
When several rooms stop together, the one furthest below its target is chosen.

- The TRVs get the maximum temperature of the room (within the TRV's own
  maximum); TRVs commanded *On / off* stay on. TRVs commanded by *Preset* get
  that temperature too, as for the valve exercise, and their preset again
  afterwards.
- The room asks for no heat meanwhile: the heat source stays off. Its target
  stays the one of its rule (the card shows it, and the reason *Kept open for
  the heat source*).
- It ends when another room asks for heat, when a stronger rule takes the room
  (window, manual change, pause, mode Off or Summer, out of season, warm
  outside, valve exercise), or when the room itself is cold enough to ask for
  heat (its target minus the hysteresis); the TRVs then get the target again.
- What you accept by turning it on: the room may get warmer than its target
  (by the heat left in the installation), and its learning skips the time it
  is kept open (an open radiator would look like a room that cools slowly).
- Rooms with relays, with a Generic Thermostat or that do not heat from the
  heat source of the house are never kept open.

**Top up while the boiler runs** (per room, off by default; only for a room
with TRVs or relays that heats from the *Heat source*, not a Generic
Thermostat, which decides its relay by itself): while the boiler runs for other
rooms, a room that is a little below its target, inside its hysteresis (0.3 °C
by default), so it does not ask for heat yet, opens its TRVs or relay and heats
up to its target. It would ask soon and start the boiler again; this way the
boiler starts less often.

For a **secondary room**, which never starts the boiler, it is for comfort: the
room catches the heat while the boiler runs for other rooms, so it does not
stay below its target until another room starts the boiler again.

- The TRVs get the maximum temperature of the room, as when kept open; a relay
  is turned on. The target of the room stays the one of its rule (the card
  shows the reason *Topped up while the heat source runs for other rooms*).
- The room asks for no heat meanwhile: it never starts the boiler, never keeps
  it running and does not count for *Rooms needed*.
- It ends at the target, when the boiler stops, or when a stronger rule takes
  the room (window, manual change, pause, mode Off or Summer, warm outside, the
  optimal stop). A TRV still heating inside the hysteresis afterwards does not
  start the boiler again; below it, the room asks for heat as usual.
- With a circuit, only while that circuit is already open (no pump is started
  for a few tenths of a degree). Its learning skips that time, as when kept
  open.
- With *Keep the last TRV open*: the room kept open is not topped up. When
  another room asks for heat and the room kept open is inside its hysteresis,
  it goes on topped up at once: its TRVs stay open, without getting the
  target in between.

**In a pause** the integration does not control the source nor the circuit
relays, with one exception: frost protection, for which it turns on the circuit
of the room and the source and turns them off again when no longer needed (also
after a restart during the pause). A circuit already on or off when the pause
began is left as it is.

**Rooms needed example.** You have four TRV rooms and *Rooms needed* 2. Only the
bedroom asks for heat: the boiler does not start, and the card shows in the
bedroom *Not heating: waiting for other rooms: 1 of 2 ask for heat*. When the
living room asks too, the boiler starts.

## Heating circuits

Some houses have several heating circuits on one boiler, each with its own
pump or zone valve: floor heating and radiators, the ground floor and the
upper floor. The boiler must not run while every circuit is closed.

1. In the options of the house, at the heat source, pick the **Circuit
   relays** (`switch` or `input_boolean`), one per circuit. The field is shown
   only with a *Heat source*.
2. In each room on the boiler, pick its **Circuit** (the step after its
   devices; shown only when the house has circuit relays). A room without one
   works as before.

What the integration does:

- When a room asks for heat, the relay of its circuit is turned on **first**,
  then the boiler.
- When no room of a circuit needs it any more, the boiler stops **first**
  (after its minimum on time, if set), then the relay is turned off. While
  another circuit keeps the boiler running, a circuit no longer needed is
  closed at once.
- The boiler is not started for a room whose circuit is off (unavailable, or
  turned off by hand): the card says *its circuit (…) is off*.
- A secondary room does not open its circuit; it heats while its circuit is
  open for another room.
- Frost protection opens the circuit and starts the boiler.
- *Keep the last TRV open* keeps the TRVs of that room open, but its circuit
  closes once the boiler is off, so a pump does not run all night.
- A room waiting for *Rooms needed* does not open its circuit: the circuits
  open only when the boiler is to start.
- In a pause the circuits are not switched, except for frost protection.
- A circuit relay unavailable longer than *Alert when a device is unavailable
  longer than* is an important alert: the rooms of its circuit get no heat, and
  with *Rooms needed* above 1 the boiler may not start for the other rooms
  either (their pumps may then run without it). Repair the relay, or change the
  circuits of the house.
- No delays: the relay does not wait for a pump to run up or a valve to
  open. A zone valve with an end switch that starts the boiler by itself
  needs no circuit here.

## When a room "heats"

For the learning and the heating time, a room **heats only while its source
runs**:

- Generic Thermostat: when it reports heating (`hvac_action`);
- relay or on / off thermostat: when it is on;
- with a *Heat source* set: in addition, only while the source runs (not for a
  room with *Heats from the heat source of the house* off).

**Rooms with their own heat.** In a house with a *Heat source*, a room heated
otherwise (an electric heater, a heat pump, an air conditioner) has *Heats from
the heat source of the house* off, in its devices step. It then does not start
the boiler (neither for *Rooms needed* nor for frost protection) and heats while
its own device runs.

**Secondary rooms.** A room on the boiler can be made secondary: in the step
after its devices, *Can start the house heat source* off (on by default; asked
only when the room heats from the heat source of the house). A secondary room
never starts the boiler for itself, does not count for *Rooms needed* and is
not the cold room of the *Alert when a room stays colder than*; its
TRVs, valves or relays still open while it is below its target, so it takes
heat only while the boiler runs for another room. Good for rooms that should
not be cold but need not be warm at a set time: enclosed balconies, a guest
room, a hall, a storage room. On a mild day the boiler may run little, so a
secondary room may stay below its target for hours. Frost protection still
starts the boiler for it, for safety. Its learning and heating time count only
while the boiler runs, as for every room of the boiler. A secondary room asking
for heat does not end *Keep the last TRV open*.

A room that asks for heat while the source waits for other rooms cools down,
and this is learned as heat loss. While the state of the source is unknown,
nothing is learned.

## When a room below its target does not heat

The card says why, and the *Decision* sensor has the `no_heat_reason`
attribute:

| Reason | Meaning |
| --- | --- |
| the room is within the thermostat tolerance | only a little below the target, the thermostat still waits |
| within the hysteresis of … | the relay waits for the room to fall below target − hysteresis |
| stopped early: the heat already given still takes the room to ~… | *Use the learned inertia*: the room still warms by itself up to that |
| the relay waits for its minimum on / off time | relay protection |
| the heat source waits for its minimum on / off time | boiler protection |
| waiting for other rooms: X of Y ask for heat | *Rooms needed* |
| a secondary room: it takes heat when another room starts the heat source | *Can start the house heat source* off |
| its circuit (…) is off: the pump or valve does not run | the circuit relay of the room is off or unavailable, see [Heating circuits](#heating-circuits) |
| the heat source is off / its state is unknown | the boiler does not run or nobody knows |
| the thermostat is off | the room thermostat is `off` |

## Alerts about the source

- **The heat source is unavailable** longer than *Alert when a device is
  unavailable longer than* (15 minutes by default): then nothing heats, not even
  frost protection.
- **A circuit relay is unavailable** longer than the same time: the rooms of its
  circuit get no heat (see [Heating circuits](#heating-circuits)).
- **Alert when a room stays colder than** (in the *Alerts* options, 0 = off by
  default, shown only with more than one room): a room stays this many degrees
  below its target while others are warm (stuck valve, window left open).

## Dynamic tariff

With an *Energy price sensor* (e.g. Nord Pool, Tibber):

- at a **high price** (*High price from* or above), *Adjustment at high price*
  is added (−1 °C by default): the house is a bit colder while energy is
  expensive;
- at a **low price** (*Low price up to* or below), *Adjustment at low price* is
  added (+0.5 °C by default): the house warms a bit more while it is cheap.

The thresholds are in your sensor's unit (e.g. €/kWh). An empty threshold turns
its adjustment off.

**Example** (chosen values): high price from 0.30, the default adjustment
−1 °C, `home` 21 °C. When the price is 0.34, the target is 21 − 1 = 20 °C.

## PV surplus

With a *PV surplus sensor* (the power exported to the grid, in W): while the
surplus is at least *Surplus from* (1000 W by default), *Adjustment with
surplus* (+0.5 °C by default) is added. Useful only with electric heating or a
heat pump: you use your own energy instead of selling it cheaply.

The energy adjustments add up with the others (compensation, solar gain), the
sum is limited to ±3 °C and never applies to a frost protection (see
[chapter 6](06-weather.md#how-the-adjustments-add-up)).

## Heating time

- **Heating time** of every room: how long the room heated (while its source
  ran).
- **Heating time** of the house: how long the heat source ran; without a
  source, how long at least one room heated.
- **Heat demand** (binary sensor) of the house: whether heat is asked for now; of
  a room: whether the room asks, with the `heating` attribute (whether its
  source runs).

The time sensors are increasing totals (hours), so Home Assistant keeps them in
the long-term statistics. The card shows the time per day, week or month (see
[chapter 10](10-card.md)).
