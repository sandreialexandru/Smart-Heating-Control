"""Schedule parsing and evaluation (pure Python, no Home Assistant imports).

A schedule is a set of named profiles. Each profile is a list of time slots;
a slot starts at a clock time and lasts until the next slot. The text format
used in the configuration is one profile per line::

    workday: 00:00 sleep, 06:00 home, 22:00 sleep
    weekend: 00:00 sleep, 08:00 home, 23:00 sleep
    fri: 00:00 sleep, 06:00 home, 23:30 sleep
    home_office: 00:00 sleep, 07:00 home, 23:00 sleep

Each profile has its days and is on or off (``profile_days``): all days,
workdays, weekend days, or chosen weekdays. Profile selection for a day,
highest priority first:
1. a profile forced for that day (a calendar event with its name),
2. an active profile for that weekday (e.g. ``wed``),
3. the active profile for workdays or for weekend days, else the active one
   for all days.
A day no active profile covers keeps the frost protection (``PRESET_FROST``).

Active profiles never overlap: the profiles of all days, of workdays and of
weekend days are one choice per kind of day, and profiles of chosen weekdays
cannot share a day. A profile of a weekday is above the others on that day.

The day boundary (default 00:00) moves the start of the schedule day, so a
night shift can keep one profile from e.g. 04:00 to 04:00 the next day.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

from .const import DAYS_ALL, DAYS_WEEKEND, DAYS_WORKDAY, PRESET_FROST, WEEKDAYS

PROFILE_WORKDAY = "workday"
PROFILE_WEEKEND = "weekend"

# Names may use any letters (ă, ș, ț...), digits, "_", spaces and "-"; the
# characters of the format (",", ":", "#") cannot be part of a name.
NAME_RE = re.compile(r"[\w -]+")
_PROFILE_RE = re.compile(r"^\w[\w -]*$")
_SLOT_RE = re.compile(r"^(\d{1,2}):(\d{2})\s+([\w -]+)$")

MINUTES_PER_DAY = 24 * 60


class ScheduleError(ValueError):
    """Raised when a schedule text cannot be parsed."""


@dataclass(frozen=True, slots=True)
class Slot:
    """A schedule slot: from ``minute`` (since midnight) the ``preset`` applies."""

    minute: int
    preset: str

    @property
    def time_str(self) -> str:
        """Return the slot start as HH:MM."""
        return f"{self.minute // 60:02d}:{self.minute % 60:02d}"


@dataclass(frozen=True, slots=True)
class ScheduleState:
    """Result of a schedule lookup."""

    preset: str
    profile: str | None  # None: no active profile (frost protection)
    slot_start: datetime
    next_change: datetime | None
    next_preset: str | None


def parse_time(value: str) -> int:
    """Parse ``HH:MM`` or ``HH:MM:SS`` into minutes since midnight."""
    parts = str(value).strip().split(":")
    if len(parts) < 2:
        raise ScheduleError(f"Invalid time '{value}'")
    try:
        hours, minutes = int(parts[0]), int(parts[1])
    except ValueError as err:
        raise ScheduleError(f"Invalid time '{value}'") from err
    if not (0 <= hours <= 23 and 0 <= minutes <= 59):
        raise ScheduleError(f"Invalid time '{value}'")
    return hours * 60 + minutes


def parse_schedule(text: str, valid_presets: Iterable[str]) -> dict[str, list[Slot]]:
    """Parse the schedule text into profiles.

    Preset names are matched case-insensitively against ``valid_presets`` and
    stored with the spelling used in ``valid_presets``.
    """
    lookup = {p.lower(): p for p in valid_presets}
    profiles: dict[str, list[Slot]] = {}
    for line_no, raw_line in enumerate((text or "").splitlines(), start=1):
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if ":" not in line:
            raise ScheduleError(f"Line {line_no}: expected 'profile: HH:MM preset, ...'")
        name, _, body = line.partition(":")
        name = name.strip().lower()
        if not _PROFILE_RE.match(name):
            raise ScheduleError(f"Line {line_no}: invalid profile name '{name}'")
        if name in profiles:
            raise ScheduleError(f"Line {line_no}: profile '{name}' is defined twice")
        slots: dict[int, Slot] = {}
        for chunk in body.split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            match = _SLOT_RE.match(chunk)
            if not match:
                raise ScheduleError(
                    f"Line {line_no}: invalid slot '{chunk}' (expected 'HH:MM preset')"
                )
            minute = parse_time(f"{match.group(1)}:{match.group(2)}")
            preset_raw = match.group(3).strip().lower()
            if preset_raw not in lookup:
                raise ScheduleError(
                    f"Line {line_no}: unknown preset '{match.group(3).strip()}'"
                    f" (valid: {', '.join(lookup.values())})"
                )
            if minute in slots:
                raise ScheduleError(f"Line {line_no}: two slots start at {chunk.split()[0]}")
            slots[minute] = Slot(minute, lookup[preset_raw])
        if not slots:
            raise ScheduleError(f"Line {line_no}: profile '{name}' has no slots")
        profiles[name] = sorted(slots.values(), key=lambda s: s.minute)
    if not profiles:
        raise ScheduleError("The schedule has no profiles")
    return profiles


def format_schedule(profiles: dict[str, list[Slot]]) -> str:
    """Format profiles back into the text representation."""
    return "\n".join(
        f"{name}: " + ", ".join(f"{s.time_str} {s.preset}" for s in slots)
        for name, slots in profiles.items()
    )


def profiles_to_dict(profiles: dict[str, list[Slot]]) -> dict[str, list[dict[str, str]]]:
    """Return a JSON friendly representation (used by the card)."""
    return {
        name: [{"time": s.time_str, "preset": s.preset} for s in slots]
        for name, slots in profiles.items()
    }


def profiles_from_dict(
    data: dict[str, list[dict[str, str]]], valid_presets: Iterable[str]
) -> dict[str, list[Slot]]:
    """Build profiles from the JSON representation and validate them.

    ``data`` is profile name -> list of {"time": "HH:MM", "preset": level}; a
    malformed value gives a clear ScheduleError.
    """
    if not isinstance(data, dict) or not data:
        raise ScheduleError(
            'profiles must be an object: profile name -> list of {"time", "preset"}'
        )
    lines = []
    for name, slots in data.items():
        if not isinstance(slots, list) or not slots:
            raise ScheduleError(f'Profile "{name}": give a list of {{"time", "preset"}}')
        parts = []
        for slot in slots:
            if not isinstance(slot, dict) or "time" not in slot or "preset" not in slot:
                raise ScheduleError(f'Profile "{name}": every slot needs "time" and "preset"')
            parts.append(f"{str(slot['time']).strip()} {str(slot['preset']).strip()}")
        lines.append(f"{name}: " + ", ".join(parts))
    return parse_schedule("\n".join(lines), valid_presets)


def _days_valid(days: object) -> bool:
    """A days value: all / workday / weekend or a non empty list of weekdays."""
    if days in (DAYS_ALL, DAYS_WORKDAY, DAYS_WEEKEND):
        return True
    return (
        isinstance(days, (list, tuple))
        and bool(days)
        and all(d in WEEKDAYS for d in days)
        and len(set(days)) == len(days)
    )


def default_profile_days(names: Iterable[str]) -> dict[str, dict]:
    """Days of profiles saved before profiles had days (same selection as before).

    ``mon`` ... ``sun`` are for their day, ``workday`` and ``weekend`` for their
    kind of day (for all days when the other one is missing), and when none of
    these exists the first profile is for all days. Other profiles are off.
    """
    names = list(names)
    result: dict[str, dict] = {}
    has_work, has_weekend = DAYS_WORKDAY in names, DAYS_WEEKEND in names
    for name in names:
        if name in WEEKDAYS:
            result[name] = {"days": [name], "enabled": True}
        elif name == DAYS_WORKDAY:
            result[name] = {"days": DAYS_WORKDAY if has_weekend else DAYS_ALL, "enabled": True}
        elif name == DAYS_WEEKEND:
            result[name] = {"days": DAYS_WEEKEND if has_work else DAYS_ALL, "enabled": True}
        else:
            result[name] = {"days": DAYS_ALL, "enabled": False}
    if names and not any(n in WEEKDAYS or n in (DAYS_WORKDAY, DAYS_WEEKEND) for n in names):
        result[names[0]] = {"days": DAYS_ALL, "enabled": True}
    return result


def overlap(a: object, b: object) -> bool:
    """True when two active profiles cannot be on together.

    All days, workdays and weekend days are one choice per kind of day (all days
    overlaps both, workdays and weekend days do not overlap). Chosen weekdays
    overlap when they share a day; they are above the other kinds, not against
    them.
    """
    a_list, b_list = isinstance(a, (list, tuple)), isinstance(b, (list, tuple))
    if a_list and b_list:
        return bool(set(a) & set(b))
    if a_list or b_list:
        return False
    if DAYS_ALL in (a, b):
        return True
    return a == b


def normalize_profile_days(data: dict | None, names: Iterable[str]) -> dict[str, dict]:
    """Days and on / off of every profile (missing or invalid entries fixed).

    Without saved data the selection of earlier versions is kept. A profile
    without (valid) data is off, for all days. When saved data has active
    profiles that overlap, the later ones are turned off.
    """
    names = list(names)
    if not isinstance(data, dict):
        return default_profile_days(names)
    result: dict[str, dict] = {}
    for name in names:
        item = data.get(name)
        days = item.get("days") if isinstance(item, dict) else None
        if isinstance(days, tuple):
            days = list(days)
        if not _days_valid(days):
            result[name] = {"days": DAYS_ALL, "enabled": False}
            continue
        if isinstance(days, list):
            days = [d for d in WEEKDAYS if d in days]
        result[name] = {"days": days, "enabled": bool(item.get("enabled"))}
    active: list[object] = []
    for name in names:
        if result[name]["enabled"]:
            if any(overlap(result[name]["days"], other) for other in active):
                result[name]["enabled"] = False
            else:
                active.append(result[name]["days"])
    return result


def validate_profile_days(data: object, names: Iterable[str]) -> dict[str, dict]:
    """Check the days sent for a schedule; raise ScheduleError when they are wrong."""
    names = list(names)
    if not isinstance(data, dict):
        raise ScheduleError("profile_days must be a mapping of profile names")
    for name, item in data.items():
        if name not in names:
            raise ScheduleError(f"Unknown profile '{name}' in profile_days")
        if not isinstance(item, dict) or not _days_valid(
            list(item.get("days")) if isinstance(item.get("days"), tuple) else item.get("days")
        ):
            raise ScheduleError(f"Invalid days for profile '{name}'")
    active = [(n, data[n]["days"]) for n in names if n in data and data[n].get("enabled")]
    for i, (name, days) in enumerate(active):
        for other, other_days in active[:i]:
            if overlap(days, other_days):
                raise ScheduleError(
                    f"Profiles '{other}' and '{name}' are both on for the same days"
                )
    return normalize_profile_days(data, names)


def uncovered_days(profile_days: dict[str, dict]) -> dict[str, object]:
    """Days without an active profile.

    ``days``: weekdays without a profile in a usual week (Monday to Friday
    workdays, Saturday and Sunday free); ``free_days``: a free weekday (a
    holiday) has no profile; ``workdays``: a workday on Saturday or Sunday has
    no profile.
    """
    active = [m["days"] for m in profile_days.values() if m.get("enabled")]
    specific = {d for days in active if isinstance(days, list) for d in days}
    has_all = DAYS_ALL in active
    work = has_all or DAYS_WORKDAY in active
    free = has_all or DAYS_WEEKEND in active
    days = [
        d for i, d in enumerate(WEEKDAYS) if d not in specific and not (work if i < 5 else free)
    ]
    return {
        "days": days,
        "free_days": not free and any(d not in specific for d in WEEKDAYS[:5]),
        "workdays": not work and any(d not in specific for d in WEEKDAYS[5:]),
    }


DayInfo = Callable[[date], tuple[bool, str | None]]
"""Return (is_workday, forced_profile) for a date."""


def resolve_local(wall: datetime, tzinfo) -> datetime:
    """The real moment of a local clock time (naive ``wall``) in ``tzinfo``.

    A time that occurs twice (the hour repeated at the end of summer time) is
    the first occurrence; a time that does not exist (the hour skipped in
    spring) is the moment that hour ends.
    """
    first = wall.replace(tzinfo=tzinfo, fold=0)
    if tzinfo is None:
        return first
    second = wall.replace(tzinfo=tzinfo, fold=1)
    u_first, u_second = first.astimezone(UTC), second.astimezone(UTC)
    if u_first == u_second or u_first.astimezone(tzinfo).replace(tzinfo=None) == wall:
        return first
    # Not a real time: the first minute after the clock jump.
    low, high = min(u_first, u_second), max(u_first, u_second)
    offset = low.astimezone(tzinfo).utcoffset()
    moment = low
    while moment < high:
        moment += timedelta(minutes=1)
        if moment.astimezone(tzinfo).utcoffset() != offset:
            return moment.astimezone(tzinfo)
    return high.astimezone(tzinfo)


class Schedule:
    """Evaluate a parsed schedule."""

    def __init__(
        self,
        profiles: dict[str, list[Slot]],
        day_boundary: int = 0,
        profile_days: dict | None = None,
    ) -> None:
        """Initialize the schedule. ``day_boundary`` is in minutes after midnight."""
        if not profiles:
            raise ScheduleError("The schedule has no profiles")
        self.profiles = profiles
        self.boundary = day_boundary % MINUTES_PER_DAY
        self.profile_days = normalize_profile_days(profile_days, profiles)

    @property
    def profile_names(self) -> list[str]:
        """Return the profile names in definition order."""
        return list(self.profiles)

    def profile_for(self, day: date, is_workday: bool, forced: str | None) -> str | None:
        """Return the profile used for the given schedule day (None: no active profile)."""
        if forced and forced.lower() in self.profiles:
            return forced.lower()
        weekday = WEEKDAYS[day.weekday()]
        active = [(n, m["days"]) for n, m in self.profile_days.items() if m["enabled"]]
        for name, days in active:
            if isinstance(days, list) and weekday in days:
                return name
        kind = DAYS_WORKDAY if is_workday else DAYS_WEEKEND
        for wanted in (kind, DAYS_ALL):
            for name, days in active:
                if days == wanted:
                    return name
        return None

    def _key(self, minute: int) -> int:
        """Position of a clock minute inside the schedule day."""
        return (minute - self.boundary) % MINUTES_PER_DAY

    def _ordered(self, profile: str | None) -> list[Slot]:
        """Slots of a profile in the order of the schedule day.

        A day without an active profile is one slot of frost protection from
        the start of the schedule day.
        """
        if profile is None:
            return [Slot(self.boundary, PRESET_FROST)]
        return sorted(self.profiles[profile], key=lambda s: self._key(s.minute))

    def schedule_day(self, moment: datetime) -> date:
        """Return the schedule day a moment belongs to."""
        return (moment - timedelta(minutes=self.boundary)).date()

    def day_start(self, day: date, tzinfo) -> datetime:
        """Return the moment a schedule day starts."""
        start = datetime.combine(day, time(0, 0)) + timedelta(minutes=self.boundary)
        return resolve_local(start, tzinfo)

    def _slot_moment(self, day: date, slot: Slot, tzinfo) -> datetime:
        """Real moment a slot starts on a schedule day.

        A clock time of the hour repeated at the end of summer time is its first
        occurrence; one in the hour skipped in spring starts when that hour ends.
        """
        wall = datetime.combine(day, time(0, 0)) + timedelta(
            minutes=self.boundary + self._key(slot.minute)
        )
        return resolve_local(wall, tzinfo)

    def lookup(self, moment: datetime, day_info: DayInfo) -> ScheduleState:
        """Return the active preset and the next change for ``moment``."""
        tz = moment.tzinfo
        day = self.schedule_day(moment)
        is_workday, forced = day_info(day)
        profile = self.profile_for(day, is_workday, forced)
        slots = self._ordered(profile)

        # Real moments, not clock times: in the repeated autumn hour a slot that
        # already started is not undone, and a slot in the skipped spring hour
        # starts when that hour ends.
        # Compared in UTC: two moments with the same time zone compare by clock time.
        now_utc = moment.astimezone(UTC)
        current: Slot | None = None
        current_day = day
        for slot in slots:
            if self._slot_moment(day, slot, tz).astimezone(UTC) <= now_utc:
                current = slot
        if current is None:
            # Before the first slot: the last slot of the previous day continues.
            prev_day = day - timedelta(days=1)
            prev_workday, prev_forced = day_info(prev_day)
            prev_profile = self.profile_for(prev_day, prev_workday, prev_forced)
            current = self._ordered(prev_profile)[-1]
            current_day = prev_day
        # Returned in UTC: an equality test between time zones is always False
        # for a clock time of the repeated autumn hour.
        slot_start = self._slot_moment(current_day, current, tz).astimezone(UTC)

        next_change, next_preset = self._next_change(moment, day, slots, current.preset, day_info)
        return ScheduleState(
            preset=current.preset,
            profile=profile,
            slot_start=slot_start,
            next_change=next_change,
            next_preset=next_preset,
        )

    def _next_change(
        self,
        moment: datetime,
        day: date,
        slots: list[Slot],
        preset: str,
        day_info: DayInfo,
    ) -> tuple[datetime | None, str | None]:
        """Find the next moment the preset actually changes (up to 8 days)."""
        tz = moment.tzinfo
        candidates: list[tuple[date, Slot]] = [
            (day, s)
            for s in slots
            if self._slot_moment(day, s, tz).astimezone(UTC) > moment.astimezone(UTC)
        ]
        for offset in range(1, 9):
            next_day = day + timedelta(days=offset)
            workday, forced = day_info(next_day)
            profile = self.profile_for(next_day, workday, forced)
            candidates.extend((next_day, s) for s in self._ordered(profile))
            for cand_day, slot in candidates:
                if slot.preset != preset:
                    return self._slot_moment(cand_day, slot, tz).astimezone(UTC), slot.preset
            candidates = []
        return None, None

    def upcoming(
        self, moment: datetime, day_info: DayInfo, horizon: timedelta
    ) -> list[tuple[datetime, str]]:
        """Return preset changes between ``moment`` and ``moment + horizon``."""
        result: list[tuple[datetime, str]] = []
        cursor = moment
        # In UTC: real time across a change of the clock.
        end = moment.astimezone(UTC) + horizon
        state = self.lookup(cursor, day_info)
        while state.next_change is not None and state.next_change.astimezone(UTC) <= end:
            result.append((state.next_change, state.next_preset or state.preset))
            # Looked up again in the local time zone (the schedule day is local).
            cursor = state.next_change.astimezone(moment.tzinfo)
            state = self.lookup(cursor, day_info)
        return result
