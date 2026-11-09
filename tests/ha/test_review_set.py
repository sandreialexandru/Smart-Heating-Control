"""A review of what users ask about: the TRV mode and its own schedule, the child
lock, travel time without a value, the away mode on the way home, a silent TRV
and heating without effect in a pause."""

from __future__ import annotations

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import Context, HomeAssistant
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.advanced_climate.learning import ThermalLearner, ThermalModel
from tests.ha.test_ha_devices import _house, _room, _tick, _unload
from tests.ha.test_ha_setup import _setup

# A TRV with a schedule of its own (Sonoff TRVZB, Zigbee2MQTT): heat, auto, off.
TRV_AUTO = {
    "hvac_modes": ["heat", "auto", "off"],
    "current_temperature": 19.0,
    "temperature": 17.0,
    "min_temp": 5.0,
    "max_temp": 30.0,
}
MINUTES = {"unit_of_measurement": "min"}


async def _trv(hass: HomeAssistant, freezer: FrozenDateTimeFactory, state: str = "heat", **room):
    """A room with one TRV driven by temperature; returns the entry and the calls."""
    calls = {
        service: async_mock_service(hass, "climate", service)
        for service in ("set_temperature", "set_hvac_mode")
    }
    hass.states.async_set("climate.trv", state, TRV_AUTO)
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
                    **room,
                },
            )
        ],
    )
    return entry, calls


