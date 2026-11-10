"""Tests for the decision engine."""

from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import UTC, datetime, timedelta

from tests.pure import const, engine

TZ = UTC
NOW = datetime(2026, 10, 12, 12, 0, tzinfo=TZ)
LEVELS = {"home": 22.0, "sleep": 19.0, "eco": 17.0, "away": 10.0, "comfort": 23.0, "activity": 20.0}


def inputs(**kwargs) -> engine.RoomInputs:
    base = engine.RoomInputs(
        now=NOW,
        mode=const.MODE_AUTO,
        paused=False,
        season_active=True,
        cutoff_active=False,
        valve_exercise=False,
        window_open=False,
        window_action=const.WINDOW_ACTION_FROST,
        override_active=False,
        vacation_active=False,
        presence=const.PRESENCE_HOME,
        arriving=False,
        room_unoccupied=False,
        sensor_failed=False,
        schedule_preset="home",
        schedule_rule=const.RULE_SCHEDULE,
        current_temp=21.0,
        frost_temp=7.0,
        max_temp=25.0,
        nearby_mode=const.NEARBY_PRESET,
        nearby_temp=None,
        level_temp=LEVELS.get,
    )
    return replace(base, **kwargs)


class RuleOrderTest(unittest.TestCase):
    def check(self, rule, kind, preset=None, temperature=None, **kwargs):
        decision = engine.decide(inputs(**kwargs))
        self.assertEqual(decision.rule, rule, decision.description)
        self.assertEqual(decision.target.kind, kind)
        if preset is not None:
            self.assertEqual(decision.target.preset, preset)
        if temperature is not None:
            self.assertAlmostEqual(decision.target.temperature, temperature)
        return decision

    def test_schedule(self) -> None:
        self.check(const.RULE_SCHEDULE, "preset", "home")

    def test_presence(self) -> None:
        self.check(const.RULE_NEARBY, "preset", "eco", presence="nearby")
        self.check(const.RULE_FAR, "preset", "away", presence="far")
        self.check(
            const.RULE_NEARBY,
            "temperature",
            temperature=16.5,
            presence="nearby",
            nearby_mode=const.NEARBY_TEMPERATURE,
            nearby_temp=16.5,
        )

    def test_arriving_uses_schedule(self) -> None:
        d = self.check(const.RULE_SCHEDULE, "preset", "home", presence="far", arriving=True)
        self.assertIn("on the way", d.description)

    def test_vacation_over_presence(self) -> None:
        self.check(const.RULE_VACATION, "preset", "away", vacation_active=True)
        self.check(const.RULE_VACATION, "preset", "away", mode=const.MODE_VACATION)

    def test_override_over_vacation(self) -> None:
        self.check(const.RULE_OVERRIDE, "none", override_active=True, vacation_active=True)

    def test_mode_away(self) -> None:
        # Nobody home, set by hand: the away level, over the presence.
        self.check(const.RULE_HOUSE_AWAY, "preset", "away", mode=const.MODE_AWAY)
        self.check(const.RULE_HOUSE_AWAY, "preset", "away", mode=const.MODE_AWAY, presence="home")
        # A manual change, a window and the vacation stay above it.
        self.check(const.RULE_OVERRIDE, "none", override_active=True, mode=const.MODE_AWAY)
        self.check(
            const.RULE_VACATION, "preset", "away", vacation_active=True, mode=const.MODE_AWAY
        )

    def test_window_over_override(self) -> None:
        self.check(
            const.RULE_WINDOW,
            "temperature",
            temperature=7.0,
            window_open=True,
            override_active=True,
        )
        self.check(
            const.RULE_WINDOW,
            "off",
            window_open=True,
            window_action=const.WINDOW_ACTION_OFF,
        )

    def test_modes(self) -> None:
        self.check(const.RULE_MODE_OFF, "temperature", temperature=7.0, mode=const.MODE_OFF)
        self.check(const.RULE_SUMMER, "off", mode=const.MODE_SUMMER)
        self.check(const.RULE_OUT_OF_SEASON, "off", season_active=False)
        self.check(const.RULE_PAUSE, "none", paused=True, window_open=True)

    def test_off_not_supported(self) -> None:
        self.check(
            const.RULE_SUMMER,
            "temperature",
            temperature=7.0,
            mode=const.MODE_SUMMER,
            supports_off=False,
        )

    def test_unoccupied_and_fallback(self) -> None:
        self.check(const.RULE_UNOCCUPIED, "preset", "eco", room_unoccupied=True)
        self.check(
            const.RULE_SCHEDULE, "preset", "away", room_unoccupied=True, schedule_preset="away"
        )
        self.check(const.RULE_SENSOR_FALLBACK, "preset", "eco", sensor_failed=True)


