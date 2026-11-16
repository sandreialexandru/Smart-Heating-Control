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

The panel has four tabs: **Rooms**, **Schedule**, **Statistics** and
**History**. The tab last used is kept in the browser.

## Rooms

The house is on top (presence, mode, pause, guests, vacation, the outdoor
temperature and the heating), the rooms are listed on the side and the chosen
room is open in the middle, with everything the card shows and does.

- A tap on a room in the list opens it. The room is kept in the address
  (`/shc#<room>`), so a link or a bookmark opens that room, and in the browser.
- On a phone the rooms are a list; a room opens on the whole screen, with
  **Back** in the top bar.

## Schedule

Every room on one day, with the bar of the profile that room uses that day on
a shared time line from 00:00 to 24:00.

- The day is chosen above the bars; today is marked and opens first. On today
  a line shows the time now.
- Next to each bar is the name of the profile used that day.
- A room with no active profile for that day shows *No active profile: frost
  protection*: on such a day the room keeps the frost protection (see
  [chapter 4](04-schedule.md)).
- A room that follows a Schedule helper shows that its schedule is edited in
  the helper.
- A tap on a room opens it on the Rooms tab with its schedule editor open.

The profile of a day is chosen as the integration chooses it: a profile of
that weekday, else the one of workdays or weekend days, else the one of all
days. Here workdays are Monday to Friday: days off from a calendar and
profiles chosen by a calendar event are not shown in this tab (the room's own
schedule and its chart show the day as it really is).

## Statistics

The heating time and the temperatures of the house and of every room, by
**day**, **week** or **month**: the last 14 days, 12 weeks or 12 months. They
come from the long-term statistics of Home Assistant (the recorder), so they
are kept for as long as Home Assistant keeps those.

- **The house**: a bar for each day, week or month with its heating time, and
  under each bar the mean outdoor temperature of that period. The title gives
  the total time and the outdoor mean with its lowest and highest value.
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
