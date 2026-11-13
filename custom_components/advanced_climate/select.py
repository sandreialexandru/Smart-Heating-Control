"""Selects for Smart Heating Control: the mode, the scenario and the heat source of the house, the profile of each room."""

from __future__ import annotations

from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import AdvancedClimateConfigEntry
from .const import CONF_SCHEDULE_SOURCE, MODES, SCHEDULE_INTERNAL
from .entity import HouseEntity, RoomEntity
from .house import House
from .room import Room
from .scenarios import activate, active_scenario, scenario_subentries
from .util import iso


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AdvancedClimateConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up selects."""
    house = entry.runtime_data
    async_add_entities([ModeSelect(house), ScenarioSelect(house)])
    if house.secondary_source:
        async_add_entities([HeatSourceSelect(house)])
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


class ScenarioSelect(HouseEntity, SelectEntity):
    """The scenario of the house: shows the one whose profiles are all on, applies the one chosen.

    A shortcut with no state of its own: choosing a scenario turns on its
    profiles in its rooms, as their profile selects do. When the rooms are
    changed one by one so that no scenario matches, it shows none.
    """

    def __init__(self, house: House) -> None:
        """Initialize."""
        super().__init__(house, "scenario")

    @property
    def options(self) -> list[str]:
        """The scenarios of the house."""
        return [sub.title for sub in scenario_subentries(self.house)]

    @property
    def current_option(self) -> str | None:
        """The scenario whose profiles are all on."""
        return active_scenario(self.house)

    async def async_select_option(self, option: str) -> None:
        """Turn on the profiles of the scenario."""
        try:
            activate(self.house, option)
        except ValueError as err:
            raise HomeAssistantError(str(err)) from err


class HeatSourceSelect(HouseEntity, SelectEntity):
    """The heat source of the house: Automatic (by the criterion), primary or secondary.

    Only with a secondary heat source; Automatic only with a criterion. The
    attributes tell the source in use and the names of both, for the card.
    """

    def __init__(self, house: House) -> None:
        """Initialize."""
        super().__init__(house, "heat_source")

    @property
    def options(self) -> list[str]:
        """Automatic (with a criterion), primary and secondary."""
        return self.house.source_options

    @property
    def current_option(self) -> str:
        """The choice that applies."""
        return self.house.source_choice

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """The source in use, both sources and the criterion."""
        house = self.house
        primary, secondary = (house.source_entities + [None, None])[:2]
        return {
            "active": house.active_source,
            "primary_entity": primary,
            "secondary_entity": secondary,
            "primary_name": self._name(primary),
            "secondary_name": self._name(secondary),
            "criterion": house.source_criterion,
            "switch_at": iso(house.source_switch_at),
        }

    def _name(self, entity_id: str | None) -> str | None:
        """The name of a heat source in Home Assistant."""
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if state is not None and state.name:
            return str(state.name)
        return entity_id.split(".", 1)[-1]

    async def async_select_option(self, option: str) -> None:
        """Choose the heat source."""
        await self.house.async_set_source(option)


class ProfileSelect(RoomEntity, SelectEntity):
    """The schedule profile of a room: shows the one chosen, activates it.

    Choosing a profile turns it on, as in the card, and turns off the active
    profiles of the same days; it stays until another one is chosen. The days
    it does not cover keep their own profile: the select shows the profile
    chosen while it is on (on a Saturday too, for a workday profile), and its
    ``today`` attribute the profile used today. Once the chosen profile is off
    (from the card), the select shows today's.
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
        """The profile chosen last while it is on, else the one used today."""
        chosen = self.room.chosen_profile
        days = self.room.schedule.profile_days
        if chosen in self.options and days.get(chosen, {}).get("enabled"):
            return chosen
        return self._today()

    def _today(self) -> str | None:
        """The profile used today (none on a day without an active profile)."""
        state = self.room.schedule_state
        profile = state.profile if state else None
        return profile if profile in self.options else None

    @property
    def extra_state_attributes(self) -> dict[str, str | None]:
        """The profile used today, which can differ from the one chosen."""
        return {"today": self._today()}

    async def async_select_option(self, option: str) -> None:
        """Turn the profile on (and those of the same days off)."""
        await self.room.async_activate_profile(option)