class AdjustmentTest(unittest.TestCase):
    def test_cutoff(self) -> None:
        d = engine.decide(inputs(cutoff_active=True))
        self.assertEqual((d.rule, d.target.kind), (const.RULE_CUTOFF, "off"))
        # The cutoff does not hide an open window.
        d = engine.decide(inputs(cutoff_active=True, window_open=True))
        self.assertEqual(d.rule, const.RULE_WINDOW)

    def test_offsets_convert_preset(self) -> None:
        d = engine.decide(inputs(offsets=[("compensation", 0.5), ("tariff", -1.0)]))
        self.assertEqual(d.target.kind, "temperature")
        self.assertAlmostEqual(d.target.temperature, 21.5)
        self.assertEqual(d.target.preset, "home")
        self.assertEqual(d.rule, const.RULE_SCHEDULE)

    def test_offsets_unknown_level(self) -> None:
        d = engine.decide(inputs(offsets=[("pv", 0.5)], level_temp=lambda p: None))
        self.assertEqual((d.target.kind, d.target.preset), ("preset", "home"))

    def test_offsets_ignored_for_override(self) -> None:
        d = engine.decide(inputs(override_active=True, offsets=[("pv", 0.5)]))
        self.assertEqual(d.target.kind, "none")


class SafetyTest(unittest.TestCase):
    def test_clamp(self) -> None:
        d = engine.decide(
            inputs(presence="nearby", nearby_mode=const.NEARBY_TEMPERATURE, nearby_temp=30)
        )
        self.assertAlmostEqual(d.target.temperature, 25.0)

    def test_frost_when_off(self) -> None:
        d = engine.decide(inputs(mode=const.MODE_SUMMER, current_temp=5.0))
        self.assertEqual((d.rule, d.target.temperature), (const.RULE_SAFETY, 7.0))
        d = engine.decide(inputs(paused=True, current_temp=6.0))
        self.assertEqual(d.rule, const.RULE_SAFETY)

    def test_preset_below_frost(self) -> None:
        levels = dict(LEVELS, away=5.0)
        d = engine.decide(inputs(presence="far", level_temp=levels.get))
        self.assertEqual((d.rule, d.target.temperature), (const.RULE_SAFETY, 7.0))

    def test_valve_exercise_not_clamped(self) -> None:
        d = engine.decide(inputs(valve_exercise=True, max_temp=25.0))
        self.assertEqual(d.rule, const.RULE_VALVE_EXERCISE)


class HierarchyTest(unittest.TestCase):
    def test_valve_exercise_in_every_mode_but_not_with_window_or_pause(self) -> None:
        for kwargs in (
            {"mode": const.MODE_SUMMER},
            {"season_active": False},
            {"mode": const.MODE_OFF},
        ):
            d = engine.decide(inputs(valve_exercise=True, **kwargs))
            self.assertEqual(d.rule, const.RULE_VALVE_EXERCISE, kwargs)
        d = engine.decide(inputs(valve_exercise=True, window_open=True))
        self.assertEqual(d.rule, const.RULE_WINDOW)
        d = engine.decide(inputs(valve_exercise=True, paused=True))
        self.assertEqual(d.rule, const.RULE_PAUSE)

    def test_maximum_applies_to_manual_changes_and_pause(self) -> None:
        for kwargs in ({"override_active": True}, {"paused": True}):
            d = engine.decide(inputs(device_setpoint=30.0, max_temp=25.0, **kwargs))
            self.assertEqual(d.rule, const.RULE_MAX, kwargs)
            self.assertEqual(d.target.temperature, 25.0)
        # A level above the maximum is sent as the maximum.
        levels = dict(LEVELS, comfort=27.0)
        d = engine.decide(inputs(schedule_preset="comfort", level_temp=levels.get, max_temp=25.0))
        self.assertEqual(
            (d.rule, d.target.kind, d.target.temperature), (const.RULE_MAX, "temperature", 25.0)
        )
        # Below the maximum the manual change is respected.
        d = engine.decide(inputs(override_active=True, device_setpoint=24.0, max_temp=25.0))
        self.assertEqual(d.rule, const.RULE_OVERRIDE)


