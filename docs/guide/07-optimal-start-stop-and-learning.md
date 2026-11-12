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
and learns five numbers:

- **Heating**: how many °C per hour the heating adds when it gives its full
  heat.
- **Weather curve**: how much more (or less) the heating gives when it is
  colder outside. A boiler with outdoor compensation heats the water more in
  the cold; a heat pump may give less; a fixed water temperature or an
  electric heater gives the same, and the curve is learned as 0.
- **Heat loss**: how fast the room cools, in proportion to how much warmer it
  is than outside (colder outside, faster).
- **Sun**: how many °C per hour the sun adds. It is learned only with a
  weather entity (it tells the clouds) and only when it is clearly seen;
  otherwise it is 0. The sun height is calculated from the time and the
  location of Home Assistant, so the orientation of the windows is not needed.
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
open, with the state of the heat source unknown, during the valve exercise,
while the TRVs are kept open for the heat source (*Keep the last TRV open*) or
the room is topped up while the boiler runs, or
outside the cold season (mode Off or Summer, outside the season).

**Until it is learned** (4 hours with heating and 4 hours without, usually
within the first day) a safe value is used: 60 minutes per degree, no inertia.
The card shows *learning…* with two bars, *with heating 2 of 4 h* and
*without heating 1 of 4 h*, and below them *default 60 min/1°C*.

**Without an outdoor temperature** in the house, the heat loss is learned as a
constant number of degrees per hour, and no weather curve is learned.

**The sun in the predictions.** Once learned, the optimal start and stop, the
time to target and the predicted temperature of the card count the sun: its
height at that time and the clouds of the hourly forecast (else the clouds of
now). Example (the room above, a learned sun of 1.5 °C/h, a sun signal of 0.3,
so 1.5 × 0.3 = 0.45 °C/h, 0 °C outdoors): from 18 to 21 °C it needs 161
minutes instead of 231. The room setting *Solar gain* is separate and stays:
it lowers the target while the sun shines. Details in
[How the integration learns](../learning.md#10-the-sun).

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
minimum off time, *Rooms needed to start the heat source* above 1, a secondary
room waiting for another room) is not part of the learning. With such waits, the optimal start may reach
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

## Starting and stopping by the inertia

Only for rooms the integration switches on and off itself: a relay, a
thermostat commanded *On / off (hvac mode)*, or TRVs with *Heat by the room sensor* (below). The hysteresis keeps the room in a
band, e.g. 20.7 – 21.3 °C around 21 °C. Without anything else, the heating stops
at 21.3 °C and the radiators, still hot, push the room higher; it starts again
at 20.7 °C and the room still falls until the radiators are warm.

With **Use the learned inertia** (on by default, in the *On / off control*
step), once the room has learned its model:

- the heating **stops** as soon as the heat still on its way would take the
  room to the top of the band by itself;
- it **starts** as soon as the room would fall to the bottom of the band
  before the heat arrives.

The band stays the limit: at 21.3 °C it always stops, at 20.7 °C it always
starts, and the minimum on / off times still apply. While stopped early and
below the target, the card says *stopped early: the heat already given still
takes the room to ~21.3°*.

**Example** (assumed values: cast iron radiators that add 2 °C per hour,
inertia 60 minutes, target 21 °C): the band alone stops at 21.3 °C and the room
peaks at about 21.6 °C; with the learned inertia it stops at about 21.1 °C and
peaks at about 21.3 °C.

Simulation (fictional rooms, not measurements): heating h and loss k of each
room as below, the outdoor temperature random between −5 and 10 °C each day
with ±3 °C between day and night, 21 °C from 06:00 to 23:00 and 18.5 °C at
night, the sensor rounded to 0.1 °C, small random disturbances, learned from
the start with the code of the integration; days 5 – 20 between 08:00 and
23:00, three runs with different weather. Radiators 20 min: h 2.5 °C/h,
k 0.06; 30 and 60 min: h 2, k 0.05; floor: h 1.6, k 0.04.

| Room (relay, hysteresis 0.3 °C) | Mean distance from the target, band alone → with the inertia | Time more than 0.5 °C above / below the target, band alone → with the inertia | Starts per hour |
|---|---|---|---|
| Radiators, inertia 20 min | 0.24 → 0.19 – 0.20 °C | 0.3 – 0.8 % / 0.7 – 1.1 % → 0 / 0 – 0.2 % | 0.45 → 0.50 |
| Radiators, inertia 30 min | 0.26 → 0.21 °C | 2.0 – 2.4 % / 2.4 – 2.9 % → 0 / 1.8 – 2.1 % | 0.31 → 0.36 |
| Cast iron, inertia 60 min | 0.33 – 0.34 → 0.27 °C | 13.7 – 14.7 % / 3.8 – 4.6 % → 0 / 6.3 – 6.8 % | 0.20 → 0.26 |
| Floor heating, inertia 180 min | 0.90 – 0.92 → 0.44 – 0.47 °C | 31 – 34 % / 34 – 36 % → 7 – 9 % / 16 – 18 % | 0.07 → 0.6 |

The slower the heating, the larger the gain: little for ordinary radiators, the
deviation halved for floor heating. The heating ran as long or less (floor:
52 – 55 % of the time → 43 – 45 %), since no heat goes above the band.

**TRVs heated by the room sensor** (*Heat by the room sensor*): the room sensor
decides the heat demand with the hysteresis, like a relay, so the learned
inertia works the same way there. In a simulation of TRVs that follow 3
minutes later (otherwise the same assumptions as above):

| Room (heating by the room sensor) | Mean distance from the target, band alone → with the inertia | Time more than 0.5 °C above the target | Starts per hour |
|---|---|---|---|
| Radiators, inertia 20 min | 0.28 → 0.23 – 0.25 °C | 5.3 – 6.7 % → 0 – 0.3 % | 0.40 → 0.45 |
| Radiators, inertia 30 min | 0.28 – 0.31 → 0.23 – 0.25 °C | 6.4 – 7.4 % → 0 – 0.1 % | 0.30 → 0.32 |
| Cast iron, inertia 60 min | 0.36 → 0.30 – 0.31 °C | 17.9 – 20.1 % → 0 | 0.20 → 0.23 |

The time more than 0.5 °C below the target stayed about the same for the
radiators (1.0 – 4.3 % → 0.7 – 3.0 %) and rose for cast iron (3.4 – 6.3 % →
7.3 – 8.0 %).

Thermostats and TRVs commanded by *Temperature* without heating by the room sensor, and Generic
Thermostat, regulate by themselves: the integration does not switch them, so
the learned inertia does not apply there.

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
  (e.g. *45 min/°C now · inertia 30 min*), or the progress while learning, the
  learned sun (only once seen), and how fast the room falls now without
  heating.
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
