"""Relays started and stopped by the learned inertia, in rooms that behave like real ones.

Every scenario simulates a room minute by minute (heating with its inertia,
heat loss to a changing outdoor temperature, small random disturbances, a
sensor rounded to 0.1 °C), learns it with the real learner and controls it
with the same decision as the integration (``engine.on_off_wanted``), against
the hysteresis alone.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import math
import random
import unittest

from tests.pure import engine, learning

H = 0.3  # the default hysteresis


def _simulate(
    *,
    h: float,
    k: float,
    tau: float,
    inertia: bool,
    days: int = 12,
    seed: int = 1,
    noise: float = 0.15,
    tau_after: float | None = None,
    change_day: int = 6,
    sensor_jitter: float = 0.0,
    outdoor_known: bool = True,
    sun_gain: float = 0.0,
    stats_from: int = 4,
    delay: int = 0,
) -> dict:
    """One room for ``days`` days; statistics of the day level from day ``stats_from`` on."""
    rnd = random.Random(seed)
    daily = [rnd.uniform(-5, 10) for _ in range(days + 1)]

    def outdoor(i: int) -> float:
        return daily[i // 1440] + 3 * math.sin(2 * math.pi * ((i % 1440) / 1440 - 0.375))

    def sun(i: int) -> float:
        minute = i % 1440
        return (
            max(0.0, math.sin(math.pi * (minute - 450) / 550)) * 0.4 if 450 < minute < 1000 else 0.0
        )

    learner = learning.ThermalLearner()
    t0 = datetime(2026, 11, 1, tzinfo=timezone.utc)
    temp, q, on = 19.0, 0.0, False
    asked: list[bool] = []
    reading_before = None
    stats = {"minutes": 0, "dev": 0.0, "above": 0, "below": 0, "starts": 0, "by_model": 0}
    peak_over = 0.0
    trace: list[bool] = []
    learned_at = None
    for i in range(days * 1440):
        minute = i % 1440
        target = 21.0 if 360 <= minute < 1380 else 18.5
        true_tau = tau_after if tau_after is not None and i >= change_day * 1440 else tau
        # TRVs follow the demand a few minutes later (``delay``).
        asked.append(on)
        valve = asked[-1 - delay] if len(asked) > delay else False
        u = 1.0 if valve else 0.0
        q = u + (q - u) * math.exp(-1 / true_tau)
        out = outdoor(i)
        temp += (h * q - k * (temp - out) + sun_gain * sun(i) + rnd.gauss(0, noise)) / 60
        reading = round(temp + rnd.uniform(-sensor_jitter, sensor_jitter), 1)
        if i % 5 == 0:
            learner.observe(
                t0 + timedelta(minutes=i),
                valve,
                reading,
                round(out, 1) if outdoor_known else None,
                False,
                outdoor_known,
                sun(i),
            )
        # The integration looks again when the reading changes (and every 5 minutes).
        if reading != reading_before or i % 5 == 0:
            reading_before = reading
            model = learner.model
            extreme = None
            if inertia and model.learned:
                lq = learner.q

                def extreme(heating: bool, m=model, r=reading, o=out, lq=lq, i=i) -> float:
                    return m.extreme(
                        r, o if outdoor_known else None, lq, heating, lambda x: sun(i + int(x))
                    )

            if learned_at is None and model.learned:
                learned_at = i
            was = on
            on, by_model = engine.on_off_wanted(on, reading, target, H, extreme)
            stats["by_model"] += by_model
            if on and not was and i // 1440 >= stats_from and 480 <= minute < 1380:
                stats["starts"] += 1
        trace.append(on)
        if i // 1440 >= stats_from and 480 <= minute < 1380:
            stats["minutes"] += 1
            stats["dev"] += abs(temp - target)
            stats["above"] += temp > target + 0.5
            stats["below"] += temp < target - 0.5
            peak_over = max(peak_over, temp - target)
    n = stats["minutes"]
    return {
        "dev": stats["dev"] / n,
        "above": stats["above"] / n,
        "below": stats["below"] / n,
        "starts_per_hour": stats["starts"] / (n / 60),
        "by_model": stats["by_model"],
        "peak_over": peak_over,
        "learned": learner.model.learned,
        "learned_at": learned_at,
        "trace": trace,
    }


class InertiaDecisionTest(unittest.TestCase):
    """The decision itself."""

    def test_the_band_always_decides_at_its_edges(self) -> None:
        never = lambda heating: 99.0 if not heating else -99.0  # noqa: E731
        self.assertEqual(engine.on_off_wanted(False, 20.7, 21.0, H, never), (True, False))
        self.assertEqual(engine.on_off_wanted(True, 21.3, 21.0, H, never), (False, False))

    def test_without_a_model_it_stays_as_it_is(self) -> None:
        self.assertEqual(engine.on_off_wanted(True, 21.0, 21.0, H), (True, False))
        self.assertEqual(engine.on_off_wanted(False, 21.0, 21.0, H), (False, False))

    def test_stops_and_starts_by_the_model(self) -> None:
        # The heat on its way takes the room to 21.35: stop now (at 21.0).
        self.assertEqual(engine.on_off_wanted(True, 21.0, 21.0, H, lambda h: 21.35), (False, True))
        # Up to 21.2 only: keep heating.
        self.assertEqual(engine.on_off_wanted(True, 21.0, 21.0, H, lambda h: 21.2), (True, False))
        # It would fall to 20.65 before the heat arrives: start now.
        self.assertEqual(engine.on_off_wanted(False, 20.9, 21.0, H, lambda h: 20.65), (True, True))

    def test_extreme_of_the_model(self) -> None:
        model = learning.ThermalModel(h=2.0, k=0.05, tau=30.0, learned=True)
        # Just stopped with the radiators hot: still rises, by less than h × τ.
        peak = model.extreme(21.0, 5.0, 1.0, False)
        # h × τ = 2 °C/h × 0.5 h = 1 °C still to come, minus the loss meanwhile
        # (0.05 × 16 = 0.8 °C/h): about a quarter of a degree more.
        self.assertGreater(peak, 21.15)
        self.assertLess(peak, 21.0 + 2.0 * 0.5)
        # Started with cold radiators: still falls a little first.
        self.assertLess(model.extreme(20.8, 5.0, 0.0, True), 20.8)
        # Without inertia nothing more comes after a stop.
        none = learning.ThermalModel(h=2.0, k=0.05, tau=0.0, learned=True)
        self.assertEqual(none.extreme(21.0, 5.0, 0.0, False), 21.0)


class InertiaRealLifeTest(unittest.TestCase):
    """Whole days of a room, three kinds of weather each."""

    def _both(self, **room) -> tuple[list[dict], list[dict]]:
        band = [_simulate(inertia=False, seed=s, **room) for s in (1, 2, 3)]
        model = [_simulate(inertia=True, seed=s, **room) for s in (1, 2, 3)]
        return band, model

    def test_radiators(self) -> None:
        band, model = self._both(h=2.0, k=0.05, tau=30.0)
        for b, m in zip(band, model, strict=True):
            self.assertTrue(m["learned"])
            self.assertGreater(m["by_model"], 0)
            self.assertLess(m["dev"], b["dev"])
            self.assertLessEqual(m["above"], b["above"])
            # No more than one start every 1.5 hours, as with the band.
            self.assertLess(m["starts_per_hour"], 0.7)

    def test_cast_iron_does_not_overheat(self) -> None:
        band, model = self._both(h=2.0, k=0.05, tau=60.0)
        for b, m in zip(band, model, strict=True):
            self.assertGreater(b["above"], 0.05)  # the band alone overshoots
            self.assertLess(m["above"], 0.01)
            self.assertLess(m["dev"], b["dev"])

    def test_floor_heating_halves_the_deviation(self) -> None:
        band, model = self._both(h=1.6, k=0.04, tau=180.0, days=14)
        for b, m in zip(band, model, strict=True):
            self.assertLess(m["dev"], 0.7 * b["dev"])
            # Still a calm floor: less than one start an hour.
            self.assertLess(m["starts_per_hour"], 1.0)

    def test_before_learning_it_is_the_band(self) -> None:
        # Until the model is learned (within the first day) the relay does
        # exactly what the band alone does.
        band = _simulate(h=1.6, k=0.04, tau=180.0, inertia=False, days=2, stats_from=0)
        model = _simulate(h=1.6, k=0.04, tau=180.0, inertia=True, days=2, stats_from=0)
        learned_at = model["learned_at"]
        self.assertIsNotNone(learned_at)
        self.assertGreater(learned_at, 60)
        self.assertEqual(band["trace"][:learned_at], model["trace"][:learned_at])

    def test_trv_boost(self) -> None:
        # TRVs with the boost: the room sensor decides like a relay, the valves
        # follow 3 minutes later.
        band, model = self._both(h=2.0, k=0.05, tau=30.0, delay=3)
        for b, m in zip(band, model, strict=True):
            self.assertGreater(b["above"], 0.03)
            self.assertLess(m["above"], 0.01)
            self.assertLess(m["dev"], b["dev"])
            self.assertLess(m["starts_per_hour"], 0.7)

    def test_house_that_changes(self) -> None:
        # New, slower radiators on day 6: the model follows; no rapid switching meanwhile.
        for seed in (1, 2, 3):
            m = _simulate(h=2.0, k=0.05, tau=20.0, tau_after=90.0, inertia=True, seed=seed, days=14)
            self.assertLess(m["starts_per_hour"], 1.0)
            self.assertLess(m["below"], 0.1)

    def test_noisy_sensor_does_not_chatter(self) -> None:
        # A sensor that jumps ±0.15 °C around the real value.
        band, model = self._both(h=2.5, k=0.06, tau=20.0, sensor_jitter=0.15)
        for b, m in zip(band, model, strict=True):
            self.assertLess(m["starts_per_hour"], max(1.5, 2 * b["starts_per_hour"]))
            self.assertLess(m["dev"], b["dev"] + 0.02)

    def test_without_outdoor_temperature(self) -> None:
        band, model = self._both(h=2.0, k=0.05, tau=60.0, outdoor_known=False)
        for b, m in zip(band, model, strict=True):
            self.assertLess(m["above"], b["above"])

    def test_sunny_room(self) -> None:
        # The sun warms the room by day: with it learned, still no overshoot.
        band, model = self._both(h=2.0, k=0.05, tau=60.0, sun_gain=1.5)
        for b, m in zip(band, model, strict=True):
            self.assertLessEqual(m["above"], b["above"])
            self.assertLess(m["dev"], b["dev"] + 0.02)


if __name__ == "__main__":
    unittest.main()
