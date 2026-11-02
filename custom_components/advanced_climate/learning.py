"""Thermal model of a room, learned for optimal start and stop (pure Python).

The room is one thermal mass that gains heat from its heating and loses heat
to the outdoors in proportion to the difference between inside and outside:

    dT/dt = h · q − k · (T − T_out)

* ``h``: how fast the room warms with the heating fully on (°C per hour);
* ``k``: how fast it loses heat per degree warmer than outdoors (per hour);
* ``q``: how much of the heating reaches the room now (0 … 1). It follows the
  heating on / off with a delay ``τ`` (the thermal inertia): the water, the
  radiators or the floor warm up first after a start, and keep giving heat
  for a while after a stop:

      dq/dt = (u − q) / τ        (u = 1 while the heating runs, else 0)

All three numbers are learned per room, continuously, from what the room
does: every stretch of ``WINDOW_MINUTES`` minutes with heating or without it
is one equation ``rise per hour = h · q̄ − k · (T − T_out)̄`` (the bars are the
means over the stretch). ``h`` and ``k`` are the least squares solution of
those equations; older stretches weigh less (half of their weight after
``HALF_LIFE_DAYS`` days), so the model follows a room that changes. ``τ`` is
the one of ``TAU_GRID`` whose model predicted the stretches best (each one is
judged before it is learned from). A stretch far from what the model says (a
door left open, cooking, the sun) weighs less: beyond ``ROBUST_LIMIT`` times
the usual error its weight shrinks in proportion (a Huber weight).

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
from dataclasses import dataclass, field
from datetime import datetime


def _finite(value: float | None) -> float | None:
    """The value, or None when it is not a real number (nan / inf from a broken sensor)."""
    return value if value is not None and math.isfinite(value) else None


DATA_VERSION = 5  # saved learning of other versions is discarded
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

    h: float = DEFAULT_RATE  # °C per hour at full heating
    k: float = 0.0  # per hour (or °C per hour when ``constant_loss``)
    tau: float = 0.0  # minutes of inertia
    constant_loss: bool = False
    learned: bool = False
    outdoor_mean: float | None = None

    def _outdoor(self, outdoor: float | None) -> float | None:
        return outdoor if outdoor is not None else self.outdoor_mean

    def rate(self, indoor: float, outdoor: float | None, q: float) -> float:
        """Degrees per hour the room changes now with ``q`` of the heating."""
        if self.constant_loss:
            return self.h * q - self.k
        out = self._outdoor(outdoor)
        loss = 0.0 if out is None else self.k * (indoor - out)
        return self.h * q - loss

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
    ) -> float:
        """Room temperature after ``minutes`` (heating on or off all the time)."""
        u = 1.0 if heating else 0.0
        t = indoor
        steps = max(0, math.ceil(minutes))
        step = minutes / steps if steps else 0.0
        for _ in range(steps):
            q, q_mean = _q_after(q, u, step, self.tau)
            t += self.rate(t, outdoor, q_mean) * step / 60
        return t

    def minutes_to_heat(
        self, indoor: float, target: float, outdoor: float | None, q: float = 0.0
    ) -> float | None:
        """Minutes until the room reaches ``target`` with the heating on (None: never)."""
        if indoor >= target:
            return 0.0
        return self._minutes_until(indoor, outdoor, q, True, target)

    def minutes_to_fall(
        self, indoor: float, floor: float, outdoor: float | None, q: float = 0.0
    ) -> float | None:
        """Minutes until the room falls to ``floor`` without heating (None: not within a day)."""
        if not self.learned:
            return None
        if indoor <= floor:
            return 0.0
        return self._minutes_until(indoor, outdoor, q, False, floor)

    def _minutes_until(
        self,
        indoor: float,
        outdoor: float | None,
        q: float,
        heating: bool,
        limit: float,
    ) -> float | None:
        """Minutes until the room crosses ``limit`` (up while heating, down without)."""
        u = 1.0 if heating else 0.0
        t = indoor
        for minute in range(1, MAX_MINUTES + 1):
            q, q_mean = _q_after(q, u, 1.0, self.tau)
            previous = t
            t += self.rate(t, outdoor, q_mean) / 60
            if (t >= limit) if heating else (t <= limit):
                # Within the last minute, in proportion.
                return minute - 1 + (limit - previous) / (t - previous)
        return None


# ---------------------------------------------------------------------------
# Learning
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class _Fit:
    """Weighted least squares of one inertia candidate."""

    tau: float
    q: float = 0.0
    a11: float = 0.0
    a12: float = 0.0
    a22: float = 0.0
    b1: float = 0.0
    b2: float = 0.0
    error: float = 0.0  # weighted sum of squared prediction errors
    weight: float = 0.0
    usual: float = 0.0  # weighted mean absolute prediction error
    windows: int = 0
    # Window being collected: integral of q over it.
    q_area: float = 0.0

    def solve(self) -> tuple[float, float] | None:
        """(h, k) with a small pull towards the default; None when impossible."""
        a11, a12, a22 = self.a11 + RIDGE, self.a12, self.a22 + RIDGE
        b1, b2 = self.b1 + RIDGE * DEFAULT_RATE, self.b2
        det = a11 * a22 - a12 * a12
        if abs(det) < 1e-12:
            return None
        h = (b1 * a22 - b2 * a12) / det
        k = (a11 * b2 - a12 * b1) / det
        if k < 0:
            # Without a loss the room would never cool: fit the heating alone.
            k, h = 0.0, b1 / a11
        if h <= 0 or not (math.isfinite(h) and math.isfinite(k)):
            return None
        return h, k

    def add(self, x1: float, x2: float, y: float) -> None:
        """Learn one stretch (judged first by the model so far)."""
        solved = self.solve()
        if solved is not None and self.windows >= 1:
            residual = y - (solved[0] * x1 + solved[1] * x2)
        else:
            residual = y - DEFAULT_RATE * x1
        weight = 1.0
        if self.windows >= ROBUST_MIN_WINDOWS and self.usual > 0:
            limit = ROBUST_LIMIT * self.usual
            if abs(residual) > limit:
                weight = limit / abs(residual)
        f = FORGET
        self.a11 = f * self.a11 + weight * x1 * x1
        self.a12 = f * self.a12 + weight * x1 * x2
        self.a22 = f * self.a22 + weight * x2 * x2
        self.b1 = f * self.b1 + weight * x1 * y
        self.b2 = f * self.b2 + weight * x2 * y
        self.error = f * self.error + weight * residual * residual
        self.usual = (
            abs(residual)
            if self.windows == 0
            else (f * self.weight * self.usual + weight * abs(residual))
            / (f * self.weight + weight)
        )
        self.weight = f * self.weight + weight
        self.windows += 1

    def as_list(self) -> list[float]:
        return [
            self.tau, self.q, self.a11, self.a12, self.a22, self.b1, self.b2,
            self.error, self.weight, self.usual, float(self.windows),
        ]  # fmt: skip

    @classmethod
    def from_list(cls, item: list) -> _Fit:
        values = [float(v) for v in item]
        if len(values) != 11 or not all(math.isfinite(v) for v in values):
            raise ValueError("bad fit")
        fit = cls(*values[:10])
        fit.windows = int(values[10])
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
    _last: tuple[datetime, float, float | None, float] | None = None
    _start: datetime | None = None
    _start_temp: float = 0.0
    _area_loss: float = 0.0  # integral of (T − T_out), or of 1 with a constant loss
    _minutes: float = 0.0
    _disturbed: bool = False
    _model: ThermalModel | None = None

    # ------------------------------------------------------------------ model
    @property
    def learned(self) -> bool:
        """Enough stretches with and without heating."""
        return self.heat_windows >= LEARNED_WINDOWS and self.idle_windows >= LEARNED_WINDOWS

    def _best(self) -> tuple[_Fit, float, float] | None:
        best = None
        for fit in self.fits:
            solved = fit.solve()
            if solved is None or fit.weight <= 0:
                continue
            score = fit.error / fit.weight
            if best is None or score < best[0]:
                best = (score, fit, solved)
        return None if best is None else (best[1], *best[2])

    @property
    def model(self) -> ThermalModel:
        """The learned model, or the default one until it is learned."""
        if self._model is None:
            mean = self.outdoor_sum / self.outdoor_weight if self.outdoor_weight > 0 else None
            best = self._best() if self.learned else None
            if best is None:
                self._model = ThermalModel(constant_loss=self.constant_loss, outdoor_mean=mean)
            else:
                fit, h, k = best
                self._model = ThermalModel(
                    h=round(h, 4),
                    k=round(k, 5),
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
    ) -> bool:
        """Feed an observation. Returns True when a stretch was learned."""
        current, outdoor = _finite(current), _finite(outdoor)
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
            self._last = (now, current, outdoor, u)
            self._begin(now, current)
            return False
        then, t0, o0, u0 = last
        minutes = (now - then).total_seconds() / 60
        if minutes <= 0:
            self._last = (then, t0, o0, u)
            return False
        # The heating reaches the room with its inertia, also across a gap.
        for fit in self.fits:
            fit.q, mean = _q_after(fit.q, u0, minutes, fit.tau)
            fit.q_area += mean * minutes
            if fit.tau <= 0:
                # Without inertia, the heating reaches the room as it starts.
                fit.q = u
        self._last = (now, current, outdoor, u)
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
        self._minutes += minutes
        if self._minutes < WINDOW_MINUTES:
            return False
        learned = False
        if not self._disturbed:
            hours = self._minutes / 60
            y = (current - self._start_temp) / hours
            x2 = -self._area_loss / self._minutes
            q_mean = 0.0
            for fit in self.fits:
                x1 = fit.q_area / self._minutes
                fit.add(x1, x2, y)
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
        self._minutes = 0.0
        self._disturbed = False
        for fit in self.fits:
            fit.q_area = 0.0

    def _drop(self) -> None:
        self._start = None
        self._minutes = 0.0
        self._area_loss = 0.0
        self._disturbed = False
        for fit in self.fits:
            fit.q_area = 0.0

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
        """Restore (learning of other versions is discarded: it is learned again)."""
        obj = cls()
        if not isinstance(data, dict) or data.get("version") != DATA_VERSION:
            return obj
        try:
            fits = [_Fit.from_list(item) for item in data.get("fits") or []]
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
