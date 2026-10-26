# 7. Optimal start and stop, learning

*[Română](07-anticipare-si-invatare.ro.md) · [Contents](README.md)*

This chapter explains in plain words how every room learns and how it uses what
it learned. The full calculations, with every case and the simulations, are in
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

## How a room learns to warm up

You do not have to describe the house (radiators, insulation, boiler). The room
**measures its own** heatings, called **episodes**:

- an episode starts when the room asks for heat, is at least the *tolerance*
  below the target and its heat source really runs;
- it ends when the room reaches the target or the heating stops;
- it is kept only if it lasted at least 10 minutes, the temperature rose, no
  window was open and it is the cold season (not mode Off or Summer, not outside
  the season);
- a restart of Home Assistant does not end it: the episode in progress is saved
  and goes on if the room still heats after the restart. If the room no longer
  heats, it is dropped, because it is not known when the heating stopped.

For every episode it notes how many degrees the room rose, in how many minutes,
and the mean outdoor temperature.

From the episodes it works out a simple formula:

```
minutes = fixed part + degrees × minutes per degree
```

- **Fixed part**: the minutes until the room starts to rise (the boiler starts,
  the water and the radiators warm up). The same for a small and for a large
  rise.
- **Minutes per degree**: how long every degree takes. They depend on the
  outdoor temperature: colder outside, usually longer.

**Example** (values assumed for the example): fixed part 25 minutes, and at
5 °C outside the room needs 50 minutes per degree. To rise from 18 to 21 °C
(3 degrees): 25 + 3 × 50 = **175 minutes**, so almost 3 hours.

**What is kept.** The last 25 small episodes (below 1 °C) and the last 25 large
ones (1 °C or more), separately, so the many small cycles of the thermostat
never push the large morning rises out of memory. The numbers are worked out
again after every episode, with the least squares method (picking the numbers
that fit all episodes best).

**Until the first episode** a safe value is used: 60 minutes per degree, no fixed
part. The card shows *learning…* and below *default 60 min/1°C*.

**How long learning takes.** A few days. The more mornings with large rises
(e.g. after `sleep`), the sooner the fixed part is learned.

## Optimal start, step by step

For the next change to a **warmer** level:

1. **How many degrees**: the next level minus the room temperature now.
2. **What the outdoor temperature will be**: with a weather entity with an hourly
   forecast, the mean forecast between the start and the change; otherwise the
   outdoor temperature now. Since the start depends on the temperature and the
   other way round, the calculation is done 3 times.
3. **How many minutes**: the formula above.
4. **The limit**: never earlier than *Maximum early start* (120 minutes by
   default).
5. Once started, it continues until the change, even if the room is warm
   earlier. The rules above the schedule (window, presence…) can interrupt it.

**Example** (chosen values, with a fixed part of 25 minutes and 50 minutes per
degree at a forecast of 5 °C): the bedroom is at 19.5 °C, `home` 22 °C at 07:00.
Degrees: 22 − 19.5 = 2.5. Minutes: 25 + 2.5 × 50 = 150. With the default limit
of 120 minutes the start is at 07:00 − 120 = **05:00** (without the limit it
would be 04:30).

The integration wakes up exactly at the calculated start, not only at the
periodic check.

**Beware of waits that are not learned.** The learned minutes start when the
room really heats. The time the room asks for heat while the source waits (the
minimum off time, *Rooms needed to start the heat source* above 1, the reference
room) is not part of the learning. With such waits, the optimal start may reach
the target later.

## How a room learns to cool down

When the room no longer asks for heat, it cools down. The integration measures
this too: a **cooling episode** lasts from the end of one heat demand to the
next and is kept if it lasted at least 10 minutes, the temperature fell and no
window was open.

A room loses heat faster the warmer it is than outside. From every episode a
**coefficient** is worked out, and the room keeps the mean of the last 30.

**Example** (chosen values): coefficient 0.0345 per hour. At 21 °C in the room
and 0 °C outside, the room loses 21 × 0.0345 = 0.72 °C per hour; at 10 °C
outside, (21 − 10) × 0.0345 = 0.38 °C per hour.

## Optimal stop, step by step

Before a change to a **colder** level:

1. **The comfort** of the current level: the level minus the *tolerance*. The
   tolerance is the `cold_tolerance` of Generic Thermostat, the hysteresis for
   relays and thermostats without `hvac_action`, and the *Optimal stop
   tolerance* for the other thermostats.
2. **How long the room can go without heat** until it falls to the comfort,
   from the learned coefficient and the expected outdoor temperature (the
   forecast of the stop period, in 3 passes).
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
- **The learning**, in *Details*: the number of episodes, the fixed part and the
  minutes per degree now (e.g. *12 episodes · 25 min + 49 min/°C now*), how fast
  the room falls now, and the last episode.
- The sensors **Heating rate** (minutes per degree now, with attributes) and
  **Cooling rate** (how fast the room falls now without heating).

## Resetting the learning

If you changed something important (other radiators, another boiler curve, new
insulation), the learning adapts by itself within a few weeks. To start from
zero at once, press **Reset heating learning** or **Reset cooling learning**
(the room buttons, or *Reset* in the card *Details*, with a second click to
confirm).

## When it is not recommended

With **TRVs** and a boiler started by a thermostat that is **not in Home
Assistant**, the integration cannot know when the boiler runs. The learning is
not reliable, so optimal start and stop are not recommended. The way out is to
put the boiler (or its relay) in Home Assistant and pick it as *Heat source*
(see [chapter 8](08-heat-source-and-energy.md)).
