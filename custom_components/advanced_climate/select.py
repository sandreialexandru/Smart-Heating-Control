"""Selects for Smart Heating Control: the global mode, and the profile of each room."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import AdvancedClimateConfigEntry
from .const import CONF_SCHEDULE_SOURCE, MODES, SCHEDULE_INTERNAL
from .entity import HouseEntity, RoomEntity
from .house import House
from .room import Room


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AdvancedClimateConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up selects."""
    house = entry.runtime_data
    async_add_entities([ModeSelect(house)])
    for room in house.rooms.values():
        if room.config.get(CONF_SCHEDULE_SOURCE, SCHEDULE_INTERNAL) == SCHEDULE_INTERNAL:
            async_add_entities([ProfileSelect(room)], config_subentry_id=room.id)


class ModeSelect(HouseEntity, SelectEntity):
    """Global mode: auto / away / vacation / off / summer."""

    def __init__(self, house: House) -> None:
        """Initialize."""
        super().__init__(house, "mode")
        self._attr_options = list(MODES)

    @property
    def current_option(self) -> str:
        """Current mode."""
        return self.house.mode

    async def async_select_option(self, option: str) -> None:
        """Change the mode."""
        await self.house.async_set_mode(option)


class ProfileSelect(RoomEntity, SelectEntity):
    """The schedule profile of a room: shows the one used today, activates the one chosen.

    Choosing a profile turns it on, as in the card, and turns off the active
    profiles of the same days; it stays until another one is chosen. The days
    it does not cover keep their own profile, so the one shown is always the
    profile of today.
    """

    def __init__(self, room: Room) -> None:
        """Initialize."""
        super().__init__(room, "schedule_profile")

    @property
    def options(self) -> list[str]:
        """The profiles of the room."""
        return self.room.schedule.profile_names

    @property
    def current_option(self) -> str | None:
        """The profile used today (none on a day without an active profile)."""
        state = self.room.schedule_state
        profile = state.profile if state else None
        return profile if profile in self.options else None

    async def async_select_option(self, option: str) -> None:
        """Turn the profile on (and those of the same days off)."""
        await self.room.async_activate_profile(option)
