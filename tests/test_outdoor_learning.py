"""Tests for outdoor tracking and heating rate learning."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import math
import unittest

from tests.pure import const, learning, outdoor

TZ = timezone.utc


class OutdoorTest(unittest.TestCase):
    def test_average(self) -> None:
        tracker = outdoor.OutdoorTracker()
        t0 = datetime(2026, 10, 12, 0, tzinfo=TZ)
        tracker.add(t0, 10.0)
        tracker.add(t0 + timedelta(hours=3), 20.0)
        self.assertAlmostEqual(tracker.average(t0 + timedelta(hours=6), 6), 15.0)
        self.assertAlmostEqual(tracker.average(t0 + timedelta(hours=6), 3), 20.0)

    def test_daily_mean_of_the_local_day(self) -> None:
        # 22:30 UTC on 12 October is already 13 October in Bucharest (UTC+3).
        from zoneinfo import ZoneInfo

        tracker = outdoor.OutdoorTracker(tz=ZoneInfo("Europe/Bucharest"))
        tracker.add(datetime(2026, 10, 12, 22, 30, tzinfo=TZ), 4.0)
        self.assertEqual(tracker.daily_means, {"2026-10-13": 4.0})

    def test_unknown_after_the_window(self) -> None:
        # No new value for the averaging window: the outdoor temperature is unknown.
        tracker = outdoor.OutdoorTracker(max_age=timedelta(hours=6))
        t0 = datetime(2026, 10, 12, 0, tzinfo=TZ)
        tracker.add(t0, 10.0)
        self.assertEqual(tracker.latest(t0 + timedelta(hours=6)), 10.0)
        self.assertEqual(tracker.average(t0 + timedelta(hours=6), 6), 10.0)
        self.assertIsNone(tracker.latest(t0 + timedelta(hours=7)))
        self.assertIsNone(tracker.average(t0 + timedelta(hours=7), 6))
        # A short gap is no problem.
        tracker.add(t0 + timedelta(hours=7), 12.0)
        self.assertEqual(tracker.latest(t0 + timedelta(hours=8)), 12.0)

    def test_daily_mean_weighted_by_time(self) -> None:
        # 10 °C from 00:00 to 06:00, then 20 °C to midnight: (6 * 10 + 18 * 20) / 24
        # = 17.5 °C (the mean of the samples would give more weight to 10 °C).
        tracker = outdoor.OutdoorTracker(max_age=timedelta(hours=6))
        t0 = datetime(2026, 10, 12, 0, tzinfo=TZ)
        for hour in range(6):
            tracker.add(t0 + timedelta(hours=hour), 10.0)
        for hour in range(6, 24, 5):
            tracker.add(t0 + timedelta(hours=hour), 20.0)
        # The next day: yesterday is worked out again until midnight.
        tracker.add(t0 + timedelta(days=1, minutes=5), 20.0)
        self.assertEqual(tracker.daily_means["2026-10-12"], 17.5)

    def test_daily_mean_uses_the_covered_time(self) -> None:
        # Values hold at most the averaging window (6 h): 10 °C 00-06, 20 °C
        # 07-13 (Home Assistant off 13-20), 10 °C 20-24: (60 + 120 + 40) / 16 = 13.75.
        tracker = outdoor.OutdoorTracker(max_age=timedelta(hours=6))
        t0 = datetime(2026, 10, 12, 0, tzinfo=TZ)
        tracker.add(t0, 10.0)
        tracker.add(t0 + timedelta(hours=7), 20.0)
        tracker.add(t0 + timedelta(hours=20), 10.0)
        tracker.add(t0 + timedelta(days=1, minutes=1), 10.0)
        self.assertEqual(tracker.daily_means["2026-10-12"], 13.75)

    def test_daily_mean_survives_a_restart(self) -> None:
        # Nights (18:00-06:00) at 5 °C, days at 15 °C: the real mean is 10 °C.
        # A restart at 04:00 or at 18:00 must not change it (only the averaging
        # window of samples is saved, the day sums are saved too).
        from zoneinfo import ZoneInfo

        zone = ZoneInfo("Europe/Bucharest")
        for restart_hour in (None, 4, 18):
            tracker = outdoor.OutdoorTracker(max_age=timedelta(hours=6), tz=zone)
            moment = datetime(2026, 10, 12, 0, tzinfo=zone)
            while moment < datetime(2026, 10, 14, 0, 10, tzinfo=zone):
                if moment.day == 13 and moment.hour == restart_hour and moment.minute == 0:
                    tracker = outdoor.OutdoorTracker.from_dict(tracker.as_dict())
                    tracker.max_age, tracker.tz = timedelta(hours=6), zone
                tracker.add(moment, 15.0 if 6 <= moment.hour < 18 else 5.0)
                moment += timedelta(minutes=10)
            self.assertEqual(tracker.daily_means["2026-10-12"], 10.0, restart_hour)
            self.assertEqual(tracker.daily_means["2026-10-13"], 10.0, restart_hour)

    def test_auto_season_needs_days_in_a_row(self) -> None:
        tracker = outdoor.OutdoorTracker()
        today = date(2026, 10, 12)
        # 10 October missing: the 3 days before today are not complete.
        tracker.daily_means = {"2026-10-08": 20.0, "2026-10-09": 20.0, "2026-10-11": 20.0}
        self.assertTrue(tracker.update_season(today, const.SEASON_AUTO, "", "", 3, 15.0))
        tracker.daily_means["2026-10-10"] = 20.0
        self.assertFalse(tracker.update_season(today, const.SEASON_AUTO, "", "", 3, 15.0))

    def test_saved_samples_cover_the_averaging_window(self) -> None:
        # One value a minute for 48 h, averaging window 24 h: the last 24 h are
        # saved (and the value valid at its start), not only the last 600 values.
        tracker = outdoor.OutdoorTracker(max_age=timedelta(hours=24))
        t0 = datetime(2026, 10, 12, 0, tzinfo=TZ)
        tracker.samples = [(t0 + timedelta(minutes=m), float(m % 7)) for m in range(48 * 60)]
        now = tracker.samples[-1][0]
        restored = outdoor.OutdoorTracker.from_dict(tracker.as_dict())
        self.assertLessEqual(restored.samples[0][0], now - timedelta(hours=24))
        self.assertEqual(restored.average(now, 24), tracker.average(now, 24))

    def test_cutoff_hysteresis(self) -> None:
        tracker = outdoor.OutdoorTracker()
        self.assertFalse(tracker.update_cutoff(17.5, 18, 1))
        self.assertTrue(tracker.update_cutoff(18.0, 18, 1))
        self.assertTrue(tracker.update_cutoff(17.5, 18, 1))
        self.assertFalse(tracker.update_cutoff(17.0, 18, 1))

    def test_forecast_cutoff_hysteresis(self) -> None:
        # Cutoff 18, hysteresis 1: on at a forecast mean of 18, off at 17.
        tracker = outdoor.OutdoorTracker()
        self.assertFalse(tracker.update_forecast_cutoff(17.5, 18, 1))
        self.assertTrue(tracker.update_forecast_cutoff(18.0, 18, 1))
        self.assertTrue(tracker.update_forecast_cutoff(17.5, 18, 1))
        self.assertFalse(tracker.update_forecast_cutoff(17.0, 18, 1))
        self.assertTrue(tracker.update_forecast_cutoff(19.0, 18, 1))
        # Without a forecast mean it is off.
        self.assertFalse(tracker.update_forecast_cutoff(None, 18, 1))
        restored = outdoor.OutdoorTracker.from_dict(
            {**tracker.as_dict(), "forecast_cutoff_active": True}
        )
        self.assertTrue(restored.forecast_cutoff_active)
        # Data saved before 2.3.3 has no forecast state: off.
        self.assertFalse(outdoor.OutdoorTracker.from_dict({"cutoff_active": True}).forecast_cutoff_active)

    def test_date_season(self) -> None:
        self.assertTrue(outdoor.in_date_season(date(2026, 12, 1), "10-15", "04-15"))
        self.assertTrue(outdoor.in_date_season(date(2026, 4, 15), "10-15", "04-15"))
        self.assertFalse(outdoor.in_date_season(date(2026, 7, 1), "10-15", "04-15"))
        self.assertTrue(outdoor.in_date_season(date(2026, 7, 1), "06-01", "08-01"))

    def test_auto_season(self) -> None:
        tracker = outdoor.OutdoorTracker()
        tracker.daily_means = {"2026-10-09": 12.0, "2026-10-10": 13.0, "2026-10-11": 14.0}
        today = date(2026, 10, 12)
        self.assertTrue(tracker.update_season(today, const.SEASON_AUTO, "", "", 3, 15.0))
        tracker.daily_means = {"2026-05-09": 16.0, "2026-05-10": 18.0, "2026-05-11": 17.0}
        self.assertFalse(
            tracker.update_season(date(2026, 5, 12), const.SEASON_AUTO, "", "", 3, 15.0)
        )
        # Mixed days keep the previous state.
        tracker.daily_means = {"2026-05-12": 14.0, "2026-05-13": 18.0, "2026-05-14": 17.0}
        self.assertFalse(
            tracker.update_season(date(2026, 5, 15), const.SEASON_AUTO, "", "", 3, 15.0)
        )

    def test_serialize(self) -> None:
        tracker = outdoor.OutdoorTracker()
        tracker.add(datetime(2026, 10, 12, tzinfo=TZ), 5.0)
        tracker.cutoff_active = True
        again = outdoor.OutdoorTracker.from_dict(tracker.as_dict())
        self.assertEqual(again.latest(), 5.0)
        self.assertTrue(again.cutoff_active)


class LearningTest(unittest.TestCase):
    T0 = datetime(2026, 10, 12, 6, tzinfo=TZ)

    def _episode(self, learner, start, outdoor, rise=3.0, minutes=90, window=False):
        learner.observe(start, True, 19.0, 22.0, outdoor)
        learner.observe(start + timedelta(minutes=30), True, 20.0, 22.0, outdoor, window)
        return learner.observe(
            start + timedelta(minutes=minutes), True, 19.0 + rise, 22.0, outdoor
        )

    def _feed(self, learner, day, outdoor, rise, minutes):
        """One episode that rises ``rise`` °C to the target in ``minutes``."""
        start = self.T0 + timedelta(days=day)
        learner.observe(start, True, 22.0 - rise, 22.0, outdoor)
        return learner.observe(start + timedelta(minutes=minutes), True, 22.0, 22.0, outdoor)

    def test_default_before_learning(self) -> None:
        learner = learning.HeatingRateLearner()
        # 60 minutes per degree until the first episode.
        self.assertEqual(learner.minutes(3.0, 5.0), 180.0)
        self.assertEqual(learner.minutes_per_degree(None), learning.DEFAULT_MINUTES_PER_DEGREE)
        self.assertEqual(learner.minutes(0.0, 5.0), 0.0)

    def test_episode(self) -> None:
        learner = learning.HeatingRateLearner()
        # Just below the target the episode goes on (no margin): it ends at the target.
        self.assertIsNone(self._episode(learner, self.T0, 5.0, rise=2.95))
        minutes = learner.observe(self.T0 + timedelta(minutes=90), True, 22.0, 22.0, 5.0)
        self.assertEqual(minutes, 90.0)
        self.assertEqual(learner.episodes[0][:3], [5.0, 3.0, 90.0])
        # One episode: 30 minutes per degree, at every outdoor temperature.
        self.assertAlmostEqual(learner.minutes(3.0, 5.0), 90.0)
        self.assertAlmostEqual(learner.minutes(1.5, -5.0), 45.0)

    def test_short_demand_ignored(self) -> None:
        # The heat demand must last at least 10 minutes.
        learner = learning.HeatingRateLearner()
        learner.observe(self.T0, True, 19.0, 22.0, 5.0)
        self.assertIsNone(learner.observe(self.T0 + timedelta(minutes=9), False, 19.5, 22.0, 5.0))
        self.assertEqual(learner.episodes, [])
        learner.observe(self.T0, True, 19.0, 22.0, 5.0)
        self.assertEqual(learner.observe(self.T0 + timedelta(minutes=10), False, 19.1, 22.0, 5.0), 10.0)

    def test_window_episode_ignored(self) -> None:
        learner = learning.HeatingRateLearner()
        self.assertIsNone(self._episode(learner, self.T0, 5.0, window=True))
        self.assertEqual(learner.episodes, [])
        # No episode starts while a window is open.
        learner.observe(self.T0, True, 19.0, 22.0, 5.0, True)
        self.assertIsNone(learner.episode_start)

    def test_fixed_part_and_outdoor_learned(self) -> None:
        # A room with 25 minutes before it rises and 60 - 2 × outdoor minutes per degree.
        learner = learning.HeatingRateLearner()
        for day, (outdoor, rise) in enumerate([(10.0, 0.4), (0.0, 3.0), (5.0, 2.0), (0.0, 0.5)]):
            self._feed(learner, day, outdoor, rise, 25 + rise * (60 - 2 * outdoor))
        model = learner.model
        self.assertTrue(model.uses_fixed and model.uses_outdoor)
        self.assertAlmostEqual(model.fixed, 25.0, places=1)
        self.assertAlmostEqual(model.per_degree, 60.0, places=1)
        self.assertAlmostEqual(model.per_outdoor, -2.0, places=2)
        # Never seen -3 °C: estimated from the trend, 25 + 3 × 66.
        self.assertAlmostEqual(learner.minutes(3.0, -3.0), 223.0, places=0)
        # Unknown outdoor temperature: the mean of the episodes (3.75 °C).
        self.assertAlmostEqual(learner.minutes_per_degree(None), 60 - 2 * 3.75, places=1)

    def test_terms_need_spread(self) -> None:
        # Same sizes (less than 1 °C apart): no fixed part.
        learner = learning.HeatingRateLearner()
        for day, (outdoor, minutes) in enumerate([(0.0, 40.0), (5.0, 30.0), (10.0, 20.0)]):
            self._feed(learner, day, outdoor, 0.5, minutes)
        self.assertFalse(learner.model.uses_fixed)
        self.assertTrue(learner.model.uses_outdoor)
        self.assertEqual(learner.model.fixed, 0.0)
        # Outdoor temperatures less than 1 °C apart: no outdoor term.
        flat = learning.HeatingRateLearner()
        for day, (outdoor, rise) in enumerate([(5.0, 0.5), (5.5, 2.0)]):
            self._feed(flat, day, outdoor, rise, 20 + rise * 50)
        self.assertFalse(flat.model.uses_outdoor)
        self.assertTrue(flat.model.uses_fixed)
        self.assertAlmostEqual(flat.minutes(1.0, -10.0), 70.0, places=1)

    def test_impossible_terms_set_to_zero(self) -> None:
        # Large episodes not slower than small ones: only a fixed part is left.
        learner = learning.HeatingRateLearner()
        self._feed(learner, 0, 5.0, 0.5, 300)
        self._feed(learner, 1, 5.0, 2.5, 100)
        self.assertEqual(learner.model.per_degree, 0.0)
        self.assertAlmostEqual(learner.minutes(3.0, 5.0), 200.0)
        # A negative fixed part: set to zero, the minutes per degree refitted.
        neg = learning.HeatingRateLearner()
        self._feed(neg, 0, 5.0, 0.5, 10)
        self._feed(neg, 1, 5.0, 2.0, 100)
        self.assertEqual(neg.model.fixed, 0.0)
        self.assertGreater(neg.model.per_degree, 0.0)
        # Far outside the learned range the minutes per degree never go below zero.
        trend = learning.HeatingRateLearner()
        for day, (outdoor, minutes) in enumerate([(0.0, 40.0), (5.0, 30.0), (10.0, 20.0)]):
            self._feed(trend, day, outdoor, 0.5, minutes)
        self.assertEqual(trend.minutes_per_degree(60.0), 0.0)

    def test_time_heated_counts_against_the_fixed_part(self) -> None:
        learner = learning.HeatingRateLearner()
        for day, (outdoor, rise) in enumerate([(5.0, 0.5), (5.0, 2.5)]):
            self._feed(learner, day, outdoor, rise, 30 + rise * 40)
        self.assertAlmostEqual(learner.model.fixed, 30.0, places=1)
        start = self.T0 + timedelta(days=5)
        self.assertAlmostEqual(learner.minutes(1.0, 5.0, start), 70.0, places=1)
        # Heating for 20 minutes already: 10 minutes of the fixed part are left.
        learner.observe(start, True, 20.0, 22.0, 5.0)
        later = start + timedelta(minutes=20)
        self.assertAlmostEqual(learner.minutes(1.0, 5.0, later), 50.0, places=1)
        # After the whole fixed part: only the minutes per degree.
        self.assertAlmostEqual(learner.minutes(1.0, 5.0, start + timedelta(hours=1)), 40.0, places=1)

    def test_outdoor_term_with_a_negative_value_at_zero(self) -> None:
        # Learned only at 10 … 15 °C: the line may cross zero below the range; the
        # model is kept (never below zero far away) and not cut at 0 °C.
        learner = learning.HeatingRateLearner()
        for day, (outdoor, minutes) in enumerate([(10.0, 15.0), (12.5, 20.0), (15.0, 25.0)]):
            self._feed(learner, day, outdoor, 0.5, minutes)
        self.assertTrue(learner.model.uses_outdoor)
        self.assertAlmostEqual(learner.minutes(0.5, 12.5), 20.0, places=1)
        self.assertEqual(learner.minutes_per_degree(-20.0), 0.0)

    def test_episodes_without_outdoor(self) -> None:
        learner = learning.HeatingRateLearner()
        self._feed(learner, 0, None, 0.5, 30)
        self._feed(learner, 1, None, 2.5, 110)
        self.assertTrue(learner.model.uses_fixed)
        self.assertAlmostEqual(learner.minutes(1.0, None), 50.0, places=1)

    def test_small_and_large_kept_apart(self) -> None:
        learner = learning.HeatingRateLearner()
        for day in range(3):
            self._feed(learner, day, 5.0, 3.0, 200)
        for day in range(3, 40):
            self._feed(learner, day, 5.0, 0.4, 40)
        sizes = [e[1] for e in learner.episodes]
        self.assertEqual(sizes.count(3.0), 3)
        self.assertEqual(sizes.count(0.4), learning.MAX_SMALL_EPISODES)
        # In time order, the large ones first here.
        self.assertEqual(sizes[:3], [3.0, 3.0, 3.0])
        for day in range(40, 70):
            self._feed(learner, day, 5.0, 2.0, 150)
        sizes = [e[1] for e in learner.episodes]
        self.assertEqual(len([g for g in sizes if g >= 1]), learning.MAX_LARGE_EPISODES)
        self.assertEqual(sizes.count(0.4), learning.MAX_SMALL_EPISODES)

    def test_cancel(self) -> None:
        # Outside the cold season the episode in progress is dropped.
        learner = learning.HeatingRateLearner()
        learner.observe(self.T0, True, 19.0, 22.0, 5.0)
        learner.cancel()
        self.assertIsNone(learner.episode_start)
        cooling = learning.CoolingLearner()
        cooling.observe(self.T0, False, 22.0, 5.0)
        cooling.cancel()
        self.assertIsNone(cooling.observe(self.T0 + timedelta(hours=2), True, 21.0, 5.0))

    def test_learning_is_free(self) -> None:
        # A very slow room is learned as measured: 0.4 °C in 3 h.
        slow = learning.HeatingRateLearner()
        slow.observe(self.T0, True, 21.3, 22.0, 7.0, tolerance=0.5)
        self.assertEqual(
            slow.observe(self.T0 + timedelta(hours=3), False, 21.7, 22.0, 7.0, tolerance=0.5),
            180.0,
        )
        self.assertAlmostEqual(slow.minutes_per_degree(7.0), 450.0)
        # A rise of only 0.1 °C is learned too; no rise is nothing to learn.
        tiny = learning.HeatingRateLearner()
        tiny.observe(self.T0, True, 21.4, 22.0, 7.0, tolerance=0.5)
        self.assertEqual(
            tiny.observe(self.T0 + timedelta(hours=1), False, 21.5, 22.0, 7.0, tolerance=0.5), 60.0
        )
        flat = learning.HeatingRateLearner()
        flat.observe(self.T0, True, 21.4, 22.0, 7.0, tolerance=0.5)
        self.assertIsNone(
            flat.observe(self.T0 + timedelta(hours=1), False, 21.4, 22.0, 7.0, tolerance=0.5)
        )

    def test_restore_and_migrate(self) -> None:
        learner = learning.HeatingRateLearner()
        self._episode(learner, self.T0, 5.0)
        again = learning.HeatingRateLearner.from_dict(learner.as_dict())
        self.assertEqual(again.episodes, learner.episodes)
        self.assertEqual(again.minutes(3.0, 5.0), learner.minutes(3.0, 5.0))
        # Older versions kept only a rate per episode: they are discarded.
        for old in (
            {"version": 3, "episodes": [[5.0, 0.8, "b"]]},
            {"version": 2, "episodes": [[5.0, 0.8, "b"]]},
            {"rates": {"above_10": 0.284}},
            None,
        ):
            restored = learning.HeatingRateLearner.from_dict(old)
            self.assertEqual(restored.episodes, [])
            self.assertEqual(restored.minutes(1.0, 2.0), learning.DEFAULT_MINUTES_PER_DEGREE)
        # Broken entries are skipped.
        broken = learning.HeatingRateLearner.from_dict(
            {"version": learning.DATA_VERSION, "episodes": [[5.0, 0.0, 30, ""], ["x"], [None, 1.0, 50, "a"]]}
        )
        self.assertEqual(broken.episodes, [[None, 1.0, 50.0, "a"]])

    def test_episode_in_progress_survives_a_restart(self) -> None:
        # 20.3 °C at the start, target 22: heating for 7 hours with a restart in between.
        learner = learning.HeatingRateLearner()
        self.assertIsNone(learner.observe(self.T0, True, 20.3, 22.0, 14.0, tolerance=0.5))
        saved = learner.as_dict()
        self.assertEqual(saved["in_progress"]["temp"], 20.3)
        again = learning.HeatingRateLearner.from_dict(saved)
        self.assertEqual(again.episode_start, self.T0)
        # Still heating after the restart: the same episode goes on.
        self.assertIsNone(again.observe(self.T0 + timedelta(hours=7), True, 21.4, 22.0, 12.0))
        minutes = again.observe(self.T0 + timedelta(hours=8), False, 21.4, 19.0, 12.0)
        self.assertEqual(minutes, 480.0)
        # 21.4 - 20.3 = 1.1 °C; outdoor mean of the 3 values (14 + 12 + 12) / 3 = 12.7.
        self.assertEqual(again.episodes[-1][:3], [12.7, 1.1, 480.0])
        self.assertNotIn("in_progress", again.as_dict())

    def test_restored_episode_dropped_when_not_heating(self) -> None:
        # Not heating at the first observation after the restart: when the heating
        # stopped is not known, so the episode is not used.
        learner = learning.HeatingRateLearner()
        learner.observe(self.T0, True, 20.3, 22.0, 14.0, tolerance=0.5)
        again = learning.HeatingRateLearner.from_dict(learner.as_dict())
        self.assertIsNone(again.observe(self.T0 + timedelta(hours=2), False, 21.0, 22.0, 12.0))
        self.assertIsNone(again.episode_start)
        self.assertEqual(again.episodes, [])
        # Malformed saved data is ignored.
        for bad in ({"start": "x", "temp": 20.0}, {"start": self.T0.isoformat(), "temp": "nan"}, "x"):
            restored = learning.HeatingRateLearner.from_dict(
                {"version": learning.DATA_VERSION, "episodes": [], "in_progress": bad}
            )
            self.assertIsNone(restored.episode_start)

    def test_episode_starts_at_tolerance(self) -> None:
        # Generic Thermostat with cold_tolerance 0.5: it heats from 0.5 below the target.
        learner = learning.HeatingRateLearner()
        learner.observe(self.T0, True, 21.6, 22.0, 5.0, tolerance=0.5)
        self.assertIsNone(learner.episode_start)
        # At least the tolerance below the target starts an episode (maintenance too).
        learner.observe(self.T0, True, 21.5, 22.0, 5.0, tolerance=0.5)
        self.assertIsNotNone(learner.episode_start)
        self.assertEqual(learning.start_gap(0.5), 0.5)


class CoolingLearnerTest(unittest.TestCase):
    T0 = datetime(2026, 10, 12, 22, 0, tzinfo=timezone.utc)

    def _cool(self, learner, start, indoor0, indoor1, outdoor, minutes, window=False):
        learner.observe(start, False, indoor0, outdoor, window)
        return learner.observe(start + timedelta(minutes=minutes), True, indoor1, outdoor, False)

    def test_coefficient_from_inside_outside_difference(self) -> None:
        learner = learning.CoolingLearner()
        # 22 -> 21.5 °C in 1 h with 7 °C outside: k = ln(15 / 14.5).
        k = self._cool(learner, self.T0, 22.0, 21.5, 7.0, 60)
        self.assertAlmostEqual(k, math.log(15 / 14.5), places=4)
        # The same house loses heat faster when it is colder outside.
        self.assertGreater(learner.rate(22.0, -5.0), learner.rate(22.0, 7.0))
        # Time to fall from 22 to 21.5 °C at 7 °C outside: 1 h.
        self.assertAlmostEqual(learner.minutes_to_fall(22.0, 21.5, 7.0), 60.0, delta=0.01)
        self.assertAlmostEqual(learner.temperature_after(22.0, 7.0, 60), 21.5, delta=0.001)

    def test_episode_conditions(self) -> None:
        learner = learning.CoolingLearner()
        # Shorter than 10 minutes without heat demand: not used.
        self.assertIsNone(self._cool(learner, self.T0, 22.0, 21.9, 7.0, 9))
        # No fall (sun, cooking): not used.
        self.assertIsNone(self._cool(learner, self.T0, 22.0, 22.0, 7.0, 60))
        # A window open: not used.
        self.assertIsNone(self._cool(learner, self.T0, 22.0, 21.0, 7.0, 60, window=True))
        # Any fall over at least 10 minutes counts.
        self.assertIsNotNone(self._cool(learner, self.T0, 22.0, 21.9, 7.0, 10))
        self.assertEqual(len(learner.episodes), 1)

    def test_restore(self) -> None:
        learner = learning.CoolingLearner()
        self._cool(learner, self.T0, 22.0, 21.5, 7.0, 60)
        again = learning.CoolingLearner.from_dict(learner.as_dict())
        self.assertEqual(again.episodes, learner.episodes)
        self.assertIsNone(learning.CoolingLearner.from_dict(None).coefficient)


if __name__ == "__main__":
    unittest.main()


class ExpectedOutdoorTest(unittest.TestCase):
    """The outdoor temperature expected during an optimal start / stop."""

    NOW = datetime(2026, 1, 10, 4, 20, tzinfo=timezone.utc)

    def hourly(self, *values: float) -> list:
        # Forecast hours from 04:00 on.
        base = datetime(2026, 1, 10, 4, 0, tzinfo=timezone.utc)
        return [(base + timedelta(hours=i), v) for i, v in enumerate(values)]

    def test_time_weighted_mean(self) -> None:
        # 05:30-07:00: half an hour at -2 (05:00), an hour at -6 (06:00).
        value, source = outdoor.expected_outdoor(
            self.NOW,
            datetime(2026, 1, 10, 5, 30, tzinfo=timezone.utc),
            datetime(2026, 1, 10, 7, 0, tzinfo=timezone.utc),
            1.0,
            self.hourly(0.0, -2.0, -6.0, -3.0),
        )
        self.assertEqual(source, "forecast")
        self.assertAlmostEqual(value, (-2 * 30 + -6 * 60) / 90, places=2)

    def test_measured_value_until_the_next_forecast_hour(self) -> None:
        # 04:20-05:20: 40 minutes at the measured 1.0, 20 at -2 (05:00).
        value, _ = outdoor.expected_outdoor(
            self.NOW,
            self.NOW,
            self.NOW + timedelta(hours=1),
            1.0,
            self.hourly(0.0, -2.0, -6.0),
        )
        self.assertAlmostEqual(value, (1.0 * 40 - 2.0 * 20) / 60, places=2)

    def test_start_in_the_past_counts_from_now(self) -> None:
        value, _ = outdoor.expected_outdoor(
            self.NOW,
            self.NOW - timedelta(hours=2),
            self.NOW + timedelta(minutes=50),
            1.0,
            self.hourly(0.0, -2.0),
        )
        self.assertAlmostEqual(value, (1.0 * 40 - 2.0 * 10) / 50, places=2)

    def test_without_a_covering_forecast_the_value_of_now(self) -> None:
        end = datetime(2026, 1, 10, 9, 0, tzinfo=timezone.utc)
        self.assertEqual(
            outdoor.expected_outdoor(self.NOW, self.NOW, end, 1.5, self.hourly(0.0, -2.0)),
            (1.5, "now"),
        )
        self.assertEqual(outdoor.expected_outdoor(self.NOW, self.NOW, end, 1.5, []), (1.5, "now"))
        # An old forecast is not used.
        old = [(self.NOW - timedelta(hours=3), -9.0), (self.NOW - timedelta(hours=2), -9.0)]
        self.assertEqual(
            outdoor.expected_outdoor(self.NOW, self.NOW, self.NOW + timedelta(minutes=10), 1.5, old),
            (1.5, "now"),
        )

    def test_only_the_measured_value_before_the_next_forecast_hour(self) -> None:
        self.assertEqual(
            outdoor.expected_outdoor(
                self.NOW, self.NOW, self.NOW + timedelta(minutes=30), 1.5, self.hourly(0.0, -2.0)
            ),
            (1.5, "now"),
        )

    def test_unknown_measured_value_uses_the_forecast(self) -> None:
        value, source = outdoor.expected_outdoor(
            self.NOW, self.NOW, self.NOW + timedelta(minutes=50), None, self.hourly(0.0, -2.0)
        )
        self.assertEqual(source, "forecast")
        self.assertAlmostEqual(value, (0.0 * 40 - 2.0 * 10) / 50, places=2)
