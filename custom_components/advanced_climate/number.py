"""Numbers for Smart Heating Control: level temperatures (rooms without GT)."""

from __future__ import annotations

import math

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import AdvancedClimateConfigEntry
from .const import CONF_NEARBY_MODE, DOMAIN, NEARBY_TEMPERATURE, PRESETS
from .entity import RoomEntity
from .room import Room
from .util import from_celsius, to_celsius


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AdvancedClimateConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up numbers."""
    house = entry.runtime_data
    registry = er.async_get(hass)
    for room in house.rooms.values():
        wanted = list(room.editable_levels)
        if room.config.get(CONF_NEARBY_MODE) == NEARBY_TEMPERATURE:
            wanted.append("nearby")
        # Levels whose temperature the integration does not set have no number.
        for preset in (*PRESETS, "nearby"):
            if preset in wanted:
                continue
            entity_id = registry.async_get_entity_id("number", DOMAIN, f"{room.id}_level_{preset}")
            if entity_id:
                registry.async_remove(entity_id)
        if wanted:
            async_add_entities(
                [LevelNumber(room, preset) for preset in wanted], config_subentry_id=room.id
            )


class LevelNumber(RoomEntity, NumberEntity):
    """Temperature of one level, in the unit of the house (kept in °C)."""

    _attr_device_class = None
    _attr_mode = NumberMode.BOX
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, room: Room, preset: str) -> None:
        """Initialize."""
        super().__init__(room, f"level_{preset}")
        self.preset = preset
        self._attr_native_unit_of_measurement = room.house.unit
        self._attr_native_step = 0.5
        if preset != "nearby" and room.preset_names.get(preset, preset) != preset:
            # Custom level name chosen by the user.
            self._attr_translation_key = "level_custom"
            self._attr_translation_placeholders = {"name": room.preset_names[preset]}

    @property
    def native_min_value(self) -> float:
        """Frost protection temperature (no level can be colder)."""
        # Rounded up to the step, so the lowest value is not below the frost protection.
        return math.ceil(float(from_celsius(self.room.frost_temp(), self.room.house.unit)) * 2) / 2

    @property
    def native_max_value(self) -> float:
        """Maximum temperature (no level can be warmer)."""
        # Rounded down to the step, so the highest value is not above the maximum.
        return math.floor(float(from_celsius(self.room.max_temp(), self.room.house.unit)) * 2) / 2

    @property
    def native_value(self) -> float:
        """Current value."""
        value = self.room.nearby_temp if self.preset == "nearby" else self.room.levels[self.preset]
        return round(float(from_celsius(value, self.room.house.unit)), 1)

    async def async_set_native_value(self, value: float) -> None:
        """Set the level temperature."""
        celsius = round(float(to_celsius(value, self.room.house.unit)), 2)
        await self.room.async_set_level(self.preset, celsius)
