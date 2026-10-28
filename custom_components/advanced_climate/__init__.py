"""Smart Heating Control: heating schedules by presence, zones, windows and weather."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    config_validation as cv,
)
from homeassistant.helpers import (
    device_registry as dr,
)
from homeassistant.helpers import (
    entity_registry as er,
)
from homeassistant.helpers.typing import ConfigType

from .const import CONF_PROFILE_DAYS, CONF_SCHEDULE, DEFAULT_SCHEDULE, DOMAIN
from .frontend import async_register_card, async_remove_lovelace_resource
from .house import House
from .services import async_setup_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.DATETIME,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type AdvancedClimateConfigEntry = ConfigEntry[House]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the integration (services and the Lovelace card)."""
    async_setup_services(hass)
    await async_register_card(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: AdvancedClimateConfigEntry) -> bool:
    """Set up a house from a config entry."""
    # A whole-house zone named like the house gets its own name, so the house
    # and the zone are not two devices with the same name.
    for subentry in list(entry.subentries.values()):
        if subentry.unique_id == "whole_house" and subentry.title == entry.title:
            hass.config_entries.async_update_subentry(entry, subentry, title="Whole house")
    house = House(hass, entry)
    await house.async_setup()
    entry.runtime_data = house
    # The house device exists before the rooms, which are linked to it.
    house.device_id = (
        dr.async_get(hass)
        .async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Smart Heating Control",
            model="House",
            entry_type=dr.DeviceEntryType.SERVICE,
        )
        .id
    )
    house.config_snapshot = _snapshot(entry)
    try:
        _remove_old_entities(hass, entry)
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except Exception:
        # The house listens to its entities already: stop it, then fail.
        await house.async_unload()
        raise
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


def _remove_old_entities(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove entities of earlier versions (the profile select of the rooms, 2.2)."""
    registry = er.async_get(hass)
    rooms = set(entry.subentries)
    for item in er.async_entries_for_config_entry(registry, entry.entry_id):
        if item.domain == "select" and any(item.unique_id == f"{rid}_profile" for rid in rooms):
            registry.async_remove(item.entity_id)


_SCHEDULE_KEYS = (CONF_SCHEDULE, CONF_PROFILE_DAYS)


def _snapshot(entry: ConfigEntry) -> tuple:
    """Settings of the house and rooms, without the schedules."""
    rooms = {
        sid: (
            sub.title,
            sub.unique_id,
            {k: v for k, v in sub.data.items() if k not in _SCHEDULE_KEYS},
        )
        for sid, sub in entry.subentries.items()
    }
    return (dict(entry.options), entry.title, rooms)


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload when options or rooms change; a new schedule is applied in place.

    Saving a schedule (e.g. from the card) does not reload the integration, so
    the entities do not become unavailable for a moment.
    """
    house = getattr(entry, "runtime_data", None)
    if house is not None and _snapshot(entry) == getattr(house, "config_snapshot", None):
        for sid, sub in entry.subentries.items():
            room = house.rooms.get(sid)
            if room is not None and any(
                sub.data.get(key) != room.config.get(key) for key in _SCHEDULE_KEYS
            ):
                room.apply_schedule(
                    sub.data.get(CONF_SCHEDULE) or DEFAULT_SCHEDULE,
                    sub.data.get(CONF_PROFILE_DAYS),
                )
        house.async_save()
        house.async_request_evaluate(0)
        return
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: AdvancedClimateConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.async_unload()
    return unloaded


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove the dashboard resource when the last house is deleted."""
    if hass.config_entries.async_entries(DOMAIN):
        return
    await async_remove_lovelace_resource(hass)
