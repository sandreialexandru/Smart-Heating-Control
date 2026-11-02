"""Open windows: from the sensors (or a quick drop of the room temperature), with delays.

Plain Python, no Home Assistant: the room gives the readings and the times.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from .const import TEMP_DROP_HOLD_MINUTES

# How long a quick drop of the room temperature counts as an open window.
DROP_HOLD = timedelta(minutes=TEMP_DROP_HOLD_MINUTES)
# A value read at most this long before the drop window still counts as its start.
DROP_STALE = timedelta(minutes=15)


class TemperatureDrop:
    """An open window found from a quick drop of the room temperature."""

    def __init__(self) -> None:
        """No readings yet."""
        # Readings as runs of the same value: [first seen, last seen, value]. Kept
        # by time (the drop window plus 15 minutes), not by count, so a house that
        # reads the temperature often does not shorten the window.
        self.samples: list[list] = []
        # Which sensors gave the room temperature (a change of them is not a drop).
        self.sources: tuple | None = None
        # Until when the drop counts as an open window.
        self.until: datetime | None = None

    def update(
        self,
        now: datetime,
        sources: tuple,
        value: float | None,
        *,
        enabled: bool,
        minutes: float,
        degrees: float,
    ) -> None:
        """A reading of the room temperature (``value``) from ``sources``.

        When a sensor stops or comes back, or the room falls back to the device
        sensor, the value jumps: the detection starts again from the new value
        instead of taking the jump for an open window.
        """
        if sources != self.sources:
            self.sources = sources
            self.samples.clear()
        if value is None:
            return
        samples = self.samples
        if samples and samples[-1][2] == value:
            samples[-1][1] = now  # the same value read again
        else:
            samples.append([now, now, value])
        keep = timedelta(minutes=minutes) + DROP_STALE
        while len(samples) > 1 and now - samples[0][1] > keep:
            samples.pop(0)
        if enabled:
            self._check(now, value, timedelta(minutes=minutes), degrees)

    def _check(self, now: datetime, value: float, window: timedelta, degrees: float) -> None:
        """Count a drop of ``degrees`` within ``window`` as an open window."""
        if self.until is not None and now < self.until:
            return  # already holding
        # Every value read inside the window (a run that lasted into it counts:
        # it was the value at the start of the window).
        recent = [v for _first, last, v in self.samples if now - last <= window]
        # The value valid just before the window, if it was read at most 15 minutes
        # before it (sensors report on change; an older value may be stale).
        before = [(last, v) for _first, last, v in self.samples if now - last > window]
        if before and now - before[-1][0] <= window + DROP_STALE:
            recent.append(before[-1][1])
        if recent and max(recent) - value >= degrees:
            self.until = now + DROP_HOLD

    def active(self, now: datetime) -> bool:
        """True while a drop counts as an open window."""
        return self.until is not None and now < self.until


class WindowState:
    """The window state of a room after the open and close delays."""

    def __init__(self) -> None:
        """Closed."""
        self.open = False
        # When the window was seen open / closed, before the delay ended.
        self.raw_since: datetime | None = None
        self.closed_since: datetime | None = None
        # When it counted as open (for the alert of a long open window).
        self.opened_at: datetime | None = None

    def update(
        self, now: datetime, raw: bool, open_delay: timedelta, close_delay: timedelta
    ) -> tuple[datetime | None, bool]:
        """The window is ``raw`` open now: (when to check again, whether it just closed)."""
        due: datetime | None = None
        closed = False
        if raw:
            self.closed_since = None
            if not self.open:
                if self.raw_since is None:
                    self.raw_since = now
                if now - self.raw_since >= open_delay:
                    self.open = True
                    self.opened_at = now
                else:
                    due = self.raw_since + open_delay
        else:
            self.raw_since = None
            if self.open:
                if self.closed_since is None:
                    self.closed_since = now
                if now - self.closed_since >= close_delay:
                    self.open = False
                    self.opened_at = None
                    self.closed_since = None
                    closed = True
                else:
                    due = self.closed_since + close_delay
        return due, closed
