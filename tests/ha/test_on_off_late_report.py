"""An on / off thermostat or relay that reports the state sent to it late (#44).

A Zigbee TRV (Aqara W600 via Zigbee2MQTT) reports ``off`` about 2 s after the
command; an evaluation in between (the boiler's own report, any room entity)
read the old ``heat`` back as the room's: the demand came back for a second and
the boiler started again. The state sent is taken until the device reports it.
"""

from __future__ import annotations

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import Context, HomeAssistant
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.advanced_climate.const import VERIFY_DELAY
from tests.ha.test_ha_devices import _house, _room, _tick, _unload

TRV = "climate.w600"
RELAY = "switch.heater"
COLD = {"hvac_modes": ["heat", "off"], "current_temperature": 15.0, "temperature": 30.0}
WARM = {**COLD, "current_temperature": 26.0}


async def _trv_room(hass: HomeAssistant, freezer: FrozenDateTimeFactory, **room: object):
    """An on / off room on one TRV, heating; the TRV takes no command by itself."""
    modes = async_mock_service(hass, "climate", "set_hvac_mode")
    async_mock_service(hass, "climate", "set_temperature")
    hass.states.async_set(TRV, "heat", COLD)
    entry = await _house(
        hass,
        freezer,
        [
            (
                "Living",
                {
                    "source": "climate",
                    "climates": [TRV],
                    "command_mode": "hvac_mode",
                    "min_on_minutes": 0,
                    "min_off_minutes": 0,
                    **room,
                },
            )
        ],
    )
    room_ = _room(entry, "Living")
    assert room_.heat_demand
    return entry, room_, modes


