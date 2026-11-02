"""Mold risk of a room from its temperature, its humidity and the outdoor temperature.

The air of a room is warm and holds its water vapour; the coldest place of an
outer wall (a corner, a window reveal) is colder, so the same vapour is a
higher relative humidity there. The method of DIN 4108-2 (also EN ISO 13788):

* the coldest wall surface is ``T_out + F_RSI · (T_room − T_out)``. ``F_RSI``
  is the temperature factor of that place; DIN 4108-2 requires at least 0.70
  at thermal bridges, so 0.70 is used (an older house may be worse);
* the vapour pressure of the room air is ``RH · p_sat(T_room)``, the same at
  the wall; the humidity at the wall is that over ``p_sat(T_wall)`` (Magnus
  formula for ``p_sat``);
* mold can grow where the humidity at the surface stays at 80 % or more
  (``MOLD_SURFACE_RH``, the criterion of DIN 4108-2).

The alert is told after the risk lasted ``MOLD_MINUTES`` (so a shower or
cooking does not raise it) and ends below ``MOLD_CLEAR_RH`` (a margin, so it
does not come and go around the limit).
"""

from __future__ import annotations

import math

F_RSI = 0.70
MOLD_SURFACE_RH = 80.0  # %
MOLD_CLEAR_RH = 75.0  # %
MOLD_MINUTES = 60.0


def saturation_pressure(temperature: float) -> float:
    """Saturation vapour pressure over water (hPa), Magnus formula."""
    return 6.112 * math.exp(17.62 * temperature / (243.12 + temperature))


def surface_temperature(room: float, outdoor: float, factor: float = F_RSI) -> float:
    """Temperature of the coldest wall surface (°C)."""
    return outdoor + factor * (room - outdoor)


def surface_humidity(room: float, humidity: float, outdoor: float, factor: float = F_RSI) -> float:
    """Relative humidity at the coldest wall surface (%, at most 100)."""
    vapour = humidity / 100 * saturation_pressure(room)
    wall = surface_temperature(room, outdoor, factor)
    return min(100.0, 100 * vapour / saturation_pressure(wall))
