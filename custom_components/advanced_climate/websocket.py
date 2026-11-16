"""Websocket commands for the panel: the history of the decisions and alerts."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN

if TYPE_CHECKING:
    from .house import House

HISTORY = f"{DOMAIN}/history"


@callback
def async_setup_websocket(hass: HomeAssistant) -> None:
    """Register the commands (once)."""
    websocket_api.async_register_command(hass, ws_history)


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
