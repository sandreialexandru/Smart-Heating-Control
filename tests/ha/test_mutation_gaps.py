"""Places the mutation tests showed without a test (2.6.4): the end of the
heating-without-effect alert, its text in °F, the long open window outside the
heating, the text of unavailable sensors, a room on a schedule helper, two
scenarios that both match, the Repairs issues of scenarios, and the humidity
range of the mold alert."""

from __future__ import annotations

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.util.unit_system import US_CUSTOMARY_SYSTEM
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.advanced_climate.const import DOMAIN, SUBENTRY_SCENARIO
from custom_components.advanced_climate.learning import ThermalLearner, ThermalModel
from tests.ha.test_ha_devices import _house, _unload
from tests.ha.test_ha_setup import _setup, _tick
from tests.ha.test_scenarios import _choose
from tests.ha.test_scenarios import _setup as _scenario_setup

TEMP = {"unit_of_measurement": "°C"}


def _learned(room, monkeypatch: pytest.MonkeyPatch) -> None:
    """A learned model that stays as it is (no learning from the test)."""
    monkeypatch.setattr(ThermalLearner, "observe", lambda self, *a, **k: False)
    room.learner._model = ThermalModel(h=1.5, k=0.01, tau=0.0, learned=True)


async def _steady(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, minutes: int, value: str, unit=TEMP
) -> None:
    """The room sensor reports the same value every 10 minutes."""
    for _ in range(minutes // 10):
        hass.states.async_set("sensor.room_temp", value, unit)
        await _tick(hass, freezer, 600)


async def _no_effect_house(hass: HomeAssistant, freezer: FrozenDateTimeFactory, monkeypatch):
    hass.states.async_set("sensor.outdoor", "0.0", TEMP)
    entry = await _setup(
        hass,
        freezer,
        house_options={"alert_silent_hours": 0, "outdoor_sensor": "sensor.outdoor"},
    )
    house = entry.runtime_data
    room = next(iter(house.rooms.values()))
    _learned(room, monkeypatch)
    await _tick(hass, freezer, 15)
    return entry, house, room


# ---------------------------------------------------------------------------
# Heating without effect
# ---------------------------------------------------------------------------
async def test_no_effect_ends_when_the_target_comes_down_to_the_room(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The alert ends when the room is near its target, also without warming up."""
    entry, house, room = await _no_effect_house(hass, freezer, monkeypatch)
    key = f"no_effect_{room.id}"
    await _steady(hass, freezer, 150, "18.0")
    assert key in house.active_alerts
    # A lower target, just above the room: near it, over.
    await hass.services.async_call(
        DOMAIN, "set_override", {"room": "Bedroom", "temperature": 18.2}, blocking=True
    )
    await _steady(hass, freezer, 10, "18.0")
    assert key not in house.active_alerts
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_no_effect_ends_when_turned_off_in_the_options(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Hours set to 0 while it is told: the alert ends at once."""
    entry, house, room = await _no_effect_house(hass, freezer, monkeypatch)
    key = f"no_effect_{room.id}"
    await _steady(hass, freezer, 150, "18.0")
    assert key in house.active_alerts
    house.options["alert_no_effect_hours"] = 0
    await _steady(hass, freezer, 10, "18.0")
    assert key not in house.active_alerts
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_no_effect_not_watched_just_below_the_target(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Less than half a degree below the target: heating, but not watched."""
    entry, house, room = await _no_effect_house(hass, freezer, monkeypatch)
    await hass.services.async_call(
        DOMAIN,
        "set_override",
        {"room": "Bedroom", "temperature": 23, "duration_hours": 6},
        blocking=True,
    )
    await _steady(hass, freezer, 180, "22.6")
    assert room.heating
    assert f"no_effect_{room.id}" not in house.active_alerts
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_no_effect_text_in_fahrenheit(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """In a house in °F the rise and the expected rise are told in °F."""
    hass.config.units = US_CUSTOMARY_SYSTEM
    fahrenheit = {"unit_of_measurement": "°F"}
    hass.states.async_set("sensor.outdoor", "32.0", fahrenheit)
    hass.states.async_set("sensor.room_temp", "64.4", fahrenheit)
    entry = await _setup(
        hass,
        freezer,
        house_options={"alert_silent_hours": 0, "outdoor_sensor": "sensor.outdoor"},
    )
    house = entry.runtime_data
    room = next(iter(house.rooms.values()))
    _learned(room, monkeypatch)
    await _tick(hass, freezer, 15)
    # 64.4 °F (18 °C) for a while, then 64.76 °F: a rise of 0.2 °C, 0.36 °F.
    await _steady(hass, freezer, 60, "64.4", fahrenheit)
    await _steady(hass, freezer, 70, "64.76", fahrenheit)
    alert = house.active_alerts[f"no_effect_{room.id}"]
    expected_c = float(alert["params"]["expected"]) / 1.8
    assert alert["params"]["rise"] == "0.4"
    # The model expects well over the 0.3 °C minimum; told in °F it is 1.8 times larger.
    assert expected_c > 0.3
    assert f"{expected_c * 1.8:.1f}" == alert["params"]["expected"]
    assert "°" in alert["message"]
    assert await hass.config_entries.async_unload(entry.entry_id)


# ---------------------------------------------------------------------------
# Long open window, unavailable sensors, schedule helper
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("mode", ["summer", "off"])
async def test_long_open_window_not_told_without_heating(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, mode: str
) -> None:
    """In summer or with the heating off a long open window is not told."""
    hass.states.async_set("binary_sensor.window", "off")
    entry = await _setup(hass, freezer, window_sensors=["binary_sensor.window"])
    house = entry.runtime_data
    room = next(iter(house.rooms.values()))
    await hass.services.async_call(
        "select", "select_option", {"entity_id": "select.home_mode", "option": mode}, blocking=True
    )
    hass.states.async_set("binary_sensor.window", "on")
    for _ in range(45):
        await _tick(hass, freezer, 60)
    assert room.window_open
    assert f"window_{room.id}" not in house.active_alerts
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_unavailable_sensor_text_names_the_fallback(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """A TRV room uses the sensor of its TRV; a relay room has none and goes to eco."""
    async_mock_service(hass, "climate", "set_temperature")
    hass.states.async_set(
        "climate.trv",
        "heat",
        {"hvac_modes": ["heat", "off"], "current_temperature": 19.0, "temperature": 21.0},
    )
    hass.states.async_set("sensor.office_temp", "unavailable")
    entry = await _house(
        hass,
        freezer,
        [
            (
                "Office",
                {
                    "source": "climate",
                    "climates": ["climate.trv"],
                    "command_mode": "temperature",
                    "temperature_sensors": ["sensor.office_temp"],
                },
            )
        ],
    )
    house = entry.runtime_data
    room = next(iter(house.rooms.values()))
    await _tick(hass, freezer, 310)
    alert = house.active_alerts[f"sensor_{room.id}"]
    assert alert["params"]["fallback"] == "device"
    assert "using the device sensor" in alert["message"]
    await _unload(hass, entry)


async def test_unavailable_sensor_of_a_relay_room_goes_to_eco(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """A relay room has no sensor of its own: eco, and the text says so."""
    entry = await _setup(hass, freezer)
    house = entry.runtime_data
    room = next(iter(house.rooms.values()))
    hass.states.async_set("sensor.room_temp", "unavailable")
    await _tick(hass, freezer, 310)
    alert = house.active_alerts[f"sensor_{room.id}"]
    assert alert["params"]["fallback"] == "eco"
    assert "using eco" in alert["message"]
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_no_gap_alert_for_a_room_on_a_schedule_helper(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """The profiles of the room do not count while a schedule helper gives its schedule."""
    async_mock_service(hass, "climate", "set_temperature")
    hass.states.async_set(
        "climate.trv",
        "heat",
        {"hvac_modes": ["heat", "off"], "current_temperature": 19.0, "temperature": 21.0},
    )
    hass.states.async_set("schedule.heating", "on", {"next_event": "2026-10-12T15:00:00+03:00"})
    entry = await _house(
        hass,
        freezer,
        [
            (
                "Office",
                {
                    "source": "climate",
                    "climates": ["climate.trv"],
                    "command_mode": "temperature",
                    "schedule_source": "helper",
                    "schedule_helper": "schedule.heating",
                    # Only workdays: the weekend would be a gap with its own schedule.
                    "schedule": "workday: 00:00 sleep, 07:00 home",
                    "profile_days": {"workday": {"days": "workday", "enabled": True}},
                },
            )
        ],
    )
    house = entry.runtime_data
    room = next(iter(house.rooms.values()))
    await _tick(hass, freezer, 310)
    assert f"schedule_gap_{room.id}" not in house.active_alerts
    await _unload(hass, entry)


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------
async def test_two_matching_scenarios_of_the_same_size_the_first_is_shown(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Both on, each with one profile: the one added first is shown."""
    await _scenario_setup(
        hass,
        freezer,
        [
            {"title": "Office works", "rooms": {"Office": ["home_office"]}},
            {"title": "Bedroom works", "rooms": {"Bedroom": ["home_office"]}},
        ],
    )
    await _tick(hass, freezer, 15)
    await _choose(hass, "Bedroom works")
    await _choose(hass, "Office works")
    await _tick(hass, freezer, 15)
    assert hass.states.get("select.home_scenario").state == "Office works"
    # The other way round: still the first added.
    await _choose(hass, "Bedroom works")
    await _tick(hass, freezer, 15)
    assert hass.states.get("select.home_scenario").state == "Office works"


async def test_repairs_issue_goes_with_its_scenario_and_its_house(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """A scenario deleted with its problem leaves no issue; nor does a deleted house."""
    entry = await _scenario_setup(
        hass,
        freezer,
        [
            {"title": "Broken", "rooms": {"Bedroom": ["no_such"]}},
            {"title": "Broken too", "rooms": {"Office": ["no_such"]}},
        ],
    )
    await _tick(hass, freezer, 15)
    subs = {s.title: s.subentry_id for s in entry.subentries.values()}
    issues = ir.async_get(hass)
    first = f"scenario_{entry.entry_id}_{subs['Broken']}"
    second = f"scenario_{entry.entry_id}_{subs['Broken too']}"
    assert issues.async_get_issue(DOMAIN, first) is not None
    assert issues.async_get_issue(DOMAIN, second) is not None
    # Deleted with its problem still there: its issue goes, the other stays.
    hass.config_entries.async_remove_subentry(entry, subs["Broken"])
    await hass.async_block_till_done()
    await _tick(hass, freezer, 15)
    assert issues.async_get_issue(DOMAIN, first) is None
    assert issues.async_get_issue(DOMAIN, second) is not None
    assert all(
        s.subentry_type != SUBENTRY_SCENARIO or s.title != "Broken"
        for s in entry.subentries.values()
    )
    # The house deleted: no issue of it left.
    assert await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert issues.async_get_issue(DOMAIN, second) is None


# ---------------------------------------------------------------------------
# Mold: the humidity range
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("value", "used"), [("0", 0.0), ("100", 100.0), ("101", None), ("-1", None)]
)
async def test_mold_humidity_range(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, value: str, used: float | None
) -> None:
    """A humidity from 0 to 100 % is used; outside it, ignored (no wall humidity)."""
    hass.states.async_set("sensor.outdoor", "0.0", TEMP)
    hass.states.async_set("sensor.room_humidity", value, {"unit_of_measurement": "%"})
    entry = await _setup(
        hass,
        freezer,
        house_options={"outdoor_sensor": "sensor.outdoor"},
        humidity_sensor="sensor.room_humidity",
    )
    await _tick(hass, freezer, 15)
    attrs = hass.states.get("sensor.bedroom_decision").attributes
    assert attrs["humidity"] == used
    assert (attrs["surface_humidity"] is None) == (used is None)
    assert await hass.config_entries.async_unload(entry.entry_id)
