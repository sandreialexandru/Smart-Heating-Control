"""The card file imports its modules from the folder of the current version."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "custom_components" / "advanced_climate"
WWW = ROOT / "www"
VERSION = json.loads((ROOT / "manifest.json").read_text())["version"]
# import "x" / import ... from "x" / export ... from "x" (no "=": not a declaration)
STATIC = re.compile(
    r"""^\s*(?:import\s*|(?:import|export)\b[^;'"=]*?\bfrom\s*)["']([^"']+)["']""", re.MULTILINE
)


class CardFilesTest(unittest.TestCase):
    def test_the_card_file_loads_the_modules_of_this_version(self) -> None:
        entry = (WWW / "smart-heating-control-card.js").read_text()
        self.assertEqual(STATIC.findall(entry), [f"/advanced_climate/{VERSION}/shc/card.js"])

    def test_the_card_shows_the_version_of_the_manifest(self) -> None:
        card = (WWW / "shc" / "card.js").read_text()
        self.assertIn(f'const CARD_VERSION = "{VERSION}";', card)

    def test_only_static_imports_of_files_that_exist(self) -> None:
        # An open dashboard must not ask for a module later: after an update
        # the folder of the old version is no longer served.
        for file in sorted(WWW.rglob("*.js")):
            text = file.read_text()
            self.assertIsNone(re.search(r"\bimport\s*\(", text), f"dynamic import in {file.name}")
            for target in STATIC.findall(text):
                if target.startswith("/advanced_climate/"):
                    continue  # the entry, checked above
                self.assertTrue(
                    (file.parent / target).resolve().is_file(), f"{file.name}: {target}"
                )
