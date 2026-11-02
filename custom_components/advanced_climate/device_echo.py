"""What the integration sent to the devices, and what the devices answer.

A thermostat reports the values it was sent, sometimes late (a sleepy Zigbee
TRV), sometimes twice (some Tuya TRVs show the new value and then the old one
once more), sometimes limited by a setting of the device itself (its own
"Max temperature"). None of these is a person's change. This module keeps what
was sent and tells such reports apart; the room decides what to do with them.

It does not use Home Assistant beyond reading the states it is given, so it is
tested on its own.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from homeassistant.const import ATTR_TEMPERATURE
from homeassistant.core import State

from .util import float_attr, valid

# Attributes of a thermostat compared to tell a report from a person's change.
COMPARED = ("preset_mode", ATTR_TEMPERATURE)


def close(value: Any, sent: Any, margin: float) -> bool:
    """True when a reported temperature is a value that was sent (within the step)."""
    try:
        return abs(float(value) - float(sent)) < margin
    except (TypeError, ValueError):
        return False


def step_margin(state: State) -> float:
    """How far a reported temperature may be from the value sent (half its step)."""
    step = float_attr(state, "target_temp_step")
    return step / 2 + 0.01 if step else 0.05


class SentValues:
    """The values sent to each device, to recognise its reports of them."""

    def __init__(self, recent: timedelta, stable: timedelta) -> None:
        """``recent``: how long a sent value may still come back; ``stable``: see ``confirm``."""
        self._recent_for = recent
        self._stable_for = stable
        # The last command per device: {entity: {"state" | attribute: value}}.
        self.last: dict[str, dict[str, Any]] = {}
        # Every value sent in the last minutes (and the one shown before each
        # command): a TRV may report an older command after a newer one.
        self.recent: dict[str, list[tuple[datetime, str, Any]]] = {}
        # Since when the device shows the last value sent, per value.
        self.confirmed: dict[str, dict[str, datetime]] = {}

    # -- what is sent -------------------------------------------------------
    def start(self, entity_id: str) -> None:
        """A new command for the device: its last values start again, unconfirmed."""
        self.last[entity_id] = {}
        self.confirmed.pop(entity_id, None)

    def set_last(self, entity_id: str, values: dict[str, Any]) -> None:
        """The last values sent to a device (a relay switched on or off)."""
        self.last[entity_id] = values

    def record(self, entity_id: str, name: str, value: Any, shown: Any, now: datetime) -> None:
        """A command was sent: ``name`` set to ``value``; the device showed ``shown`` before."""
        self.last.setdefault(entity_id, {})[name] = value
        recent = [r for r in self.recent.get(entity_id, []) if now - r[0] <= self._recent_for]
        if shown is not None and shown != value:
            recent.append((now, name, shown))
        recent.append((now, name, value))
        self.recent[entity_id] = recent
        # A new value: not shown by the device yet.
        self.confirmed.get(entity_id, {}).pop(name, None)

    def replace(self, entity_id: str, name: str, value: Any) -> None:
        """What the device holds instead of the value sent (its own limit)."""
        self.last.setdefault(entity_id, {})[name] = value

    def forget(self, entity_id: str) -> None:
        """A person changed the device: from now on its values are theirs."""
        self.last.pop(entity_id, None)
        self.recent.pop(entity_id, None)
        self.confirmed.pop(entity_id, None)

    # -- what is known --------------------------------------------------------
    def last_value(self, entity_id: str, name: str) -> Any:
        """The last value sent for ``name``, None when none was."""
        return (self.last.get(entity_id) or {}).get(name)

    def is_confirmed(self, entity_id: str, name: str) -> bool:
        """The device has shown the last value sent for ``name``."""
        return name in self.confirmed.get(entity_id, {})

    def last_sent_at(self, entity_id: str, name: str) -> datetime | None:
        """When ``name`` was last sent (within the recent minutes), None when not."""
        times = [at for at, key, _v in self.recent.get(entity_id, []) if key == name]
        return max(times) if times else None

    def recent_values(self, entity_id: str, name: str, now: datetime) -> list[Any]:
        """The values of ``name`` sent (or shown before a command) in the recent minutes."""
        return [
            v
            for at, key, v in self.recent.get(entity_id, [])
            if key == name and now - at <= self._recent_for
        ]

    # -- what the device reports ---------------------------------------------
    def is_echo(self, entity_id: str, old: State, new: State, now: datetime) -> bool:
        """True when a device only reports the values the integration sent it.

        Devices that confirm a command late get a new context, so the context
        alone cannot tell them apart from a person. Every changed value we sent
        must match it, and at least one must have been sent.
        """
        sent = self.last.get(entity_id) or {}
        stable = {
            key
            for key, since in self.confirmed.get(entity_id, {}).items()
            if now - since >= self._stable_for
        }
        recent = [
            (key, value)
            for at, key, value in self.recent.get(entity_id, [])
            if now - at <= self._recent_for and key not in stable
        ]
        if not sent and not recent:
            return False
        changed: dict[str, Any] = {}
        if old.state != new.state:
            changed["state"] = new.state
        for attr in COMPARED:
            if old.attributes.get(attr) != new.attributes.get(attr):
                changed[attr] = new.attributes.get(attr)
        matched = False
        for key, value in changed.items():
            candidates = ([sent[key]] if key in sent else []) + [v for k, v in recent if k == key]
            if not candidates:
                continue
            if key == ATTR_TEMPERATURE:
                # The device may round to its own step.
                margin = step_margin(new)
                same = any(close(value, c, margin) for c in candidates)
            else:
                same = value in candidates
            if not same:
                return False
            matched = True
        return matched

    def confirm(self, entity_id: str, new: State | None, now: datetime) -> None:
        """Note since when the device shows the last value sent.

        Once it has shown it for the stable time the older values are no
        longer expected and any other value is a person's. A report of an older
        value meanwhile (a device that bounces back once) restarts that time.
        """
        sent = self.last.get(entity_id)
        if not sent or new is None or not valid(new):
            return
        confirmed = self.confirmed.setdefault(entity_id, {})
        for key, value in sent.items():
            reported = new.state if key == "state" else new.attributes.get(key)
            if key == ATTR_TEMPERATURE:
                same = close(reported, value, step_margin(new))
            else:
                same = reported == value
            if same:
                confirmed.setdefault(key, now)
            else:
                confirmed.pop(key, None)


def limit_kind(
    sent: float,
    reported: float,
    margin: float,
    *,
    target: float | None,
    exercising: bool,
    lowest_level: float | None,
) -> str | None:
    """Whether a device reports its own limit instead of the value sent ("max", "min", None).

    After a boost or the valve exercise (a value above the target) it may
    report less, but at least the target: that is its own maximum. After frost
    protection or off (a value below every level) it may report more, but below
    the lowest level: that is its own minimum. Values in the unit of the device.
    """
    if reported < sent - margin:
        if exercising or (
            target is not None and sent > target + margin and reported >= target - margin
        ):
            return "max"
    elif reported > sent + margin and lowest_level is not None and reported < lowest_level - margin:
        return "min"
    return None


class DeviceLimits:
    """Limits devices apply by themselves, below their entity range.

    E.g. "Max temperature" 25 on a Tuya TRV whose entity goes to 35. A limit
    is forgotten after a while, to see a new setting of the device.
    """

    def __init__(self, keep: timedelta) -> None:
        """``keep``: how long a learned limit is used."""
        self._keep = keep
        # {entity: {"max" | "min": (value in its unit, when learned)}}
        self.limits: dict[str, dict[str, tuple[float, datetime]]] = {}

    def get(self, entity_id: str, kind: str, now: datetime) -> tuple[float | None, bool]:
        """The limit of a device (its unit) and whether it just expired."""
        limit = self.limits.get(entity_id, {}).get(kind)
        if limit is None:
            return None, False
        value, learned = limit
        if now - learned > self._keep:
            self.limits[entity_id].pop(kind, None)
            return None, True
        return value, False

    def learn(self, entity_id: str, kind: str, value: float, now: datetime) -> float | None:
        """Keep a limit; returns the one known before (None when new)."""
        previous = self.limits.get(entity_id, {}).get(kind)
        self.limits.setdefault(entity_id, {})[kind] = (value, now)
        return previous[0] if previous is not None else None
