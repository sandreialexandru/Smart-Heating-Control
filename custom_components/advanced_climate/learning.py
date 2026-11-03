"""Thermal model of a room, learned for optimal start and stop (pure Python).

The room is one thermal mass that gains heat from its heating and loses heat
to the outdoors in proportion to the difference between inside and outside:

    dT/dt = (h − c · T_out) · q − k · (T − T_out) + s · S

* ``h``: how fast the room warms with the heating fully on (°C per hour), at
  0 °C outdoors;
* ``c``: the weather curve: how much more the heating gives for each degree
  colder outdoors (°C per hour per °C). A boiler with a weather curve gives
  hotter water when it is colder (c > 0); a heat pump may give less (c < 0);
  a fixed flow temperature or an electric heater gives the same (c = 0);
* ``k``: how fast it loses heat per degree warmer than outdoors (per hour);
* ``s``: how much the sun warms the room (°C per hour at a sun signal of 1);
  ``S`` is the sun signal of now (0 … 1, ``sun.py``): the sun elevation
  times the share of its light coming through the clouds;
* ``q``: how much of the heating reaches the room now (0 … 1). It follows the
  heating on / off with a delay ``τ`` (the thermal inertia): the water, the
  radiators or the floor warm up first after a start, and keep giving heat
  for a while after a stop:

      dq/dt = (u − q) / τ        (u = 1 while the heating runs, else 0)

The numbers are learned per room, continuously, from what the room does:
every stretch of ``WINDOW_MINUTES`` minutes with heating or without it is one
equation ``rise per hour = h · q̄ − c · (q·T_out)̄ − k · (T − T_out)̄ + s · S̄``
(the bars are the means over the stretch). ``h``, ``c``, ``k`` and ``s`` are
the least squares solution of those equations; older stretches weigh less (half of their weight after
``HALF_LIFE_DAYS`` days), so the model follows a room that changes. ``τ`` is
the one of ``TAU_GRID`` whose model predicted the stretches best (each one is
judged before it is learned from). A stretch far from what the model says (a
door left open, cooking) weighs less: beyond ``ROBUST_LIMIT`` times
the usual error its weight shrinks in proportion (a Huber weight).

The weather curve is learned only once the stretches with heating saw outdoor
temperatures ``CURVE_MIN_SPREAD`` apart (their standard deviation); before
that, and when it would make the heating zero or less at an outdoor
temperature between ``CURVE_CHECK`` degrees, it is 0. The small pull towards
the default pulls it towards 0 as well.

The sun gain is learned only when it is clearly seen: the stretches saw
enough sun (``SUN_MIN``) and the gain is at least ``SUN_T_MIN`` times its
standard error away from 0. Otherwise (a room without sun, a house without a
weather entity, cooking at noon taken for sun) it is 0. Chosen by simulation
(docs/learning.md, section 10).

Stretches with a window or door sensor open, with an unknown state of the heat
source, during the valve exercise, or with the outdoor temperature unknown in a
house that has one, are not used. Without any outdoor temperature in the house
the loss is learned as a constant (``k`` then is degrees per hour).

Until the model has seen ``LEARNED_WINDOWS`` stretches with the heating on and
as many with it off, the room uses ``DEFAULT_RATE`` (60 minutes per degree)
and no inertia, as before any learning.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

# The sun signal (0 … 1) a given number of minutes from now.
SunAhead = Callable[[float], float]


def _finite(value: float | None) -> float | None:
    """The value, or None when it is not a real number (nan / inf from a broken sensor)."""
    return value if value is not None and math.isfinite(value) else None


DATA_VERSION = 7  # saved learning of other versions is discarded (6 is converted)
# One equation per stretch of this length (minutes): long enough that a 0.1 °C
# step of the sensor is small against the change, short enough to see a cycle.
WINDOW_MINUTES = 30.0
# Two observations further apart than this (minutes): the stretch is dropped.
MAX_GAP_MINUTES = 20.0
# Inertia candidates (minutes): 0 = none, up to 4 hours (underfloor heating).
TAU_GRID: tuple[float, ...] = (0.0, 10.0, 20.0, 30.0, 45.0, 60.0, 90.0, 120.0, 180.0, 240.0)
# Weight of a stretch halves after this many days (stretches of 30 minutes).
HALF_LIFE_DAYS = 7.0
FORGET = 0.5 ** (1.0 / (HALF_LIFE_DAYS * 24 * 60 / WINDOW_MINUTES))
# Stretches with the heating on (mean q ≥ 0.5) and off (mean q ≤ 0.2) needed
# before the learned model is used: 8 of 30 minutes = 4 hours of each.
LEARNED_WINDOWS = 8
HEAT_WINDOW_Q = 0.5
IDLE_WINDOW_Q = 0.2
# Before the model is learned: 1 °C per hour (60 minutes per degree), no loss.
DEFAULT_RATE = 1.0
DEFAULT_MINUTES_PER_DEGREE = 60.0
# Stretches with an error beyond this many times the usual one weigh less.
ROBUST_LIMIT = 2.5
ROBUST_MIN_WINDOWS = 10
# A tiny pull towards the default, so a few stretches never give wild numbers.
RIDGE = 0.01
# The weather curve needs heating stretches whose outdoor temperatures have at
# least this standard deviation (°C); with less, it cannot be told from the
# heating itself. Chosen by simulation: learning a curve that is not there costs
# less than missing one that is (docs/learning.md, section 9).
CURVE_MIN_SPREAD = 1.0
# With the curve, the heating must stay above zero between these outdoor
# temperatures (°C), the range of a heating season; otherwise no curve.
CURVE_CHECK = (-20.0, 20.0)
# The sun gain needs a weighted sum of the squared mean sun signals of the
# stretches of at least this (12 stretches with a signal of 0.3: 12 × 0.09 =
# 1.08; a clear November late morning at 45° N) and must be SUN_T_MIN
# standard errors from 0.
SUN_MIN = 1.0
SUN_T_MIN = 5.0
# Predictions look at most this far ahead (minutes), in steps of one minute.
MAX_MINUTES = 24 * 60


def _q_after(q: float, u: float, minutes: float, tau: float) -> tuple[float, float]:
    """q after ``minutes`` with input ``u``, and its mean over that time."""
    if tau <= 0:
        return u, u
    decay = math.exp(-minutes / tau)
    end = u + (q - u) * decay
    mean = u + (q - u) * tau * (1 - decay) / minutes if minutes > 0 else q
    return end, mean


# ---------------------------------------------------------------------------
# The model
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class ThermalModel:
    """A learned (or default) room model; see the module docstring."""

    h: float = DEFAULT_RATE  # °C per hour at full heating, at 0 °C outdoors
    k: float = 0.0  # per hour (or °C per hour when ``constant_loss``)
    c: float = 0.0  # weather curve: °C per hour more per °C colder outdoors
    s: float = 0.0  # sun: °C per hour at a sun signal of 1
    tau: float = 0.0  # minutes of inertia
    constant_loss: bool = False
    learned: bool = False
    outdoor_mean: float | None = None

    def _outdoor(self, outdoor: float | None) -> float | None:
        return outdoor if outdoor is not None else self.outdoor_mean

    def heating(self, outdoor: float | None) -> float:
        """°C per hour the heating adds at full heat, at ``outdoor``."""
        out = None if self.constant_loss else self._outdoor(outdoor)
        if out is None:
            return self.h
        return max(0.0, self.h - self.c * out)

    def rate(self, indoor: float, outdoor: float | None, q: float, sun: float = 0.0) -> float:
        """Degrees per hour the room changes with ``q`` of the heating and the sun signal ``sun``."""
        gain = self.s * sun
        if self.constant_loss:
            return self.h * q - self.k + gain
        out = self._outdoor(outdoor)
        loss = 0.0 if out is None else self.k * (indoor - out)
        return self.heating(outdoor) * q - loss + gain

    def loss_rate(self, indoor: float, outdoor: float | None) -> float | None:
        """Degrees per hour the room falls without heating (positive), if known."""
        if not self.learned:
            return None
        if self.constant_loss:
            return self.k
        out = self._outdoor(outdoor)
        return None if out is None else self.k * (indoor - out)

    def minutes_per_degree(self, indoor: float, outdoor: float | None) -> float | None:
        """Minutes per degree with the heating fully on, at ``indoor`` (None: it cannot rise)."""
        rate = self.rate(indoor, outdoor, 1.0)
        return 60.0 / rate if rate > 0 else None

    def simulate(
        self,
        indoor: float,
        outdoor: float | None,
        q: float,
        heating: bool,
        minutes: float,
        sun: SunAhead | None = None,
    ) -> float:
        """Room temperature after ``minutes`` (heating on or off all the time).

        ``sun(minute)`` is the sun signal that many minutes from the start.
        """
        u = 1.0 if heating else 0.0
        t = indoor
        steps = max(0, math.ceil(minutes))
        step = minutes / steps if steps else 0.0
        for index in range(steps):
            q, q_mean = _q_after(q, u, step, self.tau)
            signal = self._sun(sun, (index + 0.5) * step)
            t += self.rate(t, outdoor, q_mean, signal) * step / 60
        return t

    def _sun(self, sun: SunAhead | None, minute: float) -> float:
        return 0.0 if sun is None or self.s == 0 else sun(minute)

    def minutes_to_heat(
        self,
        indoor: float,
        target: float,
        outdoor: float | None,
        q: float = 0.0,
        sun: SunAhead | None = None,
    ) -> float | None:
        """Minutes until the room reaches ``target`` with the heating on (None: never)."""
        if indoor >= target:
            return 0.0
        return self._minutes_until(indoor, outdoor, q, True, target, sun)

    def minutes_to_fall(
        self,
        indoor: float,
        floor: float,
        outdoor: float | None,
        q: float = 0.0,
        sun: SunAhead | None = None,
    ) -> float | None:
        """Minutes until the room falls to ``floor`` without heating (None: not within a day)."""
        if not self.learned:
            return None
        if indoor <= floor:
            return 0.0
        return self._minutes_until(indoor, outdoor, q, False, floor, sun)

    def _minutes_until(
        self,
        indoor: float,
        outdoor: float | None,
        q: float,
        heating: bool,
        limit: float,
        sun: SunAhead | None = None,
    ) -> float | None:
        """Minutes until the room crosses ``limit`` (up while heating, down without)."""
        u = 1.0 if heating else 0.0
        t = indoor
        for minute in range(1, MAX_MINUTES + 1):
            q, q_mean = _q_after(q, u, 1.0, self.tau)
            previous = t
            t += self.rate(t, outdoor, q_mean, self._sun(sun, minute - 0.5)) / 60
            if (t >= limit) if heating else (t <= limit):
                # Within the last minute, in proportion.
                return minute - 1 + (limit - previous) / (t - previous)
        return None


# ---------------------------------------------------------------------------
# Learning
# ---------------------------------------------------------------------------
def _solve(m: list[list[float]], v: list[float]) -> list[float] | None:
    """Solve a small linear system (Gaussian elimination); None when singular."""
    n = len(v)
    a = [row[:] + [v[i]] for i, row in enumerate(m)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(a[r][col]))
        if abs(a[pivot][col]) < 1e-12:
            return None
        a[col], a[pivot] = a[pivot], a[col]
        for r in range(n):
            if r != col:
                f = a[r][col] / a[col][col]
                for j in range(col, n + 1):
                    a[r][j] -= f * a[col][j]
    return [a[i][n] / a[i][i] for i in range(n)]


# Order of the four unknowns: h (heating), k (loss), c (weather curve), s (sun).
_PRIOR = (DEFAULT_RATE, 0.0, 0.0, 0.0)
_N = 4


@dataclass(slots=True)
class _Fit:
    """Weighted least squares of one inertia candidate."""

    tau: float
    q: float = 0.0
    # Normal equations of x = (q̄, −(T − T_out)̄, −(q·T_out)̄, S̄), upper triangle.
    a11: float = 0.0
    a12: float = 0.0
    a13: float = 0.0
    a22: float = 0.0
    a23: float = 0.0
    a33: float = 0.0
    b1: float = 0.0
    b2: float = 0.0
    b3: float = 0.0
    error: float = 0.0  # weighted sum of squared prediction errors
    weight: float = 0.0
    usual: float = 0.0  # weighted mean absolute prediction error
    a14: float = 0.0
    a24: float = 0.0
    a34: float = 0.0
    a44: float = 0.0
    b4: float = 0.0
    windows: int = 0
    # Window being collected: integrals of q and of q · T_out over it.
    q_area: float = 0.0
    q_out_area: float = 0.0

    def spread(self) -> float:
        """Standard deviation of the outdoor temperature of the heating (°C)."""
        if self.a11 <= 0:
            return 0.0
        # x3 / x1 is −T_out of a stretch: weighted by q², its mean and variance.
        variance = self.a33 / self.a11 - (self.a13 / self.a11) ** 2
        return math.sqrt(max(0.0, variance))

    def _matrix(self) -> tuple[list[list[float]], list[float]]:
        matrix = [
            [self.a11, self.a12, self.a13, self.a14],
            [self.a12, self.a22, self.a23, self.a24],
            [self.a13, self.a23, self.a33, self.a34],
            [self.a14, self.a24, self.a34, self.a44],
        ]
        return matrix, [self.b1, self.b2, self.b3, self.b4]

    def solve(self) -> tuple[float, float, float, float] | None:
        """(h, k, c, s) with a small pull towards the default; None when impossible."""
        matrix, rhs = self._matrix()
        use = [0, 1]
        if self.spread() >= CURVE_MIN_SPREAD:
            use.append(2)
        if self.a44 >= SUN_MIN:
            use.append(3)
        for _ in range(_N + 1):
            solved = self._solve_for(matrix, rhs, use)
            if solved is None:
                return None
            h, k, c, sun = solved
            if k < 0 and 1 in use:
                # Without a loss the room would never cool: fit without it.
                use.remove(1)
                continue
            if 2 in use and any(h - c * t <= 0 for t in CURVE_CHECK):
                # The curve would leave no heating at some outdoor temperature.
                use.remove(2)
                continue
            if 3 in use and not self._sun_seen(matrix, use, sun):
                # The sun does not (clearly) warm the room.
                use.remove(3)
                continue
            break
        if h <= 0 or not all(math.isfinite(v) for v in (h, k, c, sun)):
            return None
        return h, max(0.0, k), c, sun

    def _sun_seen(self, matrix: list[list[float]], use: list[int], sun: float) -> bool:
        """The sun gain is positive and SUN_T_MIN standard errors from 0.

        The variance of the gain is the usual squared prediction error times
        its element of the inverse of the normal equations (of least squares).
        """
        if sun <= 0 or self.weight <= 0:
            return False
        m = [[matrix[i][j] + (RIDGE if i == j else 0.0) for j in use] for i in use]
        unit = [1.0 if i == 3 else 0.0 for i in use]
        column = _solve(m, unit)
        if column is None:
            return False
        variance = self.error / self.weight * column[use.index(3)]
        return variance > 0 and sun >= SUN_T_MIN * math.sqrt(variance)

    @staticmethod
    def _solve_for(
        matrix: list[list[float]], rhs: list[float], use: list[int]
    ) -> tuple[float, float, float, float] | None:
        """Least squares for the unknowns in ``use``; the others are 0."""
        m = [[matrix[i][j] + (RIDGE if i == j else 0.0) for j in use] for i in use]
        v = [rhs[i] + RIDGE * _PRIOR[i] for i in use]
        solved = _solve(m, v)
        if solved is None:
            return None
        values = [0.0] * _N
        for i, value in zip(use, solved, strict=True):
            values[i] = value
        return values[0], values[1], values[2], values[3]

    def predict(self, x1: float, x2: float, x3: float, x4: float = 0.0) -> float | None:
        solved = self.solve()
        if solved is None:
            return None
        h, k, c, sun = solved
        return h * x1 + k * x2 + c * x3 + sun * x4

    def add(self, x1: float, x2: float, x3: float, y: float, x4: float = 0.0) -> None:
        """Learn one stretch (judged first by the model so far)."""
        predicted = self.predict(x1, x2, x3, x4) if self.windows >= 1 else None
        residual = y - (predicted if predicted is not None else DEFAULT_RATE * x1)
        weight = 1.0
        if self.windows >= ROBUST_MIN_WINDOWS and self.usual > 0:
            limit = ROBUST_LIMIT * self.usual
            if abs(residual) > limit:
                weight = limit / abs(residual)
        f = FORGET
        self.a11 = f * self.a11 + weight * x1 * x1
        self.a12 = f * self.a12 + weight * x1 * x2
        self.a13 = f * self.a13 + weight * x1 * x3
        self.a14 = f * self.a14 + weight * x1 * x4
        self.a22 = f * self.a22 + weight * x2 * x2
        self.a23 = f * self.a23 + weight * x2 * x3
        self.a24 = f * self.a24 + weight * x2 * x4
        self.a33 = f * self.a33 + weight * x3 * x3
        self.a34 = f * self.a34 + weight * x3 * x4
        self.a44 = f * self.a44 + weight * x4 * x4
        self.b1 = f * self.b1 + weight * x1 * y
        self.b2 = f * self.b2 + weight * x2 * y
        self.b3 = f * self.b3 + weight * x3 * y
        self.b4 = f * self.b4 + weight * x4 * y
        self.error = f * self.error + weight * residual * residual
        self.usual = (
            abs(residual)
            if self.windows == 0
            else (f * self.weight * self.usual + weight * abs(residual))
            / (f * self.weight + weight)
        )
        self.weight = f * self.weight + weight
        self.windows += 1

    # Saved in this order; the first 14 are the ones of data version 6.
    _FIELDS = (
        "tau", "q", "a11", "a12", "a13", "a22", "a23", "a33",
        "b1", "b2", "b3", "error", "weight", "usual",
        "a14", "a24", "a34", "a44", "b4",
    )  # fmt: skip
    _FIELDS_V6 = 14

    def as_list(self) -> list[float]:
        return [float(getattr(self, name)) for name in self._FIELDS] + [float(self.windows)]

    @classmethod
    def from_list(cls, item: list, version: int = DATA_VERSION) -> _Fit:
        values = [float(v) for v in item]
        count = cls._FIELDS_V6 if version == 6 else len(cls._FIELDS)
        if len(values) != count + 1 or not all(math.isfinite(v) for v in values):
            raise ValueError("bad fit")
        fit = cls(tau=values[0])
        # Data version 6 had no sun: its sums stay 0.
        for name, value in zip(cls._FIELDS[:count], values[:count], strict=True):
            setattr(fit, name, value)
        fit.windows = int(values[-1])
        return fit


@dataclass(slots=True)
class ThermalLearner:
    """Learn the thermal model of a room (see the module docstring)."""

    constant_loss: bool = False
    fits: list[_Fit] = field(default_factory=lambda: [_Fit(tau) for tau in TAU_GRID])
    heat_windows: float = 0.0  # forgotten like the stretches
    idle_windows: float = 0.0
    outdoor_sum: float = 0.0  # weighted, for the mean outdoor temperature
    outdoor_weight: float = 0.0
    # Last observation and the stretch being collected.
    _last: tuple[datetime, float, float | None, float, float] | None = None
    _start: datetime | None = None
    _start_temp: float = 0.0
    _area_loss: float = 0.0  # integral of (T − T_out), or of 1 with a constant loss
    _area_sun: float = 0.0  # integral of the sun signal
    _minutes: float = 0.0
    _disturbed: bool = False
    _model: ThermalModel | None = None

    # ------------------------------------------------------------------ model
    @property
    def learned(self) -> bool:
        """Enough stretches with and without heating."""
        return self.heat_windows >= LEARNED_WINDOWS and self.idle_windows >= LEARNED_WINDOWS

    def _best(self) -> tuple[_Fit, tuple[float, float, float, float]] | None:
        best = None
        for fit in self.fits:
            solved = fit.solve()
            if solved is None or fit.weight <= 0:
                continue
            score = fit.error / fit.weight
            if best is None or score < best[0]:
                best = (score, fit, solved)
        return None if best is None else (best[1], best[2])

    @property
    def model(self) -> ThermalModel:
        """The learned model, or the default one until it is learned."""
        if self._model is None:
            mean = self.outdoor_sum / self.outdoor_weight if self.outdoor_weight > 0 else None
            best = self._best() if self.learned else None
            if best is None:
                self._model = ThermalModel(constant_loss=self.constant_loss, outdoor_mean=mean)
            else:
                fit, (h, k, c, sun) = best
                self._model = ThermalModel(
                    h=round(h, 4),
                    k=round(k, 5),
                    c=round(c, 5),
                    s=round(sun, 4),
                    tau=fit.tau,
                    constant_loss=self.constant_loss,
                    learned=True,
                    outdoor_mean=mean,
                )
        return self._model

    @property
    def q(self) -> float:
        """How much of the heating reaches the room now (of the model in use)."""
        model = self.model
        for fit in self.fits:
            if fit.tau == model.tau:
                return fit.q
        return 0.0

    @property
    def error(self) -> float | None:
        """Usual prediction error of the model in use (°C per hour), once learned."""
        best = self._best() if self.learned else None
        if best is None or best[0].weight <= 0:
            return None
        return math.sqrt(best[0].error / best[0].weight)

    # -------------------------------------------------------------- learning
    def observe(
        self,
        now: datetime,
        heating: bool,
        current: float | None,
        outdoor: float | None,
        disturbed: bool = False,
        outdoor_configured: bool = True,
        sun: float | None = 0.0,
    ) -> bool:
        """Feed an observation. Returns True when a stretch was learned.

        ``sun`` is the sun signal of now (0 without a weather entity; None in
        daylight with the clouds unknown: the stretch is not used).
        """
        current, outdoor = _finite(current), _finite(outdoor)
        sun_now = _finite(sun)
        if sun_now is None:
            disturbed = True
        sun_now = max(0.0, sun_now or 0.0)
        if self.constant_loss == outdoor_configured:
            # The house got (or lost) its outdoor temperature: learn anew.
            self.reset(constant_loss=not outdoor_configured)
        u = 1.0 if heating else 0.0
        last = self._last
        if current is None:
            self._drop()
            self._last = None
            return False
        if last is None:
            self._last = (now, current, outdoor, u, sun_now)
            self._begin(now, current)
            return False
        then, t0, o0, u0, s0 = last
        minutes = (now - then).total_seconds() / 60
        if minutes <= 0:
            self._last = (then, t0, o0, u, s0)
            return False
        # The heating reaches the room with its inertia, also across a gap.
        out_mid = None if o0 is None or outdoor is None else (o0 + outdoor) / 2
        for fit in self.fits:
            fit.q, mean = _q_after(fit.q, u0, minutes, fit.tau)
            fit.q_area += mean * minutes
            if out_mid is not None and not self.constant_loss:
                fit.q_out_area += mean * out_mid * minutes
            if fit.tau <= 0:
                # Without inertia, the heating reaches the room as it starts.
                fit.q = u
        self._last = (now, current, outdoor, u, sun_now)
        if minutes > MAX_GAP_MINUTES:
            self._begin(now, current)
            return False
        if disturbed:
            self._disturbed = True
        if self.constant_loss:
            self._area_loss += minutes
        elif o0 is None or outdoor is None:
            self._disturbed = True
        else:
            self._area_loss += minutes * ((t0 - o0) + (current - outdoor)) / 2
            self.outdoor_sum = FORGET * self.outdoor_sum + (o0 + outdoor) / 2 * minutes / 60
            self.outdoor_weight = FORGET * self.outdoor_weight + minutes / 60
        self._area_sun += minutes * (s0 + sun_now) / 2
        self._minutes += minutes
        if self._minutes < WINDOW_MINUTES:
            return False
        learned = False
        if not self._disturbed:
            hours = self._minutes / 60
            y = (current - self._start_temp) / hours
            x2 = -self._area_loss / self._minutes
            x4 = self._area_sun / self._minutes
            q_mean = 0.0
            for fit in self.fits:
                x1 = fit.q_area / self._minutes
                x3 = -fit.q_out_area / self._minutes
                fit.add(x1, x2, x3, y, x4)
                if fit.tau == 0.0:
                    q_mean = x1
            f = FORGET
            self.heat_windows = f * self.heat_windows + (1.0 if q_mean >= HEAT_WINDOW_Q else 0.0)
            self.idle_windows = f * self.idle_windows + (1.0 if q_mean <= IDLE_WINDOW_Q else 0.0)
            self._model = None
            learned = True
        self._begin(now, current)
        return learned

    def _begin(self, now: datetime, current: float) -> None:
        self._start = now
        self._start_temp = current
        self._area_loss = 0.0
        self._area_sun = 0.0
        self._minutes = 0.0
        self._disturbed = False
        for fit in self.fits:
            fit.q_area = 0.0
            fit.q_out_area = 0.0

    def _drop(self) -> None:
        self._start = None
        self._minutes = 0.0
        self._area_loss = 0.0
        self._area_sun = 0.0
        self._disturbed = False
        for fit in self.fits:
            fit.q_area = 0.0
            fit.q_out_area = 0.0

    def cancel(self) -> None:
        """Drop the stretch being collected (e.g. outside the heating season)."""
        self._drop()
        self._last = None

    def reset(self, constant_loss: bool | None = None) -> None:
        """Forget everything learned."""
        if constant_loss is not None:
            self.constant_loss = constant_loss
        self.fits = [_Fit(tau) for tau in TAU_GRID]
        self.heat_windows = self.idle_windows = 0.0
        self.outdoor_sum = self.outdoor_weight = 0.0
        self._model = None
        self.cancel()

    # ----------------------------------------------------------- persistence
    def as_dict(self) -> dict:
        """Serialize (the stretch being collected is not kept)."""
        return {
            "version": DATA_VERSION,
            "constant_loss": self.constant_loss,
            "fits": [fit.as_list() for fit in self.fits],
            "heat_windows": self.heat_windows,
            "idle_windows": self.idle_windows,
            "outdoor": [self.outdoor_sum, self.outdoor_weight],
        }

    @classmethod
    def from_dict(cls, data: dict | None) -> ThermalLearner:
        """Restore (learning of other versions is discarded: it is learned again).

        Version 6, the one before the sun, is kept: its sun sums start at 0.
        """
        obj = cls()
        if not isinstance(data, dict) or data.get("version") not in (6, DATA_VERSION):
            return obj
        version = int(data["version"])
        try:
            fits = [_Fit.from_list(item, version) for item in data.get("fits") or []]
            if [fit.tau for fit in fits] != list(TAU_GRID):
                return obj
            heat = float(data.get("heat_windows", 0.0))
            idle = float(data.get("idle_windows", 0.0))
            outdoor_sum, outdoor_weight = (float(v) for v in data.get("outdoor") or [0, 0])
        except (TypeError, ValueError):
            return obj
        if not all(math.isfinite(v) for v in (heat, idle, outdoor_sum, outdoor_weight)):
            return obj
        obj.constant_loss = bool(data.get("constant_loss", False))
        obj.fits = fits
        obj.heat_windows, obj.idle_windows = heat, idle
        obj.outdoor_sum, obj.outdoor_weight = outdoor_sum, outdoor_weight
        return obj
