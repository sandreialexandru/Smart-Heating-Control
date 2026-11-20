"""A change made on one of several thermostats of a room: for that one, or the whole room (#24)."""

from __future__ import annotations

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import Context, HomeAssistant
from pytest_homeassistant_custom_component.common import async_mock_service

from tests.ha.test_ha_devices import TRV, _house, _room, _tick, _unload

LEFT = "climate.living_left"
RIGHT = "climate.living_right"


async def _living(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    change: str | None,
    right: dict | None = None,
    confirm: tuple[str, ...] = (LEFT, RIGHT, "climate.office"),
    **options: object,
):
    """A living room with two TRVs (the right one can be another model) and an office."""
    calls = async_mock_service(hass, "climate", "set_temperature")
    presets = async_mock_service(hass, "climate", "set_preset_mode")
    async_mock_service(hass, "climate", "set_hvac_mode")
    hass.states.async_set(LEFT, "heat", TRV)
    hass.states.async_set(RIGHT, "heat", {**TRV, **(right or {})})
    hass.states.async_set("climate.office", "heat", TRV)
    living = {"source": "climate", "climates": [LEFT, RIGHT], "command_mode": "temperature"}
    if change is not None:
        living["device_change"] = change
    entry = await _house(
        hass,
        freezer,
        [
            ("Living", living),
            (
                "Office",
                {
                    "source": "climate",
                    "climates": ["climate.office"],
                    "command_mode": "temperature",
                },
            ),
        ],
        **options,
    )
    # The TRVs show what the decision sent them (21 °C at home on Monday noon).
    for entity_id in confirm:
        state = hass.states.get(entity_id)
        hass.states.async_set(entity_id, "heat", {**state.attributes, "temperature": 21.0})
    await _tick(hass, freezer, 5)
    return entry, calls, presets


def _sent(calls, entity_id: str) -> list[float]:
    return [c.data["temperature"] for c in calls if c.data["entity_id"] == entity_id]