class OptimalPeriodTest(unittest.TestCase):
    """The optimal start / stop is worked out with the weather expected while it runs."""

    def test_colder_forecast_starts_earlier(self) -> None:
        # Rate 2 °C/h at 5 °C outdoor, 1 °C/h at -5 °C; 2 °C to gain.
        def minutes_for(out):
            return 2 / (1.0 if out is not None and out < 0 else 2.0) * 60

        minutes, out, source = engine.optimal_period(
            180, minutes_for, lambda length: (-5.0, "forecast"), 5.0
        )
        self.assertEqual((minutes, out, source), (120, -5.0, "forecast"))

    def test_without_forecast_the_value_of_now(self) -> None:
        calls = []

        def outdoor_for(length):
            calls.append(length)
            return 5.0, "now"

        minutes, out, source = engine.optimal_period(180, lambda out: 60, outdoor_for, 5.0)
        self.assertEqual((minutes, out, source), (60, 5.0, "now"))
        self.assertEqual(calls, [60])

    def test_capped_and_not_learned(self) -> None:
        self.assertEqual(
            engine.optimal_period(30, lambda out: None, lambda length: (0.0, "forecast"), 3.0)[0],
            30,
        )
        self.assertEqual(
            engine.optimal_period(30, lambda out: 90, lambda length: (0.0, "forecast"), 3.0)[0],
            30,
        )

    def test_nothing_needed(self) -> None:
        self.assertEqual(
            engine.optimal_period(60, lambda out: 0.0, lambda length: (0.0, "forecast"), 3.0),
            (0.0, 3.0, "now"),
        )

    def test_passes_follow_the_period(self) -> None:
        # The forecast depends on how far back the period reaches.
        seen = []

        def outdoor_for(length):
            seen.append(length)
            return (-4.0 if length > 60 else 0.0), "forecast"

        def minutes_for(out):
            return 90 if out is not None and out <= 0 and out > -4 else (120 if out == -4.0 else 50)

        minutes, out, _ = engine.optimal_period(180, minutes_for, outdoor_for, 6.0)
        # 50 min (now 6 °C) -> 0 °C -> 90 min -> -4 °C -> 120 min (last pass).
        self.assertEqual(seen, [50, 90])
        self.assertEqual((minutes, out), (120, -4.0))


class NoProfileTest(unittest.TestCase):
    def test_day_without_profile_is_frost(self) -> None:
        d = engine.decide(inputs(schedule_preset=const.PRESET_FROST, offsets=[("tariff", 3.0)]))
        self.assertEqual(d.key, "no_profile")
        self.assertEqual(d.rule, const.RULE_SCHEDULE)
        self.assertEqual(d.target.kind, engine.KIND_TEMPERATURE)
        # Not adjusted: the frost temperature itself.
        self.assertEqual(d.target.temperature, inputs().frost_temp)
        # Far away or on vacation on such a day: frost protection is above away.
        self.assertEqual(
            engine.decide(
                inputs(schedule_preset=const.PRESET_FROST, presence=const.PRESENCE_FAR)
            ).key,
            "no_profile",
        )
        self.assertEqual(
            engine.decide(inputs(schedule_preset=const.PRESET_FROST, vacation_active=True)).key,
            "no_profile",
        )
        # Rules above the schedule still apply.
        self.assertEqual(
            engine.decide(inputs(schedule_preset=const.PRESET_FROST, window_open=True)).rule,
            const.RULE_WINDOW,
        )


class NearbyLimitTest(unittest.TestCase):
    def test_not_above_the_schedule_when_checked(self) -> None:
        near = {"presence": const.PRESENCE_NEARBY, "nearby_mode": const.NEARBY_TEMPERATURE}
        # Nearby 20 °C, schedule sleep (lower): unchecked keeps 20 °C.
        d = engine.decide(inputs(schedule_preset="sleep", nearby_temp=20.0, **near))
        self.assertEqual((d.key, d.target.temperature), ("nearby_temperature", 20.0))
        # Checked: the schedule (sleep) applies.
        d = engine.decide(
            inputs(schedule_preset="sleep", nearby_temp=20.0, nearby_limit=True, **near)
        )
        self.assertEqual((d.key, d.target.preset), ("nearby_schedule", "sleep"))
        # Checked, schedule higher (home): the nearby temperature stays.
        d = engine.decide(
            inputs(schedule_preset="home", nearby_temp=17.0, nearby_limit=True, **near)
        )
        self.assertEqual(d.key, "nearby_temperature")
        # Checked, a day without a profile: frost protection.
        d = engine.decide(
            inputs(schedule_preset=const.PRESET_FROST, nearby_temp=20.0, nearby_limit=True, **near)
        )
        self.assertEqual(d.key, "no_profile")


class MaxRoomTest(unittest.TestCase):
    def test_relay_off_at_the_maximum_in_a_pause_or_manual_change(self) -> None:
        maximum = inputs().max_temp
        for extra in ({"paused": True}, {"override_active": True}):
            hot = engine.decide(inputs(on_off=True, current_temp=maximum + 5, **extra))
            self.assertEqual((hot.rule, hot.key), (const.RULE_MAX, "max_room"))
            self.assertEqual(hot.target.kind, engine.KIND_OFF)
            # At the maximum too; below it nothing is sent (it stays off).
            self.assertEqual(
                engine.decide(inputs(on_off=True, current_temp=maximum, **extra)).key, "max_room"
            )
            below = engine.decide(inputs(on_off=True, current_temp=maximum - 0.1, **extra))
            self.assertEqual(below.target.kind, engine.KIND_NONE)
            # Thermostats with a set point are checked through it, not like this.
            self.assertNotEqual(
                engine.decide(inputs(on_off=False, current_temp=maximum + 5, **extra)).key,
                "max_room",
            )