async def test_trv_switched_to_auto_by_hand_is_a_manual_change(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Auto on the TRV (its own schedule) chosen by a person: a manual change, respected."""
    entry, calls = await _trv(hass, freezer)
    assert calls["set_temperature"][-1].data["temperature"] == 21.0
    # The TRV confirms the temperature sent, then a person chooses auto.
    hass.states.async_set("climate.trv", "heat", {**TRV_AUTO, "temperature": 21.0}, Context())
    await _tick(hass, freezer, 5)
    assert hass.states.get("sensor.office_decision").state != "manual_override"
    hass.states.async_set("climate.trv", "auto", {**TRV_AUTO, "temperature": 21.0}, Context())
    await _tick(hass, freezer, 5)
    decision = hass.states.get("sensor.office_decision")
    assert decision.state == "manual_override"
    # Respected: the mode is not changed back.
    assert not any(c.data.get("hvac_mode") == "heat" for c in calls["set_hvac_mode"])
    await _unload(hass, entry)


async def test_trv_turned_off_by_hand_comes_back_with_the_child_lock(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """With the child lock, a TRV turned off by hand is turned on again and set back."""
    entry, calls = await _trv(hass, freezer)
    await _room(entry, "Office").async_set_child_lock(True)
    hass.states.async_set("climate.trv", "off", {**TRV_AUTO, "temperature": 21.0}, Context())
    await _tick(hass, freezer, 5)
    assert hass.states.get("sensor.office_decision").state != "manual_override"
    assert calls["set_hvac_mode"][-1].data == {"entity_id": "climate.trv", "hvac_mode": "heat"}
    assert calls["set_temperature"][-1].data == {"entity_id": "climate.trv", "temperature": 21.0}
    await _unload(hass, entry)


async def test_trv_left_in_auto_is_put_in_heat(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """With the Temperature command a TRV found in auto (its own schedule) is put in heat."""
    entry, calls = await _trv(hass, freezer, state="auto")
    assert calls["set_hvac_mode"][-1].data == {"entity_id": "climate.trv", "hvac_mode": "heat"}
    assert calls["set_temperature"][-1].data == {"entity_id": "climate.trv", "temperature": 21.0}
    # It reports heat: nothing more to send, and not a manual change.
    sent = len(calls["set_hvac_mode"])
    hass.states.async_set("climate.trv", "heat", {**TRV_AUTO, "temperature": 21.0})
    await _tick(hass, freezer, 310)
    assert len(calls["set_hvac_mode"]) == sent
    assert hass.states.get("sensor.office_decision").state != "manual_override"
    await _unload(hass, entry)


async def test_auto_chosen_by_hand_is_put_back_in_heat_with_the_child_lock(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """With the child lock, auto chosen on the TRV is undone at once."""
    entry, calls = await _trv(hass, freezer)
    await _room(entry, "Office").async_set_child_lock(True)
    hass.states.async_set("climate.trv", "heat", {**TRV_AUTO, "temperature": 21.0}, Context())
    await _tick(hass, freezer, 5)
    hass.states.async_set("climate.trv", "auto", {**TRV_AUTO, "temperature": 21.0}, Context())
    await _tick(hass, freezer, 5)
    assert hass.states.get("sensor.office_decision").state != "manual_override"
    assert calls["set_hvac_mode"][-1].data == {"entity_id": "climate.trv", "hvac_mode": "heat"}
    await _unload(hass, entry)


async def test_auto_is_kept_with_the_preset_command_or_without_heat(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Presets may need auto, and a device with only auto heats in it: both left in auto."""
    calls = async_mock_service(hass, "climate", "set_hvac_mode")
    async_mock_service(hass, "climate", "set_temperature")
    async_mock_service(hass, "climate", "set_preset_mode")
    hass.states.async_set(
        "climate.netatmo",
        "auto",
        {
            **TRV_AUTO,
            "preset_modes": ["away", "frost_guard", "schedule"],
            "preset_mode": "schedule",
        },
    )
    hass.states.async_set("climate.only_auto", "auto", {**TRV_AUTO, "hvac_modes": ["auto", "off"]})
    entry = await _house(
        hass,
        freezer,
        [
            (
                "Hall",
                {"source": "climate", "climates": ["climate.netatmo"], "command_mode": "preset"},
            ),
            (
                "Attic",
                {
                    "source": "climate",
                    "climates": ["climate.only_auto"],
                    "command_mode": "temperature",
                },
            ),
        ],
    )
    await _tick(hass, freezer, 310)
    assert not any(c.data.get("hvac_mode") == "heat" for c in calls)
    await _unload(hass, entry)


async def test_travel_time_without_any_value_is_not_arriving(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Every travel time sensor unavailable or unknown: nobody is on the way home."""
    hass.states.async_set("sensor.waze_andrei", "unavailable", MINUTES)
    hass.states.async_set("sensor.waze_laura", "unknown", MINUTES)
    entry = await _setup(
        hass,
        freezer,
        house_options={"travel_time": ["sensor.waze_andrei", "sensor.waze_laura"]},
    )
    house = entry.runtime_data
    hass.states.async_set("person.andrei", "not_home")
    await _tick(hass, freezer, 11 * 60)
    assert hass.states.get("sensor.home_presence").state == "far"
    assert not house.arriving
    assert hass.states.get("sensor.bedroom_decision").state == "presence_far"
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_mode_away_stays_while_someone_is_on_the_way_home(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Away is set by hand: someone on the way home does not preheat until it is changed."""
    hass.states.async_set("sensor.waze_andrei", "60", MINUTES)
    entry = await _setup(hass, freezer, house_options={"travel_time": ["sensor.waze_andrei"]})
    house = entry.runtime_data
    hass.states.async_set("person.andrei", "not_home")
    await _tick(hass, freezer, 11 * 60)
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": "select.home_mode", "option": "away"},
        blocking=True,
    )
    await _tick(hass, freezer, 15)
    hass.states.async_set("sensor.waze_andrei", "10", MINUTES)
    await _tick(hass, freezer, 15)
    assert house.arriving
    assert hass.states.get("sensor.bedroom_decision").state == "house_away"
    # Back to auto: the way home counts again.
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": "select.home_mode", "option": "auto"},
        blocking=True,
    )
    await _tick(hass, freezer, 15)
    assert hass.states.get("sensor.bedroom_decision").state != "house_away"
    assert hass.states.get("sensor.bedroom_decision").state != "presence_far"
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_silent_trv_of_a_room_without_its_own_sensor(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Without a room sensor the TRV gives the temperature: it is the one watched."""
    entry, _calls = await _trv(hass, freezer)
    house = entry.runtime_data
    house.options["alert_silent_hours"] = 1
    house.options["alert_no_effect_hours"] = 0
    # Its last report now (the test clock was moved after it was first set).
    hass.states.async_set("climate.trv", "heat", {**TRV_AUTO, "temperature": 21.0})
    await _tick(hass, freezer, 5)
    for _ in range(5):
        await _tick(hass, freezer, 600)
    assert "silent_climate.trv" not in house.active_alerts
    for _ in range(3):
        await _tick(hass, freezer, 600)
    assert house.active_alerts["silent_climate.trv"]["code"] == "sensor_silent"
    # It reports again (the same values): over at the next evaluation.
    hass.states.async_set("climate.trv", "heat", {**TRV_AUTO, "temperature": 21.0})
    await _tick(hass, freezer, 310)
    assert "silent_climate.trv" not in house.active_alerts
    await _unload(hass, entry)


async def test_no_effect_not_told_in_a_pause(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A paused house heats nothing on purpose: no alert, however long."""
    hass.states.async_set("sensor.outdoor", "0.0", {"unit_of_measurement": "°C"})
    entry = await _setup(
        hass,
        freezer,
        house_options={"alert_silent_hours": 0, "outdoor_sensor": "sensor.outdoor"},
    )
    house = entry.runtime_data
    room = next(iter(house.rooms.values()))
    monkeypatch.setattr(ThermalLearner, "observe", lambda self, *a, **k: False)
    room.learner._model = ThermalModel(h=1.5, k=0.01, tau=0.0, learned=True)
    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": "switch.home_pause"}, blocking=True
    )
    for _ in range(24):
        hass.states.async_set("sensor.room_temp", "18.0", {"unit_of_measurement": "°C"})
        await _tick(hass, freezer, 600)
    assert f"no_effect_{room.id}" not in house.active_alerts
    assert await hass.config_entries.async_unload(entry.entry_id)
