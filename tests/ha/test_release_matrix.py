"""Before a release: a day and a half of a house in many configurations.

Each configuration runs from Monday morning to Tuesday evening with what happens
in a home: the people leave and come back, a window opens, a temperature is set
for a while, the pause, the outdoor temperature and the price change, the
thermostats report their temperatures, and the integration is reloaded in the
middle. Nothing must fail: no error in the log, every room with a decision and
a target in range, the panel commands and the diagnostics answer, and the house
unloads cleanly.
"""

from __future__ import annotations

import json
import logging

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.advanced_climate.const import DOMAIN
from custom_components.advanced_climate.diagnostics import async_get_config_entry_diagnostics
from custom_components.advanced_climate.websocket import HISTORY, WEEK, ws_history, ws_week
from tests.ha.test_ha_devices import _house, _tick, _unload

TRV = {"hvac_modes": ["heat", "off"], "min_temp": 5.0, "max_temp": 30.0}
CLIMATE = {"source": "climate", "command_mode": "temperature"}
BOOLEANS = ("boiler", "floor", "radiators", "heat_pump", "cheap", "electric")


def _trv_room(name: str, **extra: object) -> tuple[str, dict]:
    return name, {**CLIMATE, "climates": [f"climate.{name.lower()}"], **extra}


CONFIGS: dict[str, tuple[dict, list[tuple[str, dict]]]] = {
    "boiler and TRVs": (
        {"boiler_entity": "input_boolean.boiler"},
        [_trv_room("Living"), _trv_room("Bedroom"), _trv_room("Office")],
    ),
    "fahrenheit": (
        {"boiler_entity": "input_boolean.boiler", "temperature_unit": "°F"},
        [_trv_room("Living"), _trv_room("Bedroom")],
    ),
    "circuits and a secondary room": (
        {
            "boiler_entity": "input_boolean.boiler",
            "circuits": ["input_boolean.floor", "input_boolean.radiators"],
        },
        [
            _trv_room("Living", circuit="input_boolean.floor"),
            _trv_room("Bedroom", circuit="input_boolean.radiators"),
            _trv_room("Hall", circuit="input_boolean.radiators", starts_house_source=False),
        ],
    ),
    "secondary heat source by an entity": (
        {
            "boiler_entity": "input_boolean.boiler",
            "secondary_source": "input_boolean.heat_pump",
            "source_criterion": "entity",
            "source_criterion_entity": "input_boolean.cheap",
        },
        [_trv_room("Living"), _trv_room("Bedroom")],
    ),
    "no heat source, an electric room": (
        {},
        [
            _trv_room("Living", use_house_source=False),
            (
                "Bath",
                {
                    "source": "switch",
                    "switches": ["input_boolean.electric"],
                    "temperature_sensors": ["sensor.bath_temperature"],
                },
            ),
        ],
    ),
    "sensors of the rooms": (
        {"boiler_entity": "input_boolean.boiler", "outdoor_sensor": "sensor.outdoor"},
        [
            _trv_room(
                "Living",
                temperature_sensors=["sensor.living_temperature"],
                humidity_sensor="sensor.living_humidity",
                window_sensors=["binary_sensor.living_window"],
                occupancy_sensors=["binary_sensor.living_occupancy"],
            ),
            _trv_room("Bedroom", temperature_sensors=["sensor.bedroom_temperature"]),
        ],
    ),
    "price and solar": (
        {
            "boiler_entity": "input_boolean.boiler",
            "outdoor_sensor": "sensor.outdoor",
            "price_sensor": "sensor.price",
            "price_high": 0.40,
            "price_low": 0.10,
            "pv_sensor": "sensor.pv",
            "pv_threshold": 1000,
        },
        [_trv_room("Living"), _trv_room("Bedroom")],
    ),
    "a schedule helper": (
        {"boiler_entity": "input_boolean.boiler"},
        [
            _trv_room("Living"),
            _trv_room("Office", schedule_source="helper", schedule_helper="schedule.office"),
        ],
    ),
}


def _env(hass: HomeAssistant) -> None:
    """The entities the configurations read, at their state on Monday morning."""
    for name in ("living", "bedroom", "office", "hall"):
        hass.states.async_set(
            f"climate.{name}",
            "heat",
            {**TRV, "current_temperature": 19.5, "temperature": 20.0, "hvac_action": "idle"},
        )
    for name, value in (("living", 19.6), ("bedroom", 18.9), ("bath", 21.0)):
        hass.states.async_set(
            f"sensor.{name}_temperature",
            str(value),
            {"unit_of_measurement": "°C", "device_class": "temperature"},
        )
    hass.states.async_set(
        "sensor.living_humidity", "55", {"unit_of_measurement": "%", "device_class": "humidity"}
    )
    hass.states.async_set("binary_sensor.living_window", "off", {"device_class": "window"})
    hass.states.async_set("binary_sensor.living_occupancy", "on", {"device_class": "occupancy"})
    hass.states.async_set(
        "sensor.outdoor", "3.0", {"unit_of_measurement": "°C", "device_class": "temperature"}
    )
    hass.states.async_set("sensor.price", "0.25", {"unit_of_measurement": "EUR/kWh"})
    hass.states.async_set("sensor.pv", "0", {"unit_of_measurement": "W", "device_class": "power"})
    hass.states.async_set("schedule.office", "on")


