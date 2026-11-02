"""Base entities for Smart Heating Control."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, PRESETS, SIGNAL_UPDATE
from .house import House
from .room import Room

# Home Assistant 2026.8+ links devices by device id (via_device is deprecated).
_VIA_DEVICE_ID = "via_device_id" in getattr(DeviceInfo, "__annotations__", {})


class HouseEntity(Entity):
    """Entity attached to the house device."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, house: House, key: str) -> None:
        """Initialize."""
        self.house = house
        self._attr_translation_key = key
        self._attr_unique_id = f"{house.entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, house.entry.entry_id)},
            name=house.entry.title,
            manufacturer="Smart Heating Control",
            model="House",
            entry_type=DeviceEntryType.SERVICE,
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe to updates."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_UPDATE.format(self.house.entry.entry_id),
                self.async_write_ha_state,
            )
        )


class RoomEntity(Entity):
    """Entity attached to a room device."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, room: Room, key: str) -> None:
        """Initialize."""
        self.room = room
        self.house = room.house
        self._attr_translation_key = key
        self._attr_unique_id = f"{room.id}_{key}"
        info = DeviceInfo(
            identifiers={(DOMAIN, room.id)},
            name=room.name,
            manufacturer="Smart Heating Control",
            model="Whole house" if room.is_whole_house else "Room",
            entry_type=DeviceEntryType.SERVICE,
            suggested_area=room.area_name,
        )
        if _VIA_DEVICE_ID and room.house.device_id:
            info["via_device_id"] = room.house.device_id  # type: ignore[typeddict-unknown-key]
        elif not _VIA_DEVICE_ID:
            info["via_device"] = (DOMAIN, room.house.entry.entry_id)  # type: ignore[typeddict-unknown-key]
        self._attr_device_info = info

    async def async_added_to_hass(self) -> None:
        """Subscribe to updates."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_UPDATE.format(self.house.entry.entry_id),
                self.async_write_ha_state,
            )
        )


HOUSE_ENTITY_KEYS: dict[str, str] = {
    "mode": "select",
    "presence": "sensor",
    "outdoor_average": "sensor",
    "heating_runtime": "sensor",
    "heating_season": "binary_sensor",
    "outdoor_cutoff": "binary_sensor",
    "heat_demand": "binary_sensor",
    "pause": "switch",
    "guest_mode": "switch",
    "vacation_start": "datetime",
    "vacation_end": "datetime",
    "clear_overrides": "button",
    "reevaluate": "button",
    "clear_vacation": "button",
}

ROOM_ENTITY_KEYS: dict[str, str] = {
    "decision": "sensor",
    "target_temperature": "sensor",
    "room_temperature": "sensor",
    "next_change": "sensor",
    "heating_rate": "sensor",
    "cooling_rate": "sensor",
    "heating_runtime": "sensor",
    "heat_demand": "binary_sensor",
    "window_open": "binary_sensor",
    "manual_override": "binary_sensor",
    "child_lock": "switch",
    "clear_override": "button",
    "reset_learning": "button",
    **{f"level_{preset}": "number" for preset in (*PRESETS, "nearby")},
}


def entity_map(hass: HomeAssistant, prefix: str, keys: dict[str, str]) -> dict[str, str]:
    """Map entity keys to their current entity ids (used by the card)."""
    registry = er.async_get(hass)
    result: dict[str, str] = {}
    for key, domain in keys.items():
        entity_id = registry.async_get_entity_id(domain, DOMAIN, f"{prefix}_{key}")
        if entity_id:
            result[key] = entity_id
    return result
