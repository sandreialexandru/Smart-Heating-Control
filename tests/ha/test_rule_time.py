"""The time of the house under the rules that keep it lower (away, empty rooms,
optimal stop, a window open): counted as the time at least one room is under
the rule, in hours, kept over a restart."""

from __future__ import annotations

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant

from tests.ha.test_ha_devices import _relay_house, _tick, _unload


def _hours(hass: HomeAssistant, key: str) -> float:
    return float(hass.states.get(f"sensor.home_time_{key}").state)


async def test_a_window_open_is_counted_from_its_rule_until_it_closes(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    entry = await _relay_house(hass, freezer, 20.0)
    assert _hours(hass, "window") == 0
    hass.states.async_set("binary_sensor.window", "on")
    for _ in range(12):
        await _tick(hass, freezer, 60)
    room = next(iter(entry.runtime_data.rooms.values()))
    assert room.rule == "window_open"
    hass.states.async_set("binary_sensor.window", "off")
    for _ in range(5):
        await _tick(hass, freezer, 60)
    # 12 minutes open, of which the first (the delay of the window, 60 s) not yet under the rule.
    minutes = entry.runtime_data.rule_time_s["window"] / 60
    assert 10 <= minutes <= 12, minutes
    assert abs(_hours(hass, "window") - minutes / 60) < 0.001
    assert _hours(hass, "away") == 0
    await _unload(hass, entry)


async def test_the_house_away_counts_once_for_all_its_rooms_and_is_kept_over_a_restart(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    entry = await _relay_house(hass, freezer, 20.0)
    await hass.services.async_call(
        "select", "select_option", {"entity_id": "select.home_mode", "option": "away"}, blocking=True
    )
    for _ in range(30):
        await _tick(hass, freezer, 60)
    house = entry.runtime_data
    assert all(room.rule == "house_away" for room in house.rooms.values())
    minutes = house.rule_time_s["away"] / 60
    assert 28 <= minutes <= 30, minutes
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.runtime_data.rule_time_s["away"] >= minutes * 60 - 1, "kept over a restart"
    await _unload(hass, entry)
