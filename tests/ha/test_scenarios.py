"""Scenarios: profiles for several rooms, chosen from the house."""

from __future__ import annotations

from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.advanced_climate.const import DOMAIN, SUBENTRY_ROOM, SUBENTRY_SCENARIO
from tests.ha.test_ha_setup import _tick

SCHEDULE = (
    "workday: 00:00 sleep, 07:00 home\n"
    "weekend: 00:00 sleep, 09:00 comfort\n"
    "home_office: 00:00 sleep, 07:00 comfort\n"
    "holidays: 00:00 sleep, 09:00 comfort"
)
DAYS = {
    "workday": {"days": "workday", "enabled": True},
    "weekend": {"days": "weekend", "enabled": True},
    "home_office": {"days": "workday", "enabled": False},
    "holidays": {"days": "all", "enabled": False},
}


def _room(title: str, switch: str, sensor: str) -> dict:
    return {
        "data": {
            "source": "switch",
            "switches": [switch],
            "temperature_sensors": [sensor],
            "min_on_minutes": 0,
            "min_off_minutes": 0,
            "schedule": SCHEDULE,
            "profile_days": DAYS,
        },
        "subentry_type": SUBENTRY_ROOM,
        "title": title,
        "unique_id": None,
    }


async def _setup(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, scenarios: list[dict] | None = None
) -> MockConfigEntry:
    await hass.config.async_set_time_zone("Europe/Bucharest")
    freezer.move_to("2026-10-12 09:00:00+00:00")  # Monday 12:00
    assert await async_setup_component(
        hass, "input_boolean", {"input_boolean": {"heater": {}, "heater2": {}}}
    )
    hass.states.async_set("sensor.room_temp", "18.0", {"unit_of_measurement": "°C"})
    hass.states.async_set("sensor.office_temp", "18.0", {"unit_of_measurement": "°C"})
    hass.states.async_set("person.andrei", "home")
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Home",
        options={"persons": ["person.andrei"], "nearby_zones": []},
        subentries_data=[
            _room("Bedroom", "input_boolean.heater", "sensor.room_temp"),
            _room("Office", "input_boolean.heater2", "sensor.office_temp"),
        ],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    rooms = {sub.title: sid for sid, sub in entry.subentries.items()}
    for item in scenarios or []:
        hass.config_entries.async_add_subentry(
            entry,
            _scenario(item["title"], {rooms[t]: p for t, p in item["rooms"].items()}),
        )
    await hass.async_block_till_done()
    return entry


def _scenario(title: str, rooms: dict[str, list[str]]):
    from homeassistant.config_entries import ConfigSubentry

    return ConfigSubentry(
        data={"rooms": rooms}, subentry_type=SUBENTRY_SCENARIO, title=title, unique_id=None
    )


def _rid(entry: MockConfigEntry, title: str) -> str:
    return next(sid for sid, sub in entry.subentries.items() if sub.title == title)


def _days(entry: MockConfigEntry, title: str) -> dict:
    return entry.subentries[_rid(entry, title)].data["profile_days"]


async def _choose(hass: HomeAssistant, option: str) -> None:
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": "select.home_scenario", "option": option},
        blocking=True,
    )
    await hass.async_block_till_done()


