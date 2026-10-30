# 8. Heat source and energy

*[Română](08-sursa-si-energie.ro.md) · [Contents](README.md)*

## Do you need a *Heat source*?

It depends on who starts the boiler:

| Your case | *Heat source* |
| --- | --- |
| A **Generic Thermostat** starts the boiler (through its relay) | **Empty.** GT already starts the boiler. Never pick the relay GT uses. |
| A room **relay** starts the boiler or a heater directly | **Empty.** The relay is already controlled by the integration. |
| **TRVs** or zone valves, and the boiler has a relay or a thermostat in Home Assistant | **Pick the boiler** (or its relay). The integration starts it when rooms ask for heat. |
| TRVs, and the boiler is started by a thermostat that is **not in Home Assistant** | Nothing to pick. It works, but the learning is not reliable (see [chapter 7](07-optimal-start-stop-and-learning.md#when-it-is-not-recommended)). |

Why it matters: a TRV only opens or closes the radiator valve. If the boiler
does not start, the radiator stays cold.

## How the integration controls the heat source

The source can be a `switch`, an `input_boolean` or a `climate` (e.g. the boiler
thermostat). A `climate` is started with the mode `heat` (or `auto`, without
`heat`) and stopped with `off`.

It **starts** the source when:

- at least *Rooms needed to start the heat source* rooms ask for heat (1 by
  default, i.e. any), or
- with a *Reference room* set, when that room asks for heat (the others only
  open or close their valves), or
- a room is in **frost protection** and needs heat. Frost protection starts the
  source alone, without the rooms needed, without the reference room and even in
  a pause.

It **stops** the source when the condition is no longer met.

**Minimum times**: *Heat source minimum on time* and *Heat source minimum off
time* (0 by default, that is no wait: the source follows the heat demand at
once). A larger value protects a boiler without its own anti-cycling from
frequent starts and stops. They hold over a Home Assistant restart too. When a minimum time ends,
the integration checks again at once.

**TRVs on every radiator.** When the last room stops asking for heat (it
reached its target), its TRVs get the target and close, but the heat source runs
until its minimum on time ends, when one is set. The integration does not keep a TRV open for it:
that would heat the room above its target. The installation itself must give the
water a way through, as it must with plain mechanical TRVs: an automatic bypass,
a boiler with an internal bypass, or one radiator without a TRV (often in the
bathroom). Without one, choose a short *Heat source minimum on time* or 0 (the
default), so the source stops as soon as no room asks for heat.

**In a pause** the integration does not control the source, with one exception:
it starts it for frost protection and stops it again when no longer needed
(also after a restart during the pause).

**Rooms needed example.** You have four TRV rooms and *Rooms needed* 2. Only the
bedroom asks for heat: the boiler does not start, and the card shows in the
bedroom *Not heating: waiting for other rooms: 1 of 2 ask for heat*. When the
living room asks too, the boiler starts.

## When a room "heats"

For the learning and the heating time, a room **heats only while its source
runs**:

- Generic Thermostat: when it reports heating (`hvac_action`);
- relay or on / off thermostat: when it is on;
- with a *Heat source* set: in addition, only while the source runs.

A room that asks for heat while the source waits for other rooms cools down,
and this is learned as cooling. While the state of the source is unknown,
nothing is learned.

## When a room below its target does not heat

The card says why, and the *Decision* sensor has the `no_heat_reason`
attribute:

| Reason | Meaning |
| --- | --- |
| the room is within the thermostat tolerance | only a little below the target, the thermostat still waits |
| within the hysteresis of … | the relay waits for the room to fall below target − hysteresis |
| the relay waits for its minimum on / off time | relay protection |
| the heat source waits for its minimum on / off time | boiler protection |
| waiting for other rooms: X of Y ask for heat | *Rooms needed* |
| waiting for the reference room … | *Reference room* |
| the heat source is off / its state is unknown | the boiler does not run or nobody knows |
| the thermostat is off | the room thermostat is `off` |

## Alerts about the source

- **The heat source is unavailable** longer than *Alert when a device is
  unavailable longer than* (15 minutes by default): then nothing heats, not even
  frost protection.
- **Alert when a room stays colder than** (0 = off by default): a room stays this
  many degrees below its target while others are warm (stuck valve, window left
  open). Useful only with several rooms.

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
