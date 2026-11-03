# 6. Weather and season

*[Română](06-vreme.ro.md) · [Contents](README.md)*

The weather can **stop** the heating (when warm) or **adjust** it a little
(when very cold or sunny). It never raises the temperature above what the
schedule asks, except for the compensation of a few tenths of a degree that you
choose yourself.

Every setting is in the house options, under **Weather and season** (see
[chapter 2](02-install-and-house.md#weather-and-season)). Without an outdoor
sensor and a weather entity, the form does not let you turn on the functions
that need them.

## The outdoor temperature

It comes from the *Outdoor temperature sensor* or, without one, from the
temperature of the *Weather entity*. The outdoor sensor cannot be a temperature
sensor of a room. A value that is not a number (`nan`, `inf`) is ignored.

The integration keeps the values of the last 48 hours and works out **the
average of the last *Average over* hours** (6 by default), weighted by time:
every value counts for as long as it was valid.

*Average over* is also **how long a value stays valid**: if the sensor sends
nothing for that many hours, the outdoor temperature becomes **unknown**. Then
the cutoff, the compensation and the ignoring of windows do not apply, nothing
is learned and no optimal stop is made, until the sensor reports
again.
If no configured source gives a temperature (the sensor failed and the weather
entity missing, unavailable or without a temperature) for longer than *Alert when
a device is unavailable longer than* (15 minutes by default), you get an alert.
With the sensor failed and the weather entity fine there is no alert: the weather
temperature is used.

## Turning off when warm outside

*Turn heating off when it is warm outside* (off by default). It uses:

| Setting | Default | Role |
| --- | --- | --- |
| Outdoor cutoff temperature | 18 °C | the average at which the heating stops |
| Cutoff hysteresis | 1 °C | the heating may start again only at cutoff − hysteresis |
| Average over | 6 h | how many hours are averaged |

With the defaults: **the heating stops when the 6-hour average reaches 18 °C**
and **may start again when the average falls to 18 − 1 = 17 °C**. Between 17
and 18 °C it stays as it was. Without this band, an average swinging around the
cutoff would start and stop the heating many times.

Why an average and not the temperature now: a sunny October afternoon of 20 °C
does not mean the evening will not be cold. The 6-hour average moves slowly and
takes the whole day into account.

**Example** (chosen values). The whole morning had 14 °C, and from 12:00 it is
22 °C. At 15:00 the average of the last 6 hours (09:00–15:00) is
(3 h × 14 + 3 h × 22) ÷ 6 h = (42 + 66) ÷ 6 = 18 °C: the heating stops.

While the heating is off because of the weather, the room decision is *Warm
outside: heating off (would be …)*, and the card shows at the house *Warm
outside: on • heating is off until the average falls to 17°*.

## The forecast

*Use the forecast* (off by default) needs a **weather entity with an hourly
forecast** and the cutoff turned on. It uses **the mean forecast of the next
*Forecast hours*** (3 by default), never a single hour. In the mean every
forecast value holds for its hour, and until the next forecast hour the
temperature measured now is used.

The forecast has two effects:

**1. The heating is off because it was warm, but cold is coming.** If the
forecast mean is at **cutoff − hysteresis or below** (17 °C with the defaults),
the heating may start again, even if the measured average is still high. So a
warm afternoon does not keep the heating off in a cold evening. Above 17 °C the
heating stays off. The card shows *cancelled (forecast) • it gets cold: the
forecast mean for 3 h is …, rooms heat when they need it*.

**2. The heating runs, but warmth is coming.** If the forecast mean reaches **the
cutoff or above** (18 °C), the heating stops **earlier**, before the measured
average gets there. It stays off until the forecast mean falls to cutoff −
hysteresis (17 °C), with the same hysteresis as the measured average; the state
is saved over a restart. The card shows *on (forecast) • heating is off: the
forecast mean for 3 h is …*.

**How early it stops.** It depends on *Forecast hours* and on how warm it gets.
Example (chosen values): 10 °C now, a period of 20 °C coming, cutoff 18 °C, 3
forecast hours. The mean reaches 18 °C when the warm part is
(18 − 10) ÷ (20 − 10) = 0.8 of the window, so the heating stops
3 h × (1 − 0.8) = 0.6 h = 36 minutes before the warm period. With 6 forecast
hours it would be 72 minutes. More hours mean an earlier stop.

Without a forecast (or when it does not cover the hours) only the measured
average decides. The forecast is read every 30 minutes, and the decision is
worked out again right after every read.

## The heating season

*Heating season* decides in which period heating happens at all:

| Mode | What it does |
| --- | --- |
| **Always** (default) | Heating is possible all year. In summer you stop it with the *Summer* mode. |
| **Between dates** | Only between *Season start* and *Season end* (10-15 and 04-15 by default, i.e. 15 October – 15 April, month-day format). |
| **Automatic (outdoor temperature)** | The season starts after *Automatic season: consecutive days* (3 by default) days in a row with a daily average below the *Automatic season threshold* (15 °C by default) and ends after as many days in a row above it. |

For the automatic mode, the mean of every day is weighted by time and added up
as the values come (a restart does not spoil it). What counts are the X days
before today, in a row: a day without any value breaks the run.

**Example.** With the defaults, on 20 October the daily averages were 16, 14, 13
and 12 °C (17–20 October). On the 21st, the last 3 days (18, 19, 20 October: 14,
13, 12 °C) are all below 15 °C: the season starts.

Outside the season the rooms do not heat (frost protection stays), and the
learning stops. The valve exercise also runs outside the season.

## Outdoor compensation

*Outdoor compensation* (off by default) adds **Compensation** (+0.5 °C by
default) to the target while the outdoor temperature is below **Compensate
below** (−5 °C by default). When it is very cold, walls are cold and the same
temperature feels colder.

**Example.** The `home` target is 21 °C, outside it is −8 °C: the target becomes
21 + 0.5 = 21.5 °C.

## Solar gain

A room setting (*Solar gain*, between −3 and 0 °C, in the *Extras* step) that
appears only with a weather entity. While the sun shines, the room target drops
by the chosen value, for rooms that get warm from the sun (e.g. a living room
with large south windows).

"Sun" means: the sun is at least 10° above the horizon (from `sun.sun`) and the
weather entity says `sunny`, `clear` or `partlycloudy`.

**Example.** The living room has a solar gain of −1 °C and `home` 21 °C. At
noon, with a clear sky, the target is 21 − 1 = 20 °C.

Separately, every room with a weather entity in the house learns by itself how
much the sun warms it, for the optimal start and stop and the predicted
temperature (see [chapter 7](07-optimal-start-stop-and-learning.md#how-a-room-learns)).
That learning never changes the target; this setting does.

## Ignoring windows when warm

*Ignore windows above* (empty by default): when the outdoor temperature is at
this value or above, an open window no longer lowers the heating. In spring and
autumn, airing does not cool the room much.

## How the adjustments add up

Compensation, tariff, PV and solar gain add up. The sum is limited to ±3 °C and
applies only to a normal heating target, never to a frost protection (mode Off
or Summer, outside the season, open window, a day without a profile). The
result then goes through the safety limits (frost protection and maximum). The
card shows the active adjustments in *Details*.
