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
    """With the Temperature command a TRV that takes the temperature and stays in auto
    (its own schedule) is put in heat."""
    entry, calls = await _trv(hass, freezer, state="auto")
    # First only the temperature: many thermostats leave auto by themselves.
    assert calls["set_temperature"][-1].data == {"entity_id": "climate.trv", "temperature": 21.0}
    assert not calls["set_hvac_mode"]
    # It took it and stayed in auto (Sonoff TRVZB): now heat.
    hass.states.async_set("climate.trv", "auto", {**TRV_AUTO, "temperature": 21.0})
    await _tick(hass, freezer, 310)
    assert calls["set_hvac_mode"][-1].data == {"entity_id": "climate.trv", "hvac_mode": "heat"}
    assert hass.states.get("sensor.office_decision").state != "manual_override"
    # It reports heat: nothing more to send.
    sent = len(calls["set_hvac_mode"])
    hass.states.async_set("climate.trv", "heat", {**TRV_AUTO, "temperature": 21.0})
    await _tick(hass, freezer, 310)
    assert len(calls["set_hvac_mode"]) == sent
    assert hass.states.get("sensor.office_decision").state != "manual_override"
    await _unload(hass, entry)


async def test_thermostat_leaving_auto_by_itself_gets_no_mode(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Netatmo, Tado: a temperature set takes them out of auto; heat (a boost to the
    maximum on Netatmo) is never sent."""
    entry, calls = await _trv(hass, freezer, state="auto")
    hass.states.async_set("climate.trv", "heat", {**TRV_AUTO, "temperature": 21.0})
    for _ in range(3):
        await _tick(hass, freezer, 310)
    assert not calls["set_hvac_mode"]
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


async def test_everybody_rule_person_at_home_is_not_on_the_way(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Rule Everybody, one travel time per person: the one at home is not arriving."""
    hass.states.async_set("sensor.waze_andrei", "0", MINUTES)
    hass.states.async_set("sensor.waze_laura", "60", MINUTES)
    hass.states.async_set("person.laura", "home")
    entry = await _setup(
        hass,
        freezer,
        house_options={
            "persons": ["person.andrei", "person.laura"],
            "home_rule": "all",
            "travel_time": ["sensor.waze_andrei", "sensor.waze_laura"],
        },
    )
    house = entry.runtime_data
    hass.states.async_set("person.laura", "not_home")
    await _tick(hass, freezer, 11 * 60)
    assert hass.states.get("sensor.home_presence").state == "nearby"
    # The 0 minutes of the person at home are not someone on the way home.
    assert not house.arriving
    assert hass.states.get("sensor.bedroom_decision").state == "presence_nearby"
    # The other one comes within the arrival time: on the way home.
    hass.states.async_set("sensor.waze_laura", "10", MINUTES)
    await _tick(hass, freezer, 15)
    assert house.arriving
    # One minute from home, still on the way (only one trip is left out: one person is home).
    hass.states.async_set("sensor.waze_laura", "1", MINUTES)
    await _tick(hass, freezer, 15)
    assert house.arriving
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_nobody_home_a_short_trip_is_on_the_way(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """With nobody home, a trip of one minute is someone almost home, not left out."""
    hass.states.async_set("sensor.waze_andrei", "60", MINUTES)
    entry = await _setup(hass, freezer, house_options={"travel_time": ["sensor.waze_andrei"]})
    house = entry.runtime_data
    hass.states.async_set("person.andrei", "not_home")
    await _tick(hass, freezer, 11 * 60)
    assert not house.arriving
    hass.states.async_set("sensor.waze_andrei", "1", MINUTES)
    await _tick(hass, freezer, 15)
    assert house.arriving
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_silent_sensor_of_a_generic_thermostat_is_told(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """The sensor of the Generic Thermostat switches the heating: watched besides the
    room sensors of an older configuration, and only told (it cannot be left out)."""
    from homeassistant.helpers import entity_registry as er
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    gt = MockConfigEntry(
        domain="generic_thermostat",
        options={"heater": "switch.gt_relay", "target_sensor": "sensor.gt_temp"},
    )
    gt.add_to_hass(hass)
    climate = (
        er.async_get(hass)
        .async_get_or_create("climate", "generic_thermostat", gt.entry_id, config_entry=gt)
        .entity_id
    )
    for service in ("set_temperature", "set_hvac_mode", "set_preset_mode"):
        async_mock_service(hass, "climate", service)
    temp = {"unit_of_measurement": "°C"}
    gt_state = {"hvac_modes": ["heat", "off"], "current_temperature": 19.0, "temperature": 21.0}
    entry = await _house(
        hass,
        freezer,
        [
            (
                "Living",
                {
                    "source": "generic_thermostat",
                    "climates": [climate],
                    "switches": [],
                    "temperature_sensors": ["sensor.living"],
                },
            )
        ],
        alert_silent_hours=1,
        alert_no_effect_hours=0,
    )
    house = entry.runtime_data
    hass.states.async_set(climate, "heat", gt_state)
    hass.states.async_set("sensor.gt_temp", "19.0", temp)
    # The room sensor keeps reporting, the one of the Generic Thermostat does not.
    for _ in range(8):
        hass.states.async_set("sensor.living", "19.0", temp, force_update=True)
        await _tick(hass, freezer, 600)
    alert = house.active_alerts["silent_sensor.gt_temp"]
    assert alert["code"] == "sensor_silent"
    assert alert["params"]["left_out"] is False
    assert "silent_sensor.living" not in house.active_alerts
    assert _room(entry, "Living").current_temp == 19.0
    await _unload(hass, entry)


async def test_two_profiles_chosen_one_after_the_other_both_stay(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """An automation choosing a workday profile and then a weekend one: both are on."""
    schedule = (
        "workday: 00:00 sleep, 07:00 home\n"
        "weekend: 00:00 sleep, 09:00 comfort\n"
        "home_office: 00:00 sleep, 07:00 comfort\n"
        "guests: 00:00 sleep, 08:00 comfort"
    )
    days = {
        "workday": {"days": "workday", "enabled": True},
        "weekend": {"days": "weekend", "enabled": True},
        "home_office": {"days": "workday", "enabled": False},
        "guests": {"days": "weekend", "enabled": False},
    }
    entry = await _setup(hass, freezer, schedule=schedule, profile_days=days)
    await _tick(hass, freezer, 15)
    for option in ("home_office", "guests"):
        # No pause between them, as two actions of an automation.
        await hass.services.async_call(
            "select",
            "select_option",
            {"entity_id": "select.bedroom_schedule_profile", "option": option},
            blocking=True,
        )
    await hass.async_block_till_done()
    saved = next(iter(entry.subentries.values())).data["profile_days"]
    assert {n: d["enabled"] for n, d in saved.items()} == {
        "workday": False,
        "weekend": False,
        "home_office": True,
        "guests": True,
    }
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_trv_that_goes_back_to_auto_by_itself_is_left_in_auto(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Tuya TRV602Z (#15): put in heat it reports auto again a moment later. Before,
    it was put in heat again and again (every second); now it is left in auto."""
    from homeassistant.core import ServiceCall, callback

    temps = async_mock_service(hass, "climate", "set_temperature")
    modes: list[ServiceCall] = []

    @callback
    def _set_mode(call: ServiceCall) -> None:
        modes.append(call)
        # Heat for a moment (as Home Assistant shows it), then the TRV reports auto
        # again: within seconds of the call, so with its context (as an entity does).
        attrs = {**TRV_AUTO, "temperature": 21.0}
        hass.states.async_set("climate.trv", "heat", attrs, context=call.context)
        hass.loop.call_soon(
            lambda: hass.states.async_set("climate.trv", "auto", attrs, context=call.context)
        )

    hass.services.async_register("climate", "set_hvac_mode", _set_mode)
    hass.states.async_set("climate.trv", "auto", {**TRV_AUTO, "temperature": 21.0})
    entry = await _house(
        hass,
        freezer,
        [
            (
                "Office",
                {"source": "climate", "climates": ["climate.trv"], "command_mode": "temperature"},
            )
        ],
    )
    for _ in range(10):
        await _tick(hass, freezer, 2)
    await _tick(hass, freezer, 310)
    await _tick(hass, freezer, 310)
    assert len(modes) == 1  # tried once
    assert hass.states.get("climate.trv").state == "auto"
    room = _room(entry, "Office")
    assert "climate.trv" in room.keeps_auto
    assert room.decision.rule != "manual_override"
    assert len(temps) <= 2
    await _unload(hass, entry)


async def _trv_obeying_heat(hass: HomeAssistant, freezer: FrozenDateTimeFactory):
    """A TRV in auto that takes heat when told (the state follows the command)."""
    from homeassistant.core import ServiceCall, callback

    modes: list[ServiceCall] = []

    @callback
    def _set_mode(call: ServiceCall) -> None:
        modes.append(call)
        state = hass.states.get("climate.trv")
        hass.states.async_set(
            "climate.trv", call.data["hvac_mode"], state.attributes, context=call.context
        )

    hass.services.async_register("climate", "set_hvac_mode", _set_mode)
    async_mock_service(hass, "climate", "set_temperature")
    hass.states.async_set("climate.trv", "auto", {**TRV_AUTO, "temperature": 21.0})
    entry = await _house(
        hass,
        freezer,
        [
            (
                "Office",
                {"source": "climate", "climates": ["climate.trv"], "command_mode": "temperature"},
            )
        ],
    )
    await _tick(hass, freezer, 5)
    assert modes and modes[-1].data["hvac_mode"] == "heat"
    assert hass.states.get("climate.trv").state == "heat"
    return entry, modes


async def test_a_late_return_to_auto_is_not_a_manual_change(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """A TRV that reports auto again only a minute after heat: the device, not a person."""
    entry, modes = await _trv_obeying_heat(hass, freezer)
    room = _room(entry, "Office")
    assert "climate.trv" not in room.keeps_auto
    # A minute later, outside the context of the command: back in auto.
    await _tick(hass, freezer, 60)
    hass.states.async_set("climate.trv", "auto", {**TRV_AUTO, "temperature": 21.0}, Context())
    await _tick(hass, freezer, 5)
    assert room.decision.rule != "manual_override"
    assert "climate.trv" in room.keeps_auto
    sent = len(modes)
    await _tick(hass, freezer, 310)
    await _tick(hass, freezer, 310)
    assert len(modes) == sent
    await _unload(hass, entry)


async def test_auto_by_hand_after_the_window_is_a_manual_change(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Auto chosen by a person later than 5 minutes after heat: a manual change."""
    entry, _modes = await _trv_obeying_heat(hass, freezer)
    room = _room(entry, "Office")
    await _tick(hass, freezer, 6 * 60)
    hass.states.async_set("climate.trv", "auto", {**TRV_AUTO, "temperature": 21.0}, Context())
    await _tick(hass, freezer, 5)
    assert room.decision.rule == "manual_override"
    assert "climate.trv" not in room.keeps_auto
    await _unload(hass, entry)
