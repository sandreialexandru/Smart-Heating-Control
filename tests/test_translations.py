"""Every translation of the integration has the keys and placeholders of English."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "custom_components" / "advanced_climate"
PLACEHOLDER = re.compile(r"\{[a-z_]+\}")


def _flat(data: dict, path: tuple[str, ...] = ()) -> dict[tuple[str, ...], str]:
    out: dict[tuple[str, ...], str] = {}
    for key, value in data.items():
        if isinstance(value, dict):
            out.update(_flat(value, (*path, key)))
        else:
            out[(*path, key)] = value
    return out


class TranslationsTest(unittest.TestCase):
    def test_same_keys_and_placeholders_as_english(self) -> None:
        english = _flat(json.loads((ROOT / "translations" / "en.json").read_text()))
        strings = _flat(json.loads((ROOT / "strings.json").read_text()))
        self.assertEqual(english, strings)
        files = sorted((ROOT / "translations").glob("*.json"))
        self.assertGreaterEqual(len(files), 6)
        for file in files:
            with self.subTest(language=file.stem):
                other = _flat(json.loads(file.read_text()))
                self.assertEqual(set(other), set(english))
                for key, text in english.items():
                    self.assertEqual(
                        sorted(PLACEHOLDER.findall(other[key])),
                        sorted(PLACEHOLDER.findall(text)),
                        key,
                    )


class NotificationTextsTest(unittest.TestCase):
    """The notifications and the Repairs details have every language of the card."""

    def test_every_language_has_every_text(self) -> None:
        import importlib.util

        def load(name: str):
            spec = importlib.util.spec_from_file_location(name, ROOT / f"{name}.py")
            assert spec and spec.loader
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module

        alerts = load("alerts")
        self.assertEqual(set(alerts.TEXTS), {"en", "ro", "de", "nl", "fr", "it"})
        self.assertEqual(set(alerts.WEEKDAYS), set(alerts.TEXTS))
        for lang, texts in alerts.TEXTS.items():
            with self.subTest(language=lang):
                self.assertEqual(set(texts), set(alerts.TEXTS["en"]))
                for key, text in alerts.TEXTS["en"].items():
                    self.assertEqual(
                        sorted(PLACEHOLDER.findall(texts[key])), sorted(PLACEHOLDER.findall(text))
                    )
        self.assertEqual(alerts.language("de-CH"), "de")
        self.assertEqual(alerts.language("es"), "en")
        text = alerts.alert_text("fr", "battery_low", {"device": "TRV", "level": 9}, "x")
        self.assertEqual(text, "Batterie faible sur TRV (9 %).")
        text = alerts.alert_text(
            "de", "schedule_gap", {"days": ["sat", "sun"], "free_days": True}, "x"
        )
        self.assertIn("Samstag, Sonntag, freie Tage (Feiertage)", text)


class ScenarioTextsTest(unittest.TestCase):
    def test_every_language(self) -> None:
        source = (ROOT / "scenarios.py").read_text()
        for lang in ("en", "ro", "de", "nl", "fr", "it"):
            self.assertIn(f'    "{lang}": {{\n        "empty"', source)
