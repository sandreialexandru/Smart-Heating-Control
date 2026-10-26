"""Heating and cooling learning for optimal start and stop (pure Python).

Heating: the learner observes heating episodes (the room asks for heat and the
temperature rises) and keeps, for each one, the degrees risen, the minutes it
took and the mean outdoor temperature. An episode starts when the room is at
least the thermostat tolerance below the target, so the cycles of a thermostat
that keeps the temperature are learned too.

The time to heat is learned as

    minutes = fixed + degrees × (per_degree + per_outdoor × outdoor)

* ``fixed``: the minutes before the room starts to rise (the boiler starts, the
  water and the radiators warm up); it does not grow with the degrees;
* ``per_degree``: minutes per degree at 0 °C outdoors;
* ``per_outdoor``: how the minutes per degree change per degree outdoors.

The three numbers are the least squares fit of all the kept episodes, so the
learning follows the room as measured (all the delays of the heat source are
in the minutes) and outdoor temperatures not seen yet are estimated from the
trend. A term is used only when the episodes can tell it: the fixed part needs
episodes of different sizes, the outdoor term episodes at different outdoor
temperatures. A term that comes out impossible (a negative fixed part, a
negative number of minutes) is set to zero.

Small and large episodes are kept apart (25 of each), so the many small cycles
of a thermostat never push the few large ones out.

Episodes during which a window or door sensor of the room was open are not
used.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime


def _finite(value: float | None) -> float | None:
    """The value, or None when it is not a real number (nan / inf from a broken sensor)."""
    return value if value is not None and math.isfinite(value) else None


# An episode (with heat demand for heating, without it for cooling) is used
# only when it lasted at least this long.
MIN_DEMAND_MINUTES = 10
# Until the first heating episode: 60 minutes per degree (1 °C per hour).
DEFAULT_MINUTES_PER_DEGREE = 60.0
DATA_VERSION = 4  # saved heating data of other versions is discarded
# Heating episodes kept: the small ones and the large ones apart.
LARGE_EPISODE = 1.0  # °C risen: from this on an episode is large
MAX_SMALL_EPISODES = 25
MAX_LARGE_EPISODES = 25
# The fixed part needs episodes that differ in size by at least this much.
MIN_SIZE_SPREAD = 1.0  # °C
# The outdoor term needs episodes whose outdoor temperatures differ this much.
MIN_FIT_SPREAD = 1.0  # °C
COOLING_MAX_EPISODES = 30


def start_gap(tolerance: float) -> float:
    """Degrees below the target (at least) needed to start an episode."""
    return round(max(0.0, tolerance), 2)


def _solve(matrix: list[list[float]], vector: list[float]) -> list[float] | None:
    """Solve a small linear system (Gaussian elimination); None when singular."""
    n = len(vector)
    a = [row[:] + [vector[i]] for i, row in enumerate(matrix)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(a[r][col]))
        if abs(a[pivot][col]) < 1e-9:
            return None
        a[col], a[pivot] = a[pivot], a[col]
        for r in range(n):
            if r != col:
                factor = a[r][col] / a[col][col]
                for c in range(col, n + 1):
                    a[r][c] -= factor * a[col][c]
    return [a[i][n] / a[i][i] for i in range(n)]


def _least_squares(rows: list[list[float]], values: list[float]) -> list[float] | None:
    """Coefficients that bring rows · coefficients closest to the values."""
    n = len(rows[0])
    ata = [[sum(r[i] * r[j] for r in rows) for j in range(n)] for i in range(n)]
    atb = [sum(r[i] * v for r, v in zip(rows, values)) for i in range(n)]
    return _solve(ata, atb)


@dataclass(slots=True)
class HeatingModel:
    """The learned time to heat (see the module docstring)."""

    fixed: float = 0.0  # minutes
    per_degree: float = DEFAULT_MINUTES_PER_DEGREE  # minutes per °C at 0 °C outdoors
    per_outdoor: float = 0.0  # change of the minutes per °C, per °C outdoors
    # Mean outdoor temperature of the episodes (used when outdoor is unknown).
    outdoor_mean: float | None = None
    uses_fixed: bool = False
    uses_outdoor: bool = False

    def minutes_per_degree(self, outdoor: float | None) -> float:
        """Minutes per °C at the outdoor temperature (never negative)."""
        if outdoor is None:
            outdoor = self.outdoor_mean
        value = self.per_degree + (self.per_outdoor * outdoor if outdoor is not None else 0.0)
        return max(0.0, value)

    def minutes(self, gap: float, outdoor: float | None, elapsed: float = 0.0) -> float:
        """Minutes to rise ``gap`` °C at the outdoor temperature.

        ``elapsed`` is how long the room has been heating already: that much of
        the fixed part is behind it (the radiators are warm).
        """
        if gap <= 0:
            return 0.0
        return max(0.0, self.fixed - max(0.0, elapsed)) + gap * self.minutes_per_degree(outdoor)


def fit_model(episodes: list[list]) -> HeatingModel:
    """Fit the time to heat to the episodes [outdoor or None, °C, minutes, at]."""
    if not episodes:
        return HeatingModel()
    points = [(o, float(g), float(m)) for o, g, m, *_ in episodes]
    with_outdoor = [(float(o), g, m) for o, g, m in points if o is not None]
    outdoors = [o for o, _, _ in with_outdoor]
    outdoor_mean = round(sum(outdoors) / len(outdoors), 2) if outdoors else None
    use_outdoor = bool(outdoors) and max(outdoors) - min(outdoors) >= MIN_FIT_SPREAD
    allow_fixed = True
    while True:
        # The outdoor term is fitted on the episodes that have an outdoor temperature.
        data = with_outdoor if use_outdoor else points
        sizes = [g for _, g, _ in data]
        use_fixed = allow_fixed and max(sizes) - min(sizes) >= MIN_SIZE_SPREAD
        rows = [
            ([1.0] if use_fixed else []) + [g] + ([g * o] if use_outdoor else [])
            for o, g, _ in data
        ]
        values = [m for _, _, m in data]
        found = _least_squares(rows, values) if len(rows) >= len(rows[0]) else None
        if found is None:
            # The episodes cannot tell all the terms apart: fewer terms.
            if use_outdoor:
                use_outdoor = False
            elif use_fixed:
                allow_fixed = False
            else:
                return HeatingModel(outdoor_mean=outdoor_mean)
            continue
        fixed = found.pop(0) if use_fixed else 0.0
        per_degree = found.pop(0)
        per_outdoor = found.pop(0) if use_outdoor else 0.0
        # An impossible term is set to zero and the rest is fitted again.
        if use_fixed and fixed < 0:
            allow_fixed = False
            continue
        if (
            use_outdoor
            and min(
                per_degree + per_outdoor * min(outdoors), per_degree + per_outdoor * max(outdoors)
            )
            < 0
        ):
            use_outdoor = False
            continue
        if per_degree < 0 and not use_outdoor:
            # Larger episodes were not slower: the minutes do not grow with the
            # degrees, so only the fixed part (the mean of the episodes) is left.
            fixed, per_degree = (sum(values) / len(values) if use_fixed else 0.0), 0.0
        return HeatingModel(
            fixed=round(fixed, 2),
            per_degree=round(per_degree, 3),
            per_outdoor=round(per_outdoor, 4),
            outdoor_mean=outdoor_mean,
            uses_fixed=use_fixed,
            uses_outdoor=use_outdoor,
        )


@dataclass(slots=True)
class HeatingRateLearner:
    """Learn how long a room takes to heat up (see the module docstring)."""

    # [outdoor °C or None, °C risen, minutes, end time ISO]
    episodes: list[list] = field(default_factory=list)
    episode_start: datetime | None = None
    episode_temp: float | None = None
    # Sum and count of the outdoor temperatures seen during the episode.
    episode_outdoor_sum: float = 0.0
    episode_outdoor_count: int = 0
    episode_disturbed: bool = False
    # The episode in progress was restored after a restart: it continues only if
    # the room still heats at the first observation.
    _restored: bool = False
    _model: HeatingModel | None = None

    # ------------------------------------------------------------------ model
    @property
    def model(self) -> HeatingModel:
        """The fitted model (refitted when the episodes change)."""
        if self._model is None:
            self._model = fit_model(self.episodes)
        return self._model

    def minutes(self, gap: float, outdoor: float | None, now: datetime | None = None) -> float:
        """Minutes to rise ``gap`` °C at the outdoor temperature.

        With ``now`` during an episode, the time already heated counts against
        the fixed part.
        """
        return self.model.minutes(gap, outdoor, self.heated_minutes(now))

    def heated_minutes(self, now: datetime | None) -> float:
        """Minutes the episode in progress has been heating (0 without one)."""
        if now is None or self.episode_start is None:
            return 0.0
        return max(0.0, (now - self.episode_start).total_seconds() / 60)

    def minutes_per_degree(self, outdoor: float | None) -> float:
        """Learned minutes per °C at the outdoor temperature."""
        return self.model.minutes_per_degree(outdoor)

    def _keep(self) -> None:
        """Keep the last small and the last large episodes, in time order."""
        small = [e for e in self.episodes if float(e[1]) < LARGE_EPISODE][-MAX_SMALL_EPISODES:]
        large = [e for e in self.episodes if float(e[1]) >= LARGE_EPISODE][-MAX_LARGE_EPISODES:]
        kept = {id(e) for e in small + large}
        self.episodes = [e for e in self.episodes if id(e) in kept]
        self._model = None

    # -------------------------------------------------------------- learning
    def observe(
        self,
        now: datetime,
        heating: bool,
        current: float | None,
        target: float | None,
        outdoor: float | None,
        window_open: bool = False,
        tolerance: float = 0.0,
    ) -> float | None:
        """Feed an observation. Returns the minutes of the episode when it is used.

        ``window_open`` is True while a window or door sensor of the room is open;
        such an episode is not used. ``tolerance`` is how far below the target the
        thermostat lets the room fall before heating (its normal cycle).
        """
        current, target, outdoor = _finite(current), _finite(target), _finite(outdoor)
        if current is None:
            return None
        if self._restored:
            self._restored = False
            # Not heating any more after the restart: it is not known when the
            # heating stopped, so the restored episode cannot be measured.
            if self.episode_start is not None and not heating:
                self.cancel()
                return None
        if heating and self.episode_start is None:
            if (
                target is not None
                and target - current >= start_gap(tolerance) - 1e-9
                and not window_open
            ):
                self.episode_start = now
                self.episode_temp = current
                self.episode_outdoor_sum = outdoor if outdoor is not None else 0.0
                self.episode_outdoor_count = 1 if outdoor is not None else 0
                self.episode_disturbed = False
            return None
        if self.episode_start is None:
            return None
        if window_open:
            self.episode_disturbed = True
        if outdoor is not None:
            self.episode_outdoor_sum += outdoor
            self.episode_outdoor_count += 1
        reached = target is not None and current >= target
        if heating and not reached:
            return None
        # Episode finished (target reached or heating stopped).
        minutes = (now - self.episode_start).total_seconds() / 60
        rise = current - (self.episode_temp if self.episode_temp is not None else current)
        outdoor_mean = self._outdoor_mean()
        disturbed = self.episode_disturbed
        self.cancel()
        # The heat demand lasted at least 10 minutes; any rise counts, a slow one
        # too (it may show a problem, but it is real). Without a rise there is
        # nothing to learn.
        if disturbed or minutes < MIN_DEMAND_MINUTES or rise <= 0:
            return None
        mean_outdoor = round(outdoor_mean, 1) if outdoor_mean is not None else None
        self.episodes.append([mean_outdoor, round(rise, 2), round(minutes, 1), now.isoformat()])
        self._keep()
        return round(minutes, 1)

    def _outdoor_mean(self) -> float | None:
        """Mean outdoor temperature during the episode in progress."""
        if not self.episode_outdoor_count:
            return None
        return self.episode_outdoor_sum / self.episode_outdoor_count

    def cancel(self) -> None:
        """Drop the episode in progress (e.g. outside the heating season)."""
        self.episode_start = None
        self.episode_temp = None
        self.episode_outdoor_sum = 0.0
        self.episode_outdoor_count = 0
        self.episode_disturbed = False

    # ----------------------------------------------------------- persistence
    def as_dict(self) -> dict:
        """Serialize (with the episode in progress, so a restart does not lose it)."""
        data: dict = {"version": DATA_VERSION, "episodes": self.episodes}
        if self.episode_start is not None and self.episode_temp is not None:
            data["in_progress"] = {
                "start": self.episode_start.isoformat(),
                "temp": self.episode_temp,
                "outdoor_sum": self.episode_outdoor_sum,
                "outdoor_count": self.episode_outdoor_count,
                "disturbed": self.episode_disturbed,
            }
        return data

    @classmethod
    def from_dict(cls, data: dict | None) -> HeatingRateLearner:
        """Restore the saved episodes (data of other versions is discarded).

        Older versions kept only a rate per episode, without the degrees and the
        minutes, so they cannot be converted: the heating is learned again.
        """
        obj = cls()
        if (data or {}).get("version") != DATA_VERSION:
            return obj
        episodes = data.get("episodes")
        if isinstance(episodes, list):
            for item in episodes:
                try:
                    outdoor = None if item[0] is None else float(item[0])
                    gap, minutes = float(item[1]), float(item[2])
                    # A value that is not a real number (nan / inf) is dropped.
                    if outdoor is not None and not math.isfinite(outdoor):
                        continue
                    if not (math.isfinite(gap) and math.isfinite(minutes)):
                        continue
                    if gap <= 0 or minutes <= 0:
                        continue
                    obj.episodes.append(
                        [outdoor, gap, minutes, str(item[3]) if len(item) > 3 else ""]
                    )
                except (TypeError, ValueError, IndexError):
                    continue
        obj._keep()
        obj._restore_in_progress(data.get("in_progress"))
        return obj

    def _restore_in_progress(self, item: object) -> None:
        """The episode that was in progress at the restart (dropped when malformed)."""
        if not isinstance(item, dict):
            return
        try:
            start = datetime.fromisoformat(str(item["start"]))
            temp = float(item["temp"])
            outdoor_sum = float(item.get("outdoor_sum", 0.0))
            outdoor_count = int(item.get("outdoor_count", 0))
        except (KeyError, TypeError, ValueError):
            return
        if start.tzinfo is None or not (math.isfinite(temp) and math.isfinite(outdoor_sum)):
            return
        self.episode_start = start
        self.episode_temp = temp
        self.episode_outdoor_sum = outdoor_sum if outdoor_count > 0 else 0.0
        self.episode_outdoor_count = max(0, outdoor_count)
        self.episode_disturbed = bool(item.get("disturbed", False))
        self._restored = True


# ---------------------------------------------------------------------------
# Cooling
# ---------------------------------------------------------------------------
def cooling_coefficient(start: float, end: float, outdoor: float, hours: float) -> float | None:
    """How fast a room cools per degree warmer than outdoors (per hour).

    A room loses heat in proportion to the difference between inside and
    outside: T(t) = outdoor + (start - outdoor) * exp(-k * t). Returns k, or
    None when it cannot be measured (no drop, or not warmer than outdoors).
    """
    if hours <= 0 or end >= start or end <= outdoor:
        return None
    return math.log((start - outdoor) / (end - outdoor)) / hours


@dataclass(slots=True)
class CoolingLearner:
    """Learn how fast a room cools without heating.

    It is the opposite of the heating learning: an episode starts when the heat
    demand stops (no window or door sensor open) and ends when the heat demand
    starts again. It is used when it lasted at least 10 minutes and the
    temperature fell, however little. The cooling depends on the difference
    between inside and outside, so one coefficient per room is learned (the
    walls, radiators and insulation of each house are in it, not modelled).
    """

    # [outdoor °C, coefficient 1/h, end time ISO]
    episodes: list[list] = field(default_factory=list)
    episode_start: datetime | None = None
    episode_temp: float | None = None
    # Sum and count of the outdoor temperatures seen during the episode.
    episode_outdoor_sum: float = 0.0
    episode_outdoor_count: int = 0
    episode_disturbed: bool = False

    @property
    def coefficient(self) -> float | None:
        """Mean learned coefficient (1/h), None before the first episode."""
        if not self.episodes:
            return None
        return round(sum(float(k) for _, k, *_ in self.episodes) / len(self.episodes), 5)

    def rate(self, indoor: float | None, outdoor: float | None) -> float | None:
        """Degrees per hour the room falls now (positive), if known."""
        k = self.coefficient
        if k is None or indoor is None or outdoor is None:
            return None
        return round(k * (indoor - outdoor), 3)

    def minutes_to_fall(self, indoor: float, floor: float, outdoor: float | None) -> float | None:
        """Minutes until the room falls from ``indoor`` to ``floor`` without heating."""
        k = self.coefficient
        if k is None or outdoor is None or k <= 0:
            return None
        if indoor <= floor:
            return 0.0
        if floor <= outdoor:
            return None  # it never gets that cold
        return math.log((indoor - outdoor) / (floor - outdoor)) / k * 60

    def temperature_after(
        self, indoor: float, outdoor: float | None, minutes: float
    ) -> float | None:
        """Room temperature after ``minutes`` without heating."""
        k = self.coefficient
        if k is None or outdoor is None:
            return None
        return outdoor + (indoor - outdoor) * math.exp(-k * minutes / 60)

    def observe(
        self,
        now: datetime,
        heating: bool,
        current: float | None,
        outdoor: float | None,
        window_open: bool = False,
    ) -> float | None:
        """Feed an observation. Returns the coefficient when an episode is used."""
        current, outdoor = _finite(current), _finite(outdoor)
        if current is None:
            return None
        if not heating and self.episode_start is None:
            if not window_open:
                self.episode_start = now
                self.episode_temp = current
                self.episode_outdoor_sum = outdoor if outdoor is not None else 0.0
                self.episode_outdoor_count = 1 if outdoor is not None else 0
                self.episode_disturbed = False
            return None
        if self.episode_start is None:
            return None
        if window_open:
            self.episode_disturbed = True
        if outdoor is not None:
            self.episode_outdoor_sum += outdoor
            self.episode_outdoor_count += 1
        if not heating:
            return None
        # The heat demand started again: the episode is finished.
        minutes = (now - self.episode_start).total_seconds() / 60
        start = self.episode_temp
        mean_outdoor = self._outdoor_mean()
        disturbed = self.episode_disturbed
        self.cancel()
        if disturbed or minutes < MIN_DEMAND_MINUTES or start is None or mean_outdoor is None:
            return None
        k = cooling_coefficient(start, current, mean_outdoor, minutes / 60)
        if k is None or not math.isfinite(k):
            return None
        k = round(k, 5)
        self.episodes.append([round(mean_outdoor, 1), k, now.isoformat()])
        del self.episodes[:-COOLING_MAX_EPISODES]
        return k

    def _outdoor_mean(self) -> float | None:
        """Mean outdoor temperature during the episode in progress."""
        if not self.episode_outdoor_count:
            return None
        return self.episode_outdoor_sum / self.episode_outdoor_count

    def cancel(self) -> None:
        """Drop the episode in progress (e.g. outside the heating season)."""
        self.episode_start = None
        self.episode_temp = None
        self.episode_outdoor_sum = 0.0
        self.episode_outdoor_count = 0
        self.episode_disturbed = False

    def as_dict(self) -> dict:
        """Serialize."""
        return {"version": 1, "episodes": self.episodes}

    @classmethod
    def from_dict(cls, data: dict | None) -> CoolingLearner:
        """Restore."""
        obj = cls()
        if not data or data.get("version") != 1:
            return obj
        for item in data.get("episodes") or []:
            try:
                outdoor, k = float(item[0]), float(item[1])
                if math.isfinite(outdoor) and math.isfinite(k):
                    obj.episodes.append([outdoor, k, str(item[2])])
            except (TypeError, ValueError, IndexError):
                continue
        del obj.episodes[:-COOLING_MAX_EPISODES]
        return obj