class OffNotAdjustedTest(unittest.TestCase):
    def test_summer_and_out_of_season_frost_not_adjusted(self) -> None:
        # A device without off gets the frost temperature; the PV surplus etc.
        # must not raise it.
        offsets = [("pv", 0.5), ("compensation", 1.0)]
        for extra in ({"mode": const.MODE_SUMMER}, {"season_active": False}):
            d = engine.decide(inputs(supports_off=False, offsets=offsets, **extra))
            self.assertEqual(d.target.temperature, inputs().frost_temp, extra)


class SensorFallbackTest(unittest.TestCase):
    def test_eco_never_above_the_schedule(self) -> None:
        self.assertEqual(engine.decide(inputs(sensor_failed=True)).key, "sensor_fallback")
        for preset in ("away", "eco"):
            d = engine.decide(inputs(sensor_failed=True, schedule_preset=preset))
            self.assertEqual((d.key, d.target.preset), ("sensor_fallback_schedule", preset))


class OptimalTest(unittest.TestCase):
    def test_start(self) -> None:
        change = NOW + timedelta(minutes=50)
        preset, rule = engine.optimal_schedule(
            NOW, "sleep", change, "home", 20.5, LEVELS.get, 45.0, True, 120, False, 30
        )
        # The room needs 45 minutes; 50 minutes remain -> not yet.
        self.assertEqual((preset, rule), ("sleep", const.RULE_SCHEDULE))
        preset, rule = engine.optimal_schedule(
            NOW, "sleep", change, "home", 20.0, LEVELS.get, 60.0, True, 120, False, 30
        )
        self.assertEqual((preset, rule), ("home", const.RULE_OPTIMAL_START))

    def test_start_not_learned(self) -> None:
        # Nothing to heat (or no estimate): no optimal start.
        change = NOW + timedelta(minutes=10)
        for needed in (None, 0.0):
            preset, rule = engine.optimal_schedule(
                NOW, "sleep", change, "home", 20.0, LEVELS.get, needed, True, 120, False, 30
            )
            self.assertEqual((preset, rule), ("sleep", const.RULE_SCHEDULE))

    def test_start_capped(self) -> None:
        change = NOW + timedelta(minutes=90)
        preset, _ = engine.optimal_schedule(
            NOW, "away", change, "home", 10.0, LEVELS.get, 660.0, True, 60, False, 30
        )
        self.assertEqual(preset, "away")

    def test_stop(self) -> None:
        change = NOW + timedelta(minutes=20)
        preset, rule = engine.optimal_schedule(
            NOW, "home", change, "sleep", 22.0, LEVELS.get, None, False, 120, True, 30
        )
        self.assertEqual((preset, rule), ("sleep", const.RULE_OPTIMAL_STOP))

    def test_start_continues_once_started(self) -> None:
        # Warm early: without the start already running it would fall back to sleep.
        change = NOW + timedelta(minutes=20)
        args = (NOW, "sleep", change, "home", 21.9, LEVELS.get, 6.0, True, 120, False, 30)
        self.assertEqual(engine.optimal_schedule(*args)[0], "sleep")
        preset, rule = engine.optimal_schedule(*args, True)
        self.assertEqual((preset, rule), ("home", const.RULE_OPTIMAL_START))

    def test_started_start_is_still_overridden(self) -> None:
        d = engine.decide(inputs(schedule_rule=const.RULE_OPTIMAL_START, window_open=True))
        self.assertEqual(d.rule, const.RULE_WINDOW)

    def test_stop_from_learned_cooling(self) -> None:
        change = NOW + timedelta(minutes=50)
        args = (NOW, "home", change, "sleep", 22.0, LEVELS.get, None, False, 120, True, 90)
        # Learned: the room stays in comfort 40 minutes -> not yet with 50 left.
        self.assertEqual(engine.optimal_schedule(*args, False, 40.0)[0], "home")
        self.assertEqual(engine.optimal_schedule(*args, False, 55.0)[0], "sleep")
        # Never earlier than the maximum (90 minutes here).
        far = NOW + timedelta(minutes=100)
        args_far = (NOW, "home", far, "sleep", 22.0, LEVELS.get, None, False, 120, True, 90)
        self.assertEqual(engine.optimal_schedule(*args_far, False, 300.0)[0], "home")
        # Not learned yet: the maximum is used.
        self.assertEqual(engine.optimal_schedule(*args, False, None)[0], "sleep")
        # Once started it continues until the change.
        preset, rule = engine.optimal_schedule(*args, False, 10.0, True)
        self.assertEqual((preset, rule), ("sleep", const.RULE_OPTIMAL_STOP))

    def test_stop_cancelled_when_too_cold(self) -> None:
        # Comfort of home 22 °C with 0.5 tolerance: 21.5 °C.
        self.assertEqual(engine.optimal_stop_state(True, False, 21.6, 21.5), (True, True, False))
        # Colder than expected during the stop: cancelled, home until the change.
        self.assertEqual(engine.optimal_stop_state(True, False, 21.4, 21.5), (False, False, True))
        # It does not start again for that change, even when warm again.
        self.assertEqual(engine.optimal_stop_state(False, True, 22.0, 21.5), (False, False, True))
        # Below the comfort, no optimal stop starts.
        self.assertEqual(engine.optimal_stop_state(False, False, 21.4, 21.5), (False, False, False))


