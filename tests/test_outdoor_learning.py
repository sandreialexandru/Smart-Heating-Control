"""Tests for outdoor tracking and the thermal model of a room."""

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
        self.assertFalse(
            outdoor.OutdoorTracker.from_dict({"cutoff_active": True}).forecast_cutoff_active
        )

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


def _room(
    learner,
    *,
    h=1.5,
    k=0.04,
    tau=60.0,
    days=2.0,
    start=19.0,
    step=5,
    outdoor=None,
    spike_every=None,
    configured=True,
    curve=0.0,
):
    """Simulate a room with a thermostat (21 °C by day, 18 °C at night) and feed the learner.

    Returns the room temperature at the end. ``spike_every``: every so many
    minutes the sensor reads 1 °C too high once (a disturbance).
    """
    t0 = datetime(2026, 11, 1, tzinfo=TZ)
    temp, q, heat = start, 0.0, False
    for i in range(int(days * 24 * 60)):
        now = t0 + timedelta(minutes=i)
        target = 21.0 if 6 <= (i // 60) % 24 < 23 else 18.0
        out = outdoor if outdoor is not None else 5 + 5 * math.sin(2 * math.pi * i / 1440)
        if temp < target - 0.3:
            heat = True
        elif temp > target + 0.3:
            heat = False
        u = 1.0 if heat else 0.0
        q = u + (q - u) * math.exp(-1 / tau) if tau > 0 else u
        temp += ((h - curve * out) * q - k * (temp - out)) / 60
        if i % step == 0:
            reading = round(temp, 1)
            if spike_every and i % spike_every == 0:
                reading += 1.0
            learner.observe(now, heat, reading, round(out, 1), False, configured)
    return temp


class ThermalModelTest(unittest.TestCase):
    """The physical room model and its learning."""

    def test_default_before_learning(self) -> None:
        learner = learning.ThermalLearner()
        model = learner.model
        self.assertFalse(model.learned)
        # 60 minutes per degree, as before any learning.
        self.assertAlmostEqual(model.minutes_to_heat(18.0, 21.0, 5.0), 180.0, delta=1)
        # Nothing is known about the cooling yet.
        self.assertIsNone(model.minutes_to_fall(21.0, 20.0, 5.0))
        self.assertIsNone(model.loss_rate(21.0, 5.0))

    def test_learns_heating_loss_and_inertia(self) -> None:
        for h, k, tau in (
            (1.5, 0.04, 60.0),
            (3.0, 0.08, 20.0),
            (1.0, 0.03, 180.0),
            (2.0, 0.05, 0.0),
        ):
            learner = learning.ThermalLearner()
            _room(learner, h=h, k=k, tau=tau, days=3)
            model = learner.model
            self.assertTrue(model.learned)
            self.assertAlmostEqual(model.h, h, delta=0.05 * h)
            self.assertAlmostEqual(model.k, k, delta=0.1 * k)
            self.assertEqual(model.tau, tau)

    def test_learned_within_a_day(self) -> None:
        learner = learning.ThermalLearner()
        _room(learner, days=1)
        self.assertTrue(learner.model.learned)

    def test_physical_extrapolation_to_the_cold(self) -> None:
        learner = learning.ThermalLearner()
        _room(learner, h=1.5, k=0.04, tau=90.0, days=4)
        true = learning.ThermalModel(h=1.5, k=0.04, tau=90.0, learned=True)
        for outdoor in (10.0, 0.0, -10.0):
            learned = learner.model.minutes_to_heat(18.0, 21.0, outdoor)
            expected = true.minutes_to_heat(18.0, 21.0, outdoor)
            # At −10 °C the room barely gains (1.5 − 0.04 × 29.5 = 0.32 °C/h): a
            # small error of the numbers is a larger one in minutes, so 10 %.
            self.assertAlmostEqual(learned, expected, delta=0.1 * expected)
        # No weather curve in this room: it is learned as (almost) zero.
        self.assertAlmostEqual(learner.model.c, 0.0, delta=0.005)
        # A target above what the heating can hold is never reached.
        self.assertIsNone(true.minutes_to_heat(18.0, 60.0, -10.0))

    def test_weather_curve_is_learned(self) -> None:
        # The heating gives 0.05 °C/h more for each °C colder outdoors.
        learner = learning.ThermalLearner()
        _room(learner, h=1.5, k=0.04, tau=30.0, days=6, curve=0.05)
        model = learner.model
        self.assertAlmostEqual(model.c, 0.05, delta=0.01)
        self.assertAlmostEqual(model.h, 1.5, delta=0.05)
        true = learning.ThermalModel(h=1.5, k=0.04, c=0.05, tau=30.0, learned=True)
        for outdoor in (10.0, 0.0, -10.0):
            expected = true.minutes_to_heat(18.0, 21.0, outdoor)
            self.assertAlmostEqual(
                model.minutes_to_heat(18.0, 21.0, outdoor), expected, delta=0.1 * expected
            )

    def test_no_curve_without_outdoor_spread(self) -> None:
        # Always 5 °C outdoors: the curve cannot be told from the heating.
        learner = learning.ThermalLearner()
        _room(learner, days=3, outdoor=5.0, curve=0.05)
        self.assertEqual(learner.model.c, 0.0)

    def test_inertia_keeps_warming_after_a_stop(self) -> None:
        model = learning.ThermalModel(h=2.0, k=0.04, tau=90.0, learned=True)
        # Right after heating (all the heat still in the floor) the room still rises.
        later = model.simulate(21.0, 5.0, 1.0, False, 30)
        self.assertGreater(later, 21.0)
        # So it takes longer to fall to 20.5 °C than without inertia.
        none = learning.ThermalModel(h=2.0, k=0.04, tau=0.0, learned=True)
        self.assertGreater(
            model.minutes_to_fall(21.0, 20.5, 5.0, 1.0), none.minutes_to_fall(21.0, 20.5, 5.0, 0.0)
        )
        # A room already heating reaches its target sooner than one starting cold.
        self.assertLess(
            model.minutes_to_heat(20.0, 21.0, 5.0, 1.0), model.minutes_to_heat(20.0, 21.0, 5.0, 0.0)
        )

    def test_disturbances_weigh_less(self) -> None:
        learner = learning.ThermalLearner()
        _room(learner, h=1.5, k=0.04, tau=60.0, days=4, spike_every=360)
        self.assertAlmostEqual(learner.model.h, 1.5, delta=0.15)
        self.assertAlmostEqual(learner.model.k, 0.04, delta=0.008)

    def test_disturbed_stretches_not_used(self) -> None:
        learner = learning.ThermalLearner()
        t0 = datetime(2026, 11, 1, tzinfo=TZ)
        for i in range(0, 600, 5):
            learner.observe(t0 + timedelta(minutes=i), True, 20.0 + i / 600, 5.0, True)
        self.assertEqual(learner.heat_windows, 0.0)

    def test_gap_drops_the_stretch(self) -> None:
        learner = learning.ThermalLearner()
        t0 = datetime(2026, 11, 1, tzinfo=TZ)
        learner.observe(t0, True, 20.0, 5.0)
        self.assertFalse(learner.observe(t0 + timedelta(minutes=45), True, 21.0, 5.0))
        self.assertEqual(learner.heat_windows, 0.0)

    def test_without_outdoor_a_constant_loss(self) -> None:
        learner = learning.ThermalLearner()
        _room(learner, h=1.5, k=0.04, tau=0.0, days=3, outdoor=5.0, configured=False)
        model = learner.model
        self.assertTrue(model.learned and model.constant_loss)
        # At about 20 °C inside and 5 °C outside the loss is 0.04 × 15 = 0.6 °C per hour.
        self.assertAlmostEqual(model.k, 0.6, delta=0.1)

    def test_restore(self) -> None:
        learner = learning.ThermalLearner()
        _room(learner, days=2)
        again = learning.ThermalLearner.from_dict(learner.as_dict())
        self.assertEqual(again.model.h, learner.model.h)
        self.assertEqual(again.model.tau, learner.model.tau)
        self.assertTrue(again.model.learned)
        # Learning of an older version is learned again.
        self.assertFalse(
            learning.ThermalLearner.from_dict({"version": 4, "episodes": []}).model.learned
        )
        broken = learner.as_dict()
        broken["fits"][0][2] = "nan"
        self.assertFalse(learning.ThermalLearner.from_dict(broken).model.learned)

    def test_reset(self) -> None:
        learner = learning.ThermalLearner()
        _room(learner, days=2)
        learner.reset()
        self.assertFalse(learner.model.learned)


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
            outdoor.expected_outdoor(
                self.NOW, self.NOW, self.NOW + timedelta(minutes=10), 1.5, old
            ),
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
