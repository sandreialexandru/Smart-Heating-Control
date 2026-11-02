# 7. Optimal start and stop, learning

*[Română](07-anticipare-si-invatare.ro.md) · [Contents](README.md)*

This chapter explains in plain words how every room learns and how it uses what
it learned. The full calculations, with examples and simulations, are in
[How the integration learns](../learning.md).

## Why anticipation is needed

The schedule says "`home` 21 °C from 07:00". Without anticipation, the heating
starts at 07:00 and the room is warm only around 08:30. With **optimal start**,
the integration starts heating earlier, so at 07:00 the room is already at
21 °C.

The other way round, the schedule says "`sleep` 18 °C from 22:00". The room is
warm and would cool slowly anyway. With **optimal stop**, the colder level
begins a bit earlier, while the room stays comfortable until 22:00. Energy is
saved without you feeling the difference.

Both are turned on per room, in the *Schedule* step (see
[chapter 3](03-rooms.md#step-7-schedule)). The optimal stop needs an outdoor
temperature (sensor or weather entity).

## How a room learns

You do not have to describe the house (radiators, insulation, boiler, floor
heating). The room **watches itself** all the time, with and without heating,
and learns four numbers:

- **Heating**: how many °C per hour the heating adds when it gives its full
  heat.
- **Weather curve**: how much more (or less) the heating gives when it is
  colder outside. A boiler with outdoor compensation heats the water more in
  the cold; a heat pump may give less; a fixed water temperature or an
  electric heater gives the same, and the curve is learned as 0.
- **Heat loss**: how fast the room cools, in proportion to how much warmer it
  is than outside (colder outside, faster).
- **Inertia**: how slowly the heating reacts. After a start the boiler, the
  water and the radiators (or the floor) warm up first; after a stop they keep
  giving heat for a while. Radiators: usually 10 – 30 minutes; floor heating:
  hours. Nothing has to be set: it is learned.

**Example** (values assumed for the example): heating 2 °C per hour, no
weather curve, loss 0.05
per hour per degree of difference, inertia 30 minutes. At 19 °C inside and 5 °C
outside the room loses 0.05 × (19 − 5) = 0.7 °C per hour, so with the heating
fully on it rises 2 − 0.7 = 1.3 °C per hour. From 18 to 21 °C, starting cold,
at 5 °C outside it needs **186 minutes**, about 3 hours (calculated minute by
minute, with the inertia).

**How it learns.** Every 30 minutes the room notes how much it rose or fell,
whether it heated and the difference to outside. The numbers are the ones that
fit all these measurements best (the least squares method). Older measurements
count less (half after a week), so the learning follows the room by itself
when something changes. A measurement far from what the room usually does (a
door left open, cooking) counts less. Not used: measurements with a window
open, with the state of the heat source unknown, during the valve exercise, or
outside the cold season (mode Off or Summer, outside the season).

**Until it is learned** (4 hours with heating and 4 hours without, usually
within the first day) a safe value is used: 60 minutes per degree, no inertia.
The card shows *learning… 2 of 4 h with heating, 1 of 4 h without* and below
*default 60 min/1°C*.

**Without an outdoor temperature** in the house, the heat loss is learned as a
constant number of degrees per hour, and no weather curve is learned.

## Optimal start, step by step

For the next change to a **warmer** level:

1. **How many degrees**: the next level minus the room temperature now.
2. **What the outdoor temperature will be**: with a weather entity with an hourly
   forecast, the mean forecast between the start and the change; otherwise the
   outdoor temperature now. Since the start depends on the temperature and the
   other way round, the calculation is done 3 times.
3. **How many minutes**: the room is simulated minute by minute with the
   heating on, from its temperature now and how warm its radiators already are
   (the inertia).
4. **The limit**: never earlier than *Maximum early start* (120 minutes by
   default).
5. Once started, it continues until the change, even if the room is warm
   earlier. The rules above the schedule (window, presence…) can interrupt it.

**Example** (the room of the example above, a forecast of 5 °C): the bedroom
is at 18 °C, `home` 21 °C at 07:00. Minutes: 186. With the default limit of 120
minutes the start is at 07:00 − 120 = **05:00** (without the limit it would be
07:00 − 186 minutes = 03:54).

The integration wakes up exactly at the calculated start, not only at the
periodic check.

**Beware of waits that are not learned.** The learned minutes start when the
room really heats. The time the room asks for heat while the source waits (the
minimum off time, *Rooms needed to start the heat source* above 1, the reference
room) is not part of the learning. With such waits, the optimal start may reach
the target later.

## Optimal stop, step by step

Before a change to a **colder** level:

1. **The comfort** of the current level: the level minus the *tolerance*. The
   tolerance is the `cold_tolerance` of Generic Thermostat, the hysteresis for
   relays and thermostats without `hvac_action`, and the *Optimal stop
   tolerance* for the other thermostats.
2. **How long the room can go without heat** until it falls to the comfort,
   simulated with the learned heat loss, the inertia (warm radiators still give
   heat) and the expected outdoor temperature (the forecast of the stop period,
   in 3 passes).
3. **The limit**: never earlier than *Maximum early stop* (30 minutes by
   default). Until the cooling is learned, the colder level starts exactly this
   early.
4. Once started, it continues until the change. If the room still falls below
   the comfort (it cooled faster than learned), the stop is **cancelled**: the
   current level returns until the change. If this happens often, lower
   *Maximum early stop*.

**Example** (chosen values): `home` 22 °C until 22:00, tolerance 0.5 °C, so the
comfort is 21.5 °C. If, from what was learned, the room falls from 22 to
21.5 °C in 40 minutes, `sleep` starts at 22:00 − 40 = **21:20**. With the
default limit of 30 minutes, it starts at **21:30**.

## What you see in the card and the sensors

- **Time to target**: while the room is below the target, below the target
  temperature e.g. *~35 min* (the `time_to_target` attribute of the *Decision*
  sensor).
- **The next optimal start / stop**, in the room *Details*, e.g. *Start for
  preset home (21.0°) at 07:00 · begins ~05:10 · outdoor forecast 2.4°*;
  once started, *running since …*.
- **The expected temperature at the change**, during an optimal stop, e.g.
  *~21.5° at 22:00* (the `stop_forecast` attribute).
- In the chart, the next optimal start / stop is a shaded period.
- **The learning**, in *Details*: the minutes per degree now and the inertia
  (e.g. *45 min/°C now · inertia 30 min*), or the progress while learning, and
  how fast the room falls now without heating.
- The sensors **Heating rate** (minutes per degree now, with the learned
  numbers as attributes) and **Cooling rate** (how fast the room falls now
  without heating).

## Resetting the learning

If you changed something important (other radiators, another boiler curve, new
insulation), the learning adapts by itself within one or two weeks. To start from
zero at once, press **Reset learning** (the room button, or *Reset* in the card
*Details*, with a second click to confirm); the room learns again within about
a day.

## When it is not recommended

With **TRVs** and a boiler started by a thermostat that is **not in Home
Assistant**, the integration cannot know when the boiler runs. The learning is
not reliable, so optimal start and stop are not recommended. The way out is to
put the boiler (or its relay) in Home Assistant and pick it as *Heat source*
(see [chapter 8](08-heat-source-and-energy.md)).
