"""The values the card and the diagnostics read: rounding, units, the branches.

Each test checks exact values (the rounding of each attribute, °C and °F), so a
changed number of decimals or a wrong conversion is noticed.
"""

from __future__ import annotations

import math

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.advanced_climate.diagnostics import (
    async_get_config_entry_diagnostics,
)
from custom_components.advanced_climate.learning import LEARNED_WINDOWS, WINDOW_MINUTES
from tests.ha.test_ha_setup import _learned_cast_iron, _setup, _tick

FAHRENHEIT = {"temperature_unit": "°F"}


def _entity(hass: HomeAssistant, entity_id: str):
    """The entity object of ``entity_id`` (its values without a state write)."""
    return hass.data[entity_id.split(".")[0]].get_entity(entity_id)


def _f(celsius: float) -> float:
    return celsius * 1.8 + 32


async def _room(hass: HomeAssistant, freezer: FrozenDateTimeFactory, house=None, **extra):
    entry = await _setup(hass, freezer, house, **extra)
    await _tick(hass, freezer, 15)
    room = next(iter(entry.runtime_data.rooms.values()))
    entities = hass.states.get("sensor.bedroom_decision").attributes["entities"]
    return entry, room, entities


async def _unload(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


# ---------------------------------------------------------------- heating model
async def test_heating_rate_attributes_of_a_learned_room_in_celsius(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Every value of the learned model, with the decimals the card shows."""
    entry, room, entities = await _room(hass, freezer)
    room.learner = learner = _learned_cast_iron()
    learner.heat_windows += 0.123
    learner.idle_windows += 0.456
    model = learner.model
    sensor = _entity(hass, entities["heating_rate"])
    attrs = sensor.extra_state_attributes
    hours = WINDOW_MINUTES / 60

    assert attrs["learned"] is True
    assert attrs["heating_per_hour"] == round(model.h, 2)
    assert attrs["weather_curve"] == round(model.c, 3)
    assert attrs["sun_gain"] == round(model.s, 2)
    # No outdoor temperature in the test house: the loss is a constant (°C/h).
    assert attrs["constant_loss"] is True
    assert attrs["loss_per_hour"] == round(model.k, 3)
    assert attrs["inertia_minutes"] == round(model.tau)
    assert attrs["heat_reaching_now"] == round(learner.q, 2)
    assert attrs["error_per_hour"] == round(learner.error, 2)
    assert attrs["hours_heating"] == round(learner.heat_windows * hours, 1)
    assert attrs["hours_idle"] == round(learner.idle_windows * hours, 1)
    assert attrs["hours_needed"] == LEARNED_WINDOWS * hours
    # A constant loss: no estimate for the outdoor temperatures.
    assert attrs["minutes_per_degree"] == {}
    assert attrs["model"]["q"] == round(learner.q, 4)
    assert attrs["model"]["h"] == model.h
    assert attrs["model"]["tau"] == model.tau
    # The minutes per degree of now, one decimal.
    expected = model.minutes_per_degree(room.current_temp, entry.runtime_data.outdoor_now)
    assert sensor.native_value == round(expected, 1)
    assert sensor.suggested_display_precision == 0
    await _unload(hass, entry)


async def test_heating_rate_with_the_outdoor_loss_in_fahrenheit(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """°F: the rates in °F per hour, the estimates at round °F outdoor temperatures."""
    from custom_components.advanced_climate.learning import ThermalModel

    entry, room, entities = await _room(hass, freezer, FAHRENHEIT)
    room.learner = learner = _learned_cast_iron()
    learner.constant_loss = False
    model = ThermalModel(h=2.34567, k=0.0456789, c=0.0123456, s=0.345678, tau=45.0, learned=True)
    learner._model = model
    attrs = _entity(hass, entities["heating_rate"]).extra_state_attributes

    assert attrs["heating_per_hour"] == round(model.h * 1.8, 2)
    assert attrs["sun_gain"] == round(model.s * 1.8, 2)
    assert attrs["weather_curve"] == round(model.c, 3)
    # Not constant: per hour and per degree of difference, the same in °F.
    assert attrs["loss_per_hour"] == model.k
    indoor = room.current_temp
    assert attrs["minutes_per_degree"] == {
        f"{t}°F": round(model.minutes_per_degree(indoor, (t - 32) / 1.8) / 1.8, 1)
        for t in (14, 32, 50, 68)
    }
    await _unload(hass, entry)


async def test_minutes_per_degree_at_round_celsius_outdoor_temperatures(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """°C: the estimates at −10, 0, 10 and 20 °C outdoors; none before it is learned."""
    from custom_components.advanced_climate.learning import ThermalModel

    entry, room, entities = await _room(hass, freezer)
    sensor = _entity(hass, entities["heating_rate"])
    # Not learned yet: no estimates, no error.
    assert sensor.extra_state_attributes["minutes_per_degree"] == {}
    assert sensor.extra_state_attributes["error_per_hour"] is None
    room.learner = learner = _learned_cast_iron()
    learner.constant_loss = False
    model = ThermalModel(h=2.34567, k=0.0456789, c=0.0123456, tau=45.0, learned=True)
    learner._model = model
    attrs = sensor.extra_state_attributes
    assert attrs["minutes_per_degree"] == {
        f"{t}°C": round(model.minutes_per_degree(room.current_temp, t), 1) for t in (-10, 0, 10, 20)
    }
    room.current_temp = None
    assert sensor.extra_state_attributes["minutes_per_degree"] == {}
    await _unload(hass, entry)


async def test_cooling_rate_values(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    """The fall per hour of now (3 decimals), a constant loss in the unit of the house."""
    entry, room, entities = await _room(hass, freezer, FAHRENHEIT)
    sensor = _entity(hass, entities["cooling_rate"])
    room.learner = learner = _learned_cast_iron()
    model = learner.model
    assert sensor.native_value == round(model.k * 1.8, 3)
    assert sensor.extra_state_attributes["loss_per_hour"] == round(model.k * 1.8, 3)
    assert sensor.extra_state_attributes["inertia_minutes"] == round(model.tau)
    assert sensor.suggested_display_precision == 2
    room.current_temp = None
    assert sensor.native_value is None
    await _unload(hass, entry)


# ---------------------------------------------------------------- heating time
async def test_heating_time_in_hours_with_three_decimals(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """The heating time of the house and of a room: seconds shown as hours."""
    entry, room, entities = await _room(hass, freezer)
    house = entry.runtime_data
    house_runtime = _entity(
        hass,
        hass.states.get("sensor.bedroom_decision").attributes["house_entities"]["heating_runtime"],
    )
    room_runtime = _entity(hass, entities["heating_runtime"])
    # 20 hours: exactly 20.0 (a wrong number of seconds per hour gives 19.994).
    house.boiler_runtime_s = 72000.0
    room.runtime_s = 72000.0
    assert house_runtime.native_value == 20.0
    assert room_runtime.native_value == 20.0
    house.boiler_runtime_s = 4567.0
    room.runtime_s = 9876.0
    assert house_runtime.native_value == 1.269
    assert room_runtime.native_value == 2.743
    assert house_runtime.suggested_display_precision == 2
    assert room_runtime.suggested_display_precision == 2
    await _unload(hass, entry)


# ---------------------------------------------------------------- decision sensor
async def test_decision_levels_and_limits_in_fahrenheit_with_one_decimal(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """The levels, the frost protection and the maximum: °F with one decimal."""
    entry, room, _ = await _room(
        hass, freezer, {**FAHRENHEIT, "max_temp": 25.37, "frost_temp": 7.37}
    )
    room.levels["home"] = 20.37
    room.levels["eco"] = 17.13
    attrs = _entity(hass, "sensor.bedroom_decision").extra_state_attributes
    assert attrs["levels"]["home"] == round(_f(20.37), 1)
    assert attrs["levels"]["eco"] == round(_f(17.13), 1)
    assert attrs["min_temperature"] == round(_f(room.frost_temp()), 1)
    assert attrs["max_temperature"] == round(_f(room.max_temp()), 1)
    assert attrs["min_temperature"] == 45.3
    assert attrs["max_temperature"] == 77.7
    assert attrs["temperature_unit"] == "°F"
    # The sensors of the room show one decimal.
    entities = attrs["entities"]
    assert _entity(hass, entities["target_temperature"]).suggested_display_precision == 1
    assert _entity(hass, entities["room_temperature"]).suggested_display_precision == 1
    await _unload(hass, entry)


async def test_outdoor_sensor_cutoff_in_fahrenheit(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """The cutoff and its resume temperature, °F with one decimal."""
    entry, _, _ = await _room(
        hass,
        freezer,
        {**FAHRENHEIT, "cutoff_enabled": True, "cutoff_temp": 15.37, "cutoff_hysteresis": 1.0},
    )
    house_entities = hass.states.get("sensor.bedroom_decision").attributes["house_entities"]
    outdoor = _entity(hass, house_entities["outdoor_average"])
    attrs = outdoor.extra_state_attributes
    assert attrs["cutoff_enabled"] is True
    assert attrs["cutoff_temperature"] == 59.7
    assert attrs["cutoff_resume_temperature"] == 57.9
    assert outdoor.suggested_display_precision == 1
    await _unload(hass, entry)


async def test_next_estimate_in_fahrenheit(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """The level of the next change of an optimal start, °F with one decimal."""
    entry, room, _ = await _room(
        hass,
        freezer,
        FAHRENHEIT,
        optimal_start=True,
        schedule="workday: 00:00 sleep, 13:00 home",
    )
    room.levels["home"] = 20.37
    estimate = _entity(hass, "sensor.bedroom_decision").extra_state_attributes["next_estimate"]
    assert estimate is not None
    assert estimate["kind"] == "optimal_start"
    assert estimate["temperature"] == 68.7
    await _unload(hass, entry)


# ---------------------------------------------------------------- level numbers
async def test_level_numbers_in_fahrenheit(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Limits on the 0.5 step inside the frost protection and the maximum; °F kept as °C."""
    entry, room, entities = await _room(hass, freezer, {**FAHRENHEIT, "max_temp": 25.3})
    number = _entity(hass, entities["level_home"])
    assert number.native_step == 0.5
    assert number.native_unit_of_measurement == "°F"
    # Frost protection 7 °C = 44.6 °F: up to 45.0; maximum 25.3 °C = 77.54 °F: down to 77.5.
    assert number.native_min_value == math.ceil(_f(room.frost_temp()) * 2) / 2
    assert number.native_max_value == 77.5
    room.levels["home"] = 20.37
    assert number.native_value == round(_f(20.37), 1)
    await number.async_set_native_value(70.0)
    await hass.async_block_till_done()
    # 70 °F = 21.111 °C, kept with two decimals.
    assert room.levels["home"] == 21.11
    await _unload(hass, entry)


async def test_level_number_of_a_renamed_level_and_the_nearby_one(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """A renamed level shows its name; the nearby temperature has its own number."""
    entry, room, entities = await _room(
        hass,
        freezer,
        preset_names={"home": "Acasă"},
        nearby_mode="temperature",
    )
    home = _entity(hass, entities["level_home"])
    eco = _entity(hass, entities["level_eco"])
    assert home.translation_key == "level_custom"
    assert home.translation_placeholders == {"name": "Acasă"}
    assert eco.translation_key == "level_eco"
    assert "level_nearby" in entities
    nearby = _entity(hass, entities["level_nearby"])
    assert nearby.native_value == round(room.nearby_temp, 1)
    await _unload(hass, entry)


# ---------------------------------------------------------------- why no heat
async def test_no_heat_reason_of_a_relay_room(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """A relay room below its target that does not heat: the hysteresis, in °F, or the inertia."""
    entry, room, _ = await _room(hass, freezer, FAHRENHEIT, hysteresis=0.37)
    room.heating = False
    room.current_temp = room.target_temperature - 0.1
    room.heat_demand = False
    room.inertia_stop = None
    assert room.no_heat_reason() == {"code": "hysteresis", "value": round(0.37 * 1.8, 2)}
    room.inertia_stop = 21.234
    assert room.no_heat_reason() == {"code": "inertia", "value": round(_f(21.234), 1)}
    # At the target (or above it) there is nothing to tell.
    room.current_temp = room.target_temperature
    assert room.no_heat_reason() is None
    await _unload(hass, entry)


async def test_no_heat_reason_waits_for_the_rooms_needed_or_the_reference_room(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """A room that wants heat while the house source waits for more rooms or the reference room."""
    entry, room, _ = await _room(hass, freezer, {"boiler_min_rooms": 2})
    house = entry.runtime_data
    room.heating = False
    room.current_temp = room.target_temperature - 1
    room.heat_demand = True
    house.heat_source_state = lambda: (True, False)
    house.source_waiting = None
    assert room.no_heat_reason() == {"code": "rooms_needed", "count": 1, "needed": 2}
    house.options = {**house.options, "boiler_min_rooms": 1}
    assert room.no_heat_reason() == {"code": "source_off"}
    # The state of the heat source is unknown.
    house.heat_source_state = lambda: (True, None)
    assert room.no_heat_reason() == {"code": "source_unknown"}
    # The reference room is the room itself: it does not wait for itself.
    house.heat_source_state = lambda: (True, False)
    house.options = {**house.options, "reference_room": room.id, "boiler_min_rooms": 3}
    assert room.no_heat_reason() == {"code": "source_off"}
    await _unload(hass, entry)


# ---------------------------------------------------------------- diagnostics
async def test_diagnostics_of_the_learned_model(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """The model and every candidate inertia, with their decimals."""
    entry, room, _ = await _room(hass, freezer)
    room.learner = learner = _learned_cast_iron()
    room.runtime_s = 72000.0
    data = await async_get_config_entry_diagnostics(hass, entry)
    info = data["state"]["rooms"][room.name]
    assert info["id"] == room.id
    assert info["runtime_hours"] == 20.0
    model = info["thermal_model"]
    assert model["heat_reaching_now"] == round(learner.q, 3)
    assert model["error_per_hour"] == round(learner.error, 3)
    assert model["heating_stretches"] == round(learner.heat_windows, 1)
    assert model["idle_stretches"] == round(learner.idle_windows, 1)
    assert len(model["candidates"]) == len(learner.fits)
    for fit, cand in zip(learner.fits, model["candidates"], strict=True):
        sol = fit.solve()
        assert cand["inertia_minutes"] == fit.tau
        if sol is None:
            assert cand["heating_per_hour"] is None
            assert cand["loss"] is None
            assert cand["weather_curve"] is None
            assert cand["sun_gain"] is None
        else:
            assert cand["heating_per_hour"] == round(sol[0], 4)
            assert cand["loss"] == round(sol[1], 5)
            assert cand["weather_curve"] == round(sol[2], 5)
            assert cand["sun_gain"] == round(sol[3], 4)
        assert cand["sun_seen"] == round(fit.a44, 3)
        assert cand["outdoor_spread"] == round(fit.spread(), 2)
        expected = round(fit.error / fit.weight, 5) if fit.weight > 0 else None
        assert cand["error"] == expected
    await _unload(hass, entry)
