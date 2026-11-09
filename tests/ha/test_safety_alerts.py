"""Safety alerts: a silent temperature sensor, and heating without effect."""

from __future__ import annotations

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant

from custom_components.advanced_climate.learning import ThermalLearner, ThermalModel
from tests.ha.test_ha_setup import _setup, _tick

TEMP = {"unit_of_measurement": "°C"}


def _report(hass: HomeAssistant, value: str) -> None:
    """The sensor reports (the same value too: Home Assistant notes the report)."""
    hass.states.async_set("sensor.room_temp", value, TEMP)


async def _minutes(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, minutes: int, value: str | None = None
) -> None:
    """Let time pass in steps of 10 minutes, the sensor reporting ``value`` at each one."""
    for _ in range(minutes // 10):
        if value is not None:
            _report(hass, value)
        await _tick(hass, freezer, 600)


def _learned(room, monkeypatch: pytest.MonkeyPatch, h: float = 1.5) -> None:
    """A learned model that stays as it is (no learning from the test)."""
    monkeypatch.setattr(ThermalLearner, "observe", lambda self, *a, **k: False)
    room.learner._model = ThermalModel(h=h, k=0.01, tau=0.0, learned=True)


async def test_silent_sensor_default_12_hours(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """By default a sensor is told silent after 12 hours, not before."""
    entry = await _setup(hass, freezer, house_options={"alert_no_effect_hours": 0})
    house = entry.runtime_data
    assert house.options["alert_silent_hours"] == 12
    await _tick(hass, freezer, 15)
    _report(hass, "18.0")
    await _minutes(hass, freezer, 11 * 60 + 50)
    assert "silent_sensor.room_temp" not in house.active_alerts
    await _minutes(hass, freezer, 20)
    assert house.active_alerts["silent_sensor.room_temp"]["params"]["hours"] == "12"


async def test_silent_sensor(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    """Available but no report for the hours set (4 here): told; a report ends it."""
    entry = await _setup(
        hass, freezer, house_options={"alert_no_effect_hours": 0, "alert_silent_hours": 4}
    )
    house = entry.runtime_data
    await _tick(hass, freezer, 15)
    # The same value every 10 minutes is a working sensor.
    await _minutes(hass, freezer, 300, "18.0")
    assert "silent_sensor.room_temp" not in house.active_alerts
    # Nothing at all: 3 h 50 min after the last report, not yet.
    await _minutes(hass, freezer, 220)
    assert "silent_sensor.room_temp" not in house.active_alerts
    await _minutes(hass, freezer, 20)
    alert = house.active_alerts["silent_sensor.room_temp"]
    assert alert["code"] == "sensor_silent"
    assert alert["params"] == {"entity": "sensor.room_temp", "hours": "4"}
    attrs = hass.states.get("sensor.bedroom_decision").attributes
    assert any(a["code"] == "sensor_silent" for a in attrs["alerts"])
    # It reports again (even the same value): over.
    _report(hass, "18.0")
    await _tick(hass, freezer, 310)
    assert "silent_sensor.room_temp" not in house.active_alerts


async def test_silent_sensor_off_and_summer(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """0 hours turns it off; in summer mode a silent sensor is not told."""
    entry = await _setup(hass, freezer, house_options={"alert_silent_hours": 0})
    house = entry.runtime_data
    await _minutes(hass, freezer, 600)
    assert "silent_sensor.room_temp" not in house.active_alerts
    house.options["alert_silent_hours"] = 4
    house.mode = "summer"
    await _minutes(hass, freezer, 60)
    assert "silent_sensor.room_temp" not in house.active_alerts
    house.mode = "auto"
    await _minutes(hass, freezer, 10)
    assert house.active_alerts["silent_sensor.room_temp"]["code"] == "sensor_silent"


async def test_no_effect_only_once_learned(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Before learning nothing is told (a slow floor heating); once learned it is, until it warms."""
    hass.states.async_set("sensor.outdoor", "0.0", TEMP)
    entry = await _setup(
        hass,
        freezer,
        house_options={"alert_silent_hours": 0, "outdoor_sensor": "sensor.outdoor"},
    )
    house = entry.runtime_data
    room = next(iter(house.rooms.values()))
    key = f"no_effect_{room.id}"
    monkeypatch.setattr(ThermalLearner, "observe", lambda self, *a, **k: False)
    await _tick(hass, freezer, 15)
    assert room.heating
    assert not room.learner.model.learned
    # Three hours of heating with almost no rise: not told before learning.
    await _minutes(hass, freezer, 180, "18.1")
    assert key not in house.active_alerts
    # Learned now: the same is told after the hours set.
    _learned(room, monkeypatch)
    await _minutes(hass, freezer, 110, "18.1")
    assert key not in house.active_alerts
    await _minutes(hass, freezer, 30, "18.2")
    alert = house.active_alerts[key]
    assert alert["code"] == "no_effect"
    # It warms up: over, and not told again at once (a new watch starts).
    await _minutes(hass, freezer, 10, "18.6")
    assert key not in house.active_alerts
    await _minutes(hass, freezer, 60, "18.6")
    assert key not in house.active_alerts


async def test_no_effect_rising_window_and_near_target(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Learned room: not told when it warms enough, near the target, or with a window open."""
    hass.states.async_set("sensor.outdoor", "0.0", TEMP)
    entry = await _setup(
        hass,
        freezer,
        house_options={"alert_silent_hours": 0, "outdoor_sensor": "sensor.outdoor"},
        window_sensors=["binary_sensor.window"],
    )
    house = entry.runtime_data
    room = next(iter(house.rooms.values()))
    _learned(room, monkeypatch)
    key = f"no_effect_{room.id}"
    hass.states.async_set("binary_sensor.window", "off")
    # Rising 0.6° an hour (1.5° in 2.5 h): more than a third of the expected rise.
    for step in range(15):
        await _minutes(hass, freezer, 10, f"{18 + step * 0.1:.2f}")
    assert key not in house.active_alerts
    # Just below the target (21°) and steady: a TRV holding it, not told.
    await _minutes(hass, freezer, 180, "20.7")
    assert key not in house.active_alerts
    # Cold and steady, but a window open: not told.
    hass.states.async_set("binary_sensor.window", "on")
    await _minutes(hass, freezer, 180, "18.0")
    assert key not in house.active_alerts


@pytest.mark.parametrize(
    ("h", "end", "told"),
    [
        (1.5, "18.3", True),  # about 2.6° expected, 0.3° measured
        (1.5, "20.0", False),  # 2° of the expected 2.6°
        (0.25, "18.1", False),  # a heating too weak for the cold expects little
    ],
)
async def test_no_effect_with_model(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    monkeypatch: pytest.MonkeyPatch,
    h: float,
    end: str,
    told: bool,
) -> None:
    """Learned: compared with the rise the model expects."""
    hass.states.async_set("sensor.outdoor", "0.0", TEMP)
    entry = await _setup(
        hass,
        freezer,
        house_options={"alert_silent_hours": 0, "outdoor_sensor": "sensor.outdoor"},
    )
    house = entry.runtime_data
    room = next(iter(house.rooms.values()))
    _learned(room, monkeypatch, h)
    key = f"no_effect_{room.id}"
    await _tick(hass, freezer, 15)
    start = 18.0
    for step in range(13):
        value = start + (float(end) - start) * step / 12
        await _minutes(hass, freezer, 10, f"{value:.2f}")
    alert = house.active_alerts.get(key)
    assert (alert is not None) is told
    if told:
        assert alert["code"] == "no_effect"
        assert float(alert["params"]["expected"]) > 2
