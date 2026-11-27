# 13. The SHC panel

*[Română](13-panou.ro.md) · [Contents](README.md)*

Besides the card, the integration adds a page of its own to the sidebar of
Home Assistant: **SHC**. It shows the whole house on one screen and adds what
does not fit in a card: the schedule of every room side by side, statistics
and the history of the decisions and alerts.

The panel needs no setup. It appears with the first house and goes away when
the last house is deleted. Every user of Home Assistant sees it, not only the
administrators. It is drawn by the same code as the card, so a room looks and
works the same in both: what is said about a room in [chapter 10](10-card.md)
holds here too.

The panel has five tabs: **Rooms**, **Schedule**, **Statistics**,
**History** and **Devices**. The tab last used is kept in the
browser, and the tab shown is in the address (`#week`, `#stats`, `#history`,
`#devices`), so a link (on a dashboard, a tablet) opens the panel on it. The top bar shows the name of the house (with several houses, the
name of the integration).

On a keyboard, the arrow keys go from room to room in the list (Home and End:
the first and the last) and from tab to tab; the place the keyboard is on is
outlined.

## Rooms

The house is on top (presence, mode, pause, guests, vacation, the outdoor
temperature and the heating), the rooms are listed on the side and the chosen
room (marked in the list by a bar in the accent colour of the theme) is open in
the middle, with everything the card shows and does.

- A tap on a room in the list opens it, with a short fade. The room is kept in the address
  (`/shc#<room>`), so a link or a bookmark opens that room, and in the browser.
- On a phone the rooms are a list; a room opens on the whole screen, with
  **Back** in the top bar.

On a wide screen:

- **The house is a bar**: its name, presence and people, then the outdoor
  temperature, the heating season, the heat demand and the heating time (a tap
  changes its period). Under them the mode, the heat source, the scenarios and
  the buttons Pause, Guests, Vacation, Reevaluate and Automatic.
- **The chosen room** has its arc, its reason, what comes next and its buttons
  on the left and its chart, wider, on the right, open from the start (when
  the panel is not wide enough for both, the chart goes under the room). Under them: the
  bar of today's schedule and the temperatures of its levels (*Eco 18°*), the
  level it is on outlined; the sections opened by the buttons (schedule,
  levels, details) come after them.

On a phone the house and the room are as in the card; the chart opens in its
window.

### Groups of rooms

Next to the tabs, the rooms can be grouped **by floor** (the floor of the area
of Home Assistant the room is in, in the order of the levels of the floors) or
**by circuit** (the heating circuit of the room, see
[chapter 8](08-heat-source-and-energy.md)); the rooms of no floor or no
circuit come last. The choice is there only when some room has a floor or a
circuit, and is kept in the browser. The groups are used in the list of
rooms, in the Schedule tab and in the Devices tab.

### Several houses

With several houses, every tab shows the rooms of each house under its name,
so two rooms with the same name (a *Bedroom* in each house) are told apart.
In the History a room is written with its house (*Cabin · Bedroom*), and the
room filter lists the rooms under their house.

## Schedule

Today and the next 6 days as the schedule will run them: every room on the
day chosen, with its levels and their temperatures (*Eco 18°*, the
temperature left out when it does not fit) on a shared time line from 00:00 to
24:00.

- The days are chosen above the bars, each with its date; today is first and
  marked. On today a line shows the time now.
- Above the bars, what is special about the day:
  - a **holiday**: a weekday that the Workday integration (the *Workday
    sensor* of the house, see [chapter 4](04-schedule.md)) says is a day off,
    run with the profile of weekend days; or a weekend day that is a workday;
  - a **profile from the calendar**: a calendar event titled with the name
    of a profile chooses it for that day;
  - a **level from the calendar**: a calendar event titled with the name of a
    level sets that level for its hours; it is drawn over the bars, hatched;
  - the **vacation** planned in the house, with its start and end; it is drawn
    over the bars, hatched, until the heating starts again before its end;
    while guest mode is on the vacation is held off, so it is only told.
- Next to each bar is the name of the profile used that day (*calendar* when
  a calendar event chose it).
- A room with no active profile that day shows *No active profile: frost
  protection*.
- A room that follows a Schedule helper shows that its schedule is edited in
  the helper.
- A tap on a room opens it on the Rooms tab with its schedule editor open.
- The copy button at the end of a row (shown when the mouse is over the row,
  always on a touch screen) opens the room with *Copy to other rooms*: its whole schedule is copied to the rooms chosen (see
  [chapter 10](10-card.md)).