class VacationPreheatTest(unittest.TestCase):
    def test_schedule_applies_while_far(self) -> None:
        d = engine.decide(inputs(presence="far", vacation_preheat=True))
        self.assertEqual(d.rule, const.RULE_SCHEDULE)
        self.assertEqual(d.target.preset, "home")
        self.assertIn("preheating", d.description)
        d = engine.decide(inputs(presence="far"))
        self.assertEqual(d.rule, const.RULE_FAR)


class FrostHoldTest(unittest.TestCase):
    def test_frost_continues_while_heating(self) -> None:
        summer = {"mode": const.MODE_SUMMER}
        self.assertEqual(engine.decide(inputs(current_temp=6.9, **summer)).rule, const.RULE_SAFETY)
        held = engine.decide(inputs(current_temp=7.1, frost_holding=True, **summer))
        self.assertEqual(held.rule, const.RULE_SAFETY)
        self.assertIn("heating up", held.description)
        self.assertEqual(engine.decide(inputs(current_temp=7.1, **summer)).rule, const.RULE_SUMMER)


if __name__ == "__main__":
    unittest.main()


class ReasonKeyTest(unittest.TestCase):
    """Every decision has a reason key for the card."""

    def test_every_decision_has_a_key(self) -> None:
        import itertools

        for paused, valve, mode, window, override, presence, cutoff, current in itertools.product(
            [False, True],
            [False, True],
            [const.MODE_AUTO, const.MODE_VACATION, const.MODE_OFF, const.MODE_SUMMER],
            [False, True],
            [False, True],
            [const.PRESENCE_HOME, const.PRESENCE_NEARBY, const.PRESENCE_FAR],
            [False, True],
            [5.0, 20.0],
        ):
            d = engine.decide(
                replace(
                    inputs(),
                    paused=paused,
                    valve_exercise=valve,
                    mode=mode,
                    window_open=window,
                    override_active=override,
                    presence=presence,
                    cutoff_active=cutoff,
                    current_temp=current,
                )
            )
            self.assertTrue(d.key, d)


