"""The choice of the heat source: by hand at once, in Automatic after the switching time."""

from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta

from tests.pure import source_choice as choice

SourceChooser = choice.SourceChooser
T0 = datetime(2026, 11, 13, 12, 0, tzinfo=UTC)
DELAY = timedelta(minutes=15)


class SourceChooserTest(unittest.TestCase):
    def test_saved_state(self) -> None:
        chooser = SourceChooser("secondary", "secondary")
        self.assertEqual((chooser.choice, chooser.active), ("secondary", "secondary"))
        chooser = SourceChooser("boiler", "pump")
        self.assertEqual((chooser.choice, chooser.active), ("auto", None))

    def test_automatic_needs_a_criterion(self) -> None:
        chooser = SourceChooser()
        self.assertEqual(chooser.effective_choice(False), "primary")
        self.assertEqual(chooser.effective_choice(True), "auto")
        self.assertEqual(chooser.wanted(T0, True, False, DELAY), "primary")

    def test_by_hand_at_once(self) -> None:
        chooser = SourceChooser("secondary", "primary")
        self.assertEqual(chooser.wanted(T0, False, True, DELAY), "secondary")

    def test_first_decision_at_once_then_after_the_delay(self) -> None:
        chooser = SourceChooser()
        self.assertEqual(chooser.wanted(T0, True, True, DELAY), "secondary")
        chooser.active = "secondary"
        later = T0 + timedelta(hours=1)
        self.assertEqual(chooser.wanted(later, False, True, DELAY), "secondary")
        self.assertEqual(chooser.switch_at(False, DELAY), later + DELAY)
        self.assertEqual(
            chooser.wanted(later + DELAY - timedelta(seconds=1), False, True, DELAY), "secondary"
        )
        self.assertEqual(chooser.wanted(later + DELAY, False, True, DELAY), "primary")
        chooser.active = "primary"
        self.assertIsNone(chooser.switch_at(False, DELAY))

    def test_unknown_criterion_keeps_the_source(self) -> None:
        chooser = SourceChooser("auto", "secondary")
        self.assertEqual(chooser.wanted(T0, None, True, DELAY), "secondary")
        self.assertIsNone(chooser.switch_at(None, DELAY))

    def test_a_restored_source_waits_for_the_delay(self) -> None:
        chooser = SourceChooser("auto", "primary")
        self.assertEqual(chooser.wanted(T0, True, True, DELAY), "primary")
        self.assertEqual(chooser.wanted(T0 + DELAY, True, True, DELAY), "secondary")
