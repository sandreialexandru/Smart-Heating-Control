"""The small helpers: numbers, units, clocks, dates, distances and durations."""

from __future__ import annotations

from datetime import date, datetime, time, timezone

from homeassistant.core import HomeAssistant, State

from custom_components.advanced_climate import util


def test_numbers() -> None:
    assert util.finite("21.5") == 21.5
    assert util.finite("nan") is None
    assert util.finite(float("inf")) is None
    assert util.finite(True) is None
    assert util.finite("x") is None
    assert util.float_attr(None, "temperature") is None
    assert util.float_attr(State("climate.x", "heat", {"temperature": "20"}), "temperature") == 20.0


def test_units() -> None:
    assert util.is_fahrenheit("°F")
    assert util.is_fahrenheit("fahrenheit")
    assert not util.is_fahrenheit("°C")
    assert util.to_celsius(212.0, "°F") == 100.0
    assert util.from_celsius(100.0, "°F") == 212.0
    # A difference of 1.8 °F is 1 °C, and back.
    assert util.delta_to_celsius(1.8, "°F") == 1.0
    assert util.delta_from_celsius(1.0, "°F") == 1.8
    for convert in (
        util.to_celsius,
        util.from_celsius,
        util.delta_to_celsius,
        util.delta_from_celsius,
    ):
        assert convert(None, "°F") is None
        assert convert(3.0, "°C") == 3.0


def test_system_unit_without_units() -> None:
    class NoUnits:
        config = object()

    assert util.system_unit(NoUnits()) == util.CELSIUS  # type: ignore[arg-type]


def test_aggregate() -> None:
    assert util.aggregate([], "mean") is None
    assert util.aggregate([20.0, 21.0, 24.0], "mean") == 21.67
    assert util.aggregate([20.0, 21.0, 24.0], "min") == 20.0
    assert util.aggregate([20.0, 21.0, 24.0], "median") == 21.0


def test_heat_mode() -> None:
    assert util.heat_mode(["off", "heat", "auto"]) == "heat"
    assert util.heat_mode(["off", "auto"]) == "auto"
    assert util.heat_mode(None) == "heat"


def test_clock_and_lists() -> None:
    assert util.parse_clock("06:30") == time(6, 30)
    assert util.parse_clock("7") == time(7, 0)
    assert util.parse_clock(time(5, 15)) == time(5, 15)
    assert util.parse_clock("later", time(1, 0)) == time(1, 0)
    assert util.as_list(None) == []
    assert util.as_list("sensor.a") == ["sensor.a"]
    assert util.as_list(("sensor.a", "sensor.b")) == ["sensor.a", "sensor.b"]


async def test_dates(hass: HomeAssistant) -> None:
    await hass.config.async_set_time_zone("Europe/Bucharest")
    moment = datetime(2026, 10, 12, 9, 0, tzinfo=timezone.utc)
    assert util.from_iso(None) is None
    assert util.from_iso(moment) is moment
    assert util.from_iso("not a date") is None
    # Without a time zone: the time zone of Home Assistant (UTC+3 in October).
    assert util.from_iso("2026-10-12T12:00:00").utcoffset().total_seconds() == 3 * 3600
    assert util.calendar_moment(None) is None
    assert util.calendar_moment(moment) == moment
    naive = util.calendar_moment(datetime(2026, 10, 12, 12, 0))
    assert naive.utcoffset().total_seconds() == 3 * 3600
    assert util.calendar_moment("2026-10-12T12:00:00").hour == 12
    # A whole-day event starts at local midnight.
    day = util.calendar_moment("2026-10-13")
    assert (day.date(), day.hour) == (date(2026, 10, 13), 0)
    assert util.calendar_moment("someday") is None


def test_distances_and_durations() -> None:
    def state(value: str, unit: str | None = None) -> State:
        return State("sensor.x", value, {"unit_of_measurement": unit} if unit else {})

    assert util.distance_km(None) is None
    assert util.distance_km(state("x")) is None
    assert util.distance_km(state("1500", "m")) == 1.5
    assert util.distance_km(state("1", "mi")) == 1.609344
    assert round(util.distance_km(state("1000", "ft")), 4) == 0.3048
    assert util.distance_km(state("3")) == 3.0
    assert util.minutes_value(state("unavailable")) is None
    assert util.minutes_value(state("x", "min")) is None
    assert util.minutes_value(state("90", "s")) == 1.5
    assert util.minutes_value(state("2", "h")) == 120.0
    assert util.minutes_value(state("25")) == 25.0