async def test_a_trv_off_not_reported_yet_is_not_read_back_as_on(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Warm: off is sent; an evaluation before the TRV reports keeps the demand off."""
    entry, room, modes = await _trv_room(hass, freezer)
    hass.states.async_set(TRV, "heat", WARM)
    await _tick(hass, freezer, 2)
    assert [m.data["hvac_mode"] for m in modes] == ["off"]
    assert not room.heat_demand
    # Still "heat" in Home Assistant: another report of the TRV (its temperature)
    # starts an evaluation before it reports off.
    hass.states.async_set(TRV, "heat", {**WARM, "current_temperature": 26.2})
    await _tick(hass, freezer, 2)
    assert not room.heat_demand
    assert room._relay_on is False
    assert [m.data["hvac_mode"] for m in modes] == ["off"]
    # Its report: off, as sent.
    hass.states.async_set(TRV, "off", WARM)
    await _tick(hass, freezer, 2)
    assert not room.heat_demand
    assert [m.data["hvac_mode"] for m in modes] == ["off"]
    await _unload(hass, entry)


async def test_with_a_minimum_on_time_the_off_is_not_held_back(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """The old state read back no longer counts as a start: no minimum on time from it."""
    entry, room, modes = await _trv_room(hass, freezer, min_on_minutes=10)
    for _ in range(11):
        await _tick(hass, freezer, 60)
    hass.states.async_set(TRV, "heat", WARM)
    await _tick(hass, freezer, 2)
    hass.states.async_set(TRV, "heat", {**WARM, "current_temperature": 26.2})
    await _tick(hass, freezer, 2)
    assert not room.heat_demand
    assert room.relay_waiting is None
    assert [m.data["hvac_mode"] for m in modes] == ["off"]
    await _unload(hass, entry)


async def test_a_person_turning_it_on_meanwhile_is_seen_at_once(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """A change of its state ends the wait: a TRV turned back on by hand is on."""
    entry, room, modes = await _trv_room(hass, freezer)
    hass.states.async_set(TRV, "heat", WARM)
    await _tick(hass, freezer, 2)
    hass.states.async_set(TRV, "off", WARM)
    await _tick(hass, freezer, 2)
    assert "state" not in room.pending_command.get(TRV, {})
    hass.states.async_set(TRV, "heat", WARM, context=Context())
    await _tick(hass, freezer, 2)
    assert room._relay_actual() is True
    await _unload(hass, entry)


async def test_an_off_never_reported_is_sent_again_then_told(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """The check after the command: sent once more, then the alert; it ends once it reports."""
    entry, room, modes = await _trv_room(hass, freezer)
    hass.states.async_set(TRV, "heat", WARM)
    await _tick(hass, freezer, 2)
    assert [m.data["hvac_mode"] for m in modes] == ["off"]
    await _tick(hass, freezer, VERIFY_DELAY + 1)
    assert [m.data["hvac_mode"] for m in modes][:2] == ["off", "off"]
    assert not any(a["code"] == "not_turned_off" for a in room.house.alerts_for(room))
    await _tick(hass, freezer, VERIFY_DELAY + 1)
    alerts = [a for a in room.house.alerts_for(room) if a["code"] == "not_turned_off"]
    assert alerts and alerts[0]["params"]["entities"] == [TRV], room.house.alerts_for(room)
    # It finally reports off: the next check after a command ends the alert.
    hass.states.async_set(TRV, "off", WARM)
    await _tick(hass, freezer, 2)
    hass.states.async_set(TRV, "off", COLD)
    await _tick(hass, freezer, 2)
    assert modes[-1].data["hvac_mode"] == "heat"
    hass.states.async_set(TRV, "heat", COLD)
    await _tick(hass, freezer, VERIFY_DELAY + 1)
    assert not any(a["code"] == "not_turned_off" for a in room.house.alerts_for(room))
    await _unload(hass, entry)


async def test_a_trv_that_reports_at_once_raises_no_alert(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Reported: nothing sent again, no alert."""
    entry, room, modes = await _trv_room(hass, freezer)
    hass.states.async_set(TRV, "heat", WARM)
    await _tick(hass, freezer, 2)
    hass.states.async_set(TRV, "off", WARM)
    for _ in range(3):
        await _tick(hass, freezer, VERIFY_DELAY + 1)
    assert [m.data["hvac_mode"] for m in modes] == ["off"]
    assert not any(a["code"].startswith("not_turned") for a in room.house.alerts_for(room))
    await _unload(hass, entry)


async def _relay_room(hass: HomeAssistant, freezer: FrozenDateTimeFactory):
    """An on / off room on a relay and a room sensor; the relay takes no command by itself."""
    on = async_mock_service(hass, "switch", "turn_on")
    off = async_mock_service(hass, "switch", "turn_off")
    hass.states.async_set(RELAY, "on")
    hass.states.async_set("sensor.living", "15.0", {"unit_of_measurement": "°C"})
    entry = await _house(
        hass,
        freezer,
        [
            (
                "Living",
                {
                    "source": "switch",
                    "switches": [RELAY],
                    "temperature_sensors": ["sensor.living"],
                    "min_on_minutes": 0,
                    "min_off_minutes": 0,
                },
            )
        ],
    )
    room = _room(entry, "Living")
    assert room.heat_demand
    return entry, room, on, off


async def test_a_relay_off_not_reported_yet_is_not_read_back_as_on(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """The same for a relay (a Zigbee relay may confirm late too)."""
    entry, room, on, off = await _relay_room(hass, freezer)
    hass.states.async_set("sensor.living", "26.0", {"unit_of_measurement": "°C"})
    await _tick(hass, freezer, 2)
    assert len(off) == 1
    assert not room.heat_demand
    hass.states.async_set("sensor.living", "26.2", {"unit_of_measurement": "°C"})
    await _tick(hass, freezer, 2)
    assert not room.heat_demand
    assert len(off) == 1 and not on
    hass.states.async_set(RELAY, "off")
    await _tick(hass, freezer, 2)
    assert "state" not in room.pending_command.get(RELAY, {})
    assert not room.heat_demand
    await _unload(hass, entry)


async def test_a_relay_off_never_reported_is_told(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Sent once more, then the alert, as for the thermostats."""
    entry, room, on, off = await _relay_room(hass, freezer)
    hass.states.async_set("sensor.living", "26.0", {"unit_of_measurement": "°C"})
    await _tick(hass, freezer, 2)
    await _tick(hass, freezer, VERIFY_DELAY + 1)
    assert len(off) >= 2
    await _tick(hass, freezer, VERIFY_DELAY + 1)
    assert any(
        a["code"] == "not_turned_off" and a["params"]["entities"] == [RELAY]
        for a in room.house.alerts_for(room)
    ), room.house.alerts_for(room)
    await _unload(hass, entry)