class EdgesTest(unittest.TestCase):
    """The limits and equalities the guide describes, exactly at the limit."""

    def test_adjustments_are_capped_at_3_degrees(self) -> None:
        # +2 and +2.5 make +4.5, capped at +3: home 22 → 25 (with a maximum of 30).
        d = engine.decide(inputs(offsets=[("a", 2.0), ("b", 2.5)], max_temp=30.0))
        self.assertAlmostEqual(d.target.temperature, 25.0)
        # −5 is capped at −3: 22 → 19.
        d = engine.decide(inputs(offsets=[("tariff_high", -5.0)]))
        self.assertAlmostEqual(d.target.temperature, 19.0)

    def test_tiny_adjustments_and_rounding(self) -> None:
        # Under 0.05 °C in total: the level stays a preset.
        d = engine.decide(inputs(offsets=[("pv", 0.03), ("tariff", 0.01)]))
        self.assertEqual((d.target.kind, d.target.preset), ("preset", "home"))
        # From 0.05 °C on: a temperature, rounded to 0.1 °C (22 + 0.33 = 22.3).
        d = engine.decide(inputs(offsets=[("pv", 0.33)]))
        self.assertEqual(d.target.kind, "temperature")
        self.assertEqual(d.target.temperature, 22.3)
        self.assertEqual(d.offsets, [("pv", 0.33)])

    def test_adjustments_described_in_the_house_unit(self) -> None:
        d = engine.decide(inputs(offsets=[("tariff_high", -1.0)], unit="°F"))
        # −1 °C is −1.8 °F; 21 °C is 69.8 °F.
        self.assertIn("tariff_high -1.8", d.description)
        self.assertEqual(engine.fmt_delta(0.5, "°F"), "+0.9")
        self.assertEqual(engine.fmt_temp(21.0, "°F"), "69.8 °F")

    def test_targets_in_words(self) -> None:
        self.assertEqual(engine.Target("preset", preset="eco").describe(), "preset eco")
        self.assertEqual(engine.Target("temperature", temperature=20.0).describe("°F"), "68.0 °F")
        self.assertEqual(
            engine.Target("temperature", preset="home", temperature=21.5).describe(),
            "21.5 °C (home)",
        )
        self.assertEqual(engine.Target("off").describe(), "off")
        self.assertEqual(engine.Target("none").describe(), "no command")

    def test_a_level_exactly_at_the_maximum_or_the_frost_protection(self) -> None:
        # Comfort 23 °C with a maximum of 23 °C: allowed as it is.
        d = engine.decide(inputs(schedule_preset="comfort", max_temp=23.0))
        self.assertEqual((d.rule, d.target.kind), (const.RULE_SCHEDULE, "preset"))
        d = engine.decide(inputs(schedule_preset="comfort", max_temp=22.9))
        self.assertEqual((d.rule, d.target.temperature), (const.RULE_MAX, 22.9))
        # Away 10 °C with frost protection at 10 °C: allowed; at 10.5 °C it is raised.
        d = engine.decide(inputs(presence="far", frost_temp=10.0))
        self.assertEqual((d.rule, d.target.kind), (const.RULE_FAR, "preset"))
        d = engine.decide(inputs(presence="far", frost_temp=10.5))
        self.assertEqual((d.rule, d.target.temperature), (const.RULE_SAFETY, 10.5))

    def test_frost_protection_starts_below_it_not_at_it(self) -> None:
        d = engine.decide(inputs(mode=const.MODE_SUMMER, current_temp=7.0))
        self.assertEqual(d.rule, const.RULE_SUMMER)
        d = engine.decide(inputs(mode=const.MODE_SUMMER, current_temp=6.9))
        self.assertEqual((d.rule, d.key), (const.RULE_SAFETY, "frost_below"))

    def test_nearby_fixed_temperature_needs_a_value(self) -> None:
        d = engine.decide(
            inputs(presence="nearby", nearby_mode=const.NEARBY_TEMPERATURE, nearby_temp=None)
        )
        self.assertEqual((d.key, d.target.preset), ("nearby", "eco"))
        d = engine.decide(
            inputs(presence="nearby", nearby_mode=const.NEARBY_TEMPERATURE, nearby_temp=16.5)
        )
        self.assertEqual((d.key, d.target.temperature), ("nearby_temperature", 16.5))

    def test_nearby_not_above_the_schedule_only_when_lower(self) -> None:
        # Sleep 19 °C on the schedule, eco 19 °C: equal, so eco (nearby) applies.
        same = dict(LEVELS, eco=19.0)
        d = engine.decide(
            inputs(
                presence="nearby", schedule_preset="sleep", nearby_limit=True, level_temp=same.get
            )
        )
        self.assertEqual((d.key, d.target.preset), ("nearby", "eco"))
        lower = dict(LEVELS, eco=19.5)
        d = engine.decide(
            inputs(
                presence="nearby", schedule_preset="sleep", nearby_limit=True, level_temp=lower.get
            )
        )
        self.assertEqual((d.key, d.target.preset), ("nearby_schedule", "sleep"))

    def test_band_edges_with_the_model(self) -> None:
        # Target 20 °C, hysteresis 0.5 °C. The heat on its way takes the room exactly
        # to 20.5 °C (the top of the band): stop now, by the model.
        self.assertEqual(engine.on_off_wanted(True, 20.2, 20.0, 0.5, lambda h: 20.5), (False, True))
        # It would fall exactly to 19.5 °C (the bottom) before the heat arrives: start now.
        self.assertEqual(engine.on_off_wanted(False, 19.8, 20.0, 0.5, lambda h: 19.5), (True, True))
        # At the edges themselves the band decides, not the model.
        self.assertEqual(
            engine.on_off_wanted(False, 19.5, 20.0, 0.5, lambda h: 99.0), (True, False)
        )
        self.assertEqual(
            engine.on_off_wanted(True, 20.5, 20.0, 0.5, lambda h: -99.0), (False, False)
        )


