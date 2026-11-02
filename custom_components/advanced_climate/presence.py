"""House presence logic (pure Python, no Home Assistant imports).

Every person is classified as ``home``, ``nearby`` (inside a nearby zone, e.g.
the city) or ``far`` (outside every nearby zone). The house presence is then
derived from the people, presence sensors and guest mode, and debounced with
separate arrival and departure delays.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .const import (
    HOME_RULE_ALL,
    PRESENCE_FAR,
    PRESENCE_HOME,
    PRESENCE_NEARBY,
)

UNKNOWN_STATES = {"unknown", "unavailable", "", None}

_RANK = {PRESENCE_FAR: 0, PRESENCE_NEARBY: 1, PRESENCE_HOME: 2}


@dataclass(slots=True)
class ZoneInfo:
    """A zone used to classify people."""

    entity_id: str
    name: str
    latitude: float | None
    longitude: float | None
    radius: float

    def contains(self, latitude: float, longitude: float) -> bool:
        """Return True if the coordinates are inside the zone."""
        if self.latitude is None or self.longitude is None:
            return False
        return distance_m(self.latitude, self.longitude, latitude, longitude) <= self.radius


@dataclass(slots=True)
class PersonInfo:
    """Snapshot of a person entity."""

    entity_id: str
    state: str | None
    latitude: float | None = None
    longitude: float | None = None


def distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the great-circle distance in meters."""
    radius = 6371008.8
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def classify_person(
    person: PersonInfo,
    nearby_zones: list[ZoneInfo],
    all_zones: list[ZoneInfo],
    geometric: bool,
) -> str | None:
    """Return home / nearby / far for a person, or None if unknown."""
    state = person.state
    if state in UNKNOWN_STATES:
        return None
    if state == PRESENCE_HOME:
        return PRESENCE_HOME
    state_l = str(state).lower()
    for zone in nearby_zones:
        if state_l in (zone.name.lower(), zone.entity_id.split(".", 1)[-1].lower()):
            return PRESENCE_NEARBY
    if geometric:
        # Coordinates of the person (the most precise source).
        if (
            person.latitude is not None
            and person.longitude is not None
            and any(z.contains(person.latitude, person.longitude) for z in nearby_zones)
        ):
            return PRESENCE_NEARBY
        # A zone (e.g. "Office") whose centre lies inside a nearby zone.
        for zone in all_zones:
            if (
                state_l in (zone.name.lower(), zone.entity_id.split(".", 1)[-1].lower())
                and zone.latitude is not None
                and zone.longitude is not None
                and any(nz.contains(zone.latitude, zone.longitude) for nz in nearby_zones)
            ):
                return PRESENCE_NEARBY
    return PRESENCE_FAR


def raw_house_presence(
    classes: list[str | None],
    rule: str,
    sensors_home: bool,
    guest_mode: bool,
) -> str | None:
    """Combine people classes into a house presence. None = unknown."""
    if guest_mode or sensors_home:
        return PRESENCE_HOME
    known = [c for c in classes if c is not None]
    if not known:
        return None
    homes = [c == PRESENCE_HOME for c in known]
    if rule == HOME_RULE_ALL:
        # Everyone known must be home; unknown people do not block.
        if all(homes):
            return PRESENCE_HOME
    elif any(homes):
        return PRESENCE_HOME
    if any(c in (PRESENCE_HOME, PRESENCE_NEARBY) for c in known):
        return PRESENCE_NEARBY
    return PRESENCE_FAR


@dataclass(slots=True)
class PresenceDebouncer:
    """Apply arrival / departure delays to the raw house presence."""

    current: str | None = None
    pending: str | None = None
    pending_since: datetime | None = None
    changed_at: datetime | None = None
    history: list[tuple[str, str]] = field(default_factory=list)

    def update(
        self,
        raw: str | None,
        now: datetime,
        arrival_delay: timedelta,
        departure_delay: timedelta,
        raw_since: datetime | None = None,
    ) -> datetime | None:
        """Feed a raw value. Returns when the next check is needed, if any.

        ``raw_since`` is when the raw value really started (e.g. when the last
        person left), so a restart or a settings change does not restart the
        delay. Unknown values keep the pending change.
        """
        if raw is None:
            return None
        if self.current is None:
            self._set(raw, now)
            return None
        if raw == self.current:
            self.pending = None
            self.pending_since = None
            return None
        if raw != self.pending:
            self.pending = raw
            self.pending_since = min(raw_since, now) if raw_since else now
        delay = arrival_delay if _RANK[raw] > _RANK[self.current] else departure_delay
        assert self.pending_since is not None
        due = self.pending_since + delay
        if now >= due:
            self._set(raw, now)
            return None
        return due

    def _set(self, value: str, now: datetime) -> None:
        """Change the house presence and keep a short history."""
        self.current = value
        self.pending = None
        self.pending_since = None
        self.changed_at = now
        self.history.append((now.isoformat(), value))
        del self.history[:-20]

    def far_for(self, now: datetime) -> timedelta:
        """Return how long the house has been ``far`` (zero otherwise)."""
        if self.current != PRESENCE_FAR or self.changed_at is None:
            return timedelta(0)
        return now - self.changed_at

    def as_dict(self) -> dict:
        """Serialize."""
        return {
            "current": self.current,
            "changed_at": self.changed_at.isoformat() if self.changed_at else None,
            "pending": self.pending,
            "pending_since": self.pending_since.isoformat() if self.pending_since else None,
        }

    @classmethod
    def from_dict(cls, data: dict | None) -> PresenceDebouncer:
        """Restore."""
        obj = cls()
        if not data:
            return obj
        obj.current = data.get("current")
        for key in ("changed_at", "pending_since"):
            if data.get(key):
                try:
                    setattr(obj, key, datetime.fromisoformat(data[key]))
                except ValueError:
                    setattr(obj, key, None)
        obj.pending = data.get("pending") if obj.pending_since else None
        return obj


def is_arriving(
    distance_km: float | None,
    direction: str | None,
    travel_minutes: float | None,
    max_distance_km: float,
    max_minutes: float,
    direction_configured: bool,
) -> bool:
    """Return True if someone is on the way home (preheat).

    Someone is close when the distance or the travel time is under its
    threshold. When a direction sensor is configured the person must also be
    moving towards home, so sitting at the office near home does not count.
    """
    close = (distance_km is not None and distance_km <= max_distance_km) or (
        travel_minutes is not None and travel_minutes <= max_minutes
    )
    if not close:
        return False
    if direction_configured:
        return direction == "towards"
    return True
