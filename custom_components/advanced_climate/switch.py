"""Switches for Smart Heating Control: pause, guest mode, child lock."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import AdvancedClimateConfigEntry
from .entity import HouseEntity, RoomEntity
from .house import House
from .room import Room
from .util import iso


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AdvancedClimateConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up switches."""
    house = entry.runtime_data
    async_add_entities([PauseSwitch(house), GuestSwitch(house)])
    for room in house.rooms.values():
        async_add_entities([ChildLockSwitch(room)], config_subentry_id=room.id)


class PauseSwitch(HouseEntity, SwitchEntity):
    """Pause: only safety commands are sent (frost protection, maximum, TRV boost back)."""

    def __init__(self, house: House) -> None:
        """Initialize."""
        super().__init__(house, "pause")

    @property
    def is_on(self) -> bool:
        """State."""
        return self.house.paused

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Pause."""
        await self.house.async_set_pause(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Resume."""
        await self.house.async_set_pause(False)


class GuestSwitch(HouseEntity, SwitchEntity):
    """Guest mode: the house counts as occupied."""

    def __init__(self, house: House) -> None:
        """Initialize."""
        super().__init__(house, "guest_mode")

    @property
    def is_on(self) -> bool:
        """State."""
        return self.house.guest

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expiry."""
        return {"until": iso(self.house.guest_until)}

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable."""
        await self.house.async_set_guest(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable."""
        await self.house.async_set_guest(False)


class ChildLockSwitch(RoomEntity, SwitchEntity):
    """Child lock: manual changes are reverted immediately."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, room: Room) -> None:
        """Initialize."""
        super().__init__(room, "child_lock")

    @property
    def is_on(self) -> bool:
        """State."""
        return self.room.child_lock

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable."""
        await self.room.async_set_child_lock(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable."""
        await self.room.async_set_child_lock(False)