class OptimalEdgesTest(unittest.TestCase):
    def test_no_optimal_stop_when_it_is_off(self) -> None:
        change = NOW + timedelta(minutes=20)
        self.assertEqual(
            engine.optimal_schedule(
                NOW, "home", change, "sleep", 22.0, LEVELS.get, None, False, 120, False, 30
            ),
            ("home", const.RULE_SCHEDULE),
        )
        # Nor towards a warmer level (that is an optimal start).
        self.assertEqual(
            engine.optimal_schedule(
                NOW, "sleep", change, "home", 22.5, LEVELS.get, None, False, 120, True, 30
            ),
            ("sleep", const.RULE_SCHEDULE),
        )

    def test_exactly_on_time(self) -> None:
        # The room needs 60 minutes and 60 remain: the optimal start begins.
        change = NOW + timedelta(minutes=60)
        args = (NOW, "sleep", change, "home", 20.0, LEVELS.get)
        self.assertEqual(engine.optimal_schedule(*args, 60.0, True, 120, False, 30)[0], "home")
        self.assertEqual(engine.optimal_schedule(*args, 59.0, True, 120, False, 30)[0], "sleep")
        # The longest stop is 30 minutes and 30 remain: the optimal stop begins.
        stop = (
            NOW,
            "home",
            NOW + timedelta(minutes=30),
            "sleep",
            22.0,
            LEVELS.get,
            None,
            False,
            120,
            True,
        )
        self.assertEqual(engine.optimal_schedule(*stop, 30)[0], "sleep")
        self.assertEqual(engine.optimal_schedule(*stop, 29)[0], "home")
        # A longest stop of 0: never.
        self.assertEqual(engine.optimal_schedule(*stop, 0)[0], "home")

    def test_nothing_to_do(self) -> None:
        # The change is now, the next level is as warm, or the room is already there.
        self.assertEqual(
            engine.optimal_schedule(
                NOW, "sleep", NOW, "home", 18.0, LEVELS.get, 60.0, True, 120, False, 30
            ),
            ("sleep", const.RULE_SCHEDULE),
        )
        same = dict(LEVELS, sleep=22.0)
        self.assertEqual(
            engine.optimal_schedule(
                NOW,
                "sleep",
                NOW + timedelta(minutes=10),
                "home",
                18.0,
                same.get,
                60.0,
                True,
                120,
                False,
                30,
            )[0],
            "sleep",
        )
        self.assertEqual(
            engine.optimal_schedule(
                NOW,
                "sleep",
                NOW + timedelta(minutes=10),
                "home",
                22.0,
                LEVELS.get,
                60.0,
                True,
                120,
                False,
                30,
            )[0],
            "sleep",
        )
        # A start already running is kept only while optimal start is on.
        self.assertEqual(
            engine.optimal_schedule(
                NOW,
                "sleep",
                NOW + timedelta(minutes=10),
                "home",
                22.0,
                LEVELS.get,
                60.0,
                False,
                120,
                False,
                30,
                True,
            )[0],
            "sleep",
        )

    def test_short_period_still_follows_the_forecast(self) -> None:
        # Half a minute needed: the forecast for it is still looked up.
        minutes, out, source = engine.optimal_period(
            60, lambda out: 0.5, lambda length: (2.0, "forecast"), 5.0
        )
        self.assertEqual((minutes, out, source), (0.5, 2.0, "forecast"))
        # No forecast for the period: the value of now.
        self.assertEqual(
            engine.optimal_period(60, lambda out: 30.0, lambda length: (None, "forecast"), 5.0),
            (30.0, 5.0, "now"),
        )


class MutationGapsEngineTest(unittest.TestCase):
    """Places the mutation tests showed without a test (2.6.4)."""

    def test_unknown_level_compared_by_name(self) -> None:
        # A level with no known temperature (a preset of the thermostat): warmer
        # than eco by name, except eco itself and away.
        def levels(p):
            return None if p in ("custom", "away") else LEVELS.get(p)

        d = engine.decide(inputs(sensor_failed=True, schedule_preset="custom", level_temp=levels))
        self.assertEqual((d.rule, d.target.preset), (const.RULE_SENSOR_FALLBACK, "eco"))
        d = engine.decide(inputs(sensor_failed=True, schedule_preset="away", level_temp=levels))
        self.assertEqual(d.key, "sensor_fallback_schedule")
        self.assertEqual(d.target.preset, "away")
        # Eco known, the other unknown: still by name.
        d = engine.decide(inputs(room_unoccupied=True, schedule_preset="custom", level_temp=levels))
        self.assertEqual((d.rule, d.target.preset), (const.RULE_UNOCCUPIED, "eco"))
        # Eco unknown too, the schedule eco: not warmer than itself.
        d = engine.decide(
            inputs(room_unoccupied=True, schedule_preset="eco", level_temp=lambda p: None)
        )
        self.assertEqual((d.rule, d.target.preset), (const.RULE_SCHEDULE, "eco"))

    def test_cutoff_tells_the_temperature_it_replaces(self) -> None:
        # A preset target: the temperature of its level.
        d = engine.decide(inputs(cutoff_active=True))
        self.assertEqual(d.params["temperature"], LEVELS["home"])
        # A temperature target (someone nearby, fixed temperature): that temperature.
        d = engine.decide(
            inputs(
                cutoff_active=True,
                presence=const.PRESENCE_NEARBY,
                nearby_mode=const.NEARBY_TEMPERATURE,
                nearby_temp=18.5,
            )
        )
        self.assertEqual((d.rule, d.params["temperature"]), (const.RULE_CUTOFF, 18.5))

    def test_offsets_on_a_temperature_target(self) -> None:
        d = engine.decide(
            inputs(
                presence=const.PRESENCE_NEARBY,
                nearby_mode=const.NEARBY_TEMPERATURE,
                nearby_temp=18.5,
                offsets=[("compensation", 1.0)],
            )
        )
        self.assertEqual(d.target.kind, "temperature")
        self.assertAlmostEqual(d.target.temperature, 19.5)
        # Offsets that cancel out (below 0.05 in all): the target as it is.
        d = engine.decide(inputs(offsets=[("a", 0.5), ("b", -0.5)]))
        self.assertEqual((d.target.kind, d.target.preset), ("preset", "home"))

    def test_optimal_edges_equal_and_unknown_levels(self) -> None:
        change = NOW + timedelta(minutes=10)
        same = dict(LEVELS, sleep=22.0)
        # Started, but the next level is not warmer: no optimal start.
        self.assertEqual(
            engine.optimal_schedule(
                NOW, "sleep", change, "home", 20.0, same.get, 60.0, True, 120, False, 30, True
            ),
            ("sleep", const.RULE_SCHEDULE),
        )
        # Not warmer and not colder: no optimal stop either.
        self.assertEqual(
            engine.optimal_schedule(
                NOW, "home", change, "sleep", 22.0, same.get, None, False, 120, True, 30
            ),
            ("home", const.RULE_SCHEDULE),
        )
        # The next level unknown: nothing early.
        unknown = dict(LEVELS, home=None)
        self.assertEqual(
            engine.optimal_schedule(
                NOW, "sleep", change, "home", 18.0, unknown.get, 60.0, True, 120, False, 30
            ),
            ("sleep", const.RULE_SCHEDULE),
        )
        # A stop of one minute with half a minute left: it starts.
        soon = NOW + timedelta(seconds=30)
        self.assertEqual(
            engine.optimal_schedule(
                NOW, "home", soon, "sleep", 22.0, LEVELS.get, None, False, 120, True, 1
            ),
            ("sleep", const.RULE_OPTIMAL_STOP),
        )
        # An optimal start of a fraction of a minute counts too.
        self.assertEqual(
            engine.optimal_schedule(
                NOW, "sleep", soon, "home", 20.0, LEVELS.get, 0.75, True, 120, False, 30
            ),
            ("home", const.RULE_OPTIMAL_START),
        )

    def test_frost_exactly_at_the_limit(self) -> None:
        # Exactly at the frost temperature the room is not below it: summer stays,
        # and a frost protection that is holding says "heating up", not "below".
        summer = {"mode": const.MODE_SUMMER}
        self.assertEqual(engine.decide(inputs(current_temp=7.0, **summer)).rule, const.RULE_SUMMER)
        held = engine.decide(inputs(current_temp=7.0, frost_holding=True, **summer))
        self.assertEqual((held.rule, held.key), (const.RULE_SAFETY, "frost_holding"))
        below = engine.decide(inputs(current_temp=6.9, **summer))
        self.assertEqual((below.rule, below.key), (const.RULE_SAFETY, "frost_below"))
        # The optimal stop: exactly at the comfort floor is not below it.
        self.assertEqual(engine.optimal_stop_state(False, False, 21.5, 21.5), (True, False, False))


