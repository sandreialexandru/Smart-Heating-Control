# 5. Presence and vacation

*[Română](05-prezenta.ro.md) · [Contents](README.md)*

The integration wants to know whether someone is home, so it does not heat an
empty house. For this it uses the location of the people (usually from the
Home Assistant app on the phone), presence sensors and, optionally, the
distance to home.

## The three states of the house

| State | When | Level of the rooms |
| --- | --- | --- |
| **home** | someone is home (or everybody, by the rule) | the schedule |
| **nearby** | nobody home, but someone is in a nearby zone (e.g. in town) | `eco` or the fixed nearby temperature |
| **far** | everybody is outside home and the nearby zones | `away` |

Why three states: if you are at work in town, you may be back in 30 minutes,
so the house should not cool down too much (`eco`). If you have left town, it
can go lower (`away`).

Without nearby zones there is only *home* and *far*. Without people, the house
is always *home* and only the schedule decides.

## How every person is classified

For every person:

1. state `home` → **home**;
2. the name of a nearby zone (e.g. `Bucharest`) → **nearby**;
3. with *Use coordinates for nearby zones* (on by default):
   - the person's GPS coordinates are inside a nearby zone → **nearby** (this
     also fixes a stale `not_home` while the phone is actually in town);
   - the person is in a zone (e.g. `Office`) whose centre lies inside a nearby
     zone → **nearby**;
4. otherwise → **far**.

The states `unknown` and `unavailable` (flat phone battery, app stopped) change
nothing: the last known state is kept. They never count as leaving.

If nothing is known about anybody (e.g. right after the first start), the house
counts as *home*, so it is not cold.

## The rule for "home"

| Rule | The house is home when | Otherwise |
| --- | --- | --- |
| **At least one person is home** | anybody is home | nearby, if someone is nearby; far, if everybody is far |
| **Everybody is home** | everybody known is home | nearby, if someone is home or nearby; far, if everybody is far |

**Example with *Everybody is home*.** Andrei is home, Maria is at work in town:
the house is *nearby* (`eco`). When Maria comes too, the house is *home* (the
schedule).

## Presence sensors and guest mode

- **Presence sensors** (mmWave, motion, an `input_boolean`): while any of them
  is on, the house is *home*. Useful for people without a phone (children,
  grandparents) or as a safety net.
- **Guest mode** (the house's *Guest mode* switch): keeps the house *home*
  whatever the people do, e.g. when guests stay and you leave. It turns off by
  itself after *Guest mode turns off after* hours (0 = only by hand).

## The delays

- **Departure delay** (10 minutes by default): the house moves towards
  *nearby* or *far* only if the state stays so this many minutes. A short trip
  to the shop does not cool the house. The delay counts from when the last
  person left, so a Home Assistant restart does not start it again.
- **Arrival delay** (0 by default): the house moves towards *home* (or from
  *far* to *nearby*) after this many minutes. Keep 0 so the heating returns at
  once; raise it only if GPS sometimes reports "home" by mistake.

**Example.** You leave at 08:00. With the default delay of 10 minutes, the house
goes *far* at 08:10. If you come back at 08:05 for the forgotten keys, nothing
happens.

## Preheating on the way home

While you are *nearby* or *far*, the house can start to warm up **while you are
on the way home**, so it is warm when you arrive. You need one of:

- the Home Assistant **Proximity** integration, with its distance sensor (and
  optionally the direction sensor);
- a **travel time** sensor (Waze Travel Time, Google Travel Time).

Someone is **on the way home** (*arriving*) when closer than *Preheat below
distance* (10 km by default) **or** less than *Preheat below travel time* (20
minutes by default) away. With the direction sensor set, they must also be
coming closer (direction `towards`), so preheating does not start while sitting
at an office near home.

While someone is on the way home, the presence rules do not apply: the rooms
follow the schedule, as if you were already home.

**Example.** You come back from another city. At 10 km from home, Proximity
reports 9.8 km and direction "towards": the house goes to the schedule (e.g.
`home`) and warms up while you drive the last kilometres.

## Room occupancy

Apart from the presence of the house, a room can have **occupancy sensors**
(motion, mmWave). If they detect nobody for *Eco after no occupancy for* minutes
(30 by default), the room goes to `eco`, even if someone is in another room.

It applies only when the schedule asks for a level warmer than `eco`: e.g. at
night, with `sleep` colder than `eco`, the room stays on `sleep`.

**Example.** The office has a motion sensor. You work until 12:00, then leave
the room. At 12:30 the office goes to `eco`; when you come back in, it returns
to the schedule at once.

## Vacation

Vacation sets every room to `away`. It can start in three ways:

1. **The *Vacation* mode** (the house's *Mode* select): vacation until you
   change it.
2. **The vacation dates** (*Vacation start* and *Vacation end*, or the service
   `set_vacation`): the vacation starts and ends by itself.
   - Only an end date: the vacation starts now.
   - **Preheat before the end of a vacation** (4 hours by default): the schedule
     returns this many hours before the end, even if everybody is still far
     away, so it is warm when you come back.
3. **Automatic vacation**: *Automatic vacation after everyone is far for* (0 = off by
   default). When everybody has been far this many hours, the vacation starts by
   itself.
   - It ends when someone is *nearby* or *home*, or **on the way home** (the
     house preheats).
   - If everybody is then far again (e.g. you only passed by), it comes back only
     after another that many hours far.
   - The preheating before the end of a planned vacation wins over the automatic
     vacation.

**Guest mode wins over every vacation** (the mode, the dates or the automatic
one): while it is on, the rooms follow the schedule as if someone were home and
the card band says the vacation is suspended. When it is turned off, the
vacation goes on (the dates and the preheating stay as they were). Guest mode is
not turned off by itself because of a vacation: set *Guest mode turns off after*
if you want that.

On a day without an active schedule profile, the vacation does not bring `away`
(warmer), frost protection stays.

**Example.** You leave on Sunday morning for a week and set the end of the
vacation on the next Saturday at 18:00. With the default preheating of 4 hours,
at 14:00 the house returns to the schedule, so at 18:00 it is warm.

**Automatic vacation example.** You set 24 hours. You leave on Friday at 17:00
for the mountains and set no vacation. On Saturday at 17:00, after 24 hours far
away, the house goes to vacation (`away`) by itself. On Sunday evening, 10 km
from home, the automatic vacation ends and the house warms up.

The card has the vacation date fields and the clear button. The house's
*Presence* sensor shows in its attributes the state of every person
(`persons`), whether someone is on the way home (`arriving`), the guest mode
(`guest_mode`), whether a vacation is on (`vacation_active`) or its preheating
(`vacation_preheating`), and a change waiting for its delay (`pending`,
`pending_since`).
