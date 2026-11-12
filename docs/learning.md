# How Smart Heating Control learns (the thermal model of a room)

*[Română](learning.ro.md)*

This document explains how each room learns how it heats up, how its heating
changes with the outdoor temperature (the weather curve), how it loses heat,
how much the sun warms it and how slow its heating is to react (the thermal
inertia), how the
numbers are calculated, and how they are used for **optimal start**,
**optimal stop** and the **time to target** shown on the card. Every number in
the examples is either calculated in the text or stated as an assumption of
the example.

All calculations are done in °C internally; with a house in °F only the
display is converted (1 °C = 1.8 °F).

- [1. Why learn at all](#1-why-learn-at-all)
- [2. The model of a room](#2-the-model-of-a-room)
- [3. What is measured: stretches of 30 minutes](#3-what-is-measured-stretches-of-30-minutes)
- [4. How heating and loss are calculated](#4-how-heating-and-loss-are-calculated)
- [5. How the inertia is learned](#5-how-the-inertia-is-learned)
- [6. When the learned model is used](#6-when-the-learned-model-is-used)
- [7. Using the model](#7-using-the-model)
- [8. A house without an outdoor temperature](#8-a-house-without-an-outdoor-temperature)
- [9. Fictional simulations](#9-fictional-simulations)
- [10. The sun](#10-the-sun)
- [11. Limits](#11-limits)
- [12. Where to see it](#12-where-to-see-it)

---

## 1. Why learn at all

To have a room at 21 °C at 07:00, the heating has to start earlier. How much
earlier depends on the room: the heat source, the radiators or the floor
heating, the insulation, the outdoor temperature. Instead of asking for these
values, every room measures its own behaviour and learns from it. Nothing has
to be set: also the inertia (slow floor heating or fast radiators), the
weather curve of the boiler and the warmth of the sun are learned, not chosen
in the configuration.

---

## 2. The model of a room

The room is treated as one thermal mass that gets heat from its heating and
loses heat to the outdoors, in proportion to how much warmer it is than
outside:

```
rise per hour = (h − c × outdoor) × q − k × (room − outdoor) + s × sun
```

| Number | Name in the attributes | Meaning |
|---|---|---|
| h | `heating_per_hour` | how many °C per hour the heating adds when it gives its full heat, at 0 °C outdoors |
| c | `weather_curve` | how many °C per hour more the heating adds for each °C colder outdoors (*The weather curve* below) |
| k | `loss_per_hour` | which part of the inside / outside difference is lost per hour |
| s | `sun_gain` | how many °C per hour the sun adds at a sun signal of 1 (section 10) |
| sun | | the sun signal of now, from 0 (night, thick clouds) to 1 (the sun overhead in a clear sky) |
| q | `heat_reaching_now` | how much of the heating reaches the room now, from 0 (none) to 1 (all) |
| τ | `inertia_minutes` | how slowly q follows the heating (the thermal inertia) |

**The inertia.** After the heating starts, the boiler, the water and the
radiators (or the screed of a floor heating) warm up first; after it stops,
they keep giving heat for a while. q follows the heating with the delay τ:

```
q moves towards 1 (heating on) or 0 (heating off) by (target − q) × minutes ÷ τ
```

so after τ minutes q has covered about 63 % of the way (1 − e⁻¹), after 3 × τ
about 95 %. τ = 0 means no inertia: q is 1 as soon as the heating runs.

**Example** (values assumed for the example): h = 2 °C/h, c = 0 (no weather
curve), k = 0.05 per hour, τ = 30 minutes. Room at 19 °C, outdoors 5 °C, heating fully reached (q = 1):

- loss: 0.05 × (19 − 5) = **0.7 °C/h**;
- rise: 2 × 1 − 0.7 = **1.3 °C/h**;
- without heating (q = 0) the room falls by 0.7 °C/h.

The loss grows with the difference: at 21 °C and 0 °C outdoors it is
0.05 × 21 = 1.05 °C/h. Colder outside, the heating has less left to rise the
room, so every degree takes longer: at 20 °C room temperature, 60 ÷ (2 −
0.05 × 20) = **60 minutes per degree** at 0 °C outdoors, 60 ÷ (2 − 0.05 × 10)
= **40 minutes** at 10 °C.

**The weather curve.** A boiler with a weather curve (outdoor compensation)
makes the water hotter when it is colder outside, so the radiators give more
heat; a heat pump may give less in the cold; a boiler at a fixed water
temperature or an electric heater gives the same. c learns this: positive
when the heating gives more in the cold, negative when it gives less, 0 when
it gives the same. Example: the room above with c = 0.05 °C/h per °C gives
2 − 0.05 × (−5) = **2.25 °C/h** at −5 °C outdoors and 2 − 0.05 × 10 =
**1.5 °C/h** at 10 °C. From 18 to 21 °C, starting cold:

| Outdoor | without curve (c = 0) | with c = 0.05 |
|---|---|---|
| −5 °C | 303 minutes | 237 minutes |
| 5 °C | 186 minutes | 224 minutes |
| 10 °C | 156 minutes | 217 minutes |

A model without the curve would start an hour too early at −5 °C and an hour
too late at 10 °C in such a house.

---

## 3. What is measured: stretches of 30 minutes

The room is watched all the time, with or without heating. Every **stretch of
30 minutes** gives one measurement:

- how much the room rose or fell, per hour;
- the mean of q over the stretch (for each candidate τ, section 5);
- the mean of (room − outdoor) over the stretch;
- the mean of q × outdoor over the stretch (for the weather curve);
- the mean sun signal over the stretch (section 10).

Why 30 minutes: long enough that the sensor step (usually 0.1 °C) is small
against the change, short enough to see a heating cycle.

**A stretch is not used** when:

- a **window or door sensor** of the room (or a linked one) was open;
- the **state of the heat source** was unknown;
- the **valve exercise** was running;
- the TRVs were **kept open for the heat source** (*Keep the last TRV open*:
  the leftover heat would look like a room that cools slowly), or **topped
  up** while the heat source runs for other rooms;
- the house has an outdoor temperature (sensor or weather entity) but it was
  **unknown**;
- the house has a weather entity but its clouds were **unknown in daylight**
  (the sun signal is unknown; at night it is 0 anyway);
- the readings were more than **20 minutes** apart (the stretch starts again);
- it is not the **cold season** (mode Off or Summer, or outside the heating
  season).

"Heating" means what it meant before: the room asks for heat **and its heat
source runs** (Generic Thermostat `hvac_action`, the relay or on / off
thermostat on, the *Heat source* of the house if one is set).

**Example** (with the room of section 2): 30 minutes with the heating on, q
from 0.5 to 0.82 (with τ = 30: 1 − 0.5 × e⁻¹ = 0.82; mean 0.68), the room at
about 19 °C, outdoors 5 °C. Rise: 2 × 0.68 − 0.05 × 14 = 1.36 − 0.7 =
0.66 °C/h, so 0.33 °C in the 30 minutes. The integration sees the 0.33 °C, the
0.68 and the 14; it has to find h, c and k (and s, from the sun signal).

Nothing is kept per stretch: only the sums of the least squares (section 4),
so the memory does not grow and a restart keeps everything learned (the
stretch in progress is dropped).

---

## 4. How heating and loss are calculated

Every stretch is one equation:

```
measured rise per hour = h × (mean q) − c × (mean q × outdoor) − k × (mean room − outdoor) + s × (mean sun)
```

h, c, k and s are the numbers for which the equations of all stretches are
**as close as possible** to what was measured: the sum of the squared
differences is the smallest (**least squares**). Four unknowns give four
equations (the normal equations), solved after every stretch by Gaussian
elimination:

```
h × Σ q²   − c × Σ q·p   − k × Σ q·d   + s × Σ q·S   = Σ q·r
h × Σ q·p  − c × Σ p²    − k × Σ p·d   + s × Σ p·S   = Σ p·r
h × Σ q·d  − c × Σ p·d   − k × Σ d²    + s × Σ d·S   = Σ d·r
h × Σ q·S  − c × Σ p·S   − k × Σ d·S   + s × Σ S²    = Σ S·r
```

(q: mean q, p: mean q × outdoor, d: mean room − outdoor, S: mean sun signal,
r: rise per hour of each stretch.)

**Older stretches weigh less.** Every stretch keeps its weight for a week, then
weighs half, after two weeks a quarter (half life **7 days**). So the model
follows a room that changes (a new weather curve, new radiators, the season)
without having to be reset.

**Stretches far from the others weigh less.** A door left open without a
sensor, cooking, a sun the weather entity did not see: the room does what the model does not expect.
After 10 stretches, each new stretch is compared with what the model said
before learning from it. The usual difference is the weighted mean of these
differences; a stretch more than **2.5 times** the usual difference away
counts with a weight in proportion (at 5 times the usual difference: half).
Such a stretch still counts a little, so when the room really changed the
model follows it.

**A tiny pull towards the default** (1 °C/h, no curve, no loss, no sun), worth about
1 % of one stretch, keeps the first stretches from giving wild numbers; after a day it
no longer matters.

**Impossible values:**

- a **negative loss** (the room would warm up by itself): the loss is set to 0
  and the rest is fitted again;
- a **weather curve that would leave no heating** (h − c × outdoor zero or
  less) at −20 °C or at 20 °C outdoors, the range of a heating season: the
  curve is set to 0 and the rest is fitted again;
- a **negative sun gain** (the sun would cool the room): the sun is set to 0
  and the rest is fitted again; the sun is also left out while it is not
  clearly seen (section 10);
- a **heating of zero or less**: that candidate is not used.

**When the curve is learned.** The curve can be told apart from the heating
only when the room heated at different outdoor temperatures. It is used once
the outdoor temperatures of the stretches with heating have a standard
deviation of at least **1 °C** (for example a day and a night ±1.5 °C apart);
before that it is 0. Why 1 °C: in a simulation (10 days, outdoor 5 °C with a
daily swing, predictions down to −10 °C), a house with a curve of 0.05 °C/h
per °C missed by up to 540 minutes while its curve was not learned, while a
house without a curve, with a small wrong curve learned, missed by up to 90
minutes. With 1 °C the curve of the first house was learned (error at most 8
minutes) once its outdoor temperatures had a deviation of 1.5 °C; below 1 °C a
wrong curve went up to 330 minutes. Over a few weeks of winter the outdoor
temperatures vary far more than that.

---

## 5. How the inertia is learned

τ cannot be calculated like h and k (q depends on it in a curved way). The
integration learns **ten candidates at the same time**, each with its own τ:

```
0, 10, 20, 30, 45, 60, 90, 120, 180, 240 minutes
```

For each candidate q is followed with its τ, and h, c, k and s are fitted as in
section 4. Before learning from a stretch, each candidate **predicts** it; the
candidate with the smallest mean squared prediction error (forgotten like the
stretches) is the one used. The diagnostics show all ten with their errors.

**Why it matters** (the room of section 2, 18 → 21 °C, outdoors 0 °C, the
heating starts from cold, q = 0):

| | minutes |
|---|---|
| τ = 30 minutes | **231** |
| the same room without inertia (τ = 0) | 176 |

Without the inertia the start would be 55 minutes too late. After a stop the
effect is the other way: the room of section 2 at 21 °C (q = 1, just heated),
comfort down to 20.5 °C, outdoors 0 °C, needs **82 minutes** to fall to the
comfort with τ = 30, against 29 minutes without inertia: the optimal stop can
begin almost an hour earlier.

---

## 6. When the learned model is used

The model is used once it has seen **8 stretches with the heating on** (mean
q at least 0.5) **and 8 without** (mean q at most 0.2), that is 4 hours of
each. Both are needed: with heating only, the heating and the loss cannot be
told apart. These counts are forgotten like the stretches.

Until then the default is used: **1 °C per hour (60 minutes per degree), no
curve, no loss, no inertia**, and no optimal stop is calculated (the room *Maximum
early stop* is used as it is). In a lived-in room the 4 + 4 hours usually come
within the first day.

---

## 7. Using the model

All predictions are a **simulation minute by minute** with the learned model,
from the room temperature and the q of now, for at most 24 hours. Once a sun
gain is learned, the sun of each minute is counted: the sun height of that
time of day and the clouds of the hourly forecast for that hour (else the
clouds of now). An optimal start or stop counts the sun of the period it runs
in (section 10).

### Optimal start

For the next scheduled change to a warmer level (for example *Sleep* 18 °C →
*Home* 21 °C at 07:00):

1. the simulation runs with the heating on until the room reaches the level
   of the next preset. Example: the room of section 2 at 18 °C, a mean
   forecast of 5 °C: **186 minutes**; at −5 °C: **303 minutes**;
2. the outdoor temperature is the **mean forecast** between the start and
   07:00 (with a weather entity that has an hourly forecast; otherwise the
   measured value). The start depends on that temperature and the temperature
   on the start, so it is worked out **3 times**, each time from the period
   found before;
3. the start is **never earlier** than the room *Maximum early start*. With a
   maximum of 120 minutes the start is at 07:00 − 120 minutes = 05:00, else at
   07:00 − 186 minutes = 03:54;
4. once started it continues until 07:00, even if the room gets warm earlier.

**Already heating.** q of now is used: a room whose radiators are already warm
needs less. Example: the room of section 2, 18 → 21 °C at 0 °C, with q = 0.5:
**203 minutes** instead of 231.

### Time to target

While a room is below its target the card shows the time to the target
(*~35 min*), with the same simulation, the outdoor temperature of now and q of
now.

### Optimal stop

Before a change to a cooler level, the heating stops earlier, as long as the
room stays in the **comfort** of the current level: level − tolerance.
Example: *Home* 21 °C, tolerance 0.5 °C → comfort down to 20.5 °C. The
simulation runs **without heating** until the room reaches the comfort; the
inertia counts (the radiators still give heat). With the room of section 2
just after heating (q = 1): **82 minutes** at 0 °C outdoors, **162 minutes** at
10 °C.

The stop is never longer than the room *Optimal stop* maximum. If the room gets
colder than the comfort during the stop, the stop is cancelled and the current
level comes back until the change. With an hourly forecast, the mean forecast
of the stop period is used, in 3 passes like the start. During a stop, the
decision sensor shows the temperature expected at the change, from the same
simulation.

### Relays: starting and stopping by the inertia

For a relay, an *On / off (hvac mode)* thermostat or TRVs heated by the room sensor
(their heat demand from the room sensor) with *Use the learned inertia* on
(the default), inside the hysteresis band:

- heating on: the simulation runs **without heating** from now (q of now, the
  outdoor temperature of now, the expected sun) until the room turns down;
  when its highest temperature reaches **target + hysteresis**, the heating
  stops now;
- heating off: the simulation runs **with heating** until the room turns up;
  when its lowest temperature reaches **target − hysteresis**, the heating
  starts now.

At the edges of the band the band decides as before, and the minimum on / off
times still apply. Example (the room of section 2 with τ = 60 minutes, no
weather curve, 5 °C outdoors, target 21 °C, hysteresis 0.3, warming up from
20.5 °C with cold radiators): at 21.1 °C q is 0.84 and the simulation without
heating peaks at 21.37 °C, above 21.3 °C, so the heating stops at 21.1 °C; the
room peaks at 21.33 °C. With the band alone the heating stops at 21.3 °C
(q 0.87) and the room peaks at 21.55 °C. Simulations:
[guide, chapter 7](guide/07-optimal-start-stop-and-learning.md#starting-and-stopping-by-the-inertia).

---

## 8. A house without an outdoor temperature

Without an outdoor sensor and without a weather entity, the loss cannot depend
on the outdoor temperature: it is learned as **a constant number of °C per
hour** (`constant_loss: true`, `loss_per_hour` in °C per hour). It is the mean
loss of the recent weeks; colder days are not seen. The weather curve is not
learned either (it needs the outdoor temperature). Optimal stop needs an
outdoor temperature and is not made.

When an outdoor source is added or removed, the model is learned again from
the start, because the meaning of the loss changes.

---

## 9. Fictional simulations

The simulations below use **fictional rooms**: the numbers are chosen to be
plausible, they are not measurements.

| Room | h (°C/h) | k (per hour) | τ (minutes) |
|---|---|---|---|
| Insulated flat | 1.6 | 0.035 | 20 |
| Average house | 2.8 | 0.07 | 30 |
| Old house, poor insulation | 4.5 | 0.12 | 30 |
| Floor heating | 1.6 | 0.04 | 180 |

Assumptions: 40 days; the daily outdoor temperature random between −5 and
10 °C, with ±3 °C between day and night; a thermostat at 21 °C from 06:00 to
23:00 and 17 °C at night, ±0.3 °C; the sensor read every 5 minutes, rounded to
0.1 °C; random disturbances of the room (standard deviation 0.15 °C/h per
minute). From day 8, every morning at 06:00 the time to reach 21 °C is
predicted with the mean outdoor temperature of the heating (a perfect forecast)
and compared with the real one.

**Without a weather curve:**

| Room | model used after | learned h / c / k / τ | error: mean / largest (minutes) |
|---|---|---|---|
| Insulated flat | 0.4 days | 1.59 / −0.001 / 0.035 / 20 | 2 / 8 |
| Average house | 0.5 days | 2.78 / 0.000 / 0.070 / 30 | 2 / 5 |
| Old house | 0.8 days | 3.75 / −0.008 / 0.100 / 20 | 9 / 18 |
| Floor heating | 0.7 days | 1.60 / −0.001 / 0.040 / 180 | 2 / 7 |

The curve came out close to 0, as it should. In the old house h and k came out
lower in the same proportion (3.75 ÷ 0.100 ≈ 4.5 ÷ 0.12): the room rarely sees
the large differences that would tell them apart, and the predictions stay
close.

**With a weather curve** (the boiler gives 3 % more heat for each °C below 5 °C
outdoors: heating = power × (1 + 0.03 × (5 − outdoor)) = 1.15 × power − 0.03 ×
power × outdoor, so the true h is 1.15 × power and the true c 0.03 × power):

| Room, with weather curve | true h / c | learned h / c | error with the curve learned: mean / largest | error without a curve (before): mean / largest |
|---|---|---|---|---|
| Insulated flat | 1.84 / 0.048 | 1.82 / 0.047 | 4 / 6 | 28 / 56 |
| Average house | 3.22 / 0.084 | 2.76 / 0.062 | 8 / 15 | 22 / 52 |
| Old house | 5.17 / 0.135 | 4.22 / 0.094 | 7 / 14 | 16 / 38 |
| Floor heating | 1.84 / 0.048 | 1.84 / 0.048 | 5 / 11 | 42 / 122 |

(Errors in minutes. In the average and the old house h, c and k came out lower
together, for the reason above.)

---

## 10. The sun

**The sun signal.** How much sun can reach the room now, from 0 to 1:

```
sun = max(0, sin(sun elevation)) × (1 − 0.75 × cover^3.4)
```

- the **sun elevation** is calculated from the time and the location of Home
  Assistant (the NOAA formulas, a fraction of a degree off). Nothing is set
  for it;
- the **cover** is the cloud cover from 0 (clear) to 1 (overcast): the
  `cloud_coverage` of the weather entity (and of each hour of its forecast),
  else assumed from its condition: *sunny* / *clear-night* 0.1,
  *partlycloudy* and *windy* 0.5, *windy-variant* 0.7, *cloudy* 0.9, rain,
  snow, hail, fog, storms 1;
- `1 − 0.75 × cover^3.4` is the share of the sunlight that comes through the
  clouds (Kasten and Czeplak, 1980): 1 in a clear sky, 0.93 half covered,
  0.48 at a cover of 0.9, 0.25 overcast.

**Example** (Bucharest, 44.4° N, 12 October at noon): the sun is 36.7° high,
sin 36.7° = 0.60. Clear sky: signal 0.60; half covered: 0.60 × 0.93 = 0.56;
overcast: 0.60 × 0.25 = 0.15. At night the signal is 0. At noon on 15
November the sun is 27.2° high (signal 0.46 in a clear sky), on 21 December
22.2° (0.38).

s is how many °C per hour a signal of 1 adds: a room with s = 1.5 gains
1.5 × 0.30 = **0.45 °C/h** at a signal of 0.30. The orientation of the
windows is not needed: s is the average over the hours of sun the room gets. A
room with sun only in the morning or only in the afternoon gets a smaller s; a
room without sun, s = 0.

**When the sun is learned.** Only in a house with a weather entity (without
it the clouds are not known: s stays 0). And only when it is **clearly seen**:

- the stretches had enough sun: the sum of their squared mean sun signals,
  forgotten like the stretches, at least **1** (for example 12 stretches at a
  signal of 0.3: 12 × 0.3² = 1.08);
- s is at least **5 standard errors** from 0. The standard error comes from
  the usual squared prediction error of the stretches and the normal
  equations of section 4 (the error of a least squares coefficient). Below
  that, the warmth of the stretches with sun could just as well be chance,
  people or cooking, and s is 0.

Why 5: in a first simulation without this limit, a north room with cooking at
noon learned a sun of 0.24 – 0.40 °C/h in every run, and its day predictions
got worse (mean error 0.07 – 0.09 °C before, 0.18 – 0.22 °C after). With 5, a
sun of 2 °C/h is still learned within 9 days (3 of them clear) in the tests of
the integration.

**What the sun changes.** The **optimal start** needs less on a sunny morning,
the **optimal stop** can begin earlier on a sunny afternoon, the **time to
target** and the **predicted temperature** of the card follow the sun.
Example (the room of section 2 with s = 1.5, a constant signal of 0.3,
outdoors 0 °C): from 18 to 21 °C, starting cold, **161 minutes** instead of
231; from 21 °C just heated (q = 1) down to the comfort of 20.5 °C,
**149 minutes** instead of 82.

**The setting *Solar gain* of the room** is separate and stays: it lowers the
target while the sun shines. The learned sun only changes the predictions,
never the target.

**Simulations** (fictional rooms, the same assumptions as section 9, at 45° N
in mid November; the numbers are chosen to be plausible, they are not
measurements):

- every room: h = 2.5 °C/h, k = 0.06 per hour, τ = 30 minutes;
- the sun through a window: up to 2.2 °C/h in a clear sky with the sun
  straight on the window, in proportion to how straight it falls on it, plus
  15 % of that as diffuse light, weakened by the clouds;
- each day clear (30 %), mixed (40 %) or overcast (30 %); the clouds of the
  weather entity off by ±0.15 (standard deviation) from the real ones, those
  of the forecast by ±0.25;
- from day 15 to day 40, at 09:00, 11:00, 13:00 and 15:00 (day) and at 22:00
  (night), the temperature 3 hours ahead without heating is predicted and
  compared with the real one; three runs with different weather.

Mean error of the prediction (°C), day / night:

| Room | without sun | with the sun learned | s learned (°C/h) |
|---|---|---|---|
| South window | 1.09 – 1.22 / 0.93 – 0.99 | 0.17 – 0.21 / 0.06 – 0.08 | 2.51 – 2.56 |
| East window | 0.36 – 0.38 / 0.22 – 0.23 | 0.26 – 0.30 / 0.04 | 0.74 – 0.80 |
| West window | 0.49 – 0.55 / 0.34 – 0.37 | 0.36 – 0.41 / 0.19 – 0.23 | 0.92 – 0.98 |
| North, no sun | 0.03 – 0.04 / 0.03 – 0.04 | the same | 0 |
| North, cooking 12:00 – 13:30 (1 °C/h) | 0.45 – 0.46 / 0.10 – 0.13 | the same | 0 in 2 runs, 0.31 in 1 |

Without a sun term the model does not only miss the sun: it puts its warmth on
the heating and on a smaller loss, so also the nights come out wrong. s comes
out above 2.2 for the south room because of the diffuse light.

**A whole house** (two zones of the room above, one thermostat, the sensor in
one of them; the zones even out by 0.5 of their difference per hour with the
doors open, 0.15 with them mostly shut):

| House | without sun | with the sun learned | s learned (°C/h) |
|---|---|---|---|
| Sensor in the south zone, doors open | 0.70 – 0.76 / 0.44 – 0.49 | 0.21 – 0.23 / 0.03 – 0.04 | 1.44 – 1.48 |
| Sensor in the north zone, doors open | 0.51 – 0.58 / 0.43 – 0.47 | 0.14 – 0.16 / 0.15 – 0.20 | 1.06 – 1.16 |
| Sensor in the north zone, doors mostly shut | 0.36 – 0.41 / 0.31 – 0.36 | 0.19 – 0.23 / 0.20 – 0.25 | 0.72 – 0.74 |
| Sensor in an east zone, the other one west | 0.35 – 0.37 / 0.24 – 0.25 | 0.20 – 0.21 / 0.07 – 0.09 | 0.60 – 0.63 |

A sensor without sun of its own learns the sun that reaches it from the other
zone. A model with a sun term per side of the house (east, south, west) was
also tried: better only for east and west windows, and in a north room it
learned an east sun that was not there in 2 of 3 runs. So there is one term.

---

## 11. Limits

- **The weather curve is a straight line.** A boiler whose curve bends, or that
  reaches its highest water temperature in hard frost, is learned as the
  straight line closest to it over the recent weeks.
- **A sensor with a coarse step (0.5 °C) in steady weather.** When for a week
  the outdoor temperature changes only between day and night, such a sensor
  can lead to a wrong weather curve. In a simulation (7 days, outdoor 0 –
  10 °C between night and day, no curve in the house, three runs) the time to
  heat at −5 °C came out up to 48 % wrong; with a 0.1 °C sensor at most 5 %, and
  with the 0.5 °C sensor but days of different temperatures also at most 5 %.
  It corrects itself once days of other temperatures are seen; the *Maximum
  early start* of the room still limits the start.
- **Day to day differences are not learned.** People, cooking or walls
  colder after a long absence change the room; the least squares average
  them. The sun is learned as an average over the hours it reaches the room:
  closed blinds, snow on the ground or a tree with or without leaves change it
  until the recent weeks have followed.
- **The clouds are those of the weather entity.** A wrong cloud forecast is a
  wrong sun in the prediction; the learning uses the clouds of now.
- **TRVs with a boiler started by a thermostat that is not in Home
  Assistant**: the integration cannot tell when the boiler really runs; the
  learning is not reliable and optimal start / stop are not recommended.
- **Waits before the heat source starts** (the minimum on / off times, the
  *Rooms needed to start the heat source*, the reference room) are not
  heating: the start can be late by that wait.
- **Learning saved before 2.6** (heating and cooling episodes) does not fit the
  new model and is discarded: every room learns again after the update, within
  about a day. The learning of the 2.6.0 betas is kept; its sun starts from 0.

---

## 12. Where to see it

**`sensor.<room>_heating_rate`** – state: minutes per degree with the heating
fully on, at the room and outdoor temperatures of now (`min/°C` or `min/°F`).
Attributes:

| Attribute | Meaning |
|---|---|
| `learned` | the learned model is used (section 6) |
| `heating_per_hour` | h (at 0 °C outdoors) |
| `weather_curve` | c (°C per hour more for each °C colder outdoors) |
| `sun_gain` | s (°C per hour at a sun signal of 1; 0 while not clearly seen) |
| `loss_per_hour` | k (per hour, or °C per hour with `constant_loss`) |
| `constant_loss` | the loss is a constant (section 8) |
| `inertia_minutes` | τ |
| `heat_reaching_now` | q now |
| `error_per_hour` | the usual prediction error of a stretch (°C per hour) |
| `minutes_per_degree` | minutes per degree at −10 / 0 / 10 / 20 °C (14 / 32 / 50 / 68 °F) outdoors |
| `hours_heating`, `hours_idle`, `hours_needed` | learning progress (section 6) |
| `model` | the model in °C (h, c, k, s, τ, q, constant loss, mean outdoor temperature, `band` and `inertia_control`: how the device switches the heating) for the prediction of the card; empty until learned |

**`sensor.<house>_outdoor_average`** – attribute `sun_forecast`: the expected
sun signal every 15 minutes for the next 12 hours (with a weather entity).

**`sensor.<room>_cooling_rate`** – state: how fast the room falls now without
heating (°C/h, empty until learned); attributes: `learned`, `loss_per_hour`,
`inertia_minutes`, the tolerance of the optimal stop.

**`sensor.<room>_decision`** – `next_estimate` (when the next optimal start /
stop begins, with which outdoor temperature, and whether it is learned or
default) and `time_to_target`.

**`button.<room>_reset_learning`** – forgets the model of the room (also in the
card *Details*, with a second click to confirm).

**Card, Details** – group *Learning*: *Learning* (*learned · usual error
±0.12 °C/h*, or while learning *learning…* with two bars, *with heating 2 of
4 h* and *without heating 1 of 4 h*, and the default under them) with the
**Reset** button; once learned one tile each: *Heating* (minutes per degree
now, e.g. *45 min/°C*), *Inertia* (*30 min*), *Weather curve* (*+0.050 °C/h*
*for each °C colder outdoors*, or *none*), *Sun* once learned (*+1.50 °C/h*,
*sun overhead, clear sky · now +0.60 °C/h*: s and s × the sun signal of now)
and *Heat loss* (*0.70 °C/h*, *falls now*).

**Card, chart** – once learned, the predicted temperature for the next 12
hours (dotted): the model of section 2 simulated minute by minute along the
planned target, with the hourly forecast and the expected sun. The heating is
switched as the device does it (the `band` of the `model` attribute, °C below
and above the target): the *cold* / *hot tolerance* of Generic Thermostat,
the hysteresis for relays, on / off control, heating by the room sensor and thermostats
without `hvac_action`, with the starting and stopping by the inertia of
section 7 when `inertia_control` is on. No band when it is not known:
thermostats and TRVs that regulate by themselves, and a Generic Thermostat
whose tolerances cannot be read (one set up in YAML). Then the prediction
holds the target and draws the heating as one period.

**Diagnostics** – `thermal_model` with all the numbers of the model and the
ten inertia candidates (each with its h, c, k, s, error, `outdoor_spread`, the
deviation of the outdoor temperatures of its heating, section 4, and
`sun_seen`, the sum of the squared sun signals, section 10).