The days are computed by the integration as the rooms compute them, with the
start of the schedule day of the house, and shown in the time zone of the
house (on a day the clock changes the hours fall where they really are). They
are read again at once when a schedule, the vacation or guest mode changes. What cannot be known ahead is not in
them: presence (home or away), open windows, manual changes and a house mode
changed by hand. The holidays and the calendar events are read for today and
the next 7 days, every hour.

## Statistics

The heating time and the temperatures of the house and of every room, by
**day**, **week** or **month**: the last 14 days, 12 weeks or 12 months. They
come from the long-term statistics of Home Assistant (the recorder), so they
are kept for as long as Home Assistant keeps those. The bars grow from their
foot when a period is shown (not with *reduce motion*).

- **The house**: a bar for each day, week or month with its heating time, and
  over the bars a line of the mean outdoor temperature of each period, on a
  scale of its own (its highest, middle and lowest value, on the right of the
  bars), so
  colder periods and longer heating can be seen together. A tap on a point of
  the line shows the mean of that period with its lowest and highest value; a
  tap on it again hides them. The title gives the total time and the outdoor
  mean with its lowest and highest value.
- **A tap on a bar** chooses that period: under the bars the time of the
  house, the outdoor temperature (mean, lowest and highest) and the number of
  starts asked; the rooms below then show that period only. A tap on the same
  bar again, or on ✕, shows the whole range.
- **The rooms**: each room with its heating time, its share of the time of
  all rooms, its mean temperature and mean target (the lowest and highest when
  hovered), sorted by time.
- **Times the heat source was asked to start**, by day. These come from the
  history of Home Assistant, which is kept for 10 days by default: older days
  have no bar.
- **Optimal start**: for each room that has the optimal start, how its starts
  ended in the period shown (or the one chosen): reached **in time** (and how
  many minutes before the time of the level, on average), **late** (how many
  minutes after it, on average) or **not reached** while the level held. Only
  the starts that ran up to the time of the level count: one stopped before
  (someone left, a window, a manual change) did not get to try. The integration
  keeps the last 100 of each room, over restarts.

- **Heating by hour**: below, a row of 24 hours for each room, the darker the
  more minutes of that hour the room was heated, over the last 7 days: as the
  mean of the 7 days (when a room usually heats), or for one of them. It comes
  from the history of Home Assistant (the heat demand of each room while its
  heat source ran), so it needs those days in the history (10 by default); the
  hours are those of the time zone of the house. A tap on an hour shows its
  minutes under the grid; ✕ hides them.

The statistics are asked for again every 5 minutes while the tab is open.

## History

- **Alerts now** on top: every alert that is on, of every house, once each,
  with its room (or *Whole house*) and since when. When the alert names an
  entity (a thermostat, a sensor), a tap on its text opens that entity;
  **Open the room** opens its room. The number of alerts
  on now is shown on the History tab too.
- Below, **the history**: the decisions of every room and the alerts with
  their start and end, newest first, by day. It can show only the decisions or
  only the alerts, and one room or all (a room shows its alerts and those of
  the whole house).

The integration keeps the last 100 decisions of each room and the last 100
alerts of each house, also across restarts. An alert still on when Home
Assistant stops ends at the restart and is told again after it if it still
applies.

## Devices

### Humidity

On top, when some room has a humidity sensor: the humidity of the air of each
such room and the one estimated at its coldest wall (from the outdoor
temperature), those at risk of mold first. A room is at risk with an active
mold alert, or with 80% or more at the coldest wall, as its Details show it.
The number of rooms at risk is in the title; a tap on a room opens its
Details.

### The devices

Every entity the rooms use, of every house, in one list: thermostats, TRVs,
switches, temperature and humidity sensors, windows, occupancy sensors and
calibration entities. An entity used by several rooms (a window shared by two
rooms) is listed once, with all its rooms.

- The **unavailable** ones come first (their number is in the title), then
  those whose battery Home Assistant reports as low, then the rest by room.
- Each row shows the name, the role and the room, the state now (for a
  thermostat its temperature, its target and whether it heats), the
  **battery** and how long ago the entity last changed.
- The battery is that of the device of the entity in Home Assistant: a battery
  sensor in % or a binary *battery* sensor (*low*). An entity whose device has
  no battery entity shows none. Nothing is set up for this.
- A tap on a row opens the entity.
