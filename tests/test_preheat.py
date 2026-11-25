"""How well the optimal start hit the time of the schedule."""

from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta

from tests.pure import preheat

T = datetime(2026, 11, 25, 7, 0, tzinfo=UTC)  # the level begins


def _at(minutes: float) -> datetime:
    return T + timedelta(minutes=minutes)


def _run(tracker, steps) -> None:
    """Steps: (minutes from T, preheating, current, holding)."""
    for minutes, preheating, current, holding in steps:
        tracker.observe(_at(minutes), preheating, T, "home", 21.0, current, holding)


class PreheatTest(unittest.TestCase):
    def test_reached_before_the_time(self) -> None:
        t = preheat.PreheatTracker(None, 10)
        _run(
            t,
            [
                (-60, True, 19.0, None),
                (-12, True, 21.0, None),
                (-5, True, 21.2, None),
                (0, False, 21.1, "home"),
            ],
        )
        self.assertEqual(len(t.results), 1)
        self.assertEqual(t.results[0]["offset"], -12)
        self.assertEqual(t.results[0]["preset"], "home")
        self.assertEqual(t.results[0]["at"], T.isoformat())

    def test_reached_after_the_time(self) -> None:
        t = preheat.PreheatTracker(None, 10)
        _run(
            t,
            [
                (-40, True, 19.0, None),
                (0, False, 20.5, "home"),
                (10, False, 20.9, "home"),
                (18, False, 21.0, "home"),
            ],
        )
        self.assertEqual([r["offset"] for r in t.results], [18])

    def test_not_reached_while_the_level_held(self) -> None:
        t = preheat.PreheatTracker(None, 10)
        _run(t, [(-40, True, 19.0, None), (0, False, 20.0, "home"), (60, False, 20.5, "eco")])
        self.assertEqual([r["offset"] for r in t.results], [None])

    def test_another_rule_after_the_time_ends_it_not_reached(self) -> None:
        t = preheat.PreheatTracker(None, 10)
        _run(t, [(-40, True, 19.0, None), (5, False, 20.0, None)])
        self.assertEqual([r["offset"] for r in t.results], [None])

    def test_stopped_before_the_time_is_not_counted(self) -> None:
        t = preheat.PreheatTracker(None, 10)
        _run(
            t,
            [
                (-40, True, 19.0, None),
                (-20, False, 19.5, None),
                (0, False, 20.0, "home"),
                (30, False, 21.0, "home"),
            ],
        )
        self.assertEqual(len(t.results), 0)

    def test_the_newest_are_kept(self) -> None:
        t = preheat.PreheatTracker(
            [{"at": "x", "preset": "home", "started": "x", "offset": 1}] * 3, 3
        )
        _run(t, [(-30, True, 21.0, None), (0, False, 21.0, "home")])
        self.assertEqual(len(t.results), 3)
        self.assertEqual(t.results[-1]["offset"], -30)


if __name__ == "__main__":
    unittest.main()
