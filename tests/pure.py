"""Load the pure-Python modules of the integration without Home Assistant.

The package ``__init__`` imports Home Assistant; the logic modules do not.
They are loaded here under a stand-alone package name so they can be tested
with nothing but the standard library.
"""

from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path

_PKG = "advanced_climate_pure"
_PATH = Path(__file__).resolve().parent.parent / "custom_components" / "advanced_climate"

if _PKG not in sys.modules:
    package = types.ModuleType(_PKG)
    package.__path__ = [str(_PATH)]
    sys.modules[_PKG] = package

const = importlib.import_module(f"{_PKG}.const")
schedule = importlib.import_module(f"{_PKG}.schedule")
presence = importlib.import_module(f"{_PKG}.presence")
engine = importlib.import_module(f"{_PKG}.engine")
outdoor = importlib.import_module(f"{_PKG}.outdoor")
learning = importlib.import_module(f"{_PKG}.learning")
mold = importlib.import_module(f"{_PKG}.mold")
sun = importlib.import_module(f"{_PKG}.sun")
trend = importlib.import_module(f"{_PKG}.trend")
source_choice = importlib.import_module(f"{_PKG}.source_choice")
