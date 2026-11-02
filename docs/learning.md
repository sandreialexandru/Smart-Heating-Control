# How Smart Heating Control learns (the thermal model of a room)

*[Română](learning.ro.md)*

This document explains how each room learns how it heats up, how its heating
changes with the outdoor temperature (the weather curve), how it loses heat
and how slow its heating is to react (the thermal inertia), how the
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
- [10. Limits](#10-limits)
- [11. Where to see it](#11-where-to-see-it)

---

## 1. Why learn at all

To have a room at 21 °C at 07:00, the heating has to start earlier. How much
earlier depends on the room: the heat source, the radiators or the floor
heating, the insulation, the outdoor temperature. Instead of asking for these
values, every room measures its own behaviour and learns from it. Nothing has
to be set: also the inertia (slow floor heating or fast radiators) and the
weather curve of the boiler are learned, not chosen in the configuration.

---

## 2. The model of a room

The room is treated as one thermal mass that gets heat from its heating and
loses heat to the outdoors, in proportion to how much warmer it is than
outside:

```
rise per hour = (h − c × outdoor) × q − k × (room − outdoor)
```

| Number | Name in the attributes | Meaning |
|---|---|---|
| h | `heating_per_hour` | how many °C per hour the heating adds when it gives its full heat, at 0 °C outdoors |
| c | `weather_curve` | how many °C per hour more the heating adds for each °C colder outdoors (*The weather curve* below) |
| k | `loss_per_hour` | which part of the inside / outside difference is lost per hour |
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
- the mean of q × outdoor over the stretch (for the weather curve).

Why 30 minutes: long enough that the sensor step (usually 0.1 °C) is small
against the change, short enough to see a heating cycle.

**A stretch is not used** when:

- a **window or door sensor** of the room (or a linked one) was open;
- the **state of the heat source** was unknown;
- the **valve exercise** was running;
- the house has an outdoor temperature (sensor or weather entity) but it was
  **unknown**;
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
0.68 and the 14; it has to find h, c and k.

Nothing is kept per stretch: only the sums of the least squares (section 4),
so the memory does not grow and a restart keeps everything learned (the
stretch in progress is dropped).

---

## 4. How heating and loss are calculated

Every stretch is one equation:

```
measured rise per hour = h × (mean q) − c × (mean q × outdoor) − k × (mean room − outdoor)
```

h, c and k are the numbers for which the equations of all stretches are **as
close as possible** to what was measured: the sum of the squared differences
is the smallest (**least squares**). Three unknowns give three equations
(the normal equations), solved after every stretch by Gaussian elimination:

```
h × Σ q²   − c × Σ q·p   − k × Σ q·d   = Σ q·r
h × Σ q·p  − c × Σ p²    − k × Σ p·d   = Σ p·r
h × Σ q·d  − c × Σ p·d   − k × Σ d²    = Σ d·r
```

(q: mean q, p: mean q × outdoor, d: mean room − outdoor, r: rise per hour of
each stretch.)

**Older stretches weigh less.** Every stretch keeps its weight for a week, then
weighs half, after two weeks a quarter (half life **7 days**). So the model
follows a room that changes (a new weather curve, new radiators, the season)
without having to be reset.

**Stretches far from the others weigh less.** A door left open without a
sensor, cooking, strong sun: the room does what the model does not expect.
After 10 stretches, each new stretch is compared with what the model said
before learning from it. The usual difference is the weighted mean of these
differences; a stretch more than **2.5 times** the usual difference away
counts with a weight in proportion (at 5 times the usual difference: half).
Such a stretch still counts a little, so when the room really changed the
model follows it.

**A tiny pull towards the default** (1 °C/h, no curve, no loss), worth about
1 % of one stretch, keeps the first stretches from giving wild numbers; after a day it
no longer matters.

**Impossible values:**

- a **negative loss** (the room would warm up by itself): the loss is set to 0
  and the rest is fitted again;
- a **weather curve that would leave no heating** (h − c × outdoor zero or
  less) at −20 °C or at 20 °C outdoors, the range of a heating season: the
  curve is set to 0 and the rest is fitted again;
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

For each candidate q is followed with its τ, and h, c and k are fitted as in
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
from the room temperature and the q of now, for at most 24 hours.

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

## 10. Limits

- **The weather curve is a straight line.** A boiler whose curve bends, or that
  reaches its highest water temperature in hard frost, is learned as the
  straight line closest to it over the recent weeks.
- **Day to day differences are not learned.** The sun, people, cooking or
  walls colder after a long absence change the room; the least squares
  average them.
- **TRVs with a boiler started by a thermostat that is not in Home
  Assistant**: the integration cannot tell when the boiler really runs; the
  learning is not reliable and optimal start / stop are not recommended.
- **Waits before the heat source starts** (the minimum on / off times, the
  *Rooms needed to start the heat source*, the reference room) are not
  heating: the start can be late by that wait.
- **Learning saved before 2.6** (heating and cooling episodes) does not fit the
  new model and is discarded: every room learns again after the update, within
  about a day.

---

## 11. Where to see it

**`sensor.<room>_heating_rate`** – state: minutes per degree with the heating
fully on, at the room and outdoor temperatures of now (`min/°C` or `min/°F`).
Attributes:

| Attribute | Meaning |
|---|---|
| `learned` | the learned model is used (section 6) |
| `heating_per_hour` | h (at 0 °C outdoors) |
| `weather_curve` | c (°C per hour more for each °C colder outdoors) |
| `loss_per_hour` | k (per hour, or °C per hour with `constant_loss`) |
| `constant_loss` | the loss is a constant (section 8) |
| `inertia_minutes` | τ |
| `heat_reaching_now` | q now |
| `error_per_hour` | the usual prediction error of a stretch (°C per hour) |
| `minutes_per_degree` | minutes per degree at −10 / 0 / 10 / 20 °C (14 / 32 / 50 / 68 °F) outdoors |
| `hours_heating`, `hours_idle`, `hours_needed` | learning progress (section 6) |

**`sensor.<room>_cooling_rate`** – state: how fast the room falls now without
heating (°C/h, empty until learned); attributes: `learned`, `loss_per_hour`,
`inertia_minutes`, the tolerance of the optimal stop.

**`sensor.<room>_decision`** – `next_estimate` (when the next optimal start /
stop begins, with which outdoor temperature, and whether it is learned or
default) and `time_to_target`.

**`button.<room>_reset_learning`** – forgets the model of the room (also in the
card *Details*, with a second click to confirm).

**Card, Details** – group *Learning*: *Heating learned* (minutes per degree now
and the inertia, e.g. *45 min/°C now · inertia 30 min*, or while learning
*learning… 2 of 4 h with heating, 1 of 4 h without*, with the default under
it) and *Heat loss learned* (*falls 0.70 °C/h now*, once learned), with the
**Reset** button.

**Diagnostics** – `thermal_model` with all the numbers of the model and the
ten inertia candidates (each with its h, c, k, error and `outdoor_spread`, the
deviation of the outdoor temperatures of its heating, section 4).