class KeepOpenTest(unittest.TestCase):
    """The last room that asked for heat keeps its TRVs open (house option)."""

    def test_over_the_schedule_with_the_level_it_would_have(self) -> None:
        d = engine.decide(inputs(keep_open=True, keep_open_temp=24.0))
        self.assertEqual(d.rule, const.RULE_SCHEDULE)
        self.assertEqual(d.key, "keep_open")
        self.assertEqual((d.target.kind, d.target.temperature), ("temperature", 24.0))
        # The level stays (its colour in the card) and what it would be is told.
        self.assertEqual(d.target.preset, "home")
        self.assertEqual(d.params, {"preset": "home", "temperature": 22.0})

    def test_without_the_temperature_of_the_trv_the_maximum_of_the_room(self) -> None:
        d = engine.decide(inputs(keep_open=True))
        self.assertEqual(d.target.temperature, 25.0)

    def test_never_above_the_maximum(self) -> None:
        d = engine.decide(inputs(keep_open=True, keep_open_temp=30.0))
        self.assertEqual(d.target.temperature, 25.0)

    def test_with_the_adjustments_the_adjusted_target_is_told(self) -> None:
        d = engine.decide(inputs(keep_open=True, keep_open_temp=24.0, offsets=[("sun", -1.0)]))
        self.assertEqual(
            (d.key, d.target.temperature, d.params["temperature"]), ("keep_open", 24.0, 21.0)
        )

    def test_presence_and_vacation_rules_are_kept_open_too(self) -> None:
        for kwargs in ({"presence": "nearby"}, {"presence": "far"}, {"mode": const.MODE_VACATION}):
            d = engine.decide(inputs(keep_open=True, keep_open_temp=24.0, **kwargs))
            self.assertEqual(d.key, "keep_open", kwargs)

    def test_a_stronger_rule_is_not_kept_open(self) -> None:
        for kwargs in (
            {"paused": True},
            {"window_open": True},
            {"override_active": True},
            {"valve_exercise": True},
            {"mode": const.MODE_OFF},
            {"mode": const.MODE_SUMMER},
            {"season_active": False},
            {"cutoff_active": True},
            {"schedule_preset": const.PRESET_FROST},
        ):
            d = engine.decide(inputs(keep_open=True, keep_open_temp=24.0, **kwargs))
            self.assertNotEqual(d.key, "keep_open", kwargs)

    def test_off_by_default(self) -> None:
        self.assertNotEqual(engine.decide(inputs()).key, "keep_open")
