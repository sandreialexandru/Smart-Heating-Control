"""How much sun can reach a room: the sun signal of the learned model (pure Python).

The signal is ``max(0, sin(elevation)) × cloud factor``, from 0 (night or a
thick overcast) to 1 (the sun straight overhead in a clear sky):

* the sun elevation is worked out from the time and the location of Home
  Assistant (the NOAA formulas, accurate to a fraction of a degree);
* the cloud factor is the one of Kasten and Czeplak for the sunlight reaching
  the ground, ``1 − 0.75 · cover^3.4`` with the cloud cover from 0 to 1. The
  cover is the ``cloud_coverage`` of the weather entity (and of its hourly
  forecast); without it, a cover is assumed from the weather condition
  (``CONDITION_COVER``).

The room learns how many °C per hour a signal of 1 adds (docs/learning.md,
section 10). The orientation of the windows is not needed: a room with sun
only in the morning or only in the afternoon still gets a smaller, average
gain, and a room without sun none.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime

# Cloud cover (0 … 1) assumed from the weather condition when the weather
# entity has no cloud coverage. Rain, snow, fog and storms come with a closed
# sky; "partlycloudy" is half covered; "windy" says nothing about the clouds.
CONDITION_COVER: dict[str, float] = {
    "sunny": 0.1,
    "clear-night": 0.1,
    "partlycloudy": 0.5,
    "windy": 0.5,
    "windy-variant": 0.7,
    "cloudy": 0.9,
    "fog": 1.0,
    "rainy": 1.0,
    "pouring": 1.0,
    "snowy": 1.0,
    "snowy-rainy": 1.0,
    "hail": 1.0,
    "lightning": 1.0,
    "lightning-rainy": 1.0,
    "exceptional": 1.0,
}


def sin_elevation(when: datetime, latitude: float, longitude: float) -> float:
    """Sine of the sun elevation at ``when`` (an aware moment) and the location."""
    utc = when.astimezone(UTC)
    day = utc.timetuple().tm_yday
    hours = utc.hour + utc.minute / 60 + utc.second / 3600
    gamma = 2 * math.pi / 365 * (day - 1 + (hours - 12) / 24)
    # Equation of time (minutes) and declination (radians), NOAA.
    eqtime = 229.18 * (
        0.000075
        + 0.001868 * math.cos(gamma)
        - 0.032077 * math.sin(gamma)
        - 0.014615 * math.cos(2 * gamma)
        - 0.040849 * math.sin(2 * gamma)
    )
    decl = (
        0.006918
        - 0.399912 * math.cos(gamma)
        + 0.070257 * math.sin(gamma)
        - 0.006758 * math.cos(2 * gamma)
        + 0.000907 * math.sin(2 * gamma)
        - 0.002697 * math.cos(3 * gamma)
        + 0.00148 * math.sin(3 * gamma)
    )
    solar_minutes = hours * 60 + eqtime + 4 * longitude
    hour_angle = math.radians(solar_minutes / 4 - 180)
    lat = math.radians(latitude)
    return math.sin(lat) * math.sin(decl) + math.cos(lat) * math.cos(decl) * math.cos(hour_angle)


def cloud_factor(cover: float) -> float:
    """Share of the clear-sky sunlight that comes through ``cover`` (0 … 1)."""
    cover = min(1.0, max(0.0, cover))
    return 1 - 0.75 * cover**3.4


def cover_of(cloud_coverage: object, condition: object) -> float | None:
    """Cloud cover (0 … 1) from a cloud coverage in % or else from a condition."""
    try:
        value = float(cloud_coverage)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        value = math.nan
    if math.isfinite(value):
        return min(1.0, max(0.0, value / 100))
    if isinstance(condition, str):
        return CONDITION_COVER.get(condition)
    return None


def signal(when: datetime, latitude: float, longitude: float, cover: float | None) -> float | None:
    """The sun signal (0 … 1) at ``when``; None in daylight with the clouds unknown."""
    elevation = sin_elevation(when, latitude, longitude)
    if elevation <= 0:
        return 0.0
    if cover is None:
        return None
    return elevation * cloud_factor(cover)
