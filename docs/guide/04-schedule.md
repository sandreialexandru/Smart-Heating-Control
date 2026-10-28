# 4. Schedule

*[Română](04-program.ro.md) · [Contents](README.md)*

The schedule says **which level you want while someone is home**. Presence,
windows and the other rules can lower it (e.g. `away` when you leave), but
never raise it.

## The format

One **profile** per line. Every slot is `HH:MM level` and lasts until the next
one:

```
workday: 00:00 sleep, 06:00 home, 22:00 sleep
weekend: 00:00 sleep, 08:00 home, 23:00 sleep
```

Read: on workdays `sleep` from 00:00, `home` from 06:00, `sleep` from 22:00 to
the end of the day. At the weekend you get up at 08:00.

This is also the default schedule of every new room.

- The profile name is free (`workday`, `weekend`, `home_office`, `friday`…), also
  with accented letters; only `,` `:` and `#` cannot be used.
- The level can be any of `home`, `sleep`, `eco`, `away`, `comfort`,
  `activity`, or the names you gave the levels in the room settings.
- If the first slot does not start at 00:00 (or at the start of the day, see
  below), the last level of the day before continues until it. For example,
  with `workday: 06:00 home, 22:00 sleep`, between 00:00 and 06:00 the `sleep`
  from 22:00 of the day before stays.

A wrong schedule is not saved (*Invalid schedule*). If a saved schedule becomes
invalid, the room uses the default schedule and shows the alert *The schedule
is invalid (…); the default schedule is used*.

It is easiest to edit from the **card** (*Schedule*): start times are dragged on
the day bar, in 5-minute steps, and a profile can be copied over another (see
[chapter 10](10-card.md)).

## The days of every profile

Every profile has **its days** and is **on or off**. Set in the card:

| Days | Means |
| --- | --- |
| All days | every day |
| Workdays | Monday–Friday, without holidays (with the Workday sensor) |
| Weekend | Saturday, Sunday and holidays |
| Chosen days | e.g. only Friday, or Monday and Wednesday |

**Which profile a day uses**, in this order:

1. a **calendar event** titled with a profile name (even of a profile that is
   off);
2. the active profile for **that weekday** (e.g. a profile for Wednesday is
   above the workday profile, but only on Wednesdays);
3. the active profile of **workdays** or of the **weekend**;
4. the active profile for **all days**;
5. none: the day stays on **frost protection**, and the room shows the alert
   *No active schedule profile: …*.

**Active profiles never overlap.** Turning a profile on turns off the active
ones it would overlap: "all days" overlaps workdays and the weekend, and chosen
days overlap when they share a day. So a day never has two profiles. The card
warns before turning a profile on or off would leave days without a profile.

**Example.** You have `workday` (workdays), `weekend` (weekend) and
`home_office` (only Wednesday). On Wednesday `home_office` is used, on the other
workdays `workday`, on Saturday, Sunday and holidays `weekend`.

## Workdays and holidays

Without a Workday sensor, Monday–Friday are workdays. With the sensor of the
**Workday** integration (house options, *Workdays and calendar*), holidays count
as weekend. The integration also asks Workday about the next 7 days, so the plan
(and the optimal start) for tomorrow knows that tomorrow is a holiday.

## The calendar

Optionally, you can pick a Home Assistant **calendar** (e.g. a local or Google
calendar). The event title matters:

- **A profile name** (e.g. `home_office`): the profile is used for **the whole
  day** the event covers part of. The rule is the same today and on the coming
  days, so the plan and the optimal start worked out the day before match what
  happens.
- **A level name** (e.g. `away` or `comfort`): the level applies **while the
  event lasts**, instead of the schedule.

Events are read from the start of today for the next 7 days, every hour and as
soon as the calendar changes.

**Examples.**

- An all-day event "weekend" on a Tuesday (a day off): on Tuesday the `weekend`
  profile is used.
- An event "weekend" on Tuesday 10:00–16:00: still the `weekend` profile, for the
  whole Tuesday.
- An event "away" on Friday 09:00–17:00 (you are at a course): on Friday between
  09:00 and 17:00 the level is `away`, then the schedule returns.

The rules above the schedule (window, presence, safety) apply over the calendar
too.

## The start of the day (night shifts)

*Schedule day starts at* (00:00 by default) moves the moment the schedule day
changes.

**Example.** You work night shifts and go to bed on Friday morning at 04:00.
With the day starting at 05:00, Friday 00:00–05:00 still belongs to Thursday:
Thursday's profile (a workday) is used until 05:00, not Friday's.

## Change of the clock

The schedule uses the local clock but follows the real time:

- **in autumn**, when the hour 03:00–04:00 repeats, a slot in that hour (e.g.
  `03:30 home`) applies **once**, at its first occurrence; the second time the
  room does not go back to the level before;
- **in spring**, when the hour 03:00–04:00 does not exist, a slot in it
  (`03:30`) starts at **04:00**, and the optimal start is worked out for 04:00.

## Schedule helper

Instead of the internal schedule you can use a Home Assistant **Schedule
helper** (*Settings → Devices & services → Helpers → Schedule*). The integration
uses one level while the helper is on (`home` by default) and another while it
is off (`sleep` by default).

It suits you if you already have such a helper. The internal schedule is richer
(more levels, profiles per day, editor in the card).

## What happens at a change

At the schedule time, the room goes to the new level. With **optimal start**
the heating can begin earlier, so the new level is reached exactly at the
schedule time; with **optimal stop** a colder level can begin earlier (see
[chapter 7](07-optimal-start-stop-and-learning.md)).

The room's *Next change* sensor shows the next change, and the card shows in
the chart what comes in the next 12 hours.

## Changing the schedule from an automation

The service `advanced_climate.set_schedule` replaces the schedule of a room
(see [chapter 11](11-entities-and-services.md#services)):

```yaml
action: advanced_climate.set_schedule
data:
  room: Bedroom
  schedule: |
    workday: 00:00 sleep, 06:30 home, 22:30 sleep
    weekend: 00:00 sleep, 09:00 home, 23:30 sleep
```