async def test_by_default_a_change_stays_on_that_thermostat(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Nothing changes on an update: without the option the other TRV keeps the decision."""
    entry, calls, _presets = await _living(hass, freezer, None)
    hass.states.async_set(LEFT, "heat", {**TRV, "temperature": 23.0}, context=Context())
    await _tick(hass, freezer, 5)
    decision = hass.states.get("sensor.living_decision")
    assert decision.state == "manual_override"
    assert decision.attributes["override"]["origin"] == "device"
    assert decision.attributes["override"]["devices"] == [LEFT]
    assert 23.0 not in _sent(calls, RIGHT)
    await _unload(hass, entry)


async def test_a_temperature_set_on_one_trv_is_sent_to_the_whole_room(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    entry, calls, _presets = await _living(hass, freezer, "room")
    hass.states.async_set(LEFT, "heat", {**TRV, "temperature": 23.0}, context=Context())
    await _tick(hass, freezer, 5)
    decision = hass.states.get("sensor.living_decision")
    assert decision.state == "manual_override"
    override = decision.attributes["override"]
    assert override["origin"] == "room"
    assert override["source_device"] == LEFT
    assert override["temperature"] == 23.0
    assert override["description"] == f"23.0 °C on {LEFT}, whole room"
    assert _sent(calls, RIGHT)[-1] == 23.0
    # The other room is not touched.
    assert hass.states.get("sensor.office_decision").state != "manual_override"
    await _unload(hass, entry)


async def test_a_late_report_of_the_other_trv_is_no_new_change(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """A battery TRV that reports its old value late does not take the room back."""
    # The right TRV sleeps: it still shows 17 °C, not the 21 °C sent to it.
    entry, calls, _presets = await _living(hass, freezer, "room", confirm=(LEFT, "climate.office"))
    room = _room(entry, "Living")
    assert _sent(calls, RIGHT)[-1] == 21.0
    hass.states.async_set(LEFT, "heat", {**TRV, "temperature": 23.0}, context=Context())
    await _tick(hass, freezer, 5)
    assert _sent(calls, RIGHT)[-1] == 23.0
    # It wakes up: first it reports the earlier 21 °C, then the 23 °C.
    hass.states.async_set(RIGHT, "heat", {**TRV, "temperature": 21.0}, context=Context())
    await _tick(hass, freezer, 5)
    hass.states.async_set(RIGHT, "heat", {**TRV, "temperature": 23.0}, context=Context())
    await _tick(hass, freezer, 5)
    assert room.override is not None
    assert room.override["source_device"] == LEFT
    assert room.override["target"]["temperature"] == 23.0
    await _unload(hass, entry)


async def test_different_trvs_each_within_their_own_range(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Another model with another range and step: each gets the value within its own."""
    entry, calls, _presets = await _living(
        hass, freezer, "room", right={"min_temp": 8.0, "max_temp": 30.0, "target_temp_step": 0.5}
    )
    hass.states.async_set(LEFT, "heat", {**TRV, "temperature": 22.3}, context=Context())
    await _tick(hass, freezer, 5)
    assert _sent(calls, RIGHT)[-1] == 22.3
    # Set below the frost protection (7 °C): the room is kept at it, the right TRV at its minimum.
    hass.states.async_set(LEFT, "heat", {**TRV, "temperature": 6.0}, context=Context())
    await _tick(hass, freezer, 5)
    room = _room(entry, "Living")
    assert room.override["target"]["temperature"] == 7.0
    assert _sent(calls, LEFT)[-1] == 7.0
    assert _sent(calls, RIGHT)[-1] == 8.0
    await _unload(hass, entry)


SMART = {
    "hvac_modes": ["heat", "off"],
    "preset_modes": ["Comfort", "Eco", "Away", "Boost"],
    "preset_mode": "Comfort",
    "current_temperature": 20.0,
    "temperature": 21.0,
    "hvac_action": "idle",
}


async def test_a_preset_of_a_level_sets_that_level_in_the_whole_room(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    presets = async_mock_service(hass, "climate", "set_preset_mode")
    async_mock_service(hass, "climate", "set_temperature")
    for entity_id in (LEFT, RIGHT):
        hass.states.async_set(entity_id, "heat", SMART)
    entry = await _house(
        hass,
        freezer,
        [
            (
                "Living",
                {
                    "source": "climate",
                    "climates": [LEFT, RIGHT],
                    "command_mode": "preset",
                    "preset_map": {"home": "Comfort", "eco": "Eco", "away": "Away"},
                    "device_change": "room",
                },
            )
        ],
    )
    room = _room(entry, "Living")
    hass.states.async_set(LEFT, "heat", {**SMART, "preset_mode": "Eco"}, context=Context())
    await _tick(hass, freezer, 5)
    assert room.override["target"] == {"kind": "preset", "preset": "eco", "temperature": None}
    assert {"entity_id": RIGHT, "preset_mode": "Eco"} in [c.data for c in presets]
    # Boost is no level: it stays on that TRV.
    hass.states.async_set(LEFT, "heat", {**SMART, "preset_mode": "Boost"}, context=Context())
    await _tick(hass, freezer, 5)
    assert room.override.get("source_device") is None
    assert room.override["target"] is None
    assert room.override["devices"].keys() == {LEFT}
    assert presets[-1].data["preset_mode"] != "Boost"
    await _unload(hass, entry)


async def test_off_stays_on_that_trv(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    entry, _calls, _presets = await _living(hass, freezer, "room")
    room = _room(entry, "Living")
    preset_trv = {**TRV, "temperature": 21.0}
    hass.states.async_set(LEFT, "off", preset_trv, context=Context())
    await _tick(hass, freezer, 5)
    assert room.override is not None
    assert room.override.get("source_device") is None
    assert room.override["devices"].keys() == {LEFT}
    assert hass.states.get("sensor.living_decision").attributes["override"]["origin"] == "device"
    await _unload(hass, entry)


async def test_with_the_whole_house_scope(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """The room gets the temperature on both TRVs; the other rooms keep what they have."""
    entry, calls, _presets = await _living(hass, freezer, "room", override_scope="house")
    hass.states.async_set(LEFT, "heat", {**TRV, "temperature": 23.0}, context=Context())
    await _tick(hass, freezer, 5)
    assert _sent(calls, RIGHT)[-1] == 23.0
    office = hass.states.get("sensor.office_decision")
    assert office.state == "manual_override"
    assert office.attributes["override"]["description"].endswith("(Living)")
    assert 23.0 not in _sent(calls, "climate.office")
    await _unload(hass, entry)


async def test_the_child_lock_still_sets_the_trv_back(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    entry, calls, _presets = await _living(hass, freezer, "room")
    room = _room(entry, "Living")
    await room.async_set_child_lock(True)
    hass.states.async_set(LEFT, "heat", {**TRV, "temperature": 25.0}, context=Context())
    await _tick(hass, freezer, 5)
    assert room.override is None
    assert _sent(calls, LEFT)[-1] == 21.0
    assert 25.0 not in _sent(calls, RIGHT)
    await _unload(hass, entry)
