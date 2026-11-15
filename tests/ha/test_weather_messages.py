"""The house tells why the heating stops or starts again because of the weather."""

from __future__ import annotations

from datetime import timedelta
from itertools import pairwise

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant, SupportsResponse
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_mock_service

from tests.ha.test_ha_setup import _setup, _tick


async def test_heating_off_and_on_by_the_weather_is_told(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-10-12 09:00:00+00:00")
    hass.states.async_set("weather.home", "sunny", {"temperature": 20.0, "temperature_unit": "°C"})
    start = dt_util.utcnow().replace(minute=0, second=0, microsecond=0)

    def forecast(value: float) -> None:
        async_mock_service(
            hass,
            "weather",
            "get_forecasts",
            response={
                "weather.home": {
                    "forecast": [
                        {
                            "datetime": (start + timedelta(hours=h)).isoformat(),
                            "temperature": value,
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
    told: list[tuple[str, dict]] = []
    original = house.inform

    def inform(code: str, params: dict | None = None) -> None:
        told.append((code, params or {}))
        original(code, params)

    house.inform = inform  # type: ignore[method-assign]
    await _tick(hass, freezer, 15)
    # Warm from the start: the state found at the start is not told.
    assert house.cutoff_active
    assert not [c for c, _ in told if c.startswith("weather_")]

    # The forecast says cold: the heating may run again, told with its mean.
    forecast(12.0)
    await house._async_refresh_forecast(dt_util.utcnow())
    await _tick(hass, freezer, 15)
    assert house.cutoff_reason == "forecast_cold"
    weather = [(c, p) for c, p in told if c.startswith("weather_")]
    assert weather == [("weather_on_forecast", {"hours": "3", "temp": weather[0][1]["temp"]})]
    assert weather[0][1]["temp"].endswith("°C")

    # Measured cold, then the forecast says warm: off earlier, told.
    hass.states.async_set("weather.home", "cloudy", {"temperature": 10.0, "temperature_unit": "°C"})
    await _tick(hass, freezer, 2 * 3600)
    forecast(24.0)
    await house._async_refresh_forecast(dt_util.utcnow())
    await _tick(hass, freezer, 15)
    assert house.cutoff_reason == "forecast_warm"
    assert [c for c, _ in told if c.startswith("weather_")][-1] == "weather_off_forecast"

    # The forecast cold again (measured cold too): on again.
    forecast(10.0)
    await house._async_refresh_forecast(dt_util.utcnow())
    await _tick(hass, freezer, 15)
    codes = [c for c, _ in told if c.startswith("weather_")]
    assert codes[-1] in ("weather_on", "weather_on_forecast")
    # Every change once, never twice in a row.
    assert all(a != b for a, b in pairwise(codes))


async def test_text_of_the_weather_messages() -> None:
    from custom_components.advanced_climate.alerts import alert_text

    text = alert_text("ro", "weather_off_forecast", {"temp": "19.0 °C", "hours": "3"}, "x")
    assert (
        text
        == "Încălzirea oprită: prognoza spune că va fi cald (media 19.0 °C în următoarele 3 h)."
    )