async def _report(hass: HomeAssistant, step: int) -> None:
    """The thermostats and sensors move: warmer while asked for more, cooler otherwise."""
    for name in ("living", "bedroom", "office", "hall"):
        st = hass.states.get(f"climate.{name}")
        cur = float(st.attributes.get("current_temperature", 19.5))
        want = float(st.attributes.get("temperature") or 20.0)
        cur = round(cur + (0.2 if want > cur else -0.1), 1)
        hass.states.async_set(
            f"climate.{name}",
            "heat",
            {
                **st.attributes,
                "current_temperature": cur,
                "hvac_action": "heating" if want > cur else "idle",
            },
        )
    for name in ("living", "bedroom"):
        hass.states.async_set(
            f"sensor.{name}_temperature",
            str(hass.states.get(f"climate.{name}").attributes["current_temperature"]),
            {"unit_of_measurement": "°C", "device_class": "temperature"},
        )
    hass.states.async_set(
        "sensor.outdoor",
        str(round(3.0 - 4 * ((step % 144) / 144), 1)),
        {"unit_of_measurement": "°C", "device_class": "temperature"},
    )


async def _service(hass: HomeAssistant, service: str, data: dict) -> None:
    await hass.services.async_call(DOMAIN, service, data, blocking=True)


@pytest.mark.parametrize("name", list(CONFIGS))
async def test_a_day_and_a_half_of_a_house(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, caplog: pytest.LogCaptureFixture, name: str
) -> None:
    options, rooms = CONFIGS[name]
    assert await async_setup_component(
        hass, "input_boolean", {"input_boolean": {b: {} for b in BOOLEANS}}
    )
    async_mock_service(hass, "climate", "set_temperature")
    async_mock_service(hass, "climate", "set_hvac_mode")
    _env(hass)
    caplog.set_level(logging.WARNING, logger="custom_components.advanced_climate")
    entry = await _house(hass, freezer, rooms, at="2026-10-12 04:00:00+00:00", **options)
    first = rooms[0][0]
    # 36 hours in steps of 10 minutes, from Monday 07:00 (local time).
    for step in range(216):
        if step == 6:  # 08:00 everyone leaves
            hass.states.async_set("person.andrei", "not_home")
        if step == 12 and "living_window" in json.dumps(rooms):  # 09:00 a window opens for 40 min
            hass.states.async_set("binary_sensor.living_window", "on", {"device_class": "window"})
        if step == 16:
            hass.states.async_set("binary_sensor.living_window", "off", {"device_class": "window"})
            hass.states.async_set(
                "binary_sensor.living_occupancy", "off", {"device_class": "occupancy"}
            )
        if step == 30:  # 12:00 cheap power, sun
            hass.states.async_set("sensor.price", "0.05", {"unit_of_measurement": "EUR/kWh"})
            hass.states.async_set(
                "sensor.pv", "2500", {"unit_of_measurement": "W", "device_class": "power"}
            )
            hass.states.async_set("input_boolean.cheap", "on")
        if step == 48:  # 15:00 dear power, no sun
            hass.states.async_set("sensor.price", "0.55", {"unit_of_measurement": "EUR/kWh"})
            hass.states.async_set(
                "sensor.pv", "0", {"unit_of_measurement": "W", "device_class": "power"}
            )
            hass.states.async_set("input_boolean.cheap", "off")
            hass.states.async_set("schedule.office", "off")
        if step == 60:  # 17:00 back home, someone in the living room
            hass.states.async_set("person.andrei", "home")
            hass.states.async_set(
                "binary_sensor.living_occupancy", "on", {"device_class": "occupancy"}
            )
        if step == 66:  # 18:00 a temperature set for a while
            await _service(
                hass, "set_override", {"room": first, "temperature": 23.0, "duration_hours": 1.5}
            )
        if step == 72:  # 19:00 the pause for an hour
            await hass.services.async_call(
                "switch", "turn_on", {"entity_id": "switch.home_pause"}, blocking=True
            )
        if step == 78:
            await hass.services.async_call(
                "switch", "turn_off", {"entity_id": "switch.home_pause"}, blocking=True
            )
        if step == 84:  # 21:00 a level until the next change
            await _service(hass, "set_override", {"room": first, "preset": "comfort"})
        if step == 90:
            await _service(hass, "clear_override", {"room": first})
        if step == 100:  # Tuesday 00:40: reloaded (an update, a restart of the integration)
            assert await hass.config_entries.async_reload(entry.entry_id)
            await hass.async_block_till_done()
        await _report(hass, step)
        await _tick(hass, freezer, 600)

    errors = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert not errors, [r.getMessage() for r in errors]
    fahrenheit = options.get("temperature_unit") == "°F"
    low, high = (40.0, 95.0) if fahrenheit else (5.0, 35.0)
    for room in entry.runtime_data.rooms.values():
        decision = hass.states.get(f"sensor.{room.name.lower()}_decision")
        assert decision is not None and decision.state not in ("unknown", "unavailable"), room.name
        target = decision.attributes.get("target_temperature")
        assert target is None or low <= float(target) <= high, (room.name, target)
    assert not [a for a in entry.runtime_data.active_alerts if a.startswith("commands_")]

    sent: dict = {}

    class Connection:
        def send_result(self, msg_id: int, result: dict) -> None:
            sent[msg_id] = result

    ws_week(hass, Connection(), {"id": 1, "type": WEEK})
    ws_history(hass, Connection(), {"id": 2, "type": HISTORY})
    assert [len(h["rooms"]) for h in sent[1]["houses"]] == [len(rooms)]
    assert all(not r.get("failed") for h in sent[1]["houses"] for r in h["rooms"])
    assert any(r["decisions"] for h in sent[2]["houses"] for r in h["rooms"])
    json.dumps(await async_get_config_entry_diagnostics(hass, entry), default=str)
    await _unload(hass, entry)
