"""Values shared by the parts of the room controller."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.const import ATTR_TEMPERATURE
from homeassistant.core import State

from .const import DEVICE_LIMIT_HOURS, SENT_RECENT_MINUTES, SENT_STABLE_SECONDS

# How far below the frost protection temperature a room is told (°C).
FROST_ALERT_MARGIN = 0.5
SENT_RECENT = timedelta(minutes=SENT_RECENT_MINUTES)
SENT_STABLE = timedelta(seconds=SENT_STABLE_SECONDS)
DEVICE_LIMIT_KEEP = timedelta(hours=DEVICE_LIMIT_HOURS)


def device_values(state: State) -> dict[str, Any]:
    """What a person set on a device: mode (or on / off), preset and temperature."""
    values: dict[str, Any] = {"state": state.state}
    if state.domain == "climate":
        values["preset_mode"] = state.attributes.get("preset_mode")
        values["temperature"] = state.attributes.get(ATTR_TEMPERATURE)
    return values
