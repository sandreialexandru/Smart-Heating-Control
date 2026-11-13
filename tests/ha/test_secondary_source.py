"""A secondary heat source of the house: only one of the two runs.

The select of the house chooses it (Automatic by a criterion, primary or
secondary); the source not in use stays off; an unavailable one is replaced by
the other; the options ask only for what applies.
"""

from __future__ import annotations

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import Context, HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import HomeAssistantError
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.advanced_climate.const import SUBENTRY_ROOM
from tests.ha.test_ha_config_flow import _house_with_rooms, _keys
from tests.ha.test_ha_devices import _house, _room, _tick, _unload

TRV = {
    "hvac_modes": ["heat", "off"],
    "current_temperature": 20.0,
    "min_temp": 5.0,
    "max_temp": 30.0,
}
ROOM = {"source": "climate", "command_mode": "temperature", "climates": ["climate.bedroom"]}
BOILER, PUMP = "input_boolean.boiler", "input_boolean.pump"


async def _setup(hass: HomeAssistant, freezer: FrozenDateTimeFactory, **options):
    async_mock_service(hass, "climate", "set_temperature")
    async_mock_service(hass, "climate", "set_hvac_mode")
    assert await async_setup_component(
        hass, "input_boolean", {"input_boolean": {"boiler": {}, "pump": {}, "sunny": {}}}
    )
    hass.states.async_set("climate.bedroom", "heat", {**TRV, "temperature": 21.0})
    return await _house(
        hass,
        freezer,
        [("Bedroom", ROOM)],
        boiler_entity=BOILER,
        secondary_source=PUMP,
        **options,
    )


def _report(hass: HomeAssistant, action: str) -> None:
    hass.states.async_set(
        "climate.bedroom", "heat", {**TRV, "temperature": 21.0, "hvac_action": action}, Context()
    )


def _on(hass: HomeAssistant, entity_id: str) -> bool:
    return hass.states.get(entity_id).state == "on"


def _select(hass: HomeAssistant) -> str:
    return "select.home_heat_source"


async def _choose(hass: HomeAssistant, freezer: FrozenDateTimeFactory, option: str) -> None:
    await hass.services.async_call(
        "select", "select_option", {"entity_id": _select(hass), "option": option}, blocking=True
    )
    await _tick(hass, freezer, 5)


