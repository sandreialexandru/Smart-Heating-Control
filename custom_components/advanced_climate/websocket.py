"""Websocket commands for the panel: the history of the decisions and alerts,
and the schedule of the next days as the rooms will follow it."""

from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, callback
from homeassistant.util import dt as dt_util

from .const import CONF_SCHEDULE_SOURCE, DOMAIN, PRESET_AWAY, SCHEDULE_INTERNAL

if TYPE_CHECKING:
    from .house import House

HISTORY = f"{DOMAIN}/history"
WEEK = f"{DOMAIN}/week"
# The days of the week shown: today and the next 6 (the Workday days and the
# calendar events are read for today and the next 7).
WEEK_DAYS = 7


@callback
def async_setup_websocket(hass: HomeAssistant) -> None:
    """Register the commands (once)."""
    websocket_api.async_register_command(hass, ws_history)
    websocket_api.async_register_command(hass, ws_week)


def _decision(item: dict[str, Any], unit: str) -> dict[str, Any]:
    """A logged decision with its temperatures in the unit of the house."""
    # Here, not at the top: sensor.py imports the package, which imports this module.
    from .sensor import _reason_params, _t

    target = dict(item.get("target") or {})
    if target.get("temperature") is not None:
        target["temperature"] = _t(target["temperature"], unit, 1)
    return {
        "time": item.get("time"),
        "rule": item.get("rule"),
        "target": target,
        "description": item.get("description"),
        "reason_key": item.get("key"),
        "reason_params": _reason_params(item.get("params") or {}, unit),
    }


def history(house: House) -> dict[str, Any]:
    """The decisions of every room and the alerts of the house, oldest first."""
    unit = house.unit
    return {
        "entry_id": house.entry.entry_id,
        "name": house.entry.title,
        "temperature_unit": unit,
        "rooms": [
            {
                "room_id": room.id,
                "name": room.name,
                "decisions": [_decision(d, unit) for d in room.decisions],
            }
            for room in house.rooms.values()
        ],
        "alerts": [dict(a) for a in house.notifier.journal],
    }


@websocket_api.websocket_command({vol.Required("type"): HISTORY, vol.Optional("entry_id"): str})
@callback
def ws_history(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """The history of every loaded house (or of the one given)."""
    houses = [
        entry.runtime_data
        for entry in hass.config_entries.async_entries(DOMAIN)
        if entry.state is ConfigEntryState.LOADED and msg.get("entry_id") in (None, entry.entry_id)
    ]
    connection.send_result(msg["id"], {"houses": [history(h) for h in houses]})


def week(house: House) -> dict[str, Any]:
    """The next days of a house as the schedule will run them.

    For each day: whether it is a workday (the Workday integration: holidays).
    The calendar events of those days and the planned vacation. For each room
    with its own schedule: the profile of each schedule day (with the profile
    a calendar event forces) and every change of level, from the start of
    today to the end of the last day, computed as the room computes them; the
    calendar events titled with a level of the room, with that level.
    """
    zone = dt_util.get_default_time_zone()
    today = dt_util.now().date()
    start = datetime.combine(today, time(0), tzinfo=zone)
    end = datetime.combine(today + timedelta(days=WEEK_DAYS), time(0), tzinfo=zone)
    days = [today + timedelta(days=i) for i in range(WEEK_DAYS)]
    events = [(s, e, summary) for s, e, summary in house.calendar_events if s < end and e > start]
    vacation = None
    if house.vacation_end is not None and house.vacation_end > start:
        resume = house._vacation_resume()  # the end of the vacation level
        vacation = {
            "start": house.vacation_start.isoformat() if house.vacation_start else None,
            "end": house.vacation_end.isoformat(),
            "resume": resume.isoformat() if resume else None,
            "preset": PRESET_AWAY,
        }
    rooms = []
    for room in house.rooms.values():
        item: dict[str, Any] = {"room_id": room.id, "name": room.name}
        if room.config.get(CONF_SCHEDULE_SOURCE, SCHEDULE_INTERNAL) != SCHEDULE_INTERNAL:
            item["editable"] = False
            rooms.append(item)
            continue
        schedule = room.schedule
        profiles = []
        for day in days:
            workday, forced = room._day_info(day)  # as the room decides
            profiles.append(
                {
                    "date": day.isoformat(),
                    "profile": schedule.profile_for(day, workday, forced),
                    "forced": forced is not None,
                }
            )
        first = schedule.lookup(start, room._day_info)
        changes = schedule.upcoming(start, room._day_info, end - start)
        item.update(
            editable=True,
            profiles=profiles,
            changes=[{"at": start.isoformat(), "preset": first.preset}]
            + [{"at": at.isoformat(), "preset": preset} for at, preset in changes],
            levels=[
                {
                    "start": s.isoformat(),
                    "end": e.isoformat(),
                    "preset": room.aliases[summary.lower()],
                    "summary": summary,
                }
                for s, e, summary in events
                if summary.lower() in room.aliases
            ],
        )
        rooms.append(item)
    return {
        "entry_id": house.entry.entry_id,
        "name": house.entry.title,
        "days": [
            {"date": day.isoformat(), "workday": house.is_workday(day), "weekday": day.weekday()}
            for day in days
        ],
        "events": [
            {"start": s.isoformat(), "end": e.isoformat(), "summary": summary}
            for s, e, summary in events
        ],
        "vacation": vacation,
        "rooms": rooms,
    }


@websocket_api.websocket_command({vol.Required("type"): WEEK, vol.Optional("entry_id"): str})
@callback
def ws_week(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """The next days of every loaded house (or of the one given)."""
    houses = [
        entry.runtime_data
        for entry in hass.config_entries.async_entries(DOMAIN)
        if entry.state is ConfigEntryState.LOADED and msg.get("entry_id") in (None, entry.entry_id)
    ]
    connection.send_result(msg["id"], {"houses": [week(h) for h in houses]})
