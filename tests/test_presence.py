"""Tests for presence classification and debouncing."""

from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta

from tests.pure import presence

TZ = UTC
BUCHAREST = presence.ZoneInfo("zone.bucharest", "Bucharest", 44.4198, 26.0369, 23829)
OFFICE = presence.ZoneInfo("zone.office", "Office", 44.4377, 26.0997, 100)
BRASOV = presence.ZoneInfo("zone.parents", "Parents", 45.6427, 25.5887, 200)
ALL = [BUCHAREST, OFFICE, BRASOV]


def person(state, lat=None, lon=None):
    return presence.PersonInfo("person.x", state, lat, lon)


class ClassifyTest(unittest.TestCase):
    def classify(self, p, geometric=True):
        return presence.classify_person(p, [BUCHAREST], ALL, geometric)

    def test_states(self) -> None:
        self.assertEqual(self.classify(person("home")), "home")
        self.assertEqual(self.classify(person("Bucharest")), "nearby")
        self.assertEqual(self.classify(person("bucharest")), "nearby")
        self.assertEqual(self.classify(person("not_home")), "far")
        self.assertEqual(self.classify(person("Parents")), "far")
        self.assertIsNone(self.classify(person("unavailable")))
        self.assertIsNone(self.classify(person("unknown")))

    def test_stale_state_uses_coordinates(self) -> None:
        # not_home but the coordinates are inside Bucharest.
        self.assertEqual(self.classify(person("not_home", 44.4377, 26.0997)), "nearby")
        self.assertEqual(
            self.classify(person("not_home", 44.4377, 26.0997), geometric=False), "far"
        )

    def test_zone_inside_nearby_zone(self) -> None:
        self.assertEqual(self.classify(person("Office")), "nearby")
        self.assertEqual(self.classify(person("Office"), geometric=False), "far")


class HouseTest(unittest.TestCase):
    def test_rules(self) -> None:
        raw = presence.raw_house_presence
        self.assertEqual(raw(["home", "far"], "any", False, False), "home")
        self.assertEqual(raw(["home", "far"], "all", False, False), "nearby")
        self.assertEqual(raw(["nearby", "far"], "any", False, False), "nearby")
        self.assertEqual(raw(["far", "far"], "any", False, False), "far")
        self.assertEqual(raw(["far", None], "any", False, False), "far")
        self.assertIsNone(raw([None, None], "any", False, False))
        self.assertEqual(raw(["far"], "any", True, False), "home")
        self.assertEqual(raw(["far"], "any", False, True), "home")


class DebounceTest(unittest.TestCase):
    def test_delays(self) -> None:
        deb = presence.PresenceDebouncer()
        t0 = datetime(2026, 10, 12, 8, tzinfo=TZ)
        arrive, depart = timedelta(0), timedelta(minutes=10)
        deb.update("home", t0, arrive, depart)
        self.assertEqual(deb.current, "home")
        due = deb.update("nearby", t0 + timedelta(minutes=1), arrive, depart)
        self.assertEqual(deb.current, "home")
        self.assertEqual(due, t0 + timedelta(minutes=11))
        # Flapping back home cancels the pending departure.
        deb.update("home", t0 + timedelta(minutes=2), arrive, depart)
        self.assertIsNone(deb.pending)
        deb.update("nearby", t0 + timedelta(minutes=3), arrive, depart)
        deb.update("nearby", t0 + timedelta(minutes=13), arrive, depart)
        self.assertEqual(deb.current, "nearby")
        # Arrival is immediate.
        deb.update("home", t0 + timedelta(minutes=14), arrive, depart)
        self.assertEqual(deb.current, "home")

    def test_unknown_keeps_state(self) -> None:
        deb = presence.PresenceDebouncer()
        t0 = datetime(2026, 10, 12, 8, tzinfo=TZ)
        deb.update("far", t0, timedelta(0), timedelta(0))
        deb.update(None, t0, timedelta(0), timedelta(0))
        self.assertEqual(deb.current, "far")
        self.assertEqual(deb.far_for(t0 + timedelta(hours=3)), timedelta(hours=3))

    def test_serialize(self) -> None:
        deb = presence.PresenceDebouncer()
        t0 = datetime(2026, 10, 12, 8, tzinfo=TZ)
        deb.update("far", t0, timedelta(0), timedelta(0))
        again = presence.PresenceDebouncer.from_dict(deb.as_dict())
        self.assertEqual((again.current, again.changed_at), ("far", t0))

    def test_pending_survives_restart(self) -> None:
        deb = presence.PresenceDebouncer()
        t0 = datetime(2026, 10, 12, 8, tzinfo=TZ)
        arrive, depart = timedelta(0), timedelta(minutes=10)
        deb.update("home", t0, arrive, depart)
        deb.update("nearby", t0 + timedelta(minutes=2), arrive, depart)
        again = presence.PresenceDebouncer.from_dict(deb.as_dict())
        self.assertEqual(again.pending, "nearby")
        again.update("nearby", t0 + timedelta(minutes=12), arrive, depart)
        self.assertEqual(again.current, "nearby")

    def test_departure_counts_from_real_change(self) -> None:
        deb = presence.PresenceDebouncer()
        t0 = datetime(2026, 10, 12, 8, tzinfo=TZ)
        arrive, depart = timedelta(0), timedelta(minutes=10)
        deb.update("home", t0, arrive, depart)
        # The last person left 11 minutes ago (e.g. noticed only after a restart).
        now = t0 + timedelta(minutes=30)
        deb.update("nearby", now, arrive, depart, now - timedelta(minutes=11))
        self.assertEqual(deb.current, "nearby")
        # Unknown values keep the pending change.
        deb.update("far", now, arrive, depart)
        deb.update(None, now + timedelta(minutes=1), arrive, depart)
        self.assertEqual(deb.pending, "far")


class ArrivingTest(unittest.TestCase):
    def test_arriving(self) -> None:
        arr = presence.is_arriving
        self.assertTrue(arr(5, "towards", None, 10, 20, True))
        self.assertFalse(arr(5, "away_from", None, 10, 20, True))
        self.assertFalse(arr(15, "towards", None, 10, 20, True))
        self.assertTrue(arr(None, None, 12, 10, 20, False))
        self.assertFalse(arr(None, None, 25, 10, 20, False))
        self.assertTrue(arr(5, None, None, 10, 20, False))


if __name__ == "__main__":
    unittest.main()
