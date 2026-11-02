# How Smart Heating Control learns (heating and cooling)

*[Română](learning.ro.md)*

This document explains in detail how each room learns how long it takes to
heat up and how fast it cools down, how the numbers are calculated, and how
they are used for **optimal start**, **optimal stop** and the **time to
target** shown on the card. Every number in the examples is either calculated
in the text or stated as an assumption of the example.

All calculations are done in °C internally; with a house in °F only the
display is converted (1 °C = 1.8 °F).

- [1. Why learn at all](#1-why-learn-at-all)
- [2. Heating episodes](#2-heating-episodes)
- [3. The heating model](#3-the-heating-model)
- [4. How the three numbers are calculated](#4-how-the-three-numbers-are-calculated)
- [5. When a term is used, and impossible values](#5-when-a-term-is-used-and-impossible-values)
- [6. Which episodes are kept](#6-which-episodes-are-kept)
- [7. Using the heating model](#7-using-the-heating-model)
- [8. Cooling learning and optimal stop](#8-cooling-learning-and-optimal-stop)
- [9. Fictional simulations](#9-fictional-simulations)
- [10. Limits](#10-limits)
- [11. Where to see it](#11-where-to-see-it)

---

## 1. Why learn at all

To have a room at 21 °C at 07:00, the heating has to start earlier. How much
earlier depends on the room: the heat source, the radiators or the floor
heating, the insulation, the outdoor temperature. Instead of asking for these
values, every room measures its own behaviour and learns from it.

---

## 2. Heating episodes

An **episode** is one measured heating: from the moment the room starts to
ask for heat until it reaches the target or the heating stops.

**Start.** An episode starts when the room asks for heat and its temperature
is at least the **tolerance** below the target. The tolerance is not a new
setting; it is taken from where the room already has it:

| Room control | Tolerance used |
|---|---|
| Generic Thermostat | its `cold_tolerance` |
| Relay, on / off control | the room *Hysteresis* |
| Other thermostats | the room *Thermostat tolerance* (default 0) |

Example: target 22 °C, tolerance 0.5 °C → an episode can start at 21.5 °C or
lower (22 − 0.5 = 21.5).

**End.** The episode ends when the room reaches the target or the heat demand
stops. It is **used** only when:

- the heat demand lasted **at least 10 minutes**;
- the temperature **rose**, however little (a slow rise is real and is learned);
- no **window or door sensor** of the room (or a linked one) was open;
- the **heat source was running** the whole time it counted as heating
  (Generic Thermostat `hvac_action`, the relay or on / off thermostat on, the
  *Heat source* of the house if one is set);
- it is the **cold season** (not mode Off or Summer, not outside the heating
  season).

**What is saved** for each episode:

| Field | Example | Meaning |
|---|---|---|
| outdoor | 5.0 | mean outdoor temperature during the episode (°C), or empty if unknown |
| degrees | 2.0 | how many °C the room rose |
| minutes | 125 | how long it took |
| at | 2026-10-20T07:00 | when it ended |

The minutes are counted from the moment the room **really heats** (it asks
for heat and its heat source runs) to the end. Inside them: the boiler
warming up, the water and the radiators warming up. **Not** inside them: the
time before the heat source starts — the minimum on / off times of a relay or
of the house heat source, and the wait for other rooms (*Rooms needed to start the heat source* or
the reference room). None of them has to be known or configured, but an
optimal start can begin later by that wait, because it is not learned.

---

## 3. The heating model

The time to heat is learned as:

```
minutes = fixed part + degrees × minutes per degree
minutes per degree = M + S × outdoor
```

| Number | Name in the attributes | Meaning |
|---|---|---|
| fixed part (F) | `fixed_minutes` | minutes before the room starts to rise (heat source starting, radiators warming up); the same for a small and a large rise |
| M | `minutes_per_degree_at_0` (diagnostics) | minutes per °C when it is 0 °C outdoors |
| S | `per_outdoor_degree` | how the minutes per °C change for each °C outdoors (usually negative: warmer outside, faster) |

**Example** (values assumed for the example): F = 25 minutes, M = 60, S = −2.
At 5 °C outdoors the minutes per degree are 60 + (−2 × 5) = 50. To rise 3 °C:
25 + 3 × 50 = **175 minutes**.

### Why a fixed part

The versions before 2.0 learned a single speed per episode (degrees ÷ hours).
That mixes the fixed part into the speed. With the room of the example above
(F = 25, 50 minutes per degree at 5 °C):

- a small top-up of 0.4 °C takes 25 + 0.4 × 50 = 45 minutes → speed
  0.4 ÷ 0.75 h = **0.53 °C/h**;
- a rise of 3 °C after a night setback takes 25 + 3 × 50 = 175 minutes →
  speed 3 ÷ 2.92 h = **1.03 °C/h**.

If 60 % of the episodes are small and 40 % large, the average speed is
0.6 × 0.53 + 0.4 × 1.03 = **0.73 °C/h**. For a rise of 3 °C that gives
3 ÷ 0.73 = 4.1 h = **247 minutes**, against 175 real: **72 minutes too early**,
and more episodes do not fix it, because the average stays the same. The
fixed part removes this error.

### Why the outdoor temperature is a straight line

When it is colder outside the room loses more heat, so each degree takes
longer. A boiler with a weather curve does the opposite: colder outside,
hotter water, faster heating. The single number S takes both effects
together, as they are in that house, without having to separate them.

---

## 4. How the three numbers are calculated

F, M and S are the values for which the calculated durations of all kept
episodes are **as close as possible** to the measured ones: the sum of the
squared differences is the smallest possible (**least squares**). It is not
trial and error: this condition gives three equations with three unknowns,
whose solution is that minimum.

### Worked example

Four episodes of a fictional room (made with F = 25, M = 60, S = −2, so the
result can be checked):

| Episode | degrees (g) | outdoor (o) | minutes (d) | how it was made |
|---|---|---|---|---|
| A | 0.4 | 10 | 41 | 25 + 0.4 × (60 − 2 × 10) = 25 + 0.4 × 40 |
| B | 3.0 | 0 | 205 | 25 + 3 × 60 |
| C | 2.0 | 5 | 125 | 25 + 2 × (60 − 2 × 5) = 25 + 2 × 50 |
| D | 0.5 | 0 | 55 | 25 + 0.5 × 60 |

The integration sees only g, o and d.

**Step 1: the sums.**

| Sum | Calculation | Value |
|---|---|---|
| number of episodes | | 4 |
| Σ g | 0.4 + 3 + 2 + 0.5 | 5.9 |
| Σ g·o | 0.4·10 + 3·0 + 2·5 + 0.5·0 = 4 + 0 + 10 + 0 | 14 |
| Σ g² | 0.16 + 9 + 4 + 0.25 | 13.41 |
| Σ g²·o | 0.16·10 + 9·0 + 4·5 + 0.25·0 = 1.6 + 20 | 21.6 |
| Σ (g·o)² | 4² + 0 + 10² + 0 = 16 + 100 | 116 |
| Σ d | 41 + 205 + 125 + 55 | 426 |
| Σ g·d | 16.4 + 615 + 250 + 27.5 | 908.9 |
| Σ g·o·d | 4·41 + 0 + 10·125 + 0 = 164 + 1250 | 1414 |

**Step 2: the three equations** (each sum in its place):

```
   4 × F +  5.9  × M +  14  × S =  426
 5.9 × F + 13.41 × M + 21.6 × S =  908.9
  14 × F + 21.6  × M + 116  × S = 1414
```

**Step 3: the solution** (Gaussian elimination in the code): **F = 25,
M = 60, S = −2**. Check in the first equation: 4 × 25 + 5.9 × 60 + 14 × (−2) =
100 + 354 − 28 = 426. ✓

**Step 4: use.** Tomorrow the room is at 18 °C and has to reach 21 °C, with a
mean forecast of −3 °C (never seen in the episodes): minutes per degree
60 + (−2 × −3) = 66, minutes 25 + 3 × 66 = **223**. The line is extended
beyond what was seen; the *Maximum early start* of the room still limits it.

**Outdoor temperature unknown** (no sensor, no forecast): the mean outdoor
temperature of the episodes is used, here (10 + 0 + 5 + 0) ÷ 4 = 3.75 °C →
60 + (−2 × 3.75) = 52.5 minutes per degree.

With real episodes the durations are not exact (sun, people, cooking, the
sensor step), so no three numbers fit all of them; least squares chooses the
ones that fit best. The calculation is done again after every episode and
takes less than a millisecond for 50 episodes.

---

## 5. When a term is used, and impossible values

A term is calculated only when the episodes can tell it apart from the
others.

**The fixed part needs episodes of different sizes**: the largest minus the
smallest must be at least **1 °C**. Why: two episodes of 0.4 °C that took 45
minutes each can be explained by 25 + 0.4 × 50, by 5 + 0.4 × 100 or by
45 + 0.4 × 0 (all give 45). Only an episode of a different size, e.g. 3 °C in
175 minutes, leaves one answer: 25 + 3 × 50 = 175, while 5 + 3 × 100 = 305 and
45 + 3 × 0 = 45 do not fit. The value 1 °C was chosen because with the usual
sensor step of 0.1 °C the reading error is then at most 10 % of the
difference (0.1 ÷ 1).

**The outdoor term needs outdoor temperatures at least 1 °C apart** (among the
episodes with an outdoor temperature). Below that, the slope of the line
would be guessed from noise.

Until a term can be used it is zero; the formula stays the same:

| Episodes | What is calculated |
|---|---|
| none | default: 60 minutes per degree, no fixed part (1 °C per hour) |
| same size, same outdoor temperature | minutes per degree only |
| same size, different outdoor temperatures | minutes per degree and the outdoor term |
| different sizes, same outdoor temperature | fixed part and minutes per degree |
| different sizes and outdoor temperatures | all three |

**Impossible values are set to zero and the rest is calculated again:**

- a **negative fixed part** (possible from noise) → fixed part 0, fitted
  again without it;
- minutes per degree **negative at the coldest or warmest learned outdoor
  temperature** → the outdoor term is dropped, fitted again;
- **larger episodes not slower than small ones** (negative minutes per degree
  without outdoor term) → only a fixed part is left, the mean of the
  episodes. Example: 0.5 °C in 300 minutes and 2.5 °C in 100 minutes → fixed
  part (300 + 100) ÷ 2 = 200 minutes;
- far outside the learned outdoor range the line may cross zero: the minutes
  per degree never go **below zero** there.

**Already heating.** When the room is in an episode already, the time it has
heated counts against the fixed part, because the radiators are warm.
Example: fixed part 30 minutes, 40 minutes per degree, 1 °C to go: before
heating 30 + 40 = 70 minutes; after 20 minutes of heating (30 − 20 =) 10 + 40 =
50 minutes; after an hour 0 + 40 = 40 minutes.

---

## 6. Which episodes are kept

The last **25 small episodes** (less than 1 °C) and the last **25 large
episodes** (1 °C or more) are kept, in time order. A new episode pushes out the
oldest one **of its own kind**.

Why apart: a thermostat that keeps the temperature makes many small cycles
(for example 6 a day), while a large rise happens once a day or once a week.
With a single list of the last 30, the small cycles push the large ones out:
in the simulation of section 9.3 only 4 large episodes were left out of 30,
and the fixed part could not be learned well. With 25 + 25 the large episodes
stay.

At about one large episode a day, the 25 large ones are renewed in about 25
days, so after a change (a new weather curve on the boiler, new radiators)
the learning follows within a few weeks. To start again at once, each room has
the buttons **Reset heating learning** and **Reset cooling learning** (also in
the card *Details*, next to each learning, with a second click to confirm).

### Episodes far from the others

A door left open during a heating, cooking, a sensor that jumped: such an
episode takes much longer (or shorter) than the others and would pull the fit
towards it. With at least 8 episodes, every episode is compared with what the
fit of all of them says (its minutes minus the minutes of the fit). The usual
difference is the median absolute difference from the median, scaled to a
standard deviation (× 1.4826). An episode more than **3.5 times** the usual
difference away (at least 1 minute) is left out and the rest is fitted again,
once. At least 5 episodes must remain, otherwise all are used.

Nothing is set for a particular house: "far" is measured from the room's own
episodes. The episode left out is still kept: when the room really changed
(new radiators), the new episodes soon outnumber the old ones and the fit
follows them. The *Heating rate* sensor shows how many are left out
(`episodes_left_out`).

**Example.** Ten episodes of 20 minutes + 30 minutes per degree (2 °C in 80
minutes) and one of 2 °C in 300 minutes (a window open without a sensor). Fitted
together, 2 °C come out at about 104 minutes; without the far episode at 80.

**Checked in simulations** of houses (two months of winter each, sensors with
noise and gaps, cooking, windows opened without sensors): about the same error
as before in steady houses, and clearly closer after a change of the house
(radiators 50 % stronger): in the 3 weeks after the change the mean error of
the time to heat fell from 33 to 28 minutes, and later 90 % of the predictions
were within 28 minutes instead of 37.

---

## 7. Using the heating model

### Optimal start

For the next scheduled change to a warmer level (for example *Sleep* 19 °C →
*Home* 22 °C at 07:00):

1. degrees = level of the next preset − room temperature now. Example:
   22 − 19.5 = **2.5 °C**.
2. outdoor = the **mean forecast** between the start and 07:00 (with a weather
   entity that has an hourly forecast; otherwise the measured value). The
   start depends on that temperature and the temperature on the start, so it
   is worked out **3 times**, each time from the period found before.
3. minutes = the heating model (section 3). Example with F = 25, M = 60,
   S = −2 and a mean forecast of 5 °C: 25 + 2.5 × 50 = **150 minutes**.
4. the start is **never earlier** than the room *Maximum early start*. With a
   maximum of 120 minutes the start is at 07:00 − 120 minutes = 05:00, else at
   07:00 − 150 minutes = 04:30.
5. once started it continues until 07:00, even if the room gets warm earlier.

### Time to target

While a room is below its target the card shows the time to the target
(*~35 min*), with the same model, the outdoor temperature of now and the time
already heated (section 5).

### Before the first episode

The default is used: **60 minutes per degree, no fixed part**. The card shows
*learning…* with a small line under it: *default 60 min/1°C* (33 min/1°F in a
house in °F, because 60 ÷ 1.8 = 33.3).

---

## 8. Cooling learning and optimal stop

### Cooling episodes

A cooling episode lasts from the end of a heat demand to the start of the
next one, and is used when it lasted at least 10 minutes, the temperature
fell, however little, and no window or door sensor was open.

### The coefficient

A room loses heat in proportion to how much warmer it is than outside:

```
T(t) = outdoor + (start − outdoor) × e^(−k × hours)
k = ln[(start − outdoor) ÷ (end − outdoor)] ÷ hours
```

**Example** (fictional): outdoors 0 °C, the room falls from 21 °C to 19.6 °C
in 2 hours.

- (21 − 0) ÷ (19.6 − 0) = 1.0714
- ln(1.0714) = 0.0690
- k = 0.0690 ÷ 2 = **0.0345 per hour**

The room loses 0.0345 °C per hour for each degree it is warmer than outside:
at 21 °C and 0 °C outdoors, 21 × 0.0345 = 0.72 °C per hour; at 21 °C and
10 °C outdoors, 11 × 0.0345 = 0.38 °C per hour. One coefficient per room is
kept: the **mean of the last 30** cooling episodes.

### Optimal stop

Before a change to a cooler level, the heating stops earlier, as long as the
room stays in the **comfort** of the current level: level − tolerance.
Example: *Home* 21 °C, tolerance 0.5 °C → comfort down to 20.5 °C.

```
minutes = ln[(room − outdoor) ÷ (comfort − outdoor)] ÷ k × 60
```

With k = 0.0345, room 21 °C, comfort 20.5 °C:

- at 0 °C outdoors: ln(21 ÷ 20.5) = 0.0241 → 0.0241 ÷ 0.0345 × 60 = **42
  minutes**;
- at 10 °C outdoors: ln(11 ÷ 10.5) = 0.0465 → 0.0465 ÷ 0.0345 × 60 = **81
  minutes**.

The stop is never longer than the room *Optimal stop* maximum; before any
cooling is learned the maximum is used. If the room gets colder than the
comfort during the stop, the stop is cancelled and the current level comes
back until the change. With an hourly forecast, the mean forecast of the stop
period is used, in 3 passes like the start.

---

## 9. Fictional simulations

The simulations below compare the learning of version 2.0 with the one of
1.x. They use **fictional houses**: the numbers are chosen to be plausible,
they are not measurements.

### 9.1 The fictional houses

Each house heats as: rise per hour = power − k × (inside − outside), after a
fixed delay.

| House | Delay | Power (°C/h) | k (per hour) |
|---|---|---|---|
| Insulated flat | 15 min | 1.6 | 0.035 |
| Average house | 24 min | 2.8 | 0.07 |
| Old house, poor insulation | 30 min | 4.5 | 0.12 |
| Floor heating (slow) | 90 min | 1.6 | 0.04 |

**With a weather curve**: the flow temperature is 35 + 0.8 × (14.5 − outdoor)
(0.8 °C more flow for each °C colder, e.g. 41 °C at 7 °C and 35 °C at
14.5 °C), and the power is proportional to (flow − room), scaled to be the
power of the table at 5 °C outdoors.

### 9.2 Version 2.0 against version 1.x

Assumptions:

- 80 days, outdoor temperature random between −5 and 10 °C each day;
- three programmes: **night setback every day** (8 hours without heating from
  21 °C, not below 17 °C), **setback at the weekend only**, **no setback**
  (the morning starts 0.3 – 0.6 °C below 21 °C);
- 6 thermostat cycles a day of 0.1 – 0.3 °C;
- the sensor reading rounded to its step (0.1 °C or 0.5 °C); tolerance 0.3 or
  0 °C; with and without a weather curve;
- ±7 % random noise on every duration;
- the first 50 days learn, the mornings of days 51 – 80 are predicted (the
  learning goes on during them).

4 houses × 2 curves × 2 tolerances × 2 sensor steps = **32 combinations** per
programme, 3 repetitions each.

| Programme | 1.x: mean error | 2.0: mean error | Combinations where 2.0 is worse |
|---|---|---|---|
| Night setback every day | 173 min | 4 min | 0 of 32 |
| Setback at the weekend | 92 min | 4 min | 0 of 32 |
| No setback | 16 min | 11 min | 0 of 32 |

(Mean error: the mean of the absolute differences between the predicted and
the real duration, then the mean over the 32 combinations.)

The large gain comes from the large rises after a setback (section 3, *Why a
fixed part*). Without a setback the rises are small and both versions are
close.

### 9.3 Keeping small and large episodes apart

Same houses, setback every night, sensor step 0.1 °C, **tolerance 0** (the
case where the thermostat cycles reach the learning), 300 mornings per house.
Values: mean / largest error in minutes, and how many large episodes were in
the memory on average.

| House (no curve) | last 30 episodes | 15 small + 15 large | 25 small + 25 large |
|---|---|---|---|
| Insulated flat | 9 / 64 (4 large) | 6 / 34 (15) | 6 / 25 (25) |
| Average house | 8 / 53 | 6 / 29 | 5 / 23 |
| Old house | 6 / 43 | 5 / 24 | 4 / 19 |
| Floor heating | 15 / 97 | 10 / 55 | 9 / 42 |

With tolerance 0.3 °C all three give similar results (for example the
insulated flat 6 / 23, 6 / 22 and 5 / 23), so keeping them apart costs
nothing when it is not needed.

### 9.4 How far apart the outdoor temperatures must be

The hardest case: 50 days of learning with an outdoor temperature that
changes **very little** (between 5 °C and 5 °C + the change in the table),
then 30 days between −5 and 10 °C, far outside what was learned.
Insulated flat with a weather curve, mean / largest error in minutes:

| Outdoor changed while learning | threshold 0.5 °C | 1 °C | 2 °C | 3 °C |
|---|---|---|---|---|
| 1 °C | 5 / 143 | 4 / 34 | 4 / 34 | 4 / 34 |
| 2 °C | 4 / 87 | 4 / 87 | 4 / 36 | 4 / 36 |
| 3 °C | 4 / 74 | 4 / 74 | 4 / 74 | 4 / 39 |

The mean error does not depend on the threshold; only the worst case does,
and only in the **first 3 days** of the new weather. With the threshold of
1 °C, case "2 °C" above:

| Days of the new weather | 1 – 3 | 4 – 7 | 8 – 14 | 15 – 30 |
|---|---|---|---|---|
| mean / largest error (min) | 12 / 87 | 5 / 20 | 4 / 11 | 3 / 14 |

The new episodes are learned and the error falls by itself. 0.5 °C stays
worse even later, so 1 °C was chosen.

### 9.5 Weather curve: why a single outdoor term

A first idea was a physical model (fixed heating power plus the learned
cooling). Without a weather curve it is slightly better than 2.0; **with** a
curve it is clearly worse, because the power changes with the weather:

| House, with curve | 1.x | physical model | 2.0 |
|---|---|---|---|
| Insulated flat | 41 | 31 | 3 |
| Average house | 38 | 19 | 2 |
| Old house | 54 | 13 | 1 |
| Floor heating | 177 | 39 | 8 |

(Mean error in minutes over five test situations: 18 → 21 °C at 5, −5 and
12 °C outdoors, 19 → 21 °C at 0 °C, 20.5 → 21 °C at 5 °C; 30 learned episodes,
60 % small.)

---

## 10. Limits

- **Day to day differences are not learned.** The same rise can take
  different times because of the sun, people, cooking, or because the walls
  are colder after a long absence. Least squares averages them; it cannot
  predict them. In practice the error falls to the size of these differences
  and not further.
- **Changes of the heat source** (a new weather curve, a new setpoint of the
  boiler zone) are learned again over the next episodes (section 6).
- **TRVs with a boiler started by a thermostat that is not in Home
  Assistant**: the integration cannot tell when the boiler really runs; the
  learning is not reliable and optimal start / stop are not recommended.
- **Learning saved before 2.0** kept only a speed per episode, without the
  degrees and the minutes, so it cannot be converted: the heating is learned
  again after the update. The cooling is kept.

---

## 11. Where to see it

**`sensor.<room>_heating_rate`** – state: minutes per degree at the outdoor
temperature of now (`min/°C` or `min/°F`). Attributes:

| Attribute | Meaning |
|---|---|
| `fixed_minutes` | the fixed part |
| `minutes_per_degree` | minutes per degree at −10 / 0 / 10 / 20 °C (14 / 32 / 50 / 68 °F) |
| `per_outdoor_degree` | change of the minutes per degree for each degree outdoors |
| `uses_fixed`, `uses_outdoor` | which terms are used (section 5) |
| `episodes`, `large_episodes` | kept episodes, and how many of them are large |
| `learning_starts_below_target` | the tolerance from which an episode starts |
| `last_episodes` | the last 5 episodes (outdoor, rise, minutes, time) |

**`sensor.<room>_cooling_rate`** – state: how fast the room falls now without
heating (°C/h); attributes: the coefficient, the episodes, the tolerance.

**`sensor.<room>_decision`** – `next_estimate` (when the next optimal start /
stop begins, with which outdoor temperature, and whether it is learned or
default) and `time_to_target`.

**Card, Details** – group *Learning*: *Heating learned* (number of episodes,
the fixed part and the minutes per degree now, e.g. *12 episodes · 25 min +
49 min/°C now*) and *Cooling learned*, each with its **Reset** button, then the
last heating episode (*+0.2° in 167 min, outdoor 12.0°, 09:11*); group
*Schedule*: the next optimal start / stop.

**Diagnostics** – `learned_heating` with all the numbers of the model.
