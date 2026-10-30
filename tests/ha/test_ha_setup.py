"""Set up a house with a relay room and check the control loop."""

from __future__ import annotations

from datetime import datetime, timedelta

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from homeassistant.core import Context, SupportsResponse
from homeassistant.exceptions import ServiceValidationError
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
    async_mock_service,
)

from custom_components.advanced_climate.const import DOMAIN, SUBENTRY_ROOM


async def _setup(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    house_options: dict | None = None,
    **extra: object,
) -> MockConfigEntry:
    await hass.config.async_set_time_zone("Europe/Bucharest")
    # Monday 12:00 local time.
    freezer.move_to("2026-10-12 09:00:00+00:00")
    assert await async_setup_component(hass, "input_boolean", {"input_boolean": {"heater": {}}})
    hass.states.async_set("sensor.room_temp", "18.0", {"unit_of_measurement": "°C"})
    hass.states.async_set("person.andrei", "home")
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Home",
        options={"persons": ["person.andrei"], "nearby_zones": [], **(house_options or {})},
        subentries_data=[
            {
                "data": {
                    "source": "switch",
                    "switches": ["input_boolean.heater"],
                    "temperature_sensors": ["sensor.room_temp"],
                    "min_on_minutes": 0,
                    "min_off_minutes": 0,
                    **extra,
                },
                "subentry_type": SUBENTRY_ROOM,
                "title": "Bedroom",
                "unique_id": None,
            }
        ],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def _tick(hass: HomeAssistant, freezer: FrozenDateTimeFactory, seconds: float) -> None:
    # Let the listeners of earlier state changes run first: on older Home Assistant
    # versions they run only now, and a timer they start must count from before the tick.
    await hass.async_block_till_done()
    freezer.tick(timedelta(seconds=seconds))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()


