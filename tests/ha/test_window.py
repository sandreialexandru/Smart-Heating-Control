"""Open windows on their own (no Home Assistant running)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from custom_components.advanced_climate.window import TemperatureDrop, WindowState

T0 = datetime(2026, 11, 2, 8, 0, tzinfo=UTC)
SENSOR = ("sensor.living",)


def _min(minutes: float) -> datetime:
    return T0 + timedelta(minutes=minutes)


def _read(drop: TemperatureDrop, minutes: float, value: float | None, sources=SENSOR) -> None:
    drop.update(_min(minutes), sources, value, enabled=True, minutes=5, degrees=1.0)


def test_a_quick_drop_is_an_open_window_for_15_minutes() -> None:
    drop = TemperatureDrop()
    _read(drop, 0, 21.0)
    _read(drop, 2, 20.5)
    assert not drop.active(_min(2))
    _read(drop, 4, 19.9)
    assert drop.active(_min(4))
    assert drop.until == _min(19)
    assert not drop.active(_min(19))


def test_a_slow_drop_is_not_a_window() -> None:
    drop = TemperatureDrop()
    for i, value in enumerate((21.0, 20.7, 20.4, 20.1, 19.8)):
        _read(drop, i * 6, value)
    assert drop.until is None


def test_a_run_of_the_same_value_counts_from_its_last_reading() -> None:
    drop = TemperatureDrop()
    _read(drop, 0, 21.0)
    _read(drop, 10, 21.0)  # still 21 at minute 10
    assert len(drop.samples) == 1
    _read(drop, 13, 19.8)
    assert drop.active(_min(13))


def test_a_stale_value_before_the_window_is_not_used() -> None:
    drop = TemperatureDrop()
    _read(drop, 0, 21.0)
    # Next report 25 minutes later (window 5 + 15 stale minutes passed).
    _read(drop, 25, 19.5)
    assert drop.until is None


def test_a_change_of_the_sensors_starts_again() -> None:
    drop = TemperatureDrop()
    _read(drop, 0, 21.0)
    _read(drop, 1, 19.0, sources=("device", "climate.trv"))
    assert drop.until is None
    assert len(drop.samples) == 1


def test_disabled_keeps_the_readings_but_finds_nothing() -> None:
    drop = TemperatureDrop()
    drop.update(T0, SENSOR, 21.0, enabled=False, minutes=5, degrees=1.0)
    drop.update(_min(2), SENSOR, 19.0, enabled=False, minutes=5, degrees=1.0)
    assert drop.until is None
    assert len(drop.samples) == 2


def test_no_value_only_notes_the_sources() -> None:
    drop = TemperatureDrop()
    _read(drop, 0, 21.0)
    _read(drop, 1, None, sources=())
    assert drop.samples == []
    assert drop.sources == ()


def test_old_readings_are_dropped_by_time() -> None:
    drop = TemperatureDrop()
    for i in range(60):
        _read(drop, i, 21.0 + (i % 2) * 0.1)
    # Window 5 + 15 minutes: about 21 runs kept, not 60.
    assert len(drop.samples) <= 22


def test_window_opens_and_closes_after_the_delays() -> None:
    win = WindowState()
    open_delay, close_delay = timedelta(seconds=30), timedelta(seconds=60)
    due, closed = win.update(T0, True, open_delay, close_delay)
    assert not win.open and due == T0 + open_delay and not closed
    due, closed = win.update(T0 + timedelta(seconds=30), True, open_delay, close_delay)
    assert win.open and due is None and win.opened_at == T0 + timedelta(seconds=30)
    # Closed for 20 s, open again: still open, the close delay starts again.
    t = T0 + timedelta(seconds=40)
    due, closed = win.update(t, False, open_delay, close_delay)
    assert win.open and due == t + close_delay
    win.update(t + timedelta(seconds=20), True, open_delay, close_delay)
    assert win.closed_since is None
    t2 = t + timedelta(seconds=30)
    win.update(t2, False, open_delay, close_delay)
    due, closed = win.update(t2 + close_delay, False, open_delay, close_delay)
    assert not win.open and closed and due is None and win.opened_at is None


def test_a_short_opening_does_not_count() -> None:
    win = WindowState()
    delay = timedelta(seconds=30)
    win.update(T0, True, delay, delay)
    win.update(T0 + timedelta(seconds=10), False, delay, delay)
    assert win.raw_since is None
    due, _ = win.update(T0 + timedelta(seconds=35), True, delay, delay)
    assert not win.open and due == T0 + timedelta(seconds=65)
