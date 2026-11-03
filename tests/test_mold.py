"""Tests for the mold risk of a room."""

from __future__ import annotations

import unittest

from tests.pure import mold


class MoldTest(unittest.TestCase):
    def test_saturation_pressure(self) -> None:
        # Magnus formula: about 23.4 hPa at 20 °C, 6.1 hPa at 0 °C.
        self.assertAlmostEqual(mold.saturation_pressure(20.0), 23.37, delta=0.05)
        self.assertAlmostEqual(mold.saturation_pressure(0.0), 6.112, delta=0.001)

    def test_coldest_wall(self) -> None:
        # Room 20 °C, outdoor 0 °C, factor 0.70: the wall is 0 + 0.7 × 20 = 14 °C.
        self.assertAlmostEqual(mold.surface_temperature(20.0, 0.0), 14.0)

    def test_surface_humidity(self) -> None:
        # 60 % at 20 °C is 0.6 × 23.37 hPa of vapour; at 14 °C that is about 88 %.
        self.assertAlmostEqual(mold.surface_humidity(20.0, 60.0, 0.0), 87.7, delta=0.5)
        self.assertGreaterEqual(mold.surface_humidity(20.0, 60.0, 0.0), mold.MOLD_SURFACE_RH)
        # 50 %: about 73 %, no risk.
        self.assertLess(mold.surface_humidity(20.0, 50.0, 0.0), mold.MOLD_SURFACE_RH)
        # Never above 100 %.
        self.assertEqual(mold.surface_humidity(20.0, 95.0, -15.0), 100.0)
        # Warmer outside, warmer walls: less risk.
        self.assertLess(
            mold.surface_humidity(20.0, 60.0, 10.0), mold.surface_humidity(20.0, 60.0, 0.0)
        )

    def test_warmer_outside_than_inside(self) -> None:
        # No wall is colder than the room: its own humidity is the one at the walls.
        self.assertEqual(mold.surface_temperature(25.0, 30.0), 25.0)
        self.assertAlmostEqual(mold.surface_humidity(25.0, 85.0, 30.0), 85.0)
        # As warm outside as inside: the same.
        self.assertAlmostEqual(mold.surface_humidity(20.0, 70.0, 20.0), 70.0)


if __name__ == "__main__":
    unittest.main()
