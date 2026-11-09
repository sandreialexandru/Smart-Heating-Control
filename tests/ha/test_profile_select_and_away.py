"""The schedule profile select of a room, and the away mode of the house."""

from __future__ import annotations

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from tests.ha.test_ha_setup import _setup, _tick

SCHEDULE = (
    "workday: 00:00 sleep, 07:00 home\n"
    "weekend: 00:00 sleep, 09:00 comfort\n"
    "home_office: 00:00 sleep, 07:00 comfort"
)
DAYS = {
    "workday": {"days": "workday", "enabled": True},
    "weekend": {"days": "weekend", "enabled": True},
    "home_office": {"days": "workday", "enabled": False},
}


async def _select(hass: HomeAssistant, entity_id: str, option: str) -> None:
    await hass.services.async_call(
        "select", "select_option", {"entity_id": entity_id, "option": option}, blocking=True
    )
    await hass.async_block_till_done()


async def test_profile_select(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    """Shows the profile of today; choosing one turns it on like the card does."""
    entry = await _setup(hass, freezer, schedule=SCHEDULE, profile_days=DAYS)
    await _tick(hass, freezer, 15)
    select = hass.states.get("select.bedroom_schedule_profile")
    # Monday: the workday profile.
    assert select.state == "workday"
    assert select.attributes["options"] == ["workday", "weekend", "home_office"]
    assert hass.states.get("sensor.bedroom_decision").attributes["preset"] == "home"

    await _select(hass, "select.bedroom_schedule_profile", "home_office")
    await _tick(hass, freezer, 15)
    assert hass.states.get("select.bedroom_schedule_profile").state == "home_office"
    decision = hass.states.get("sensor.bedroom_decision").attributes
    assert decision["preset"] == "comfort"
    # Saved in the room, as from the card: the workday profile of the same days is off.
    days = next(iter(entry.subentries.values())).data["profile_days"]
    assert days["home_office"]["enabled"] is True
    assert days["workday"]["enabled"] is False
    assert days["weekend"]["enabled"] is True
    assert decision["profile_days"]["workday"]["enabled"] is False

    assert hass.states.get("select.bedroom_schedule_profile").attributes["today"] == "home_office"

    # Saturday: the weekend profile is used (the choice did not touch it); the
    # select still shows the profile chosen, its attribute the one of today.
    await _tick(hass, freezer, 5 * 86400)
    select = hass.states.get("select.bedroom_schedule_profile")
    assert select.state == "home_office"
    assert select.attributes["today"] == "weekend"
    assert hass.states.get("sensor.bedroom_decision").attributes["profile"] == "weekend"
    # The next Monday: home office still.
    await _tick(hass, freezer, 2 * 86400)
    assert hass.states.get("select.bedroom_schedule_profile").state == "home_office"

    # Back to the workday profile.
    await _select(hass, "select.bedroom_schedule_profile", "workday")
    await _tick(hass, freezer, 15)
    assert hass.states.get("select.bedroom_schedule_profile").state == "workday"
    days = next(iter(entry.subentries.values())).data["profile_days"]
    assert days["home_office"]["enabled"] is False
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_profile_select_options_follow_the_schedule(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """A profile added from the card (set_schedule) is offered at once."""
    entry = await _setup(hass, freezer)
    await _tick(hass, freezer, 15)
    await hass.services.async_call(
        "advanced_climate",
        "set_schedule",
        {
            "room": "Bedroom",
            "profiles": {
                "workday": [{"time": "00:00", "preset": "home"}],
                "night_shift": [{"time": "00:00", "preset": "sleep"}],
            },
        },
        blocking=True,
    )
    await _tick(hass, freezer, 15)
    options = hass.states.get("select.bedroom_schedule_profile").attributes["options"]
    assert options == ["workday", "night_shift"]
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_mode_away(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    """Away by hand: the away level with everyone home; guests win; back to the schedule."""
    entry = await _setup(hass, freezer)
    await _tick(hass, freezer, 15)
    assert "away" in hass.states.get("select.home_mode").attributes["options"]
    await _select(hass, "select.home_mode", "away")
    await _tick(hass, freezer, 15)
    decision = hass.states.get("sensor.bedroom_decision")
    assert decision.state == "house_away"
    assert decision.attributes["preset"] == "away"
    # Guests: the rooms follow the schedule.
    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": "switch.home_guest_mode"}, blocking=True
    )
    await _tick(hass, freezer, 15)
    assert hass.states.get("sensor.bedroom_decision").state != "house_away"
    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": "switch.home_guest_mode"}, blocking=True
    )
    await _tick(hass, freezer, 15)
    assert hass.states.get("sensor.bedroom_decision").state == "house_away"
    await _select(hass, "select.home_mode", "auto")
    await _tick(hass, freezer, 15)
    assert hass.states.get("sensor.bedroom_decision").state == "schedule"
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_mode_away_survives_a_restart(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """The away mode is kept over a reload."""
    entry = await _setup(hass, freezer)
    await _select(hass, "select.home_mode", "away")
    await _tick(hass, freezer, 15)
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    await _tick(hass, freezer, 15)
    assert hass.states.get("select.home_mode").state == "away"
    assert hass.states.get("sensor.bedroom_decision").state == "house_away"
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_profile_select_removed_for_a_helper_schedule(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """A room switched to a schedule helper has no profiles: its select goes away."""
    entry = await _setup(hass, freezer)
    await _tick(hass, freezer, 15)
    assert hass.states.get("select.bedroom_schedule_profile") is not None
    sub = next(iter(entry.subentries.values()))
    hass.states.async_set("schedule.x", "off")
    hass.config_entries.async_update_subentry(
        entry,
        sub,
        data={**sub.data, "schedule_source": "helper", "schedule_helper": "schedule.x"},
    )
    await hass.async_block_till_done()
    await _tick(hass, freezer, 15)
    assert er.async_get(hass).async_get("select.bedroom_schedule_profile") is None
    assert hass.states.get("select.bedroom_schedule_profile") is None
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_profile_select_leaving_days_without_profile_is_told(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """A workday profile chosen over an all-days one leaves the weekend without a
    profile: the schedule gap alert tells it (as when it is done in the card)."""
    days = {
        "workday": {"days": "all", "enabled": True},
        "weekend": {"days": "weekend", "enabled": False},
        "home_office": {"days": "workday", "enabled": False},
    }
    entry = await _setup(hass, freezer, schedule=SCHEDULE, profile_days=days)
    house = entry.runtime_data
    room = next(iter(house.rooms.values()))
    await _tick(hass, freezer, 15)
    assert f"schedule_gap_{room.id}" not in house.active_alerts
    await _select(hass, "select.bedroom_schedule_profile", "home_office")
    await _tick(hass, freezer, 15)
    saved = next(iter(entry.subentries.values())).data["profile_days"]
    assert saved["workday"]["enabled"] is False
    alert = house.active_alerts[f"schedule_gap_{room.id}"]
    assert alert["code"] == "schedule_gap"
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_profile_select_chosen_kept_and_dropped(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """The profile chosen is kept over a restart; once it is off, today's is shown."""
    entry = await _setup(hass, freezer, schedule=SCHEDULE, profile_days=DAYS)
    await _tick(hass, freezer, 15)
    # Before any choice: the profile of today (Monday).
    assert hass.states.get("select.bedroom_schedule_profile").state == "workday"
    await _select(hass, "select.bedroom_schedule_profile", "weekend")
    await _tick(hass, freezer, 15)
    select = hass.states.get("select.bedroom_schedule_profile")
    assert select.state == "weekend"
    assert select.attributes["today"] == "workday"
    # Kept over a restart.
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    await _tick(hass, freezer, 15)
    assert hass.states.get("select.bedroom_schedule_profile").state == "weekend"
    # Turned off elsewhere (as from the card): the select shows today's profile.
    sub = next(iter(entry.subentries.values()))
    days = {n: dict(m) for n, m in sub.data["profile_days"].items()}
    days["weekend"]["enabled"] = False
    hass.config_entries.async_update_subentry(entry, sub, data={**sub.data, "profile_days": days})
    await hass.async_block_till_done()
    await _tick(hass, freezer, 15)
    assert hass.states.get("select.bedroom_schedule_profile").state == "workday"
    assert await hass.config_entries.async_unload(entry.entry_id)