async def test_only_the_chosen_source_runs(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    entry = await _setup(hass, freezer)
    state = hass.states.get(_select(hass))
    # No criterion: no Automatic, the primary source by default.
    assert state.attributes["options"] == ["primary", "secondary"]
    assert state.state == "primary"
    _report(hass, "heating")
    await _tick(hass, freezer, 5)
    assert _on(hass, BOILER) and not _on(hass, PUMP)
    assert _room(entry, "Bedroom").heating

    # Chosen by hand: at once, the boiler stops before the pump starts.
    await _choose(hass, freezer, "secondary")
    assert _on(hass, PUMP) and not _on(hass, BOILER)
    assert hass.states.get(_select(hass)).attributes["active"] == "secondary"
    assert entry.runtime_data.heat_source_state() == (True, True)

    # The source not in use is kept off.
    await hass.services.async_call("input_boolean", "turn_on", {"entity_id": BOILER}, blocking=True)
    await _tick(hass, freezer, 65)
    assert not _on(hass, BOILER)

    _report(hass, "idle")
    await _tick(hass, freezer, 5)
    assert not _on(hass, PUMP) and not _on(hass, BOILER)
    await _unload(hass, entry)


async def test_automatic_by_the_criterion_after_the_switching_time(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    entry = await _setup(
        hass,
        freezer,
        source_criterion="entity",
        source_criterion_entity="input_boolean.sunny",
        source_switch_minutes=15,
    )
    state = hass.states.get(_select(hass))
    assert state.attributes["options"] == ["auto", "primary", "secondary"]
    assert state.state == "auto"
    _report(hass, "heating")
    await _tick(hass, freezer, 5)
    assert _on(hass, BOILER)

    # The sun comes out: the pump only after 15 minutes.
    await hass.services.async_call(
        "input_boolean", "turn_on", {"entity_id": "input_boolean.sunny"}, blocking=True
    )
    await _tick(hass, freezer, 5)
    assert _on(hass, BOILER) and not _on(hass, PUMP)
    assert hass.states.get(_select(hass)).attributes["switch_at"] is not None
    # A cloud for 5 minutes: the waiting starts again.
    await _tick(hass, freezer, 300)
    await hass.services.async_call(
        "input_boolean", "turn_off", {"entity_id": "input_boolean.sunny"}, blocking=True
    )
    await _tick(hass, freezer, 5)
    await _tick(hass, freezer, 300)
    await hass.services.async_call(
        "input_boolean", "turn_on", {"entity_id": "input_boolean.sunny"}, blocking=True
    )
    await _tick(hass, freezer, 5)
    await _tick(hass, freezer, 600)
    assert _on(hass, BOILER) and not _on(hass, PUMP)
    await _tick(hass, freezer, 300)
    assert _on(hass, PUMP) and not _on(hass, BOILER)
    assert hass.states.get(_select(hass)).attributes["switch_at"] is None

    # By hand the primary one: at once, whatever the criterion says.
    await _choose(hass, freezer, "primary")
    assert _on(hass, BOILER) and not _on(hass, PUMP)
    # Back to Automatic: the criterion has been on for long, at once.
    await _choose(hass, freezer, "auto")
    assert _on(hass, PUMP) and not _on(hass, BOILER)
    await _unload(hass, entry)


async def test_the_choice_is_kept_over_a_restart(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    entry = await _setup(hass, freezer)
    await _choose(hass, freezer, "secondary")
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    await _tick(hass, freezer, 15)
    assert hass.states.get(_select(hass)).state == "secondary"
    assert entry.runtime_data.active_source == "secondary"
    await _unload(hass, entry)


async def test_pv_surplus_and_cold_criteria(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    hass.states.async_set("sensor.pv", "2000")
    entry = await _setup(
        hass, freezer, pv_sensor="sensor.pv", pv_threshold=1500, source_criterion="pv_surplus"
    )
    house = entry.runtime_data
    assert house.source_criterion == "pv_surplus"
    assert house.criterion_on() is True
    hass.states.async_set("sensor.pv", "800")
    assert house.criterion_on() is False
    hass.states.async_set("sensor.pv", "unavailable")
    assert house.criterion_on() is None
    await _unload(hass, entry)


async def test_a_criterion_that_cannot_work_gives_no_automatic(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    # Cheap power without the price sensor, cold without an outdoor temperature.
    entry = await _setup(hass, freezer, source_criterion="cheap_power")
    assert entry.runtime_data.source_criterion == "none"
    assert hass.states.get(_select(hass)).attributes["options"] == ["primary", "secondary"]
    await _unload(hass, entry)


async def test_an_unavailable_source_is_replaced_by_the_other(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    entry = await _setup(hass, freezer, alert_unavailable_minutes=15)
    await _choose(hass, freezer, "secondary")
    _report(hass, "heating")
    await _tick(hass, freezer, 5)
    assert _on(hass, PUMP)
    hass.states.async_set(PUMP, "unavailable")
    await _tick(hass, freezer, 65)
    assert entry.runtime_data.active_source == "primary"
    assert _on(hass, BOILER)
    await _tick(hass, freezer, 16 * 60)
    alerts = entry.runtime_data.notifier.active
    assert alerts[f"unavailable_{PUMP}"]["code"] == "source_unavailable_other"
    # Back: the chosen one heats again, at once.
    hass.states.async_set(PUMP, "off")
    await _tick(hass, freezer, 65)
    assert entry.runtime_data.active_source == "secondary"
    assert _on(hass, PUMP) and not _on(hass, BOILER)
    assert f"unavailable_{PUMP}" not in entry.runtime_data.notifier.active
    await _unload(hass, entry)


async def test_no_select_without_a_secondary_source(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    async_mock_service(hass, "climate", "set_temperature")
    assert await async_setup_component(hass, "input_boolean", {"input_boolean": {"boiler": {}}})
    hass.states.async_set("climate.bedroom", "heat", {**TRV, "temperature": 21.0})
    entry = await _house(hass, freezer, [("Bedroom", ROOM)], boiler_entity=BOILER)
    assert hass.states.get(_select(hass)) is None
    assert entry.runtime_data.source_entity == BOILER
    await _unload(hass, entry)


# ---------------------------------------------------------------------------
# Options: only what applies
# ---------------------------------------------------------------------------
async def _boiler_flow(hass: HomeAssistant, entry, first: dict):
    options = hass.config_entries.options
    result = await options.async_init(entry.entry_id)
    result = await options.async_configure(result["flow_id"], {"next_step_id": "boiler"})
    return options, await options.async_configure(result["flow_id"], first)


async def test_options_without_a_secondary_source_ask_nothing_of_it(hass: HomeAssistant) -> None:
    entry = _house_with_rooms(hass, options={"boiler_entity": "switch.boiler"})
    _, result = await _boiler_flow(hass, entry, {"boiler_entity": "switch.boiler"})
    assert result["step_id"] == "boiler_details"
    assert "source_criterion" not in _keys(result)


async def test_options_of_a_secondary_source(hass: HomeAssistant) -> None:
    entry = _house_with_rooms(hass, options={"pv_sensor": "sensor.pv"})
    options, result = await _boiler_flow(hass, entry, {"secondary_source": "switch.pump"})
    assert result["errors"] == {"secondary_source": "secondary_without_primary"}
    result = await options.async_configure(
        result["flow_id"], {"boiler_entity": "switch.boiler", "secondary_source": "switch.boiler"}
    )
    assert result["errors"] == {"secondary_source": "secondary_is_primary"}
    result = await options.async_configure(
        result["flow_id"], {"boiler_entity": "switch.boiler", "secondary_source": "switch.pump"}
    )
    assert result["step_id"] == "boiler_details"
    assert "source_criterion" in _keys(result)
    field = next(k for k in result["data_schema"].schema if str(k) == "source_criterion")
    # Only what can work: the PV sensor is set, no outdoor temperature, no price.
    assert result["data_schema"].schema[field].config["options"] == [
        "none",
        "pv_surplus",
        "entity",
    ]
    # Not a circuit either.
    result = await options.async_configure(
        result["flow_id"], {"circuits": ["switch.pump"], "source_criterion": "none"}
    )
    assert result["errors"] == {"circuits": "circuit_is_source"}
    # PV surplus: only the switching time is asked.
    result = await options.async_configure(result["flow_id"], {"source_criterion": "pv_surplus"})
    assert result["step_id"] == "boiler_source"
    assert _keys(result) == {"source_switch_minutes"}
    result = await options.async_configure(result["flow_id"], {"source_switch_minutes": 20})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["secondary_source"] == "switch.pump"
    assert entry.options["source_criterion"] == "pv_surplus"
    assert entry.options["source_switch_minutes"] == 20


async def test_options_of_the_entity_and_cold_criteria(hass: HomeAssistant) -> None:
    entry = _house_with_rooms(
        hass,
        options={
            "boiler_entity": "switch.boiler",
            "secondary_source": "switch.pump",
            "outdoor_sensor": "sensor.outdoor",
        },
    )
    options, result = await _boiler_flow(
        hass, entry, {"boiler_entity": "switch.boiler", "secondary_source": "switch.pump"}
    )
    result = await options.async_configure(result["flow_id"], {"source_criterion": "entity"})
    assert _keys(result) == {"source_criterion_entity", "source_switch_minutes"}
    result = await options.async_configure(
        result["flow_id"], {"source_criterion_entity": "switch.pump", "source_switch_minutes": 15}
    )
    assert result["errors"] == {"source_criterion_entity": "criterion_is_source"}
    result = await options.async_configure(
        result["flow_id"],
        {"source_criterion_entity": "binary_sensor.sunny", "source_switch_minutes": 15},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY

    # Cold outside: the temperature instead of the entity, which is no longer kept.
    options, result = await _boiler_flow(
        hass, entry, {"boiler_entity": "switch.boiler", "secondary_source": "switch.pump"}
    )
    result = await options.async_configure(result["flow_id"], {"source_criterion": "cold"})
    assert _keys(result) == {"source_cold_below", "source_switch_minutes"}
    result = await options.async_configure(
        result["flow_id"], {"source_cold_below": -3, "source_switch_minutes": 15}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["source_cold_below"] == -3
    assert "source_criterion_entity" not in entry.options

    # None: no third step, nothing of the criteria kept.
    options, result = await _boiler_flow(
        hass, entry, {"boiler_entity": "switch.boiler", "secondary_source": "switch.pump"}
    )
    result = await options.async_configure(result["flow_id"], {"source_criterion": "none"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert "source_cold_below" not in entry.options

    # Without the secondary source, nothing of it is kept.
    options, result = await _boiler_flow(hass, entry, {"boiler_entity": "switch.boiler"})
    result = await options.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert "secondary_source" not in entry.options
    assert "source_criterion" not in entry.options


async def test_a_secondary_source_is_not_a_device_of_a_room(hass: HomeAssistant) -> None:
    entry = _house_with_rooms(
        hass, options={"boiler_entity": "switch.boiler", "secondary_source": "switch.pump"}
    )
    flow = hass.config_entries.subentries
    result = await flow.async_init((entry.entry_id, SUBENTRY_ROOM), context={"source": SOURCE_USER})
    result = await flow.async_configure(result["flow_id"], {"name": "Hall", "source": "switch"})
    result = await flow.async_configure(
        result["flow_id"], {"switches": ["switch.pump"], "use_house_source": False}
    )
    assert result["errors"] == {"switches": "entity_is_source"}


async def test_cold_and_cheap_power_criteria(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    hass.states.async_set("sensor.outdoor", "-8", {"unit_of_measurement": "°C"})
    hass.states.async_set("sensor.price", "0.10")
    entry = await _setup(
        hass,
        freezer,
        outdoor_sensor="sensor.outdoor",
        price_sensor="sensor.price",
        price_low=0.12,
        source_criterion="cold",
        source_cold_below=-5.0,
    )
    house = entry.runtime_data
    assert house.source_criterion == "cold"
    assert house.criterion_on() is True
    house.options["source_criterion"] = "cheap_power"
    assert house.criterion_on() is True
    hass.states.async_set("sensor.price", "0.30")
    assert house.criterion_on() is False
    # Only the choices of the select.
    with pytest.raises(HomeAssistantError):
        await house.async_set_source("boiler")
    await _unload(hass, entry)


async def test_the_select_goes_with_the_secondary_source(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    entry = await _setup(hass, freezer)
    assert hass.states.get(_select(hass)) is not None
    hass.config_entries.async_update_entry(
        entry, options={k: v for k, v in entry.options.items() if k != "secondary_source"}
    )
    await hass.async_block_till_done()
    await _tick(hass, freezer, 15)
    assert hass.states.get(_select(hass)) is None
    await _unload(hass, entry)
