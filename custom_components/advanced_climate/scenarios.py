"""Scenarios: a choice of profiles for several rooms, chosen from the house.

A scenario is a subentry of the house: a name and, for every room in it, the
profiles to turn on. Choosing it does in every room what its profile select
does (the chosen profiles on, the active ones of the same days off); it adds no
state of its own. The house shows as active the scenario whose profiles are all
on. A room in it that cannot take its profiles (a profile deleted or renamed,
profiles of the same days, a room without its own schedule) is skipped and told
in Repairs; a deleted room leaves the scenarios.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigSubentry
from homeassistant.helpers import issue_registry as ir

from .const import (
    CONF_SCENARIO_ROOMS,
    CONF_SCHEDULE_SOURCE,
    DOMAIN,
    SCHEDULE_INTERNAL,
    SUBENTRY_SCENARIO,
)
from .schedule import overlap

if TYPE_CHECKING:
    from .house import House
    from .room import Room

# The problems of a scenario, in the language of Home Assistant (the Repairs text).
_TEXTS: dict[str, dict[str, str]] = {
    "en": {
        "empty": "it has no rooms",
        "missing": "{room}: no profile {profile}",
        "overlap": "{room}: {profiles} share days",
        "helper": "{room}: the room has no schedule of its own",
    },
    "ro": {
        "empty": "nu are camere",
        "missing": "{room}: nu există profilul {profile}",
        "overlap": "{room}: {profiles} au zile comune",
        "helper": "{room}: camera nu are program propriu",
    },
}


def scenario_subentries(house: House) -> list[ConfigSubentry]:
    """The scenarios of the house, in the order they were added."""
    return [
        sub for sub in house.entry.subentries.values() if sub.subentry_type == SUBENTRY_SCENARIO
    ]


def scenario_rooms(sub: ConfigSubentry) -> dict[str, list[str]]:
    """Room id → profiles of a scenario."""
    return {
        rid: list(profiles)
        for rid, profiles in dict(sub.data.get(CONF_SCENARIO_ROOMS) or {}).items()
    }


def own_schedule(room: Room) -> bool:
    """True for a room with its own schedule (profiles), not a schedule helper."""
    return room.config.get(CONF_SCHEDULE_SOURCE, SCHEDULE_INTERNAL) == SCHEDULE_INTERNAL


def overlapping(room: Room, profiles: list[str]) -> list[str]:
    """The profiles of the list that share days with another one of it."""
    days = room.schedule.profile_days
    known = [p for p in profiles if p in days]
    return [
        p for p in known if any(q != p and overlap(days[p]["days"], days[q]["days"]) for q in known)
    ]


def room_problems(room: Room, profiles: list[str]) -> list[tuple[str, dict[str, str]]]:
    """Why a room cannot take these profiles (code, placeholders); empty when it can."""
    if not own_schedule(room):
        return [("helper", {"room": room.name})]
    names = room.schedule.profile_names
    problems = [("missing", {"room": room.name, "profile": p}) for p in profiles if p not in names]
    if shared := overlapping(room, profiles):
        problems.append(("overlap", {"room": room.name, "profiles": ", ".join(shared)}))
    return problems


def problems(house: House, sub: ConfigSubentry) -> list[tuple[str, dict[str, str]]]:
    """The problems of a scenario (code, placeholders)."""
    rooms = scenario_rooms(sub)
    if not rooms:
        return [("empty", {})]
    found: list[tuple[str, dict[str, str]]] = []
    for rid, profiles in rooms.items():
        if (room := house.rooms.get(rid)) is not None:
            found += room_problems(room, profiles)
    return found


def active_scenario(house: House) -> str | None:
    """The scenario whose profiles are all on (none when no one matches).

    A room that cannot take its profiles is left out, as when the scenario is
    chosen (``activate``): a scenario applied without it is shown; one with no
    room left is not. When several match (one is part of another), the one
    that sets the most profiles; between equals, the first added.
    """
    best: tuple[int, str] | None = None
    for sub in scenario_subentries(house):
        ok = False
        size = 0
        for rid, profiles in scenario_rooms(sub).items():
            room = house.rooms.get(rid)
            if room is None or room_problems(room, profiles):
                continue
            days = room.schedule.profile_days
            if not all(days[p]["enabled"] for p in profiles):
                ok = False
                break
            ok = True
            size += len(profiles)
        if ok and (best is None or size > best[0]):
            best = (size, sub.title)
    return best[1] if best else None


def activate(house: House, title: str) -> list[str]:
    """Turn on the profiles of a scenario in its rooms; returns the rooms skipped."""
    sub = next((s for s in scenario_subentries(house) if s.title == title), None)
    if sub is None:
        raise ValueError(f"Unknown scenario {title}")
    skipped: list[str] = []
    for rid, profiles in scenario_rooms(sub).items():
        room = house.rooms.get(rid)
        if room is None:
            continue
        if room_problems(room, profiles):
            skipped.append(room.name)
            continue
        room.activate_profiles(profiles)
    return skipped


def issue_id(house: House, sub_id: str) -> str:
    """The Repairs issue of a scenario."""
    return f"scenario_{house.entry.entry_id}_{sub_id}"


def check(house: House) -> None:
    """Drop deleted rooms from the scenarios; tell their problems in Repairs."""
    hass = house.hass
    entry = house.entry
    language = "ro" if str(hass.config.language or "").lower().startswith("ro") else "en"
    texts = _TEXTS[language]
    current: set[str] = set()
    for sub in scenario_subentries(house):
        rooms = scenario_rooms(sub)
        kept = {rid: profiles for rid, profiles in rooms.items() if rid in house.rooms}
        if kept != rooms:
            hass.config_entries.async_update_subentry(
                entry, sub, data={**sub.data, CONF_SCENARIO_ROOMS: kept}
            )
        iid = issue_id(house, sub.subentry_id)
        current.add(iid)
        found = problems(house, sub)
        if found:
            ir.async_create_issue(
                hass,
                DOMAIN,
                iid,
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="scenario_problem",
                translation_placeholders={
                    "scenario": sub.title,
                    "house": entry.title,
                    "details": "; ".join(texts[code].format(**params) for code, params in found),
                },
            )
        else:
            ir.async_delete_issue(hass, DOMAIN, iid)
    # The issues of scenarios deleted since.
    prefix = f"scenario_{entry.entry_id}_"
    for domain, iid in list(ir.async_get(hass).issues):
        if domain == DOMAIN and iid.startswith(prefix) and iid not in current:
            ir.async_delete_issue(hass, DOMAIN, iid)


def remove_issues(hass: Any, entry_id: str) -> None:
    """Remove the Repairs issues of a house (when it is deleted)."""
    prefix = f"scenario_{entry_id}_"
    for domain, iid in list(ir.async_get(hass).issues):
        if domain == DOMAIN and iid.startswith(prefix):
            ir.async_delete_issue(hass, DOMAIN, iid)
