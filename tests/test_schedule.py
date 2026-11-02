"""Tests for schedule parsing and lookup."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import unittest

from tests.pure import const, schedule

TZ = timezone(timedelta(hours=3))
PRESETS = const.PRESETS


def weekday_info(day: date) -> tuple[bool, str | None]:
    return day.weekday() < 5, None


class ParseTest(unittest.TestCase):
    def test_parse_default(self) -> None:
        profiles = schedule.parse_schedule(const.DEFAULT_SCHEDULE, PRESETS)
        self.assertEqual(list(profiles), ["workday", "weekend"])
        self.assertEqual(profiles["workday"][1].minute, 6 * 60)
        self.assertEqual(profiles["workday"][1].preset, "home")

    def test_roundtrip(self) -> None:
        profiles = schedule.parse_schedule(const.DEFAULT_SCHEDULE, PRESETS)
        text = schedule.format_schedule(profiles)
        self.assertEqual(schedule.parse_schedule(text, PRESETS), profiles)

    def test_case_and_comments(self) -> None:
        profiles = schedule.parse_schedule(
            "# comment\nWorkday: 06:00 HOME, 00:00 Sleep  # trailing\n", PRESETS
        )
        self.assertEqual([s.preset for s in profiles["workday"]], ["sleep", "home"])

    def test_errors(self) -> None:
        for text in (
            "",
            "workday 06:00 home",
            "workday: 25:00 home",
            "workday: 06:00 boost",
            "workday: 06:00 home, 06:00 sleep",
            "workday: 06:00 home\nworkday: 07:00 home",
            "workday: ",
        ):
            with self.subTest(text=text), self.assertRaises(schedule.ScheduleError):
                schedule.parse_schedule(text, PRESETS)

    def test_custom_names(self) -> None:
        profiles = schedule.parse_schedule("workday: 06:00 Day, 22:00 Night", ["Day", "Night"])
        self.assertEqual(profiles["workday"][0].preset, "Day")


class LookupTest(unittest.TestCase):
    def setUp(self) -> None:
        self.sched = schedule.Schedule(schedule.parse_schedule(const.DEFAULT_SCHEDULE, PRESETS))

    def test_workday_morning(self) -> None:
        # 2026-10-12 is a Monday.
        state = self.sched.lookup(datetime(2026, 10, 12, 7, 0, tzinfo=TZ), weekday_info)
        self.assertEqual(state.preset, "home")
        self.assertEqual(state.profile, "workday")
        self.assertEqual(state.next_change, datetime(2026, 10, 12, 22, 0, tzinfo=TZ))
        self.assertEqual(state.next_preset, "sleep")

    def test_friday_night_to_saturday(self) -> None:
        state = self.sched.lookup(datetime(2026, 10, 16, 23, 0, tzinfo=TZ), weekday_info)
        self.assertEqual(state.preset, "sleep")
        # Saturday 00:00 is still sleep, so the next change is Saturday 08:00.
        self.assertEqual(state.next_change, datetime(2026, 10, 17, 8, 0, tzinfo=TZ))
        self.assertEqual(state.next_preset, "home")

    def test_weekend(self) -> None:
        state = self.sched.lookup(datetime(2026, 10, 17, 7, 59, tzinfo=TZ), weekday_info)
        self.assertEqual((state.profile, state.preset), ("weekend", "sleep"))
        state = self.sched.lookup(datetime(2026, 10, 17, 8, 0, tzinfo=TZ), weekday_info)
        self.assertEqual(state.preset, "home")

    def test_forced_and_weekday_profiles(self) -> None:
        sched = schedule.Schedule(
            schedule.parse_schedule(
                const.DEFAULT_SCHEDULE + "\nfri: 00:00 sleep, 07:00 comfort\nparty: 00:00 activity",
                PRESETS,
            )
        )
        friday = datetime(2026, 10, 16, 9, 0, tzinfo=TZ)
        self.assertEqual(sched.lookup(friday, weekday_info).preset, "comfort")
        forced = sched.lookup(friday, lambda d: (True, "party"))
        self.assertEqual((forced.profile, forced.preset), ("party", "activity"))

    def test_holiday_uses_weekend(self) -> None:
        state = self.sched.lookup(datetime(2026, 12, 1, 7, 0, tzinfo=TZ), lambda d: (False, None))
        self.assertEqual((state.profile, state.preset), ("weekend", "sleep"))

    def test_missing_first_slot_wraps(self) -> None:
        sched = schedule.Schedule(
            schedule.parse_schedule("workday: 06:00 home, 22:00 sleep", PRESETS)
        )
        state = sched.lookup(datetime(2026, 10, 12, 3, 0, tzinfo=TZ), weekday_info)
        self.assertEqual(state.preset, "sleep")
        self.assertEqual(state.slot_start, datetime(2026, 10, 11, 22, 0, tzinfo=TZ))

    def test_day_boundary(self) -> None:
        sched = schedule.Schedule(
            schedule.parse_schedule(
                "workday: 04:00 home, 23:00 sleep\nweekend: 04:00 sleep, 10:00 home",
                PRESETS,
            ),
            day_boundary=4 * 60,
        )
        # Saturday 02:00 still belongs to Friday (workday) -> sleep from 23:00.
        state = sched.lookup(datetime(2026, 10, 17, 2, 0, tzinfo=TZ), weekday_info)
        self.assertEqual((state.profile, state.preset), ("workday", "sleep"))
        self.assertEqual(state.next_change, datetime(2026, 10, 17, 10, 0, tzinfo=TZ))

    def test_upcoming(self) -> None:
        start = datetime(2026, 10, 12, 5, 0, tzinfo=TZ)
        changes = self.sched.upcoming(start, weekday_info, timedelta(hours=24))
        self.assertEqual(
            changes,
            [
                (datetime(2026, 10, 12, 6, 0, tzinfo=TZ), "home"),
                (datetime(2026, 10, 12, 22, 0, tzinfo=TZ), "sleep"),
            ],
        )

    def test_dict_roundtrip(self) -> None:
        data = schedule.profiles_to_dict(self.sched.profiles)
        self.assertEqual(schedule.profiles_from_dict(data, PRESETS), self.sched.profiles)


if __name__ == "__main__":
    unittest.main()


TEXT = (
    "workday: 00:00 sleep, 06:00 home, 22:00 sleep\n"
    "weekend: 00:00 sleep, 08:00 home, 23:00 sleep\n"
    "workday2: 00:00 sleep, 06:00 comfort, 22:00 sleep\n"
    "wednesday: 00:00 sleep, 09:00 activity, 22:00 sleep\n"
    "week: 00:00 sleep, 07:00 home, 22:00 sleep"
)
# 2026-10-12 Monday, 2026-10-14 Wednesday, 2026-10-15 Thursday, 2026-10-17 Saturday.
MON, WED, THU, SAT = (datetime(2026, 10, d, 12, 0, tzinfo=TZ) for d in (12, 14, 15, 17))


class ProfileDaysTest(unittest.TestCase):
    def _sched(self, days: dict | None) -> object:
        return schedule.Schedule(schedule.parse_schedule(TEXT, PRESETS), 0, days)

    def test_defaults_keep_the_earlier_selection(self) -> None:
        days = schedule.default_profile_days(["workday", "weekend", "fri", "party"])
        self.assertEqual(days["workday"], {"days": "workday", "enabled": True})
        self.assertEqual(days["weekend"], {"days": "weekend", "enabled": True})
        self.assertEqual(days["fri"], {"days": ["fri"], "enabled": True})
        self.assertEqual(days["party"], {"days": "all", "enabled": False})
        # Only one of workday / weekend: it is for all days, as before.
        self.assertEqual(
            schedule.default_profile_days(["workday", "x"])["workday"],
            {"days": "all", "enabled": True},
        )
        # No known name: the first profile for all days.
        only = schedule.default_profile_days(["home_office", "late"])
        self.assertEqual(only["home_office"], {"days": "all", "enabled": True})
        self.assertFalse(only["late"]["enabled"])

    def test_selection(self) -> None:
        sched = self._sched(
            {
                "workday2": {"days": "workday", "enabled": True},
                "weekend": {"days": "weekend", "enabled": True},
                "wednesday": {"days": ["wed"], "enabled": True},
            }
        )
        self.assertEqual(sched.lookup(MON, weekday_info).profile, "workday2")
        self.assertEqual(sched.lookup(MON, weekday_info).preset, "comfort")
        # A profile of a weekday is above the workday profile on that day only.
        self.assertEqual(sched.lookup(WED, weekday_info).profile, "wednesday")
        self.assertEqual(sched.lookup(THU, weekday_info).profile, "workday2")
        self.assertEqual(sched.lookup(SAT, weekday_info).profile, "weekend")
        # A holiday on a weekday uses the weekend profile.
        self.assertEqual(sched.lookup(MON, lambda d: (False, None)).profile, "weekend")
        # A calendar event forces any profile, also one that is off.
        self.assertEqual(sched.lookup(MON, lambda d: (True, "week")).profile, "week")

    def test_all_days(self) -> None:
        sched = self._sched({"week": {"days": "all", "enabled": True}})
        for moment in (MON, WED, SAT):
            self.assertEqual(sched.lookup(moment, weekday_info).profile, "week")

    def test_uncovered_day_is_frost(self) -> None:
        sched = self._sched({"workday": {"days": "workday", "enabled": True}})
        state = sched.lookup(SAT, weekday_info)
        self.assertIsNone(state.profile)
        self.assertEqual(state.preset, const.PRESET_FROST)
        # Friday evening: the next change is the frost of Saturday 00:00.
        friday = datetime(2026, 10, 16, 23, 0, tzinfo=TZ)
        state = sched.lookup(friday, weekday_info)
        self.assertEqual(state.next_change, datetime(2026, 10, 17, 0, 0, tzinfo=TZ))
        self.assertEqual(state.next_preset, const.PRESET_FROST)
        # Sunday: Monday 00:00 is sleep again.
        sunday = datetime(2026, 10, 18, 12, 0, tzinfo=TZ)
        state = sched.lookup(sunday, weekday_info)
        self.assertEqual((state.preset, state.next_preset), (const.PRESET_FROST, "sleep"))
        self.assertEqual(state.next_change, datetime(2026, 10, 19, 0, 0, tzinfo=TZ))

    def test_overlap(self) -> None:
        o = schedule.overlap
        self.assertTrue(o("all", "workday"))
        self.assertTrue(o("all", "weekend"))
        self.assertTrue(o("workday", "workday"))
        self.assertFalse(o("workday", "weekend"))
        self.assertFalse(o(["wed"], "workday"))
        self.assertFalse(o(["wed"], "all"))
        self.assertTrue(o(["wed", "fri"], ["fri"]))
        self.assertFalse(o(["wed"], ["thu"]))

    def test_validate_and_normalize(self) -> None:
        names = ["workday", "weekend", "workday2"]
        with self.assertRaises(schedule.ScheduleError):
            schedule.validate_profile_days(
                {
                    "workday": {"days": "workday", "enabled": True},
                    "workday2": {"days": "workday", "enabled": True},
                },
                names,
            )
        for bad in (
            {"nope": {"days": "all", "enabled": True}},
            {"workday": {"days": [], "enabled": True}},
            {"workday": {"days": ["xyz"], "enabled": True}},
            {"workday": {"days": "daily"}},
        ):
            with self.assertRaises(schedule.ScheduleError):
                schedule.validate_profile_days(bad, names)
        ok = schedule.validate_profile_days(
            {"workday2": {"days": ["fri", "mon"], "enabled": True}}, names
        )
        self.assertEqual(ok["workday2"], {"days": ["mon", "fri"], "enabled": True})
        # Profiles without data are off; overlapping saved data: the later one is turned off.
        self.assertEqual(ok["workday"], {"days": "all", "enabled": False})
        fixed = schedule.normalize_profile_days(
            {
                "workday": {"days": "all", "enabled": True},
                "weekend": {"days": "weekend", "enabled": True},
            },
            names,
        )
        self.assertFalse(fixed["weekend"]["enabled"])

    def test_uncovered_days(self) -> None:
        u = schedule.uncovered_days
        self.assertEqual(
            u(
                {
                    "a": {"days": "workday", "enabled": True},
                    "b": {"days": "weekend", "enabled": True},
                }
            ),
            {"days": [], "free_days": False, "workdays": False},
        )
        self.assertEqual(
            u({"a": {"days": "workday", "enabled": True}}),
            {"days": ["sat", "sun"], "free_days": True, "workdays": False},
        )
        self.assertEqual(
            u(
                {
                    "a": {"days": ["mon", "wed"], "enabled": True},
                    "b": {"days": "weekend", "enabled": True},
                }
            ),
            {"days": ["tue", "thu", "fri"], "free_days": False, "workdays": True},
        )
        self.assertEqual(u({"a": {"days": "all", "enabled": True}})["days"], [])


class ClockChangeTest(unittest.TestCase):
    """A slot at 03:30 on the days the clock changes (Romania: 03:00 / 04:00)."""

    def setUp(self) -> None:
        from zoneinfo import ZoneInfo

        self.zone = ZoneInfo("Europe/Bucharest")
        profiles = schedule.parse_schedule(
            "all: 00:00 sleep, 03:30 home, 22:00 sleep", const.PRESETS
        )
        self.sched = schedule.Schedule(profiles, 0, {"all": {"days": "all", "enabled": True}})

    def lookup(self, utc: datetime) -> schedule.ScheduleState:
        return self.sched.lookup(utc.astimezone(self.zone), lambda _day: (True, None))

    def test_repeated_autumn_hour_does_not_go_back(self) -> None:
        # 25 October 2026: 04:00 summer time (01:00 UTC) becomes 03:00 again.
        # 03:30 happens first at 00:30 UTC; at 03:10 the second time (01:10
        # UTC) home stays and the next change is not in the past.
        utc = timezone.utc
        before = self.lookup(datetime(2026, 10, 25, 0, 10, tzinfo=utc))
        self.assertEqual(before.preset, "sleep")
        self.assertEqual(before.next_change, datetime(2026, 10, 25, 0, 30, tzinfo=utc))
        again = self.lookup(datetime(2026, 10, 25, 1, 10, tzinfo=utc))
        self.assertEqual(again.preset, "home")
        self.assertGreater(again.next_change, datetime(2026, 10, 25, 1, 10, tzinfo=utc))
        self.assertEqual(again.next_change, datetime(2026, 10, 25, 20, 0, tzinfo=utc))

    def test_skipped_spring_hour_starts_when_it_ends(self) -> None:
        # 28 March 2027: 03:00 (01:00 UTC) becomes 04:00; 03:30 does not exist,
        # so home starts at 04:00 and is predicted for then.
        utc = timezone.utc
        before = self.lookup(datetime(2027, 3, 28, 0, 50, tzinfo=utc))
        self.assertEqual(before.preset, "sleep")
        self.assertEqual(before.next_change, datetime(2027, 3, 28, 1, 0, tzinfo=utc))
        self.assertEqual(self.lookup(datetime(2027, 3, 28, 1, 0, tzinfo=utc)).preset, "home")

    def test_plan_across_the_change(self) -> None:
        start = datetime(2026, 10, 24, 18, 0, tzinfo=timezone.utc).astimezone(self.zone)
        changes = self.sched.upcoming(start, lambda _day: (True, None), timedelta(hours=36))
        self.assertEqual(
            [(t.astimezone(timezone.utc), p) for t, p in changes],
            [
                (datetime(2026, 10, 24, 19, 0, tzinfo=timezone.utc), "sleep"),
                (datetime(2026, 10, 25, 0, 30, tzinfo=timezone.utc), "home"),
                (datetime(2026, 10, 25, 20, 0, tzinfo=timezone.utc), "sleep"),
                (datetime(2026, 10, 26, 1, 30, tzinfo=timezone.utc), "home"),
            ],
        )