async def test_relay_room(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    """The relay follows the schedule, presence and mode."""
    entry = await _setup(hass, freezer)
    assert hass.states.get("sensor.bedroom_decision").state == "starting"

    await _tick(hass, freezer, 15)
    decision = hass.states.get("sensor.bedroom_decision")
    assert decision.state == "schedule"
    assert decision.attributes["preset"] == "home"
    assert hass.states.get("sensor.bedroom_target_temperature").state == "21.0"
    # The reason for the card, in its language.
    assert decision.attributes["reason_key"] == "schedule"
    assert decision.attributes["reason_params"] == {"preset": "home"}
    assert hass.states.get("input_boolean.heater").state == "on"
    assert hass.states.get("sensor.home_presence").state == "home"
    # Nothing learned yet: no cooling rate.
    assert hass.states.get("sensor.bedroom_cooling_rate").state == "unknown"
    # Heating: 60 minutes per degree until the first episode.
    heating = hass.states.get("sensor.bedroom_heating_rate")
    assert float(heating.state) == 60.0
    assert heating.attributes["unit_of_measurement"] == "min/°C"
    assert heating.attributes["fixed_minutes"] == 0.0
    assert heating.attributes["episodes"] == 0

    # The learning of each kind can be reset from its button.
    room = next(iter(entry.runtime_data.rooms.values()))
    room.learner.episodes.append([5.0, 2.0, 120.0, ""])
    room.learner._model = None
    room.cooling.episodes.append([5.0, 0.02, ""])
    await hass.services.async_call(
        "button", "press", {"entity_id": "button.bedroom_reset_heating_learning"}, blocking=True
    )
    await hass.async_block_till_done()
    assert room.learner.episodes == []
    assert room.cooling.episodes == [[5.0, 0.02, ""]]
    await hass.services.async_call(
        "button", "press", {"entity_id": "button.bedroom_reset_cooling_learning"}, blocking=True
    )
    await hass.async_block_till_done()
    assert room.cooling.episodes == []
    assert hass.states.get("sensor.bedroom_decision").attributes["entities"]["reset_heating_learning"] == (
        "button.bedroom_reset_heating_learning"
    )

    # Warm room: the relay turns off.
    hass.states.async_set("sensor.room_temp", "21.5", {"unit_of_measurement": "°C"})
    await _tick(hass, freezer, 5)
    assert hass.states.get("input_boolean.heater").state == "off"

    # Summer mode.
    await hass.services.async_call(
        "select", "select_option",
        {"entity_id": "select.home_mode", "option": "summer"}, blocking=True,
    )
    await hass.async_block_till_done()
    assert hass.states.get("sensor.bedroom_decision").state == "summer"

    # Service: manual temperature for one hour.
    await hass.services.async_call(
        "select", "select_option",
        {"entity_id": "select.home_mode", "option": "auto"}, blocking=True,
    )
    await hass.services.async_call(
        DOMAIN, "set_override", {"room": "Bedroom", "temperature": 23, "duration_hours": 1},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert hass.states.get("sensor.bedroom_decision").state == "manual_override"
    assert hass.states.get("binary_sensor.bedroom_manual_change").state == "on"

    await hass.services.async_call(DOMAIN, "clear_override", {"room": "Bedroom"}, blocking=True)
    await hass.async_block_till_done()
    assert hass.states.get("sensor.bedroom_decision").state == "schedule"

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_relay_off_at_the_maximum_in_a_pause(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """A relay left on by a pause is turned off at the maximum (25 °C by default)."""
    entry = await _setup(hass, freezer)
    await _tick(hass, freezer, 15)
    assert hass.states.get("input_boolean.heater").state == "on"  # 18 °C, home 21 °C
    await hass.services.async_call("switch", "turn_on", {"entity_id": "switch.home_pause"}, blocking=True)
    await hass.async_block_till_done()
    assert hass.states.get("input_boolean.heater").state == "on"  # the pause sends nothing
    hass.states.async_set("sensor.room_temp", "30.0", {"unit_of_measurement": "°C"})
    await _tick(hass, freezer, 15)
    assert hass.states.get("sensor.bedroom_decision").state == "maximum_temperature"
    assert hass.states.get("input_boolean.heater").state == "off"
    # Below the maximum: the pause again, the relay is not turned on to heat back up.
    hass.states.async_set("sensor.room_temp", "24.0", {"unit_of_measurement": "°C"})
    await _tick(hass, freezer, 15)
    assert hass.states.get("sensor.bedroom_decision").state == "pause"
    assert hass.states.get("input_boolean.heater").state == "off"
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_relay_switched_off_by_hand_in_the_band_stays_off(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Inside the hysteresis band the real relay state is kept (switched off by hand)."""
    hass.states.async_set("binary_sensor.window", "off")
    entry = await _setup(hass, freezer, window_sensors=["binary_sensor.window"])
    await _tick(hass, freezer, 15)
    assert hass.states.get("input_boolean.heater").state == "on"
    # Window open: frost protection 7 °C; the room at 7.2 °C is inside the
    # 0.3 °C band (6.7-7.3 °C), so the relay neither has to start nor stop.
    hass.states.async_set("sensor.room_temp", "7.2", {"unit_of_measurement": "°C"})
    await _window(hass, freezer, "on")
    assert hass.states.get("sensor.bedroom_decision").state == "window_open"
    await hass.services.async_call(
        "input_boolean", "turn_off", {"entity_id": "input_boolean.heater"}, blocking=True
    )
    await _tick(hass, freezer, 60)
    assert hass.states.get("input_boolean.heater").state == "off"
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_relay_switches_when_the_minimum_time_ends(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """The relay is evaluated again when its minimum on time ends, not at the next periodic check."""
    entry = await _setup(
        hass, freezer, house_options={"reevaluation_minutes": 60}, min_on_minutes=10
    )
    await _tick(hass, freezer, 15)
    assert hass.states.get("input_boolean.heater").state == "on"
    # Warm right away: it has to stay on for the 10 minutes.
    hass.states.async_set("sensor.room_temp", "23.0", {"unit_of_measurement": "°C"})
    await _tick(hass, freezer, 15)
    assert hass.states.get("input_boolean.heater").state == "on"
    # 10 minutes after it was turned on (well before the 60 min periodic check).
    await _tick(hass, freezer, 10 * 60 - 15 + 2)
    assert hass.states.get("input_boolean.heater").state == "off"
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_weather_options_without_an_outdoor_source(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Saved weather options without a source: the automatic season stays on, with an alert."""
    entry = await _setup(
        hass, freezer, house_options={"season_mode": "auto", "cutoff_enabled": True}
    )
    house = entry.runtime_data
    house.outdoor.season_active = False  # e.g. saved in summer, before the sensor was removed
    await _tick(hass, freezer, 15)
    assert house.season_active
    assert hass.states.get("sensor.bedroom_decision").state == "schedule"
    alert = house.active_alerts["weather_without_source"]
    assert alert["code"] == "weather_without_source"
    assert alert["params"]["features"] == ["cutoff", "season_auto"]
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_outdoor_source_unavailable_alert(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """The alert follows the outdoor temperature itself, not the state of one entity."""
    hass.states.async_set("sensor.outdoor", "5.0", {"unit_of_measurement": "°C"})
    hass.states.async_set("weather.home", "cloudy", {"temperature": 6.0, "temperature_unit": "°C"})
    entry = await _setup(
        hass, freezer, house_options={"outdoor_sensor": "sensor.outdoor", "weather": "weather.home"}
    )
    house = entry.runtime_data
    await _tick(hass, freezer, 15)
    # The sensor fails, the weather entity still gives 6 °C: no alert.
    hass.states.async_set("sensor.outdoor", "unavailable")
    await _tick(hass, freezer, 16 * 60)  # longer than the default alert time of 15 min
    assert house.outdoor_temperature() == 6.0
    assert "unavailable_outdoor" not in house.active_alerts
    # The weather entity is available but has no temperature: nothing gives one.
    hass.states.async_set("weather.home", "cloudy", {"temperature_unit": "°C"})
    await _tick(hass, freezer, 60)
    assert "unavailable_outdoor" not in house.active_alerts
    await _tick(hass, freezer, 15 * 60)
    alert = house.active_alerts["unavailable_outdoor"]
    assert alert["code"] == "outdoor_unavailable"
    assert alert["params"]["entities"] == ["sensor.outdoor", "weather.home"]
    # The sensor reports again: the alert goes.
    hass.states.async_set("sensor.outdoor", "6.5", {"unit_of_measurement": "°C"})
    await _tick(hass, freezer, 15)
    assert "unavailable_outdoor" not in house.active_alerts
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_levels_from_room_settings(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Temperatures chosen in the room settings are used and shown as numbers."""
    entry = await _setup(hass, freezer, levels={"home": 22.5, "sleep": 18.5})
    await _tick(hass, freezer, 15)
    assert hass.states.get("sensor.bedroom_target_temperature").state == "22.5"
    assert hass.states.get("number.bedroom_level_home").state == "22.5"
    decision = hass.states.get("sensor.bedroom_decision")
    assert decision.attributes["device_levels"] == []
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_set_schedule_service(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    """The card saves schedules through the service."""
    entry = await _setup(hass, freezer)
    await _tick(hass, freezer, 15)
    seen: list[str] = []
    hass.bus.async_listen(
        "state_changed",
        lambda event: seen.append(event.data["new_state"].state)
        if event.data["entity_id"] == "sensor.bedroom_decision" and event.data["new_state"]
        else None,
    )
    await hass.services.async_call(
        DOMAIN,
        "set_schedule",
        {"room": "Bedroom", "profiles": {"workday": [{"time": "00:00", "preset": "eco"}]}},
        blocking=True,
    )
    await hass.async_block_till_done()
    subentry = next(iter(entry.subentries.values()))
    assert subentry.data["schedule"] == "workday: 00:00 eco"
    await _tick(hass, freezer, 15)
    assert hass.states.get("sensor.bedroom_decision").attributes["preset"] == "eco"
    # Saving a schedule does not reload the integration.
    assert "unavailable" not in seen
    # The profile select of earlier versions is gone.
    assert hass.states.get("select.bedroom_profile") is None

    # Days and on / off of the profiles: Monday has no active profile -> frost.
    await hass.services.async_call(
        DOMAIN,
        "set_schedule",
        {
            "room": "Bedroom",
            "profiles": {
                "workday": [{"time": "00:00", "preset": "home"}],
                "weekend": [{"time": "00:00", "preset": "sleep"}],
            },
            "profile_days": {
                "workday": {"days": ["tue", "wed", "thu", "fri"], "enabled": True},
                "weekend": {"days": "weekend", "enabled": True},
            },
        },
        blocking=True,
    )
    await hass.async_block_till_done()
    await _tick(hass, freezer, 15)
    decision = hass.states.get("sensor.bedroom_decision")
    assert decision.attributes["reason_key"] == "no_profile"
    assert decision.attributes["profile"] is None
    assert decision.attributes["profile_days"]["workday"]["days"] == ["tue", "wed", "thu", "fri"]
    assert decision.attributes["next_preset"] == "home"
    gap = [a for a in decision.attributes["alerts"] if a.get("code") == "schedule_gap"]
    assert gap and gap[0]["params"]["days"] == ["mon"]
    # Profiles on for the same days are refused.
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            "set_schedule",
            {
                "room": "Bedroom",
                "profiles": {
                    "workday": [{"time": "00:00", "preset": "home"}],
                    "weekend": [{"time": "00:00", "preset": "sleep"}],
                },
                "profile_days": {
                    "workday": {"days": "all", "enabled": True},
                    "weekend": {"days": "weekend", "enabled": True},
                },
            },
            blocking=True,
        )
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_card_resource(hass: HomeAssistant) -> None:
    """The card is added to (and kept up to date in) the dashboard resources."""
    from custom_components.advanced_climate.const import CARD_URL
    from custom_components.advanced_climate.frontend import (
        async_ensure_lovelace_resource,
        async_remove_lovelace_resource,
        lovelace_resources,
    )

    assert await async_setup_component(hass, "lovelace", {})
    resources = lovelace_resources(hass)
    assert resources is not None
    assert await async_ensure_lovelace_resource(hass, f"{CARD_URL}?v=1.0.0")
    assert await async_ensure_lovelace_resource(hass, f"{CARD_URL}?v=1.1.1")
    mine = [i for i in resources.async_items() if i["url"].startswith(CARD_URL)]
    assert len(mine) == 1
    assert mine[0]["url"] == f"{CARD_URL}?v=1.1.1"
    assert mine[0]["type"] == "module"
    await async_remove_lovelace_resource(hass)
    assert not [i for i in resources.async_items() if i["url"].startswith(CARD_URL)]


async def test_card_resource_moved_after_the_rename(hass: HomeAssistant) -> None:
    """The resource of the card before the rename is moved to the new URL."""
    from custom_components.advanced_climate.const import CARD_URL, LEGACY_CARD_URL
    from custom_components.advanced_climate.frontend import (
        async_ensure_lovelace_resource,
        async_remove_lovelace_resource,
        lovelace_resources,
    )

    assert await async_setup_component(hass, "lovelace", {})
    resources = lovelace_resources(hass)
    await resources.async_load()
    resources.loaded = True
    await resources.async_create_item({"res_type": "module", "url": f"{LEGACY_CARD_URL}?v=2.3.4"})
    assert await async_ensure_lovelace_resource(hass, f"{CARD_URL}?v=2.3.5")
    urls = [i["url"] for i in resources.async_items()]
    assert urls == [f"{CARD_URL}?v=2.3.5"]
    await async_remove_lovelace_resource(hass)
    assert not list(resources.async_items())


async def test_fahrenheit_house(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    """A house in °F: sensors, levels, card attributes and services use °F; values kept in °C."""
    await hass.config.async_set_time_zone("Europe/Bucharest")
    freezer.move_to("2026-10-12 09:00:00+00:00")
    assert await async_setup_component(hass, "input_boolean", {"input_boolean": {"heater": {}}})
    # 64.4 °F = 18 °C
    hass.states.async_set("sensor.room_temp", "64.4", {"unit_of_measurement": "°F"})
    hass.states.async_set("person.andrei", "home")
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Home",
        options={"persons": ["person.andrei"], "nearby_zones": [], "temperature_unit": "fahrenheit"},
        subentries_data=[
            {
                "data": {
                    "source": "switch",
                    "switches": ["input_boolean.heater"],
                    "temperature_sensors": ["sensor.room_temp"],
                    "min_on_minutes": 0,
                    "min_off_minutes": 0,
                },
                "subentry_type": SUBENTRY_ROOM,
                "title": "Bedroom",
                "unique_id": None,
            }
        ],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    await _tick(hass, freezer, 15)

    decision = hass.states.get("sensor.bedroom_decision")
    assert decision.attributes["temperature_unit"] == "°F"
    assert decision.attributes["current_temperature"] == 64.4
    # Level home = 21 °C = 69.8 °F
    assert decision.attributes["target_temperature"] == 69.8
    assert decision.attributes["levels"]["home"] == 69.8
    target = hass.states.get("sensor.bedroom_target_temperature")
    assert target.attributes["unit_of_measurement"] == "°F"
    assert float(target.state) == 69.8
    assert hass.states.get("input_boolean.heater").state == "on"
    level = hass.states.get("number.bedroom_level_home")
    assert level.attributes["unit_of_measurement"] == "°F"
    assert float(level.state) == 69.8

    # A manual temperature is given in °F.
    await hass.services.async_call(
        DOMAIN, "set_override", {"room": "Bedroom", "temperature": 72, "duration_hours": 1},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert hass.states.get("sensor.bedroom_decision").attributes["target_temperature"] == 72.0

    # Setting a level in °F stores it in °C.
    await hass.services.async_call(
        "number", "set_value", {"entity_id": "number.bedroom_level_home", "value": 71.6},
        blocking=True,
    )
    await hass.async_block_till_done()
    room = entry.runtime_data.rooms[next(iter(entry.subentries))]
    assert round(room.levels["home"], 2) == 22.0
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_late_device_report_is_not_manual(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """A TRV that confirms a command later (new context) is not a manual change."""
    await hass.config.async_set_time_zone("Europe/Bucharest")
    freezer.move_to("2026-10-12 09:00:00+00:00")
    calls = async_mock_service(hass, "climate", "set_temperature")
    trv = {
        "hvac_modes": ["heat", "off"],
        "current_temperature": 18.0,
        "temperature": 17.0,
        "target_temp_step": 0.5,
    }
    hass.states.async_set("climate.trv", "heat", trv)
    hass.states.async_set("person.andrei", "home")
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Home",
        options={"persons": ["person.andrei"], "nearby_zones": []},
        subentries_data=[
            {
                "data": {"source": "climate", "climates": ["climate.trv"], "command_mode": "temperature"},
                "subentry_type": SUBENTRY_ROOM,
                "title": "Office",
                "unique_id": None,
            }
        ],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    await _tick(hass, freezer, 15)
    assert calls and calls[-1].data["temperature"] == 21.0

    # The device reports the new set point a minute later, with its own context.
    await _tick(hass, freezer, 60)
    hass.states.async_set("climate.trv", "heat", {**trv, "temperature": 21.0}, context=Context())
    await _tick(hass, freezer, 5)
    assert hass.states.get("binary_sensor.office_manual_change").state == "off"
    assert hass.states.get("sensor.office_decision").state == "schedule"

    # A person changes it: respected.
    hass.states.async_set("climate.trv", "heat", {**trv, "temperature": 23.0}, context=Context())
    await _tick(hass, freezer, 5)
    assert hass.states.get("binary_sensor.office_manual_change").state == "on"

    # Back to the value the integration sent before: still a person's change.
    hass.states.async_set("climate.trv", "heat", {**trv, "temperature": 21.0}, context=Context())
    await _tick(hass, freezer, 5)
    override = hass.states.get("binary_sensor.office_manual_change").attributes
    assert override["description"] == "21.0 °C"

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_vacation_end_only_and_preheat(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Only an end date starts the vacation now; before the end the schedule applies."""
    entry = await _setup(hass, freezer)
    # Automatic vacation after 1 h far away must not block the preheating.
    entry.runtime_data.options["auto_vacation_hours"] = 1.0
    await _tick(hass, freezer, 15)
    hass.states.async_set("person.andrei", "not_home")
    await _tick(hass, freezer, 11 * 60)
    assert hass.states.get("sensor.home_presence").state == "far"

    end = dt_util.now() + timedelta(hours=10)
    await hass.services.async_call(DOMAIN, "set_vacation", {"end": end}, blocking=True)
    await hass.async_block_till_done()
    assert hass.states.get("sensor.bedroom_decision").state == "vacation"
    # The card plans away until the preheating starts (4 h before the end).
    hold = hass.states.get("sensor.bedroom_decision").attributes["hold_until"]
    assert dt_util.parse_datetime(hold) == dt_util.as_utc(end) - timedelta(hours=4)

    # 4 h before the end (default): the schedule, although nobody is near.
    await _tick(hass, freezer, 6 * 3600 + 60)
    decision = hass.states.get("sensor.bedroom_decision")
    assert decision.state == "schedule", decision.attributes["reason"]
    assert "preheating" in decision.attributes["reason"]
    assert hass.states.get("sensor.home_presence").attributes["vacation_preheating"] is True

    # After the end, still far away for hours: the automatic vacation again.
    await _tick(hass, freezer, 4 * 3600)
    assert hass.states.get("sensor.bedroom_decision").state == "vacation"

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_saved_outdoor_values_dropped_without_source(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, hass_storage: dict
) -> None:
    """Without an outdoor sensor or weather the saved outdoor values are not used."""
    entry_id = "house_without_outdoor"
    hass_storage[f"{DOMAIN}.{entry_id}"] = {
        "version": 1,
        "key": f"{DOMAIN}.{entry_id}",
        "data": {
            "house": {
                "outdoor": {
                    "samples": [["2026-10-12T08:00:00+00:00", 5.0]],
                    "daily_means": {"2026-10-11": 5.0},
                    "cutoff_active": True,
                    "season_active": True,
                }
            },
            "rooms": {},
        },
    }
    freezer.move_to("2026-10-12 09:00:00+00:00")
    entry = MockConfigEntry(domain=DOMAIN, title="Home", options={}, entry_id=entry_id)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    house = entry.runtime_data
    assert house.outdoor.latest() is None
    assert house.outdoor.daily_means == {}
    assert house.outdoor.cutoff_active is False
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_heating_counts_only_while_the_heat_source_runs(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """A TRV room that asks for heat while the boiler waits for other rooms does not heat."""
    await hass.config.async_set_time_zone("Europe/Bucharest")
    freezer.move_to("2026-10-12 09:00:00+00:00")
    async_mock_service(hass, "climate", "set_temperature")
    assert await async_setup_component(hass, "input_boolean", {"input_boolean": {"boiler": {}}})
    trv = {"hvac_modes": ["heat", "off"], "current_temperature": 18.0, "temperature": 21.0}
    hass.states.async_set("climate.trv", "heat", {**trv, "hvac_action": "heating"})
    hass.states.async_set("person.andrei", "home")
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Home",
        options={
            "persons": ["person.andrei"],
            "nearby_zones": [],
            "boiler_entity": "input_boolean.boiler",
            "boiler_min_rooms": 2,  # one room is not enough: the boiler waits
        },
        subentries_data=[
            {
                "data": {"source": "climate", "climates": ["climate.trv"], "command_mode": "temperature"},
                "subentry_type": SUBENTRY_ROOM,
                "title": "Office",
                "unique_id": None,
            }
        ],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    await _tick(hass, freezer, 15)
    room = next(iter(entry.runtime_data.rooms.values()))
    demand = hass.states.get("binary_sensor.office_heat_demand")
    assert demand.state == "on"
    assert demand.attributes["heating"] is False
    assert room.learner.episode_start is None
    await _tick(hass, freezer, 1800)
    assert room.runtime_s == 0

    # The heat source runs (paused, so the integration does not switch it off
    # for the missing second room): now the room heats and learns.
    await hass.services.async_call("switch", "turn_on", {"entity_id": "switch.home_pause"}, blocking=True)
    await hass.services.async_call(
        "input_boolean", "turn_on", {"entity_id": "input_boolean.boiler"}, blocking=True
    )
    await _tick(hass, freezer, 5)
    assert hass.states.get("binary_sensor.office_heat_demand").attributes["heating"] is True
    assert room.learner.episode_start is not None
    await _tick(hass, freezer, 600)
    assert room.runtime_s >= 600

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def _trv_house(hass, freezer, **options):
    """A house with one TRV room and an input_boolean as its heat source."""
    await hass.config.async_set_time_zone("Europe/Bucharest")
    freezer.move_to("2026-10-12 09:00:00+00:00")
    async_mock_service(hass, "climate", "set_temperature")
    assert await async_setup_component(hass, "input_boolean", {"input_boolean": {"boiler": {}}})
    hass.states.async_set("person.andrei", "home")
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Home",
        options={
            "persons": ["person.andrei"],
            "nearby_zones": [],
            "boiler_entity": "input_boolean.boiler",
            **options,
        },
        subentries_data=[
            {
                "data": {"source": "climate", "climates": ["climate.trv"], "command_mode": "temperature"},
                "subentry_type": SUBENTRY_ROOM,
                "title": "Office",
                "unique_id": None,
            }
        ],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_frost_protection_starts_the_heat_source(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Frost protection starts the heat source alone, also while paused."""
    cold = {"hvac_modes": ["heat", "off"], "current_temperature": 5.0, "temperature": 7.0}
    hass.states.async_set("climate.trv", "heat", {**cold, "hvac_action": "heating"})
    entry = await _trv_house(hass, freezer, boiler_min_rooms=2)
    await hass.services.async_call(
        "select", "select_option", {"entity_id": "select.home_mode", "option": "off"}, blocking=True
    )
    await _tick(hass, freezer, 15)
    # One room is fewer than the rooms needed, but it is in frost protection.
    assert hass.states.get("input_boolean.boiler").state == "on"

    # Warm again: the heat source stops.
    hass.states.async_set(
        "climate.trv", "heat", {**cold, "current_temperature": 8.0, "hvac_action": "idle"}
    )
    await _tick(hass, freezer, 600)
    assert hass.states.get("input_boolean.boiler").state == "off"

    # Paused: no commands, except for frost protection.
    await hass.services.async_call("switch", "turn_on", {"entity_id": "switch.home_pause"}, blocking=True)
    hass.states.async_set("climate.trv", "heat", {**cold, "hvac_action": "heating"})
    await _tick(hass, freezer, 600)
    assert hass.states.get("input_boolean.boiler").state == "on"
    hass.states.async_set(
        "climate.trv", "heat", {**cold, "current_temperature": 8.0, "hvac_action": "idle"}
    )
    await _tick(hass, freezer, 600)
    assert hass.states.get("input_boolean.boiler").state == "off"

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_frost_start_in_a_pause_survives_a_restart(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """A heat source started for frost protection in a pause is stopped after a restart.

    The minimum on time (5 min by default) also holds across the restart.
    """
    cold = {"hvac_modes": ["heat", "off"], "current_temperature": 5.0, "temperature": 7.0}
    hass.states.async_set("climate.trv", "heat", {**cold, "hvac_action": "heating"})
    entry = await _trv_house(hass, freezer)
    await hass.services.async_call("switch", "turn_on", {"entity_id": "switch.home_pause"}, blocking=True)
    await _tick(hass, freezer, 15)
    assert hass.states.get("input_boolean.boiler").state == "on"

    # Restart of the integration; meanwhile the room is warm again.
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    hass.states.async_set(
        "climate.trv", "heat", {**cold, "current_temperature": 8.0, "hvac_action": "idle"}
    )
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    house = entry.runtime_data
    assert house.paused
    await _tick(hass, freezer, 15)
    # Started 15 s ago (less than the 5 min minimum on time): it waits.
    assert hass.states.get("input_boolean.boiler").state == "on"
    assert house.source_waiting == "min_on"
    # After the minimum on time it is stopped: it was started for frost protection.
    await _tick(hass, freezer, 600)
    assert hass.states.get("input_boolean.boiler").state == "off"
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_durations_across_the_dst_change(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """A manual change for 2 hours lasts 2 real hours across the end of summer time."""
    entry = await _setup(hass, freezer)
    await _tick(hass, freezer, 15)
    # 02:30 summer time on 25 October 2026; at 04:00 the clock goes back to 03:00.
    freezer.move_to("2026-10-24 23:30:00+00:00")
    await hass.services.async_call(
        DOMAIN, "set_override", {"room": "Bedroom", "temperature": 23, "duration_hours": 2},
        blocking=True,
    )
    await hass.async_block_till_done()
    until = dt_util.parse_datetime(
        hass.states.get("binary_sensor.bedroom_manual_change").attributes["until"]
    )
    assert dt_util.as_utc(until) == dt_util.parse_datetime("2026-10-25 01:30:00+00:00")
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_service_temperature_within_the_safety_limits(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """set_override keeps a temperature between frost protection and the maximum."""
    entry = await _setup(hass, freezer)
    await _tick(hass, freezer, 15)
    await hass.services.async_call(
        DOMAIN, "set_override", {"room": "Bedroom", "temperature": 35}, blocking=True
    )
    await hass.async_block_till_done()
    room = next(iter(entry.runtime_data.rooms.values()))
    assert room.override["target"]["temperature"] == 25.0  # the default maximum
    decision = hass.states.get("sensor.bedroom_decision")
    assert decision.attributes["max_temperature"] == 25.0
    assert decision.attributes["min_temperature"] == 7.0
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_heat_source_unavailable_alert(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """An unavailable heat source is reported after the configured time."""
    hass.states.async_set(
        "climate.trv", "heat", {"hvac_modes": ["heat", "off"], "current_temperature": 20.0,
                                "temperature": 21.0, "hvac_action": "idle"}
    )
    entry = await _trv_house(hass, freezer)
    await _tick(hass, freezer, 15)
    hass.states.async_set("input_boolean.boiler", "unavailable")
    await _tick(hass, freezer, 60)
    house = entry.runtime_data
    assert "unavailable_input_boolean.boiler" not in house._alerts  # noqa: SLF001
    await _tick(hass, freezer, 16 * 60)
    assert "unavailable_input_boolean.boiler" in house._alerts  # noqa: SLF001
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_rounded_down_to_the_step_at_the_maximum(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """A thermostat never gets more than the maximum because of its own step."""
    trv = {"hvac_modes": ["heat", "off"], "current_temperature": 18.0, "temperature": 17.0,
           "target_temp_step": 0.5, "hvac_action": "idle"}
    hass.states.async_set("climate.trv", "heat", trv)
    entry = await _trv_house(hass, freezer, max_temp=24.8, boiler_entity=None)
    calls = async_mock_service(hass, "climate", "set_temperature")
    await _tick(hass, freezer, 15)
    room = next(iter(entry.runtime_data.rooms.values()))
    room.levels["home"] = 26.0
    await hass.services.async_call(DOMAIN, "reevaluate", {}, blocking=True)
    await hass.async_block_till_done()
    assert calls[-1].data["temperature"] == 24.5  # 24.8 would become 25.0 on the TRV
    # The valve exercise is meant to go above the maximum: sent as it is.
    state = hass.states.get("climate.trv")
    assert room._device_value(state, 30.0) == 30.0  # noqa: SLF001
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_forecast_cancels_or_triggers_the_cutoff(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """The forecast mean of the next hours stops the heating earlier or cancels the stop."""
    freezer.move_to("2026-10-12 09:00:00+00:00")
    hass.states.async_set("weather.home", "sunny", {"temperature": 20.0, "temperature_unit": "°C"})
    start = dt_util.utcnow().replace(minute=0, second=0, microsecond=0)

    def forecast(value: float, warm_hour: datetime | None = None) -> None:
        async_mock_service(
            hass,
            "weather",
            "get_forecasts",
            response={
                "weather.home": {
                    "forecast": [
                        {
                            "datetime": (start + timedelta(hours=h)).isoformat(),
                            "temperature": 30.0 if start + timedelta(hours=h) == warm_hour else value,
                        }
                        for h in range(48)
                    ]
                }
            },
            supports_response=SupportsResponse.ONLY,
        )

    forecast(20.0)
    entry = await _setup(
        hass,
        freezer,
        house_options={
            "weather": "weather.home",
            "cutoff_enabled": True,
            "cutoff_temp": 18.0,
            "cutoff_hysteresis": 1.0,
            "cutoff_avg_hours": 1,
            "forecast_enabled": True,
            "forecast_hours": 3,
        },
    )
    house = entry.runtime_data
    await _tick(hass, freezer, 15)
    # Warm measured and warm forecast: off, because of the measured average.
    assert house.cutoff_reason == "measured"
    assert hass.states.get("binary_sensor.home_warm_outside").state == "on"

    # It gets cold: the forecast mean (12 °C) is below the resume temperature
    # (17 °C), so the stop is cancelled while the measured average is still warm.
    forecast(12.0)
    await house._async_refresh_forecast(dt_util.utcnow())
    await _tick(hass, freezer, 15)
    assert house.outdoor.cutoff_active
    assert house.cutoff_reason == "forecast_cold"
    assert hass.states.get("binary_sensor.home_warm_outside").state == "off"
    outdoor = hass.states.get("sensor.home_outdoor_average").attributes
    assert outdoor["cutoff_reason"] == "forecast_cold"
    assert outdoor["forecast_hours"] == 3
    assert hass.states.get("sensor.bedroom_decision").state != "outdoor_cutoff"

    # Measured cold: one warm forecast hour (30 °C) does not turn the heating
    # off, only the mean counts. With r hours (0 < r <= 1) of the measured
    # 10 °C until the next forecast hour, then 1 h of 30 °C and 2 - r hours of
    # 12 °C, the 3 h mean is (10 r + 30 + 12 (2 - r)) / 3 = (54 - 2 r) / 3,
    # below the 18 °C cutoff.
    hass.states.async_set("weather.home", "cloudy", {"temperature": 10.0, "temperature_unit": "°C"})
    await _tick(hass, freezer, 2 * 3600)
    now = dt_util.utcnow()
    hours = [start + timedelta(hours=h) for h in range(48)]
    forecast(12.0, warm_hour=next(t for t in hours if t > now))
    await house._async_refresh_forecast(dt_util.utcnow())
    await _tick(hass, freezer, 15)
    assert house.forecast_mean < 18
    assert house.cutoff_reason is None
    assert hass.states.get("binary_sensor.home_warm_outside").state == "off"

    # Measured cold, forecast mean warm: the heating is turned off earlier (the
    # mean of the next 3 h reaches the cutoff: measured 10 °C for at most 1 h,
    # then 24 °C, so at least (10 + 2 * 24) / 3 = 19.3 °C).
    forecast(24.0)
    await house._async_refresh_forecast(dt_util.utcnow())
    await _tick(hass, freezer, 15)
    assert not house.outdoor.cutoff_active
    assert house.cutoff_reason == "forecast_warm"
    assert house.forecast_mean >= 18
    assert hass.states.get("binary_sensor.home_warm_outside").state == "on"
    assert hass.states.get("sensor.bedroom_decision").state == "outdoor_cutoff"

    # Measured and forecast 17.5 °C, between the resume temperature (18 - 1 =
    # 17 °C) and the cutoff: the heating stays off (hysteresis).
    hass.states.async_set("weather.home", "cloudy", {"temperature": 17.5, "temperature_unit": "°C"})
    forecast(17.5)
    await house._async_refresh_forecast(dt_util.utcnow())
    await _tick(hass, freezer, 15)
    assert 17 < house.forecast_mean < 18
    assert not house.outdoor.cutoff_active
    assert house.cutoff_reason == "forecast_warm"
    assert hass.states.get("binary_sensor.home_warm_outside").state == "on"

    # Forecast 12 °C: the 3 h mean is at most (17.5 + 2 * 12) / 3 = 13.8 °C
    # (measured 17.5 °C for at most 1 h), at or below 17 °C: heating may run.
    forecast(12.0)
    await house._async_refresh_forecast(dt_util.utcnow())
    await _tick(hass, freezer, 15)
    assert house.cutoff_reason is None
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_arriving_ends_the_automatic_vacation(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """On the way home the automatic vacation ends, so the house preheats."""
    hass.states.async_set("sensor.distance", "50", {"unit_of_measurement": "km"})
    entry = await _setup(
        hass,
        freezer,
        house_options={"auto_vacation_hours": 1.0, "proximity_distance": "sensor.distance"},
    )
    house = entry.runtime_data
    await _tick(hass, freezer, 15)
    hass.states.async_set("person.andrei", "not_home")
    await _tick(hass, freezer, 11 * 60)
    assert hass.states.get("sensor.home_presence").state == "far"
    await _tick(hass, freezer, 3600)
    assert house.auto_vacation
    assert hass.states.get("sensor.bedroom_decision").state == "vacation"

    # 5 km away, below the 10 km arrival distance (default): arriving.
    hass.states.async_set("sensor.distance", "5", {"unit_of_measurement": "km"})
    await _tick(hass, freezer, 15)
    assert house.arriving
    assert not house.auto_vacation
    assert hass.states.get("sensor.bedroom_decision").state != "vacation"

    # Turned back: far again, the automatic vacation waits another hour.
    hass.states.async_set("sensor.distance", "50", {"unit_of_measurement": "km"})
    await _tick(hass, freezer, 30 * 60)
    assert not house.arriving
    assert not house.auto_vacation
    await _tick(hass, freezer, 31 * 60)
    assert house.auto_vacation
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_calendar_profile_of_tomorrow(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """An event of tomorrow titled with a profile name selects it for tomorrow."""
    hass.states.async_set("calendar.home", "off", {})
    tomorrow = (dt_util.parse_datetime("2026-10-12T12:00:00+03:00") + timedelta(days=1)).date()
    events = []
    async_mock_service(
        hass,
        "calendar",
        "get_events",
        response={"calendar.home": {"events": events}},
        supports_response=SupportsResponse.ONLY,
    )
    entry = await _setup(hass, freezer, house_options={"calendar": "calendar.home"})
    house = entry.runtime_data
    room = next(iter(house.rooms.values()))
    name = sorted(room.schedule.profiles)[0]
    # An all-day event (dates only), read again when the calendar is refreshed.
    events.append(
        {
            "start": tomorrow.isoformat(),
            "end": (tomorrow + timedelta(days=1)).isoformat(),
            "summary": name.upper(),
        }
    )
    await house._async_refresh_calendar()  # noqa: SLF001
    assert room._day_info(tomorrow)[1] == name  # noqa: SLF001
    today = tomorrow - timedelta(days=1)
    assert room._day_info(today)[1] is None  # noqa: SLF001
    # An event of today that already ended (09:00-10:00, now 12:00) selects the
    # profile for the whole day, as a coming day would use it.
    events.append(
        {
            "start": "2026-10-12T09:00:00+03:00",
            "end": "2026-10-12T10:00:00+03:00",
            "summary": name,
        }
    )
    await house._async_refresh_calendar()  # noqa: SLF001
    assert room._day_info(today)[1] == name  # noqa: SLF001
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_climate_heat_source_without_heat_mode(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """A climate heat source without "heat" is started with "auto", never "off"."""
    calls = async_mock_service(hass, "climate", "set_hvac_mode")
    hass.states.async_set("climate.boiler", "off", {"hvac_modes": ["off", "auto"]})
    cold = {"hvac_modes": ["heat", "off"], "current_temperature": 18.0, "temperature": 21.0}
    hass.states.async_set("climate.trv", "heat", {**cold, "hvac_action": "heating"})
    entry = await _trv_house(hass, freezer, boiler_entity="climate.boiler")
    await _tick(hass, freezer, 15)
    modes = [c.data["hvac_mode"] for c in calls if c.data.get("entity_id") == "climate.boiler"]
    assert modes and modes[-1] == "auto"
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_optimal_stop_and_start_with_the_forecast(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """The optimal stop / start uses the outdoor temperature forecast for when it runs."""
    freezer.move_to("2026-10-12 09:00:00+00:00")
    hass.states.async_set("weather.home", "cloudy", {"temperature": 8.0, "temperature_unit": "°C"})
    start = dt_util.utcnow().replace(minute=0, second=0, microsecond=0)
    forecast = [
        # 2 °C until 18:00 UTC, then -3 °C.
        {"datetime": (start + timedelta(hours=h)).isoformat(), "temperature": 2.0 if h < 9 else -3.0}
        for h in range(40)
    ]
    async_mock_service(
        hass,
        "weather",
        "get_forecasts",
        response={"weather.home": {"forecast": forecast}},
        supports_response=SupportsResponse.ONLY,
    )
    hass.states.async_set("sensor.room_temp", "21.5", {"unit_of_measurement": "°C"})
    entry = await _setup(
        hass,
        freezer,
        house_options={"weather": "weather.home", "forecast_enabled": False},
        optimal_start=True,
        optimal_stop=True,
    )
    hass.states.async_set("sensor.room_temp", "21.5", {"unit_of_measurement": "°C"})
    await _tick(hass, freezer, 15)

    # Monday 12:00 local, sleep at 22:00 (19:00 UTC): nothing learned, the longest
    # stop (30 min), 18:30-19:00 UTC, all at the forecast -3 °C.
    estimate = hass.states.get("sensor.bedroom_decision").attributes["next_estimate"]
    assert estimate["kind"] == "optimal_stop"
    assert estimate["preset"] == "sleep"
    # A relay room: the level is a temperature.
    assert estimate["sent_as"] == "temperature"
    assert estimate["temperature"] == 18.0
    assert estimate["minutes"] == 30
    assert estimate["outdoor"] == -3.0
    assert estimate["outdoor_source"] == "forecast"
    assert estimate["learned"] is False
    assert estimate["started_at"] is None
    assert dt_util.parse_datetime(estimate["starts_at"]) == dt_util.parse_datetime(
        "2026-10-12T18:30:00+00:00"
    )
    # The house wakes up at the moment the stop is expected to begin.
    room = next(iter(entry.runtime_data.rooms.values()))
    assert room.next_wakeup == dt_util.parse_datetime("2026-10-12T18:30:00+00:00")

    # At 18:31 UTC the stop runs. Until the next forecast hour (19:00) the
    # measured temperature stands; what it started with is kept.
    await _tick(hass, freezer, 9 * 3600 + 31 * 60 - 15)
    decision = hass.states.get("sensor.bedroom_decision")
    assert decision.state == "optimal_stop", decision.attributes["reason"]
    started = decision.attributes["next_estimate"]
    assert started["started_at"] is not None
    assert (started["outdoor"], started["outdoor_source"]) == (8.0, "now")
    hass.states.async_set("weather.home", "cloudy", {"temperature": 7.0, "temperature_unit": "°C"})
    await _tick(hass, freezer, 60)
    assert hass.states.get("sensor.bedroom_decision").attributes["next_estimate"] == started

    # Summer mode: no optimal start / stop can happen, none is shown.
    await hass.services.async_call(
        "select", "select_option", {"entity_id": "select.home_mode", "option": "summer"}, blocking=True
    )
    await hass.async_block_till_done()
    assert hass.states.get("sensor.bedroom_decision").attributes["next_estimate"] is None
    await hass.services.async_call(
        "select", "select_option", {"entity_id": "select.home_mode", "option": "auto"}, blocking=True
    )
    await hass.async_block_till_done()

    # After 22:00 local: home at 06:00 (03:00 UTC) is warmer -> optimal start.
    await _tick(hass, freezer, 3600)
    hass.states.async_set("sensor.room_temp", "19.0", {"unit_of_measurement": "°C"})
    await _tick(hass, freezer, 5)
    estimate = hass.states.get("sensor.bedroom_decision").attributes["next_estimate"]
    assert estimate["kind"] == "optimal_start"
    assert estimate["preset"] == "home"
    assert estimate["outdoor"] == -3.0
    assert estimate["outdoor_source"] == "forecast"
    assert estimate["minutes"] == 120  # 2 °C at the default 60 minutes per degree

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_estimate_without_forecast_uses_the_value_of_now(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Without an hourly forecast the outdoor temperature of now is used."""
    freezer.move_to("2026-10-12 09:00:00+00:00")
    hass.states.async_set("weather.home", "cloudy", {"temperature": 8.0, "temperature_unit": "°C"})
    hass.states.async_set("sensor.room_temp", "21.5", {"unit_of_measurement": "°C"})
    entry = await _setup(
        hass, freezer, house_options={"weather": "weather.home"}, optimal_stop=True
    )
    hass.states.async_set("sensor.room_temp", "21.5", {"unit_of_measurement": "°C"})
    await _tick(hass, freezer, 15)
    estimate = hass.states.get("sensor.bedroom_decision").attributes["next_estimate"]
    assert estimate["kind"] == "optimal_stop"
    assert estimate["outdoor"] == 8.0
    assert estimate["outdoor_source"] == "now"

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def _window_trv_house(hass, freezer):
    """One TRV room with a window sensor."""
    await hass.config.async_set_time_zone("Europe/Bucharest")
    freezer.move_to("2026-10-12 09:00:00+00:00")
    calls = async_mock_service(hass, "climate", "set_temperature")
    trv = {"hvac_modes": ["heat", "off"], "current_temperature": 18.0, "temperature": 17.0}
    hass.states.async_set("climate.trv", "heat", trv)
    hass.states.async_set("binary_sensor.window", "off")
    hass.states.async_set("person.andrei", "home")
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Home",
        options={"persons": ["person.andrei"], "nearby_zones": []},
        subentries_data=[
            {
                "data": {
                    "source": "climate",
                    "climates": ["climate.trv"],
                    "command_mode": "temperature",
                    "window_sensors": ["binary_sensor.window"],
                },
                "subentry_type": SUBENTRY_ROOM,
                "title": "Office",
                "unique_id": None,
            }
        ],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    await _tick(hass, freezer, 15)
    return entry, calls, trv


async def _window(hass, freezer, state: str) -> None:
    hass.states.async_set("binary_sensor.window", state)
    await _tick(hass, freezer, 65)


async def test_card_manual_change_set_again_after_a_window(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """A temperature set by the card comes back on the thermostat after a window."""
    entry, calls, trv = await _window_trv_house(hass, freezer)
    assert calls[-1].data["temperature"] == 21.0
    await hass.services.async_call(
        DOMAIN, "set_override", {"room": "Office", "temperature": 23, "duration_hours": 2},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert hass.states.get("sensor.office_decision").state == "manual_override"
    assert calls[-1].data["temperature"] == 23.0

    await _window(hass, freezer, "on")
    assert hass.states.get("sensor.office_decision").state == "window_open"
    assert calls[-1].data["temperature"] == 7.0
    assert hass.states.get("sensor.office_decision").attributes["override"]["temperature"] == 23.0
    await _window(hass, freezer, "off")
    assert hass.states.get("sensor.office_decision").state == "manual_override"
    assert calls[-1].data["temperature"] == 23.0

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_card_manual_change_is_verified(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """A temperature set by the card is checked on the device: sent again once, then an alert."""
    entry, calls, _trv = await _window_trv_house(hass, freezer)
    house = entry.runtime_data
    room = next(iter(house.rooms.values()))
    await hass.services.async_call(
        DOMAIN, "set_override", {"room": "Office", "temperature": 23, "duration_hours": 2},
        blocking=True,
    )
    await hass.async_block_till_done()
    sent = len([c for c in calls if c.data["temperature"] == 23.0])
    # The thermostat keeps 17 °C (the mocked service changes nothing).
    await _tick(hass, freezer, 121)  # VERIFY_DELAY is 120 s
    assert len([c for c in calls if c.data["temperature"] == 23.0]) == sent + 1
    assert f"verify_{room.id}" not in house._alerts  # noqa: SLF001
    await _tick(hass, freezer, 121)
    assert f"verify_{room.id}" in house._alerts  # noqa: SLF001
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_device_manual_change_set_again_after_a_window(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """A temperature set on the thermostat is respected, and set again after a window."""
    entry, calls, trv = await _window_trv_house(hass, freezer)
    hass.states.async_set("climate.trv", "heat", {**trv, "temperature": 23.0}, context=Context())
    await _tick(hass, freezer, 5)
    assert hass.states.get("sensor.office_decision").state == "manual_override"
    sent = len(calls)
    await _tick(hass, freezer, 300)
    assert len(calls) == sent  # respected: nothing is sent

    await _window(hass, freezer, "on")
    assert calls[-1].data["temperature"] == 7.0
    # The card plans what the manual change holds, not the frost protection of now.
    held = hass.states.get("sensor.office_decision").attributes["override"]
    assert held["temperature"] == 23.0
    assert hass.states.get("binary_sensor.office_manual_change").attributes["temperature"] == 23.0
    # The thermostat confirms the command (the integration's value: not a manual change).
    hass.states.async_set("climate.trv", "heat", {**trv, "temperature": 7.0}, context=Context())
    await _tick(hass, freezer, 5)
    await _window(hass, freezer, "off")
    assert hass.states.get("sensor.office_decision").state == "manual_override"
    assert calls[-1].data["temperature"] == 23.0
    hass.states.async_set("climate.trv", "heat", {**trv, "temperature": 23.0}, context=Context())
    sent = len(calls)
    await _tick(hass, freezer, 300)
    assert len(calls) == sent
    assert hass.states.get("binary_sensor.office_manual_change").attributes["description"] == "23.0 °C"

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_pause_sends_nothing_for_a_manual_relay(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """In a pause a relay with a manual temperature is not switched."""
    entry = await _setup(hass, freezer)
    await _tick(hass, freezer, 15)
    await hass.services.async_call(
        DOMAIN, "set_override", {"room": "Bedroom", "temperature": 23, "duration_hours": 2},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert hass.states.get("input_boolean.heater").state == "on"

    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": "switch.home_pause"}, blocking=True
    )
    await hass.async_block_till_done()
    assert hass.states.get("sensor.bedroom_decision").state == "pause"
    # Below the maximum (25 °C): nothing is sent (at the maximum it is turned off).
    hass.states.async_set("sensor.room_temp", "24.0", {"unit_of_measurement": "°C"})
    await _tick(hass, freezer, 5)
    assert hass.states.get("input_boolean.heater").state == "on"

    # A manual change in a pause is kept, but sent only after the pause.
    await hass.services.async_call(
        DOMAIN, "set_override", {"room": "Bedroom", "temperature": 22, "duration_hours": 2},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert hass.states.get("input_boolean.heater").state == "on"
    override = hass.states.get("sensor.bedroom_decision").attributes["override"]
    assert override["applied"] is False  # the card shows: applies after the pause
    hass.states.async_set("sensor.room_temp", "24.5", {"unit_of_measurement": "°C"})
    await _tick(hass, freezer, 5)
    assert hass.states.get("input_boolean.heater").state == "on"

    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": "switch.home_pause"}, blocking=True
    )
    await hass.async_block_till_done()
    assert hass.states.get("sensor.bedroom_decision").state == "manual_override"
    assert hass.states.get("input_boolean.heater").state == "off"
    assert hass.states.get("sensor.bedroom_decision").attributes["override"]["applied"] is True

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_card_attributes_not_heating_alerts_cutoff(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Why a room does not heat, its alerts, the cutoff thresholds and the manual change origin."""
    hass.states.async_set("sensor.outside", "5.0", {"unit_of_measurement": "°C"})
    entry = await _setup(hass, freezer, house_options={"outdoor_sensor": "sensor.outside"})
    await _tick(hass, freezer, 15)
    assert hass.states.get("input_boolean.heater").state == "on"
    # Warm: the relay turns off; just below the target it stays off (hysteresis).
    hass.states.async_set("sensor.room_temp", "21.6", {"unit_of_measurement": "°C"})
    await _tick(hass, freezer, 5)
    hass.states.async_set("sensor.room_temp", "20.8", {"unit_of_measurement": "°C"})
    await _tick(hass, freezer, 5)
    assert hass.states.get("input_boolean.heater").state == "off"
    attrs = hass.states.get("sensor.bedroom_decision").attributes
    assert attrs["no_heat_reason"]["code"] == "hysteresis"
    assert attrs["alerts"] == []

    outdoor = hass.states.get("sensor.home_outdoor_average").attributes
    assert outdoor["cutoff_temperature"] == 18.0
    assert outdoor["cutoff_resume_temperature"] == 17.0  # default hysteresis 1 °C
    assert outdoor["forecast"] == []

    # The temperature sensor fails: an alert for the room, with a code for the card.
    hass.states.async_set("sensor.room_temp", "unavailable")
    await _tick(hass, freezer, 5)
    alerts = hass.states.get("sensor.bedroom_decision").attributes["alerts"]
    assert [a["code"] for a in alerts] == ["sensor_unavailable"]
    hass.states.async_set("sensor.room_temp", "20.8", {"unit_of_measurement": "°C"})
    await _tick(hass, freezer, 5)
    assert hass.states.get("sensor.bedroom_decision").attributes["alerts"] == []

    await hass.services.async_call(
        DOMAIN, "set_override", {"room": "Bedroom", "temperature": 23, "duration_hours": 1},
        blocking=True,
    )
    await hass.async_block_till_done()
    override = hass.states.get("sensor.bedroom_decision").attributes["override"]
    assert override["origin"] == "card"
    assert override["interrupted"] is False

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_set_override_rejects_bad_values(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """nan / inf and durations outside the form range are errors; a preset is trimmed."""
    entry = await _setup(hass, freezer)
    await _tick(hass, freezer, 15)
    for data, key in (
        ({"temperature": float("nan")}, "temperature_invalid"),
        ({"temperature": float("inf")}, "temperature_invalid"),
        ({"temperature": 21, "duration_hours": 0}, "duration_invalid"),
        ({"temperature": 21, "duration_hours": -1}, "duration_invalid"),
        ({"temperature": 21, "duration_hours": 0.1}, "duration_invalid"),
        ({"temperature": 21, "duration_hours": 73}, "duration_invalid"),
        ({"temperature": 21, "duration_hours": float("nan")}, "duration_invalid"),
        ({"preset": "   "}, "preset_or_temperature"),
    ):
        with pytest.raises(ServiceValidationError) as err:
            await hass.services.async_call(
                DOMAIN, "set_override", {"room": "Bedroom", **data}, blocking=True
            )
        assert err.value.translation_key == key, data
    room = next(iter(entry.runtime_data.rooms.values()))
    assert room.override is None
    # Spaces around a level and another case are accepted.
    await hass.services.async_call(
        DOMAIN,
        "set_override",
        {"room": "Bedroom", "preset": " Sleep ", "duration_hours": 0.25},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert room.override["target"]["preset"] == "sleep"
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_vacation_datetime_end_after_start(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """The vacation datetime entities refuse an end before the start."""
    from homeassistant.helpers import entity_registry as er

    entry = await _setup(hass, freezer)
    await _tick(hass, freezer, 15)
    registry = er.async_get(hass)
    start_id = registry.async_get_entity_id("datetime", DOMAIN, f"{entry.entry_id}_vacation_start")
    end_id = registry.async_get_entity_id("datetime", DOMAIN, f"{entry.entry_id}_vacation_end")
    start = dt_util.now() + timedelta(days=2)
    await hass.services.async_call(
        "datetime", "set_value", {"entity_id": start_id, "datetime": start}, blocking=True
    )
    with pytest.raises(ServiceValidationError) as err:
        await hass.services.async_call(
            "datetime",
            "set_value",
            {"entity_id": end_id, "datetime": start - timedelta(hours=1)},
            blocking=True,
        )
    assert err.value.translation_key == "vacation_order"
    assert entry.runtime_data.vacation_end is None
    await hass.services.async_call(
        "datetime",
        "set_value",
        {"entity_id": end_id, "datetime": start + timedelta(days=1)},
        blocking=True,
    )
    assert entry.runtime_data.vacation_end is not None
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_more_rooms_needed_than_the_house_has(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Rooms needed above the number of rooms raises an alert."""
    entry = await _setup(
        hass,
        freezer,
        house_options={"boiler_entity": "input_boolean.boiler", "boiler_min_rooms": 2},
    )
    hass.states.async_set("input_boolean.boiler", "off")
    house = entry.runtime_data
    await _tick(hass, freezer, 15)
    alert = house.active_alerts["boiler_min_rooms"]
    assert alert["params"] == {"needed": 2, "rooms": 1}
    house.options["boiler_min_rooms"] = 1
    await _tick(hass, freezer, 15)
    assert "boiler_min_rooms" not in house.active_alerts
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def _boost_house(hass, freezer, room: dict, **options):
    """A house with one TRV room with the TRV boost and a room sensor, no heat source."""
    await hass.config.async_set_time_zone("Europe/Bucharest")
    # Monday 12:00 local time: the default schedule asks for home (21 °C).
    freezer.move_to("2026-10-12 09:00:00+00:00")
    hass.states.async_set("person.andrei", "home")
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Home",
        options={"persons": ["person.andrei"], "nearby_zones": [], **options},
        subentries_data=[
            {
                "data": {
                    "source": "climate",
                    "climates": ["climate.trv"],
                    "command_mode": "temperature",
                    "temperature_sensors": ["sensor.office_temp"],
                    "trv_boost": True,
                    "hysteresis": 0.2,
                    **room,
                },
                "subentry_type": SUBENTRY_ROOM,
                "title": "Office",
                "unique_id": None,
            }
        ],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def _room_temp(hass, freezer, value: float) -> None:
    hass.states.async_set("sensor.office_temp", str(value), {"unit_of_measurement": "°C"})
    await hass.services.async_call(DOMAIN, "reevaluate", {}, blocking=True)
    await hass.async_block_till_done()


async def test_trv_boost_while_heating(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    """The TRV gets the boost temperature while the room sensor asks for heat."""
    # The TRV sensor next to the radiator is warmer than the room; it reports no
    # hvac_action: the demand comes from the room sensor anyway.
    trv = {"hvac_modes": ["heat", "off"], "current_temperature": 23.0, "temperature": 21.0}
    hass.states.async_set("climate.trv", "heat", trv)
    hass.states.async_set("sensor.office_temp", "20.9", {"unit_of_measurement": "°C"})
    calls = async_mock_service(hass, "climate", "set_temperature")
    entry = await _boost_house(hass, freezer, {})
    await _tick(hass, freezer, 15)
    room = next(iter(entry.runtime_data.rooms.values()))
    # 20.9 is within 21 ± 0.2: no demand, the TRV keeps the target.
    assert not room.heat_demand
    assert all(c.data["temperature"] == 21.0 for c in calls)
    # 20.8 = 21 - 0.2: demand, the TRV gets the maximum of the house (25 °C).
    await _room_temp(hass, freezer, 20.8)
    assert room.heat_demand and room.heating
    assert calls[-1].data["temperature"] == 25.0
    attrs = hass.states.get("sensor.office_decision").attributes
    assert attrs["trv_boost"] == {"temperature": 25.0, "active": True}
    # Inside the band (21.1 < 21.2) it goes on.
    hass.states.async_set("climate.trv", "heat", {**trv, "temperature": 25.0})
    await _room_temp(hass, freezer, 21.1)
    assert room.heat_demand
    # 21.2 = 21 + 0.2: the demand ends and the TRV gets the target again.
    await _room_temp(hass, freezer, 21.2)
    assert not room.heat_demand
    assert calls[-1].data["temperature"] == 21.0
    assert hass.states.get("sensor.office_decision").attributes["trv_boost"]["active"] is False
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_trv_boost_temperature_frost_and_pause(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """The chosen boost temperature, also for frost protection; a pause takes it back."""
    trv = {"hvac_modes": ["heat", "off"], "current_temperature": 22.0, "temperature": 21.0}
    hass.states.async_set("climate.trv", "heat", trv)
    hass.states.async_set("sensor.office_temp", "20.0", {"unit_of_measurement": "°C"})
    calls = async_mock_service(hass, "climate", "set_temperature")
    entry = await _boost_house(hass, freezer, {"trv_boost_temperature": 23.0})
    await _tick(hass, freezer, 15)
    room = next(iter(entry.runtime_data.rooms.values()))
    assert calls[-1].data["temperature"] == 23.0
    # A level above the boost temperature is sent as it is (never below the target).
    room.levels["home"] = 24.0
    await _room_temp(hass, freezer, 20.0)
    assert calls[-1].data["temperature"] == 24.0
    room.levels["home"] = 21.0
    await _room_temp(hass, freezer, 20.0)
    assert calls[-1].data["temperature"] == 23.0
    # A pause sends nothing, but the boost left on the TRV is taken back to the target.
    hass.states.async_set("climate.trv", "heat", {**trv, "temperature": 23.0})
    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": "switch.home_pause"}, blocking=True
    )
    await hass.async_block_till_done()
    assert calls[-1].data["temperature"] == 21.0
    count = len(calls)
    await _room_temp(hass, freezer, 19.0)
    assert len(calls) == count  # nothing more while paused
    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": "switch.home_pause"}, blocking=True
    )
    await hass.async_block_till_done()
    # Mode off: frost protection (7 °C); the room at 6 °C asks for heat and is boosted.
    await hass.services.async_call(
        "select", "select_option", {"entity_id": "select.home_mode", "option": "off"}, blocking=True
    )
    await hass.async_block_till_done()
    assert calls[-1].data["temperature"] == 7.0  # the room at 19 °C: no demand
    hass.states.async_set("climate.trv", "heat", {**trv, "temperature": 7.0})
    await _room_temp(hass, freezer, 6.0)
    assert room.heat_demand
    assert calls[-1].data["temperature"] == 23.0
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_frost_protection_from_the_room_sensor_opens_the_trv(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """A TRV reading warmer than the room is boosted for frost protection."""
    assert await async_setup_component(hass, "input_boolean", {"input_boolean": {"boiler": {}}})
    # The room at 5 °C, the TRV next to the radiator at 8 °C: idle at 7 °C.
    trv = {"hvac_modes": ["heat", "off"], "current_temperature": 8.0, "temperature": 7.0,
           "hvac_action": "idle"}
    hass.states.async_set("climate.trv", "heat", trv)
    hass.states.async_set("sensor.office_temp", "5.0", {"unit_of_measurement": "°C"})
    calls = async_mock_service(hass, "climate", "set_temperature")
    entry = await _boost_house(
        hass, freezer, {"trv_boost": False}, boiler_entity="input_boolean.boiler"
    )
    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": "switch.home_pause"}, blocking=True
    )
    await _tick(hass, freezer, 15)
    room = next(iter(entry.runtime_data.rooms.values()))
    assert hass.states.get("sensor.office_decision").state == "frost_protection"
    assert room.heat_demand and room.frost_demand
    assert calls[-1].data["temperature"] == 25.0  # the maximum of the house opens the TRV
    assert hass.states.get("input_boolean.boiler").state == "on"
    hass.states.async_set("climate.trv", "heat", {**trv, "temperature": 25.0})
    # Up to frost protection + hysteresis (7 + 0.2) it goes on, then 7 °C again.
    await _room_temp(hass, freezer, 7.1)
    assert room.frost_demand
    await _room_temp(hass, freezer, 7.2)
    assert not room.heat_demand
    assert calls[-1].data["temperature"] == 7.0
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_device_change_in_a_pause_is_kept(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """A change made on the thermostat in a pause applies after the pause."""
    trv = {"hvac_modes": ["heat", "off"], "current_temperature": 20.0, "temperature": 21.0,
           "hvac_action": "idle"}
    hass.states.async_set("climate.trv", "heat", trv)
    entry = await _trv_house(hass, freezer, boiler_entity=None)
    calls = async_mock_service(hass, "climate", "set_temperature")
    await _tick(hass, freezer, 15)
    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": "switch.home_pause"}, blocking=True
    )
    await hass.async_block_till_done()
    # A person sets 23 °C on the TRV during the pause.
    hass.states.async_set("climate.trv", "heat", {**trv, "temperature": 23.0}, context=Context())
    await hass.async_block_till_done()
    room = next(iter(entry.runtime_data.rooms.values()))
    assert room.override is not None
    count = len(calls)
    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": "switch.home_pause"}, blocking=True
    )
    await hass.async_block_till_done()
    assert hass.states.get("sensor.office_decision").state == "manual_override"
    assert len(calls) == count  # the 23 °C set by hand is not overwritten
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_clear_override_of_an_unknown_room(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """A room that does not exist gives an error; without a room every room is cleared."""
    entry = await _setup(hass, freezer)
    await _tick(hass, freezer, 15)
    with pytest.raises(ServiceValidationError) as err:
        await hass.services.async_call(
            DOMAIN, "clear_override", {"room": "Nowhere"}, blocking=True
        )
    assert err.value.translation_key == "room_not_found"
    await hass.services.async_call(DOMAIN, "clear_override", {}, blocking=True)
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_calibration_entity_with_a_value_that_is_not_a_number(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """A calibration entity that is not a number is skipped; the room is still evaluated."""
    trv = {"hvac_modes": ["heat", "off"], "current_temperature": 20.0, "temperature": 21.0,
           "hvac_action": "heating"}
    hass.states.async_set("climate.trv", "heat", trv)
    hass.states.async_set("sensor.office_temp", "19.0", {"unit_of_measurement": "°C"})
    hass.states.async_set("number.trv_calibration", "abc", {"min": -5, "max": 5, "step": 0.1})
    async_mock_service(hass, "climate", "set_temperature")
    entry = await _boost_house(
        hass,
        freezer,
        {
            "trv_boost": False,
            "calibration_mode": "offset",
            "calibration_entities": ["number.trv_calibration"],
        },
    )
    await _tick(hass, freezer, 15)
    room = next(iter(entry.runtime_data.rooms.values()))
    assert room.heat_demand  # evaluated to the end (hvac_action heating)
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_a_sensor_that_stops_is_not_an_open_window(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """With two sensors, one that stops moves the mean: no window; a real drop still is one."""
    hass.states.async_set("sensor.room_temp_2", "22.0", {"unit_of_measurement": "°C"})
    entry = await _setup(
        hass,
        freezer,
        temperature_sensors=["sensor.room_temp", "sensor.room_temp_2"],
        window_drop_detect=True,
        window_drop_degrees=1.0,
        window_drop_minutes=3,
    )
    room = next(iter(entry.runtime_data.rooms.values()))
    await _tick(hass, freezer, 15)
    assert room.current_temp == 20.0  # mean of 18 and 22

    # The 22° sensor stops: the room is 18° now (2° less at once), not an open window.
    hass.states.async_set("sensor.room_temp_2", "unavailable")
    await _tick(hass, freezer, 30)
    assert room.current_temp == 18.0
    assert room._drop_until is None

    # It comes back, then the room really cools by 1.5° within 3 minutes: an open window.
    hass.states.async_set("sensor.room_temp_2", "22.0", {"unit_of_measurement": "°C"})
    await _tick(hass, freezer, 30)
    hass.states.async_set("sensor.room_temp", "16.5", {"unit_of_measurement": "°C"})
    hass.states.async_set("sensor.room_temp_2", "20.5", {"unit_of_measurement": "°C"})
    await _tick(hass, freezer, 60)
    assert room.current_temp == 18.5  # mean of 16.5 and 20.5, 1.5° below 20
    assert room._drop_until is not None

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def _read_falling(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, room, minutes: int, every: int = 5
) -> None:
    """Read the room every ``every`` seconds while it falls evenly from 20° to 19°."""
    steps = minutes * 60 // every
    for i in range(steps + 1):
        freezer.tick(timedelta(seconds=every))
        value = round(20.0 - i / steps, 1)
        hass.states.async_set("sensor.room_temp", f"{value}", {"unit_of_measurement": "°C"})
        await hass.async_block_till_done()
        room._update_temperature(dt_util.utcnow())  # a reading on every step, as in a busy house


async def test_long_drop_window_with_many_readings(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """1° in 25 minutes with a 30-minute window is an open window, however often it is read."""
    entry = await _setup(
        hass, freezer, window_drop_detect=True, window_drop_degrees=1.0, window_drop_minutes=30
    )
    room = next(iter(entry.runtime_data.rooms.values()))
    await _tick(hass, freezer, 15)
    # 301 readings in 25 minutes (more than the 120 kept before by count).
    await _read_falling(hass, freezer, room, 25)
    assert room.current_temp == 19.0
    assert room._drop_until is not None
    # Only the readings of the window (plus 15 minutes) are kept, as runs of one value.
    assert len(room._temp_samples) <= 13

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_slow_drop_is_not_an_open_window(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """1° in 40 minutes with a 30-minute window: at most 0.8° in any 30 minutes, no window."""
    entry = await _setup(
        hass, freezer, window_drop_detect=True, window_drop_degrees=1.0, window_drop_minutes=30
    )
    room = next(iter(entry.runtime_data.rooms.values()))
    hass.states.async_set("sensor.room_temp", "20.0", {"unit_of_measurement": "°C"})
    await _tick(hass, freezer, 15)
    await _read_falling(hass, freezer, room, 40)
    assert room.current_temp == 19.0
    assert room._drop_until is None

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def _trv_room(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, trvs: dict[str, dict], **room: object
) -> MockConfigEntry:
    """A house with one room of TRVs (temperature commands), no room sensor."""
    await hass.config.async_set_time_zone("Europe/Bucharest")
    freezer.move_to("2026-10-12 09:00:00+00:00")
    for entity_id, attrs in trvs.items():
        hass.states.async_set(entity_id, "heat", attrs)
    hass.states.async_set("person.andrei", "home")
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Home",
        options={"persons": ["person.andrei"], "nearby_zones": []},
        subentries_data=[
            {
                "data": {
                    "source": "climate",
                    "climates": list(trvs),
                    "command_mode": "temperature",
                    **room,
                },
                "subentry_type": SUBENTRY_ROOM,
                "title": "Office",
                "unique_id": None,
            }
        ],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_a_trv_that_stops_is_not_an_open_window(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Without a room sensor, two TRVs (22 and 19 °C) give 20.5; one stopping is no window."""
    async_mock_service(hass, "climate", "set_temperature")
    base = {"hvac_modes": ["heat", "off"], "temperature": 21.0}
    entry = await _trv_room(
        hass,
        freezer,
        {
            "climate.trv_1": {**base, "current_temperature": 22.0},
            "climate.trv_2": {**base, "current_temperature": 19.0},
        },
        window_drop_detect=True,
        window_drop_degrees=1.0,
        window_drop_minutes=3,
    )
    room = next(iter(entry.runtime_data.rooms.values()))
    await _tick(hass, freezer, 15)
    assert room.current_temp == 20.5

    hass.states.async_set("climate.trv_1", "unavailable")
    await _tick(hass, freezer, 30)
    assert room.current_temp == 19.0
    assert room._drop_until is None

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_an_older_command_reported_late_is_not_manual(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """21 °C is sent, then another value; the TRV reports the 21 only afterwards: no manual change."""
    calls = async_mock_service(hass, "climate", "set_temperature")
    trv = {"hvac_modes": ["heat", "off"], "current_temperature": 18.0, "temperature": 17.0,
           "target_temp_step": 0.5}
    entry = await _trv_room(hass, freezer, {"climate.trv": trv})
    await _tick(hass, freezer, 15)
    assert calls[-1].data["temperature"] == 21.0

    # A change from the card for two hours: 23 °C is sent.
    await hass.services.async_call(
        DOMAIN, "set_override", {"room": "Office", "temperature": 23, "duration_hours": 2},
        blocking=True,
    )
    await _tick(hass, freezer, 5)
    assert calls[-1].data["temperature"] == 23.0
    # Only now the TRV reports the 21 sent before (a sleepy device, its own context).
    hass.states.async_set("climate.trv", "heat", {**trv, "temperature": 21.0}, context=Context())
    await _tick(hass, freezer, 5)
    override = hass.states.get("binary_sensor.office_manual_change").attributes
    # The change from the card stays, with its duration (not one "on the device").
    assert override["origin"] == "card"
    assert override["until"] is not None

    # The TRV then shows 23 (the command sent again); once it has kept it, 21 set
    # by hand is a person's change again.
    hass.states.async_set("climate.trv", "heat", {**trv, "temperature": 23.0}, context=Context())
    await _tick(hass, freezer, 6 * 60)
    hass.states.async_set("climate.trv", "heat", {**trv, "temperature": 21.0}, context=Context())
    await _tick(hass, freezer, 5)
    override = hass.states.get("binary_sensor.office_manual_change").attributes
    assert override["origin"] == "device"

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_older_values_forgotten_once_the_last_is_confirmed(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Once the TRV reports the last command, an older value set by hand is a manual change."""
    calls = async_mock_service(hass, "climate", "set_temperature")
    trv = {"hvac_modes": ["heat", "off"], "current_temperature": 18.0, "temperature": 17.0,
           "target_temp_step": 0.5}
    entry = await _trv_room(hass, freezer, {"climate.trv": trv})
    await _tick(hass, freezer, 15)
    assert calls[-1].data["temperature"] == 21.0
    await hass.services.async_call(
        DOMAIN, "set_override", {"room": "Office", "temperature": 23, "duration_hours": 2},
        blocking=True,
    )
    await _tick(hass, freezer, 5)
    assert calls[-1].data["temperature"] == 23.0
    # The TRV confirms 23 (the last command) ...
    hass.states.async_set("climate.trv", "heat", {**trv, "temperature": 23.0}, context=Context())
    await _tick(hass, freezer, 5)
    assert hass.states.get("binary_sensor.office_manual_change").attributes["origin"] == "card"
    # ... and keeps it for a minute: then 21 set by hand is a person's change,
    # not the old command.
    await _tick(hass, freezer, 125)
    hass.states.async_set("climate.trv", "heat", {**trv, "temperature": 21.0}, context=Context())
    await _tick(hass, freezer, 5)
    override = hass.states.get("binary_sensor.office_manual_change").attributes
    assert override["origin"] == "device"
    assert override["description"] == "21.0 °C"

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_a_trv_that_bounces_back_once_is_not_manual(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """A TRV shows the new value at once, then reports the old one once more (Tuya TS0601)."""
    calls = async_mock_service(hass, "climate", "set_temperature")
    trv = {"hvac_modes": ["heat", "off"], "current_temperature": 18.0, "temperature": 17.0,
           "target_temp_step": 0.5}
    entry = await _trv_room(hass, freezer, {"climate.trv": trv})
    await _tick(hass, freezer, 15)
    assert calls[-1].data["temperature"] == 21.0
    hass.states.async_set("climate.trv", "heat", {**trv, "temperature": 21.0}, context=Context())
    await _tick(hass, freezer, 300)  # 21 confirmed long ago
    await hass.services.async_call(
        DOMAIN, "set_override", {"room": "Office", "temperature": 12, "duration_hours": 2},
        blocking=True,
    )
    await _tick(hass, freezer, 5)
    assert calls[-1].data["temperature"] == 12.0
    # 12 shown at once, then the old 21 once more, then 12 again.
    for value in (12.0, 21.0, 12.0):
        hass.states.async_set("climate.trv", "heat", {**trv, "temperature": value}, context=Context())
        await _tick(hass, freezer, 10)
    override = hass.states.get("binary_sensor.office_manual_change").attributes
    assert override["origin"] == "card"
    assert override["until"] is not None

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_a_level_named_like_another_level_keeps_the_schedule(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Eco named "home" (saved before the form refused it) does not turn home into eco."""
    entry = await _setup(hass, freezer, preset_names={"home": "Acasă", "eco": "home"})
    await _tick(hass, freezer, 15)
    decision = hass.states.get("sensor.bedroom_decision")
    # Monday noon: the default schedule has home.
    assert decision.attributes["preset"] == "home"
    assert hass.states.get("sensor.bedroom_target_temperature").state == "21.0"

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_turned_off_by_hand_right_after_on_is_manual(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """The integration turns a TRV on; a person turns it off within the minute: manual."""
    async_mock_service(hass, "climate", "set_temperature")
    modes = async_mock_service(hass, "climate", "set_hvac_mode")
    trv = {"hvac_modes": ["heat", "off"], "current_temperature": 18.0, "temperature": 21.0}
    hass.states.async_set("climate.trv", "off", trv)
    entry = await _trv_room(hass, freezer, {"climate.trv": trv})
    hass.states.async_set("climate.trv", "off", trv)
    await _tick(hass, freezer, 15)
    assert modes and modes[-1].data["hvac_mode"] == "heat"
    hass.states.async_set("climate.trv", "heat", trv, context=Context())
    await _tick(hass, freezer, 10)
    assert hass.states.get("binary_sensor.office_manual_change").state == "off"
    # Turned off by hand 20 seconds later: respected as a manual change.
    hass.states.async_set("climate.trv", "off", trv, context=Context())
    await _tick(hass, freezer, 10)
    override = hass.states.get("binary_sensor.office_manual_change").attributes
    assert override["origin"] == "device"
    assert override["description"] == "turned off"

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_guests_suspend_every_vacation(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """A planned vacation and the vacation mode wait while guest mode is on."""
    entry = await _setup(hass, freezer)
    await _tick(hass, freezer, 15)
    end = dt_util.now() + timedelta(days=3)
    await hass.services.async_call(DOMAIN, "set_vacation", {"end": end}, blocking=True)
    await hass.async_block_till_done()
    assert hass.states.get("sensor.bedroom_decision").state == "vacation"

    async def guests(on: bool) -> None:
        await hass.services.async_call(
            "switch", "turn_on" if on else "turn_off", {"entity_id": "switch.home_guest_mode"},
            blocking=True,
        )
        await hass.async_block_till_done()

    # Guests: the schedule (home at noon); the vacation waits.
    await guests(True)
    assert hass.states.get("sensor.bedroom_decision").state == "schedule"
    presence = hass.states.get("sensor.home_presence").attributes
    assert presence["vacation_active"] is False
    assert presence["vacation_suspended"] is True
    # Guests gone: the vacation goes on, with its dates.
    await guests(False)
    assert hass.states.get("sensor.bedroom_decision").state == "vacation"

    # The same with the vacation mode.
    await hass.services.async_call(DOMAIN, "set_vacation", {}, blocking=True)
    await hass.services.async_call(
        "select", "select_option", {"entity_id": "select.home_mode", "option": "vacation"},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert hass.states.get("sensor.bedroom_decision").state == "vacation"
    await guests(True)
    assert hass.states.get("sensor.bedroom_decision").state == "schedule"
    await guests(False)
    assert hass.states.get("sensor.bedroom_decision").state == "vacation"

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_automatic_vacation_goes_on_after_the_guests(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Guests suspend the automatic vacation; after them it goes on at once."""
    entry = await _setup(hass, freezer)
    entry.runtime_data.options["auto_vacation_hours"] = 1.0
    await _tick(hass, freezer, 15)
    hass.states.async_set("person.andrei", "not_home")
    await _tick(hass, freezer, 11 * 60)
    await _tick(hass, freezer, 3600)
    assert hass.states.get("sensor.bedroom_decision").state == "vacation"

    async def guests(on: bool) -> None:
        await hass.services.async_call(
            "switch", "turn_on" if on else "turn_off", {"entity_id": "switch.home_guest_mode"},
            blocking=True,
        )
        await hass.async_block_till_done()

    await guests(True)
    assert hass.states.get("sensor.bedroom_decision").state == "schedule"
    assert hass.states.get("sensor.home_presence").attributes["vacation_suspended"] is True
    await _tick(hass, freezer, 2 * 3600)
    await guests(False)
    assert hass.states.get("sensor.home_presence").state == "far"
    assert hass.states.get("sensor.bedroom_decision").state == "vacation"

    # Someone of the people comes by while guests are there and leaves again:
    # after the guests the automatic vacation comes back all the same.
    await guests(True)
    hass.states.async_set("person.andrei", "home")
    await _tick(hass, freezer, 30)
    hass.states.async_set("person.andrei", "not_home")
    await _tick(hass, freezer, 30)
    await guests(False)
    assert hass.states.get("sensor.bedroom_decision").state == "vacation"
    # Someone of the people is home when the guests leave: no vacation.
    await guests(True)
    hass.states.async_set("person.andrei", "home")
    await _tick(hass, freezer, 30)
    await guests(False)
    assert hass.states.get("sensor.bedroom_decision").state == "schedule"

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_trv_limit_is_not_a_manual_change(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """The TRV applies its own maximum (25) to a boost of 28: a limit, not a manual change."""
    trv = {"hvac_modes": ["heat", "off"], "current_temperature": 23.0, "temperature": 21.0,
           "max_temp": 35.0, "target_temp_step": 0.5}
    hass.states.async_set("climate.trv", "heat", trv)
    hass.states.async_set("sensor.office_temp", "20.9", {"unit_of_measurement": "°C"})
    calls = async_mock_service(hass, "climate", "set_temperature")
    # A house maximum of 30 °C, so the boost of 28 °C is sent as it is.
    entry = await _boost_house(hass, freezer, {"trv_boost_temperature": 28}, max_temp=30)
    room = next(iter(entry.runtime_data.rooms.values()))
    await _tick(hass, freezer, 15)
    await _room_temp(hass, freezer, 20.8)
    assert calls[-1].data["temperature"] == 28.0
    # The TRV holds 25 (its own Max temperature), with its own context.
    hass.states.async_set("climate.trv", "heat", {**trv, "temperature": 25.0}, context=Context())
    await _tick(hass, freezer, 5)
    assert hass.states.get("binary_sensor.office_manual_change").state == "off"
    assert any(a["code"] == "device_limit_max" for a in room.house.alerts_for(room))
    # The demand ends (the target again), then the next boost is sent within the limit.
    await _room_temp(hass, freezer, 21.2)
    assert calls[-1].data["temperature"] == 21.0
    hass.states.async_set("climate.trv", "heat", {**trv, "temperature": 21.0}, context=Context())
    await _tick(hass, freezer, 5)
    await _room_temp(hass, freezer, 20.8)
    assert calls[-1].data["temperature"] == 25.0
    assert hass.states.get("binary_sensor.office_manual_change").state == "off"

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


@pytest.mark.parametrize("after", [30, 10 * 60, 60 * 60])
async def test_lower_value_after_an_accepted_boost_is_a_manual_change(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, after: int
) -> None:
    """The TRV showed the boost (28), then a person turns it to 23: a manual change.

    It accepted 28, so 23 is not its maximum: no limit is learned, no alert.
    Tried 30 seconds, 10 minutes and 1 hour after the TRV showed 28.
    """
    trv = {"hvac_modes": ["heat", "off"], "current_temperature": 23.0, "temperature": 21.0,
           "max_temp": 35.0, "target_temp_step": 0.5}
    hass.states.async_set("climate.trv", "heat", trv)
    hass.states.async_set("sensor.office_temp", "20.9", {"unit_of_measurement": "°C"})
    calls = async_mock_service(hass, "climate", "set_temperature")
    entry = await _boost_house(hass, freezer, {"trv_boost_temperature": 28}, max_temp=30)
    room = next(iter(entry.runtime_data.rooms.values()))
    await _tick(hass, freezer, 15)
    await _room_temp(hass, freezer, 20.8)
    assert calls[-1].data["temperature"] == 28.0
    hass.states.async_set("climate.trv", "heat", {**trv, "temperature": 28.0}, context=Context())
    await _tick(hass, freezer, after)
    hass.states.async_set("climate.trv", "heat", {**trv, "temperature": 23.0}, context=Context())
    await _tick(hass, freezer, 5)
    assert hass.states.get("binary_sensor.office_manual_change").state == "on"
    assert not any(a["code"] == "device_limit_max" for a in room.house.alerts_for(room))
    assert room._device_limits.get("climate.trv", {}).get("max") is None

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_higher_value_after_accepted_frost_is_a_manual_change(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Mode Off sends frost protection (7), the TRV shows it, then a person sets 10.

    10 is below the lowest level (away, 12 by default), but the TRV accepted 7:
    a manual change, not its minimum.
    """
    trv = {"hvac_modes": ["heat"], "current_temperature": 21.0, "temperature": 21.0,
           "max_temp": 35.0, "min_temp": 5.0, "target_temp_step": 0.5}
    hass.states.async_set("climate.trv", "heat", trv)
    hass.states.async_set("sensor.office_temp", "21.5", {"unit_of_measurement": "°C"})
    calls = async_mock_service(hass, "climate", "set_temperature")
    entry = await _boost_house(hass, freezer, {})
    room = next(iter(entry.runtime_data.rooms.values()))
    await hass.services.async_call(
        "select", "select_option", {"entity_id": "select.home_mode", "option": "off"},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert calls[-1].data["temperature"] == 7.0
    hass.states.async_set("climate.trv", "heat", {**trv, "temperature": 7.0}, context=Context())
    await _tick(hass, freezer, 60)
    hass.states.async_set("climate.trv", "heat", {**trv, "temperature": 10.0}, context=Context())
    await _tick(hass, freezer, 5)
    assert not any(a["code"] == "device_limit_min" for a in room.house.alerts_for(room))
    assert room._device_limits.get("climate.trv", {}).get("min") is None

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_trv_already_at_its_limit_is_learned_without_a_report(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """The TRV already holds 25 (its own maximum) when 28 is sent: no change is reported.

    The verification learns the limit instead of telling that it was not
    accepted, and 28 is no longer sent again and again.
    """
    trv = {"hvac_modes": ["heat", "off"], "current_temperature": 23.0, "temperature": 25.0,
           "max_temp": 35.0, "target_temp_step": 0.5}
    hass.states.async_set("climate.trv", "heat", trv)
    hass.states.async_set("sensor.office_temp", "20.8", {"unit_of_measurement": "°C"})
    calls = async_mock_service(hass, "climate", "set_temperature")
    entry = await _boost_house(hass, freezer, {"trv_boost_temperature": 28}, max_temp=30)
    room = next(iter(entry.runtime_data.rooms.values()))
    await _tick(hass, freezer, 15)
    assert calls[-1].data["temperature"] == 28.0
    # The first check (2 minutes later) sends it again (the TRV may just be slow);
    # the second one sees 25 still held: a limit, learned instead of the alert.
    await _tick(hass, freezer, 125)
    assert not any(a["code"] == "device_limit_max" for a in room.house.alerts_for(room))
    await _tick(hass, freezer, 125)
    assert any(a["code"] == "device_limit_max" for a in room.house.alerts_for(room))
    sent = len(calls)
    assert not any(a["code"] == "not_accepted" for a in room.house.alerts_for(room))
    # Nothing more is sent while the TRV holds its limit.
    for _ in range(3):
        await _room_temp(hass, freezer, 20.8)
    assert len(calls) == sent
    assert hass.states.get("binary_sensor.office_manual_change").state == "off"

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
