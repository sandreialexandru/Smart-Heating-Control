"""Whether the room is warming or cooling now (pure Python), for the arrow of the card.

The trend is the change of the room temperature over the last
``TREND_MINUTES`` minutes, per hour. Shorter than that it is not known (after
a start, or when the sensors changed). Below ``TREND_MIN`` °C per hour it is
steady: one step of a usual sensor (0.1 °C) in 30 minutes is 0.2 °C per hour.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta

TREND_MINUTES = 30.0
TREND_MIN = 0.2


class TemperatureTrend:
    """The room temperature of the last ``TREND_MINUTES`` (and a bit) minutes."""

    def __init__(self) -> None:
        """No readings yet."""
        self._readings: deque[tuple[datetime, float]] = deque()
        self._sources: tuple | None = None

    def update(self, now: datetime, sources: tuple, value: float | None) -> None:
        """A reading of the room temperature from ``sources`` (another set starts anew)."""
        if sources != self._sources:
            self._sources = sources
            self._readings.clear()
        if value is None:
            return
        readings = self._readings
        if not readings or readings[-1][1] != value:
            readings.append((now, value))
        keep = timedelta(minutes=2 * TREND_MINUTES)
        while len(readings) > 1 and now - readings[1][0] > keep:
            readings.popleft()

    def per_hour(self, now: datetime) -> float | None:
        """°C per hour over the last ``TREND_MINUTES`` minutes; None when not known yet."""
        readings = self._readings
        if not readings:
            return None
        window = timedelta(minutes=TREND_MINUTES)
        # The value at the start of the window: the last one read before it.
        before = [(t, v) for t, v in readings if now - t >= window]
        if not before:
            return None
        start = before[-1][1]
        current = readings[-1][1]
        return (current - start) / (TREND_MINUTES / 60)

    def direction(self, now: datetime) -> int:
        """1 warming, −1 cooling, 0 steady or not known."""
        rate = self.per_hour(now)
        if rate is None or abs(rate) < TREND_MIN - 1e-9:
            return 0
        return 1 if rate > 0 else -1
