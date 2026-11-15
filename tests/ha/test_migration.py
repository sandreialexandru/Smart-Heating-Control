"""A house saved by an older version is brought up to date."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.advanced_climate.const import DOMAIN, SUBENTRY_ROOM

ROOM = {"source": "climate", "climates": ["climate.trv"], "command_mode": "temperature"}


async def _setup(hass: HomeAssistant, options: dict, minor_version: int) -> MockConfigEntry:
    hass.states.async_set("climate.trv", "heat", {"hvac_modes": ["heat", "off"]})
    hass.states.async_set("switch.floor", "off")
    hass.states.async_set("switch.boiler", "off")
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Home",
        minor_version=minor_version,
        options={"persons": [], "nearby_zones": [], **options},
        subentries_data=[
            {
                "data": {**ROOM, "circuit": "switch.floor"},
                "subentry_type": SUBENTRY_ROOM,
                "title": "Office",
                "unique_id": None,
            },
            {"data": ROOM, "subentry_type": SUBENTRY_ROOM, "title": "Hall", "unique_id": None},
        ],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _circuits(entry: MockConfigEntry) -> tuple:
    rooms = {s.title: s.data.get("circuit") for s in entry.subentries.values()}
    return entry.options.get("circuits"), rooms


async def test_circuits_left_from_a_removed_heat_source_are_cleared(hass: HomeAssistant) -> None:
    entry = await _setup(hass, {"circuits": ["switch.floor"], "boiler_min_rooms": 2}, 1)
    assert entry.minor_version == 2
    assert _circuits(entry) == (None, {"Office": None, "Hall": None})
    # The rest is kept.
    assert entry.options["boiler_min_rooms"] == 2
    assert next(iter(entry.subentries.values())).data["climates"] == ["climate.trv"]
    await hass.config_entries.async_unload(entry.entry_id)


async def test_circuits_of_a_heat_source_are_kept(hass: HomeAssistant) -> None:
    entry = await _setup(hass, {"boiler_entity": "switch.boiler", "circuits": ["switch.floor"]}, 1)
    assert entry.minor_version == 2
    assert _circuits(entry) == (["switch.floor"], {"Office": "switch.floor", "Hall": None})
    await hass.config_entries.async_unload(entry.entry_id)


async def test_circuits_without_a_heat_source_of_this_version_are_kept(
    hass: HomeAssistant,
) -> None:
    entry = await _setup(hass, {"circuits": ["switch.floor"]}, 2)
    assert _circuits(entry) == (["switch.floor"], {"Office": "switch.floor", "Hall": None})
    await hass.config_entries.async_unload(entry.entry_id)


async def test_a_house_of_a_newer_version_is_not_loaded(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, title="Home", version=2, options={})
    entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(entry.entry_id)
