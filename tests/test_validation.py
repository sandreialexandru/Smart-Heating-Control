"""Values that are not real numbers and malformed schedule data are rejected."""

from __future__ import annotations

import unittest
from datetime import UTC, datetime

from tests.pure import const, learning, outdoor, schedule

TZ = UTC
NOW = datetime(2026, 10, 12, 0, tzinfo=TZ).isoformat()


class NotANumberTest(unittest.TestCase):
    def test_outdoor_ignores_nan_and_inf(self) -> None:
        tracker = outdoor.OutdoorTracker()
        t0 = datetime(2026, 10, 12, 0, tzinfo=TZ)
        tracker.add(t0, float("nan"))
        tracker.add(t0, float("inf"))
        self.assertEqual(tracker.samples, [])
        tracker.add(t0, 10.0)
        self.assertEqual(tracker.latest(t0), 10.0)

    def test_outdoor_restore_drops_nan(self) -> None:
        tracker = outdoor.OutdoorTracker.from_dict(
            {
                "samples": [(NOW, "nan"), (NOW, 5.0), (NOW, "inf")],
                "daily_means": {"2026-10-10": "nan", "2026-10-11": 4.0},
                "daily_sums": {"2026-10-11": ["nan", 3600], "2026-10-12": [36000.0, 3600.0]},
            }
        )
        self.assertEqual([v for _, v in tracker.samples], [5.0])
        self.assertEqual(tracker.daily_means, {"2026-10-11": 4.0})
        self.assertEqual(tracker.daily_sums, {"2026-10-12": [36000.0, 3600.0]})

    def test_learning_restore_drops_nan(self) -> None:
        learner = learning.ThermalLearner()
        data = learner.as_dict()
        data["heat_windows"] = "nan"
        self.assertEqual(learning.ThermalLearner.from_dict(data).heat_windows, 0.0)


class ProfilesFromDictTest(unittest.TestCase):
    def test_clear_errors(self) -> None:
        presets = list(const.PRESETS)
        for bad, text in (
            ([], "profiles must be an object"),
            ({}, "profiles must be an object"),
            ({"workday": "06:00 home"}, 'Profile "workday"'),
            ({"workday": []}, 'Profile "workday"'),
            ({"workday": [{"time": "06:00"}]}, '"time" and "preset"'),
            ({"workday": ["06:00 home"]}, '"time" and "preset"'),
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(schedule.ScheduleError) as ctx:
                    schedule.profiles_from_dict(bad, presets)
                self.assertIn(text, str(ctx.exception))

    def test_valid(self) -> None:
        profiles = schedule.profiles_from_dict(
            {
                "workday": [
                    {"time": "00:00", "preset": "sleep"},
                    {"time": " 06:00 ", "preset": "home"},
                ]
            },
            list(const.PRESETS),
        )
        self.assertEqual(len(profiles["workday"]), 2)


if __name__ == "__main__":
    unittest.main()


class UnicodeNamesTest(unittest.TestCase):
    def test_letters_with_diacritics(self) -> None:
        profiles = schedule.parse_schedule(
            "sâmbătă: 00:00 Noapte, 08:30 Seară\nvacanță: 00:00 Dimineață",
            ["home", "sleep", "Noapte", "Seară", "Dimineață"],
        )
        self.assertEqual([s.preset for s in profiles["sâmbătă"]], ["Noapte", "Seară"])
        # Case does not matter, also for letters with diacritics.
        profiles = schedule.parse_schedule("zi: 06:00 seară", ["Seară"])
        self.assertEqual(profiles["zi"][0].preset, "Seară")

    def test_format_characters_are_not_names(self) -> None:
        for name in ("Seară, zi", "a:b", "x#y"):
            with self.subTest(name=name):
                self.assertIsNone(schedule.NAME_RE.fullmatch(name))
        self.assertIsNotNone(schedule.NAME_RE.fullmatch("Seară târzie-2"))
