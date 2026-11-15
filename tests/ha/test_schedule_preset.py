"""A thermostat on its schedule preset (e.g. Aqara, Tuya: ``schedule``) with a ``manual``
one, driven by temperature: put on manual once it took the temperature, so it
keeps it; one that goes back to its schedule by itself is left there (as the
TRVs that go back to auto, #15)."""

from __future__ import annotations

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import Context, HomeAssistant, ServiceCall, callback
from pytest_homeassistant_custom_component.common import async_mock_service

from tests.ha.test_ha_devices import _house, _room, _tick, _unload

BOSCH = {
    "hvac_modes": ["heat", "off"],
    "preset_modes": ["schedule", "manual", "boost"],
    "current_temperature": 19.0,
    "min_temp": 5.0,
    "max_temp": 30.0,
}
ROOM = {"source": "climate", "climates": ["climate.bosch"], "command_mode": "temperature"}


async def _bosch(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    goes_back: bool = False,
    room: dict | None = None,
    **attrs,
):
    presets: list[ServiceCall] = []

    @callback
    def _set_preset(call: ServiceCall) -> None:
        presets.append(call)
        state = hass.states.get("climate.bosch")
        new = {**state.attributes, "preset_mode": call.data["preset_mode"]}
        hass.states.async_set("climate.bosch", state.state, new, context=call.context)
        if goes_back:
            back = {**new, "preset_mode": "schedule"}
            hass.loop.call_soon(
                lambda: hass.states.async_set(
                    "climate.bosch", state.state, back, context=call.context
                )
            )

    hass.services.async_register("climate", "set_preset_mode", _set_preset)
    temps = async_mock_service(hass, "climate", "set_temperature")
    modes = async_mock_service(hass, "climate", "set_hvac_mode")
    hass.states.async_set(
        "climate.bosch",
        "heat",
        {**BOSCH, "temperature": 21.0, "preset_mode": "schedule", **attrs},
    )
    entry = await _house(hass, freezer, [("Office", {**ROOM, **(room or {})})])
    return entry, presets, temps, modes


async def test_on_its_schedule_it_is_put_on_manual(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    entry, presets, _temps, modes = await _bosch(hass, freezer)
    await _tick(hass, freezer, 5)
    assert [c.data["preset_mode"] for c in presets] == ["manual"]
    assert hass.states.get("climate.bosch").attributes["preset_mode"] == "manual"
    assert not modes
    room = _room(entry, "Office")
    assert room.decision.rule != "manual_override"
    # On manual: nothing more to send.
    await _tick(hass, freezer, 310)
    await _tick(hass, freezer, 310)
    assert len(presets) == 1
    await _unload(hass, entry)


async def test_one_that_goes_back_to_its_schedule_is_left_there(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    entry, presets, _temps, _modes = await _bosch(hass, freezer, goes_back=True)
    for _ in range(10):
        await _tick(hass, freezer, 2)
    await _tick(hass, freezer, 310)
    await _tick(hass, freezer, 310)
    assert len(presets) == 2  # tried twice
    assert hass.states.get("climate.bosch").attributes["preset_mode"] == "schedule"
    room = _room(entry, "Office")
    assert "climate.bosch" in room.keeps_auto
    assert room.decision.rule != "manual_override"
    await _unload(hass, entry)


async def test_a_late_return_to_the_schedule_is_not_a_manual_change(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Back on its schedule by itself, whenever (e.g. after its manual time): put
    on manual again; the second time it is left there."""
    entry, presets, _temps, _modes = await _bosch(hass, freezer)
    await _tick(hass, freezer, 5)
    room = _room(entry, "Office")
    for back in (1, 2):
        await _tick(hass, freezer, 3 * 3600)
        state = hass.states.get("climate.bosch")
        hass.states.async_set(
            "climate.bosch", "heat", {**state.attributes, "preset_mode": "schedule"}, Context()
        )
        await _tick(hass, freezer, 5)
        assert room.decision.rule != "manual_override"
        assert len(presets) == 2  # put on manual again once, then left on its schedule
    assert "climate.bosch" in room.keeps_auto
    sent = len(presets)
    await _tick(hass, freezer, 310)
    assert len(presets) == sent
    await _unload(hass, entry)


async def test_without_a_manual_preset_or_with_the_preset_command_it_is_left_alone(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    entry, presets, _temps, _modes = await _bosch(hass, freezer, preset_modes=["schedule", "boost"])
    await _tick(hass, freezer, 310)
    assert not presets
    await _unload(hass, entry)


async def test_the_preset_command_keeps_its_schedule(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    entry, presets, _temps, _modes = await _bosch(
        hass, freezer, room={"command_mode": "preset", "preset_map": {}}
    )
    await _tick(hass, freezer, 310)
    assert not any(c.data["preset_mode"] == "manual" for c in presets)
    await _unload(hass, entry)


async def test_its_schedule_chosen_in_home_assistant_is_a_manual_change(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    entry, presets, _temps, _modes = await _bosch(hass, freezer)
    await _tick(hass, freezer, 5)
    room = _room(entry, "Office")
    # After the time a TRV may still report its old preset once more.
    await _tick(hass, freezer, 6 * 60)
    state = hass.states.get("climate.bosch")
    hass.states.async_set(
        "climate.bosch",
        "heat",
        {**state.attributes, "preset_mode": "schedule"},
        context=Context(user_id="someone"),
    )
    await _tick(hass, freezer, 5)
    assert room.decision.rule == "manual_override"
    assert "climate.bosch" not in room.keeps_auto
    assert len(presets) == 1
    await _unload(hass, entry)


async def test_one_that_refuses_the_temperature_on_its_schedule_is_put_on_manual(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """On its schedule it keeps the temperature of the schedule (18): put on
    manual first, then it takes the temperature, without being sent it again
    and again."""
    temps: list[ServiceCall] = []
    presets: list[ServiceCall] = []

    @callback
    def _set_temperature(call: ServiceCall) -> None:
        temps.append(call)
        state = hass.states.get("climate.trv")
        on_schedule = state.attributes["preset_mode"] == "schedule"
        value = 18.0 if on_schedule else call.data["temperature"]
        new = {**state.attributes, "temperature": value}
        hass.states.async_set("climate.trv", state.state, new, context=call.context)

    @callback
    def _set_preset(call: ServiceCall) -> None:
        presets.append(call)
        state = hass.states.get("climate.trv")
        new = {**state.attributes, "preset_mode": call.data["preset_mode"]}
        hass.states.async_set("climate.trv", state.state, new, context=call.context)

    hass.services.async_register("climate", "set_temperature", _set_temperature)
    hass.services.async_register("climate", "set_preset_mode", _set_preset)
    async_mock_service(hass, "climate", "set_hvac_mode")
    hass.states.async_set(
        "climate.trv",
        "heat",
        {
            **BOSCH,
            "preset_modes": ["schedule", "manual", "holiday"],
            "preset_mode": "schedule",
            "temperature": 18.0,
        },
    )
    entry = await _house(hass, freezer, [("Office", {**ROOM, "climates": ["climate.trv"]})])
    for _ in range(30):
        await _tick(hass, freezer, 60)
    state = hass.states.get("climate.trv")
    assert state.attributes["preset_mode"] == "manual"
    assert state.attributes["temperature"] == 21.0
    assert [c.data["preset_mode"] for c in presets] == ["manual"]
    assert len(temps) <= 2
    room = _room(entry, "Office")
    assert room.decision.rule != "manual_override"
    assert "climate.trv" not in room.keeps_auto
    await _unload(hass, entry)
