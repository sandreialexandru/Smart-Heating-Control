"""Diagnostics for Smart Heating Control."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import AdvancedClimateConfigEntry
from .const import (
    CONF_NEARBY_ZONES,
    CONF_NOTIFY_CRITICAL,
    CONF_NOTIFY_INFO,
    CONF_NOTIFY_SERVICE,
    CONF_NOTIFY_WARNING,
    CONF_PERSONS,
    CONF_PROXIMITY_DIRECTION,
    CONF_PROXIMITY_DISTANCE,
    CONF_TRAVEL_TIME,
    SUBENTRY_ROOM,
    SUBENTRY_SCENARIO,
)

# Diagnostics end up attached to public issues: leave out who lives in the
# house, where they are and how to reach them.
TO_REDACT = {
    # Alert recipients (phones, e-mail addresses).
    CONF_NOTIFY_CRITICAL,
    CONF_NOTIFY_WARNING,
    CONF_NOTIFY_INFO,
    CONF_NOTIFY_SERVICE,
    # The people, their zones and the sensors that follow them.
    CONF_PERSONS,
    "person_classes",
    CONF_NEARBY_ZONES,
    CONF_PROXIMITY_DISTANCE,
    CONF_PROXIMITY_DIRECTION,
    CONF_TRAVEL_TIME,
    # The text of the calendar event now.
    "calendar_message",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: AdvancedClimateConfigEntry
) -> dict[str, Any]:
    """Return configuration, state and the last decisions of every room."""
    house = entry.runtime_data
    data: dict[str, Any] = async_redact_data(
        {
            "options": dict(entry.options),
            "rooms": {
                sub.subentry_id: {"title": sub.title, "data": dict(sub.data)}
                for sub in entry.subentries.values()
                if sub.subentry_type == SUBENTRY_ROOM
            },
            "scenarios": {
                sub.subentry_id: {"title": sub.title, "data": dict(sub.data)}
                for sub in entry.subentries.values()
                if sub.subentry_type == SUBENTRY_SCENARIO
            },
            "state": house.diagnostics(),
        },
        TO_REDACT,
    )
    return data