async def test_scenario_select(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    """Choosing a scenario turns its profiles on; the select shows the one that matches."""
    entry = await _setup(
        hass,
        freezer,
        [
            {
                "title": "Home office",
                "rooms": {"Bedroom": ["workday"], "Office": ["home_office"]},
            },
            {"title": "Holidays", "rooms": {"Bedroom": ["holidays"], "Office": ["holidays"]}},
        ],
    )
    await _tick(hass, freezer, 15)
    select = hass.states.get("select.home_scenario")
    assert select.attributes["options"] == ["Home office", "Holidays"]
    assert select.state == "unknown"  # the office is on its workday profile

    await _choose(hass, "Home office")
    await _tick(hass, freezer, 15)
    assert hass.states.get("select.home_scenario").state == "Home office"
    assert _days(entry, "Office")["home_office"]["enabled"] is True
    assert _days(entry, "Office")["workday"]["enabled"] is False
    assert _days(entry, "Bedroom")["workday"]["enabled"] is True
    assert hass.states.get("select.office_schedule_profile").state == "home_office"
    assert hass.states.get("sensor.office_decision").attributes["preset"] == "comfort"

    # A profile for every day: the others go off.
    await _choose(hass, "Holidays")
    await _tick(hass, freezer, 15)
    assert hass.states.get("select.home_scenario").state == "Holidays"
    assert {n for n, d in _days(entry, "Bedroom").items() if d["enabled"]} == {"holidays"}

    # A room changed by hand: no scenario matches.
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": "select.bedroom_schedule_profile", "option": "workday"},
        blocking=True,
    )
    await _tick(hass, freezer, 15)
    assert hass.states.get("select.home_scenario").state == "unknown"
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_scenario_flow(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    """Add (with its checks) and reconfigure a scenario; no reload."""
    entry = await _setup(hass, freezer)
    house = entry.runtime_data
    bedroom, office = _rid(entry, "Bedroom"), _rid(entry, "Office")
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_SCENARIO), context={"source": SOURCE_USER}
    )
    assert result["step_id"] == "rooms"
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"name": " ", "rooms": []}
    )
    assert result["errors"] == {"name": "name_required", "rooms": "rooms_required"}
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"name": "Home office", "rooms": [bedroom, office]}
    )
    assert result["step_id"] == "profiles"
    assert {str(k) for k in result["data_schema"].schema} == {"Bedroom", "Office"}
    # Profiles of the same days in one room.
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"Bedroom": ["workday", "home_office"], "Office": ["home_office"]}
    )
    assert result["errors"] == {"Bedroom": "profiles_overlap"}
    assert result["description_placeholders"]["overlap"] == "workday, home_office"
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"Bedroom": ["workday", "weekend"], "Office": ["home_office"]}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.runtime_data is house  # applied in place, not reloaded
    scenario = next(s for s in entry.subentries.values() if s.subentry_type == SUBENTRY_SCENARIO)
    assert scenario.title == "Home office"
    assert scenario.data["rooms"] == {bedroom: ["workday", "weekend"], office: ["home_office"]}
    await _tick(hass, freezer, 15)
    assert hass.states.get("select.home_scenario").attributes["options"] == ["Home office"]

    # A second one with the same name is refused.
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_SCENARIO), context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"name": "Home office", "rooms": [office]}
    )
    assert result["errors"] == {"name": "name_taken"}

    # Reconfigure: rename, only the office.
    result = await entry.start_subentry_reconfigure_flow(hass, scenario.subentry_id)
    assert result["step_id"] == "rooms"
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"name": "Work from home", "rooms": [office]}
    )
    assert {str(k) for k in result["data_schema"].schema} == {"Office"}
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"Office": ["home_office"]}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()
    scenario = entry.subentries[scenario.subentry_id]
    assert scenario.title == "Work from home"
    assert scenario.data["rooms"] == {office: ["home_office"]}
    assert entry.runtime_data is house
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_scenario_problems(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    """A missing profile is told in Repairs and skipped; a deleted room leaves the scenario."""
    entry = await _setup(
        hass,
        freezer,
        [
            {
                "title": "Home office",
                "rooms": {"Bedroom": ["no_such"], "Office": ["home_office"]},
            }
        ],
    )
    await _tick(hass, freezer, 15)
    scenario = next(s for s in entry.subentries.values() if s.subentry_type == SUBENTRY_SCENARIO)
    issue_id = f"scenario_{entry.entry_id}_{scenario.subentry_id}"
    issue = ir.async_get(hass).async_get_issue(DOMAIN, issue_id)
    assert issue is not None
    assert "Bedroom: no profile no_such" in issue.translation_placeholders["details"]

    # Chosen: the office takes it, the bedroom is skipped.
    await _choose(hass, "Home office")
    await _tick(hass, freezer, 15)
    assert _days(entry, "Office")["home_office"]["enabled"] is True
    assert _days(entry, "Bedroom")["workday"]["enabled"] is True

    # The bedroom is deleted: it leaves the scenario, and the problem with it.
    bedroom = _rid(entry, "Bedroom")
    hass.config_entries.async_remove_subentry(entry, bedroom)
    await hass.async_block_till_done()
    await _tick(hass, freezer, 15)
    scenario = entry.subentries[scenario.subentry_id]
    assert bedroom not in scenario.data["rooms"]
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None

    # The scenario deleted: no issue left behind.
    hass.config_entries.async_remove_subentry(entry, scenario.subentry_id)
    await hass.async_block_till_done()
    await _tick(hass, freezer, 15)
    assert hass.states.get("select.home_scenario").attributes["options"] == []
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_scenario_empty(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    """A scenario whose only room is deleted stays, and is told."""
    entry = await _setup(
        hass, freezer, [{"title": "Office only", "rooms": {"Office": ["home_office"]}}]
    )
    scenario = next(s for s in entry.subentries.values() if s.subentry_type == SUBENTRY_SCENARIO)
    hass.config_entries.async_remove_subentry(entry, _rid(entry, "Office"))
    await hass.async_block_till_done()
    assert entry.subentries[scenario.subentry_id].data["rooms"] == {}
    issue = ir.async_get(hass).async_get_issue(
        DOMAIN, f"scenario_{entry.entry_id}_{scenario.subentry_id}"
    )
    assert issue is not None
    assert issue.translation_placeholders["details"] == "it has no rooms"
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_most_specific_scenario_is_shown(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Of two matching scenarios (one part of the other), the one setting more is shown."""
    entry = await _setup(
        hass,
        freezer,
        [
            {"title": "Office", "rooms": {"Office": ["home_office"]}},
            {
                "title": "Home office",
                "rooms": {"Bedroom": ["workday"], "Office": ["home_office"]},
            },
        ],
    )
    await _choose(hass, "Home office")
    await _tick(hass, freezer, 15)
    assert hass.states.get("select.home_scenario").state == "Home office"
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_scenario_with_a_room_skipped_is_shown(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """A room that cannot take its profiles is skipped when choosing and when showing."""
    entry = await _setup(
        hass,
        freezer,
        [
            {"title": "Home office", "rooms": {"Bedroom": ["no_such"], "Office": ["home_office"]}},
            {"title": "Broken", "rooms": {"Bedroom": ["no_such"]}},
        ],
    )
    await _tick(hass, freezer, 15)
    assert hass.states.get("select.home_scenario").state not in ("Home office", "Broken")
    await _choose(hass, "Home office")
    await _tick(hass, freezer, 15)
    # Applied without the bedroom, and shown.
    assert _days(entry, "Office")["home_office"]["enabled"] is True
    assert hass.states.get("select.home_scenario").state == "Home office"
    # A scenario with no room that can take it is never shown.
    await _choose(hass, "Broken")
    await _tick(hass, freezer, 15)
    assert hass.states.get("select.home_scenario").state == "Home office"
    # The office changed by hand: no scenario matches any more.
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": "select.office_schedule_profile", "option": "workday"},
        blocking=True,
    )
    await hass.async_block_till_done()
    await _tick(hass, freezer, 15)
    assert hass.states.get("select.home_scenario").state not in ("Home office", "Broken")
    assert await hass.config_entries.async_unload(entry.entry_id)
