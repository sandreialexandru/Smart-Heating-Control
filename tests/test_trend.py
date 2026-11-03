"""Warming, cooling or steady: the arrow of the card."""

from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta

from tests.pure import trend

T0 = datetime(2026, 11, 3, 18, 0, tzinfo=UTC)


def _at(minutes: float) -> datetime:
    return T0 + timedelta(minutes=minutes)


class TrendTest(unittest.TestCase):
    def test_not_known_before_30_minutes(self) -> None:
        t = trend.TemperatureTrend()
        t.update(_at(0), ("s",), 20.0)
        t.update(_at(20), ("s",), 20.3)
        self.assertIsNone(t.per_hour(_at(20)))
        self.assertEqual(t.direction(_at(20)), 0)

    def test_warming_and_cooling(self) -> None:
        t = trend.TemperatureTrend()
        for minute, value in ((0, 20.0), (10, 20.1), (20, 20.2), (30, 20.3), (40, 20.4)):
            t.update(_at(minute), ("s",), value)
        # From 20.1 (read at minute 10, the last before 40 − 30) to 20.4: 0.3 °C in 30 min.
        self.assertAlmostEqual(t.per_hour(_at(40)), 0.6)
        self.assertEqual(t.direction(_at(40)), 1)
        for minute, value in ((50, 20.2), (60, 20.0), (70, 19.8)):
            t.update(_at(minute), ("s",), value)
        self.assertEqual(t.direction(_at(70)), -1)

    def test_one_sensor_step_in_30_minutes_is_the_limit(self) -> None:
        # 0.1 °C in 30 minutes = 0.2 °C/h: the smallest change shown.
        t = trend.TemperatureTrend()
        t.update(_at(0), ("s",), 20.0)
        t.update(_at(29), ("s",), 20.1)
        self.assertEqual(t.direction(_at(31)), 1)
        steady = trend.TemperatureTrend()
        steady.update(_at(0), ("s",), 20.0)
        self.assertEqual(steady.direction(_at(120)), 0)
        self.assertEqual(steady.per_hour(_at(120)), 0.0)

    def test_other_sensors_start_anew(self) -> None:
        t = trend.TemperatureTrend()
        t.update(_at(0), ("a",), 20.0)
        t.update(_at(40), ("b",), 22.0)
        self.assertIsNone(t.per_hour(_at(40)))

    def test_old_readings_are_dropped(self) -> None:
        t = trend.TemperatureTrend()
        for minute in range(0, 600, 5):
            t.update(_at(minute), ("s",), 20.0 + (minute % 10) / 100)
        self.assertLess(len(t._readings), 30)


if __name__ == "__main__":
    unittest.main()
