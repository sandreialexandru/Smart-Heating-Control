"""How well the optimal start hit the time of the schedule.

Pure Python (no Home Assistant): a room tells it, at each evaluation, whether
it is heating up early for the next level, and its temperature. For each
optimal start that ran up to the time of the level, it notes when the room
reached the temperature of that level, against that time:

- reached before the time: in time, so many minutes early;
- reached after it, while the level still holds: so many minutes late;
- the level ended (or another rule took over) without reaching it: not reached.

An optimal start that stopped before the time (someone left, a window, a
manual change...) is not counted: it did not get to try.
"""

from __future__ import annotations

from collections import deque
from datetime import UTC, datetime
from typing import Any


class PreheatTracker:
    """The optimal starts of a room and how they ended."""

    def __init__(self, stored: list[dict[str, Any]] | None, keep: int) -> None:
        """The results kept (the newest ``keep``)."""
        self.results: deque[dict[str, Any]] = deque(stored or [], maxlen=keep)
        # The one running or waiting for the room to get there.
        self._active: dict[str, Any] | None = None
        # One that got there late: shown while its level still holds.
        self._late: dict[str, Any] | None = None

    def observe(
        self,
        now: datetime,
        preheating: bool,
        change_at: datetime | None,
        preset: str | None,
        target: float | None,
        current: float | None,
        holding: str | None,
    ) -> None:
        """One evaluation of the room.

        ``preheating``: the decision is the optimal start, for the level
        ``preset`` (``target`` °C) of ``change_at``. Else ``holding`` is the
        level the schedule holds now (None when another rule decides).
        """
        if self._late is not None and holding != self._late["preset"]:
            self._late = None
        active = self._active
        if preheating and change_at is not None and preset is not None and target is not None:
            if active is None or active["at"] != change_at:
                active = self._active = {
                    "at": change_at,
                    "preset": preset,
                    "target": target,
                    "started": now,
                    "reached": None,
                }
            active["target"] = target
            if active["reached"] is None and current is not None and current >= target:
                active["reached"] = now
            return
        if active is None:
            return
        if now < active["at"]:
            # Stopped before its time: it did not get to try.
            self._active = None
            return
        if active["reached"] is not None:
            self._note(active, active["reached"])
            return
        if holding != active["preset"]:
            # The level is over (or another rule decides): not reached.
            self._note(active, None)
            return
        if current is not None and current >= active["target"]:
            self._note(active, now)

    def status(self, now: datetime) -> dict[str, Any] | None:
        """What the room shows of its optimal start now, or None.

        - ``early``: it got there before the time of the level (until that time);
        - ``late``: the time of the level is past and it still heats to it;
        - ``reached_late``: it got there late (while that level holds).
        """
        active = self._active
        if active is not None:
            if active["reached"] is not None and now < active["at"]:
                return self._shown("early", active, active["reached"])
            if active["reached"] is None and now >= active["at"]:
                return self._shown("late", active, None)
            return None
        late = self._late
        return self._shown("reached_late", late, late["reached"]) if late else None

    @staticmethod
    def _shown(state: str, item: dict[str, Any], reached: datetime | None) -> dict[str, Any]:
        return {
            "state": state,
            "at": item["at"].astimezone(UTC).isoformat(),
            "preset": item["preset"],
            "target": item["target"],
            "reached": reached.astimezone(UTC).isoformat() if reached else None,
        }

    def _note(self, active: dict[str, Any], reached: datetime | None) -> None:
        self._active = None
        if reached is not None and reached > active["at"]:
            self._late = {**active, "reached": reached}
        self.results.append(
            {
                "at": active["at"].astimezone(UTC).isoformat(),
                "preset": active["preset"],
                "started": active["started"].astimezone(UTC).isoformat(),
                # Minutes after the time of the level (before it: negative).
                "offset": None
                if reached is None
                else round((reached - active["at"]).total_seconds() / 60),
            }
        )
