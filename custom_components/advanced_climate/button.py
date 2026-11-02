"""Buttons for Smart Heating Control."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import AdvancedClimateConfigEntry
from .entity import HouseEntity, RoomEntity
from .house import House
from .room import Room


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AdvancedClimateConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up buttons."""
    house = entry.runtime_data
    async_add_entities(
        [
            ClearOverridesButton(house),
            ReevaluateButton(house),
            ClearVacationButton(house),
        ]
    )
    for room in house.rooms.values():
        async_add_entities(
            [
                ClearRoomOverrideButton(room),
                ResetLearningButton(room),
            ],
            config_subentry_id=room.id,
        )


class ClearOverridesButton(HouseEntity, ButtonEntity):
    """Clear all manual overrides."""

    def __init__(self, house: House) -> None:
        """Initialize."""
        super().__init__(house, "clear_overrides")

    async def async_press(self) -> None:
        """Press."""
        await self.house.async_clear_overrides()


class ReevaluateButton(HouseEntity, ButtonEntity):
    """Evaluate everything now."""

    def __init__(self, house: House) -> None:
        """Initialize."""
        super().__init__(house, "reevaluate")

    async def async_press(self) -> None:
        """Press."""
        await self.house.async_evaluate_or_notify()


class ClearVacationButton(HouseEntity, ButtonEntity):
    """Clear the vacation period."""

    def __init__(self, house: House) -> None:
        """Initialize."""
        super().__init__(house, "clear_vacation")

    async def async_press(self) -> None:
        """Press."""
        await self.house.async_set_vacation(None, None)


class ClearRoomOverrideButton(RoomEntity, ButtonEntity):
    """Clear the manual override of the room."""

    def __init__(self, room: Room) -> None:
        """Initialize."""
        super().__init__(room, "clear_override")

    async def async_press(self) -> None:
        """Press."""
        self.room.clear_override()
        await self.house.async_evaluate_or_notify()


class ResetLearningButton(RoomEntity, ButtonEntity):
    """Forget the learned thermal model of the room (it is learned again)."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, room: Room) -> None:
        """Initialize."""
        super().__init__(room, "reset_learning")

    async def async_press(self) -> None:
        """Press."""
        self.room.reset_learning()
        await self.house.async_evaluate_or_notify()
