"""Which heat source of the house runs: the first one or the secondary one.

The user chooses Primary, Secondary or Automatic (the select of the house). In
Automatic a criterion decides (PV surplus, cold outside, cheap power or an on /
off entity): on = the secondary source. The criterion must stay changed for the
switching time before the source changes, so a cloud or a short price spike does
not switch the sources back and forth.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from .const import HEAT_SOURCE_AUTO, HEAT_SOURCE_PRIMARY, HEAT_SOURCE_SECONDARY

CHOICES = (HEAT_SOURCE_AUTO, HEAT_SOURCE_PRIMARY, HEAT_SOURCE_SECONDARY)


class SourceChooser:
    """The choice of the user, the source in use and the delay of the criterion."""

    def __init__(self, choice: str | None = None, active: str | None = None) -> None:
        """Initialize (from the saved state)."""
        self.choice = choice if choice in CHOICES else HEAT_SOURCE_AUTO
        # None: never decided yet (a new house), the first decision applies at once.
        self.active: str | None = (
            active if active in (HEAT_SOURCE_PRIMARY, HEAT_SOURCE_SECONDARY) else None
        )
        self._criterion: bool | None = None
        self._since: datetime | None = None

    def effective_choice(self, auto_available: bool) -> str:
        """The choice that applies: Automatic needs a criterion, else the primary source."""
        if self.choice == HEAT_SOURCE_AUTO and not auto_available:
            return HEAT_SOURCE_PRIMARY
        return self.choice

    def wanted(
        self, now: datetime, criterion: bool | None, auto_available: bool, delay: timedelta
    ) -> str:
        """The source to use now (primary or secondary).

        A source chosen by hand applies at once. In Automatic the criterion
        decides once it has stayed the same for ``delay``; an unknown criterion
        keeps the source in use.
        """
        choice = self.effective_choice(auto_available)
        if choice != HEAT_SOURCE_AUTO:
            return choice
        if criterion is not None and criterion != self._criterion:
            self._criterion = criterion
            self._since = now
        current = self.active or HEAT_SOURCE_PRIMARY
        if criterion is None:
            return current
        want = HEAT_SOURCE_SECONDARY if criterion else HEAT_SOURCE_PRIMARY
        if want == current:
            return want
        if self.active is None or self._since is None or now - self._since >= delay:
            return want
        return current

    def switch_at(self, criterion: bool | None, delay: timedelta) -> datetime | None:
        """When Automatic will switch to what the criterion says (None: not waiting)."""
        if self._since is None or criterion is None or self._criterion != criterion:
            return None
        want = HEAT_SOURCE_SECONDARY if criterion else HEAT_SOURCE_PRIMARY
        if want == (self.active or HEAT_SOURCE_PRIMARY):
            return None
        return self._since + delay
