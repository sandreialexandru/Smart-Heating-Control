"""A change made on one of several thermostats of a room: for that one, or the whole room (#24)."""

from __future__ import annotations

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import Context, HomeAssistant, ServiceCall
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_mock_service

from custom_components.advanced_climate.const import (
    CONF_REEVAL_MINUTES,
    HOUSE_DEFAULTS,
    VERIFY_DELAY,
)
from tests.ha.test_ha_devices import GT_OPTIONS, GT_STATE, TRV, _house, _room, _tick, _unload

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
    # The boost ends by itself (back to Comfort at 21 °C): still that TRV only.
    hass.states.async_set(LEFT, "heat", SMART, context=Context())
    await _tick(hass, freezer, 5)
    assert room.override.get("source_device") is None
    # A temperature set while the TRV keeps showing its preset: the temperature, not the preset.
    hass.states.async_set(LEFT, "heat", {**SMART, "temperature": 24.0}, context=Context())
    await _tick(hass, freezer, 5)
    assert room.override["source_device"] == LEFT
    assert room.override["target"] == {"kind": "temperature", "preset": None, "temperature": 24.0}
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
    # Turned on again with nothing else changed: that TRV only, nothing for the others.
    sent = len(_calls)
    hass.states.async_set(LEFT, "heat", preset_trv, context=Context())
    await _tick(hass, freezer, 5)
    assert room.override.get("source_device") is None
    assert not [c for c in _calls[sent:] if c.data["entity_id"] == RIGHT]
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


def _two_gts(hass: HomeAssistant) -> list[str]:
    """Two Generic Thermostats set up in the UI, in one room."""
    registry = er.async_get(hass)
    ids = []
    for name in ("living_gt_a", "living_gt_b"):
        gt_entry = MockConfigEntry(domain="generic_thermostat", options=GT_OPTIONS)
        gt_entry.add_to_hass(hass)
        entity_id = registry.async_get_or_create(
            "climate",
            "generic_thermostat",
            gt_entry.entry_id,
            config_entry=gt_entry,
            suggested_object_id=name,
        ).entity_id
        hass.states.async_set(entity_id, "heat", GT_STATE)
        ids.append(entity_id)
    return ids


async def test_generic_thermostats_for_the_whole_room_without_a_loop(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Generic Thermostats take the preset of a temperature set (22 °C: comfort) by themselves.

    A temperature of a preset set on one becomes that level in the room; one
    of no preset becomes the temperature; nothing is sent over and over.
    """
    gt_a, gt_b = _two_gts(hass)
    temps = {p: GT_OPTIONS[f"{p}_temp"] for p in ("home", "eco", "away", "sleep", "comfort")}
    calls: list[tuple[str, str, object]] = []
    saved = {gt_a: GT_STATE["temperature"], gt_b: GT_STATE["temperature"]}

    def show(entity_id: str, value: float, preset: str, context: Context) -> None:
        state = hass.states.get(entity_id)
        hass.states.async_set(
            entity_id,
            state.state,
            {**state.attributes, "temperature": value, "preset_mode": preset},
            context=context,
        )

    async def set_temperature(call: ServiceCall) -> None:
        entity_id, value = call.data["entity_id"], float(call.data["temperature"])
        calls.append((entity_id, "temperature", value))
        preset = next((p for p, t in temps.items() if t == value), "none")
        if preset == "none":
            saved[entity_id] = value
        show(entity_id, value, preset, call.context)

    async def set_preset_mode(call: ServiceCall) -> None:
        entity_id, preset = call.data["entity_id"], call.data["preset_mode"]
        calls.append((entity_id, "preset", preset))
        state = hass.states.get(entity_id)
        if state.attributes.get("preset_mode") in (None, "none"):
            saved[entity_id] = state.attributes["temperature"]
        show(
            entity_id, saved[entity_id] if preset == "none" else temps[preset], preset, call.context
        )

    hass.services.async_register("climate", "set_temperature", set_temperature)
    hass.services.async_register("climate", "set_preset_mode", set_preset_mode)
    entry = await _house(
        hass,
        freezer,
        [
            (
                "Living",
                {"source": "generic_thermostat", "climates": [gt_a, gt_b], "device_change": "room"},
            )
        ],
    )
    room = _room(entry, "Living")
    assert hass.states.get(gt_b).attributes["preset_mode"] == "home"

    # 22 °C on the first one: it takes comfort by itself, the room takes comfort.
    calls.clear()
    hass.states.async_set(
        gt_a, "heat", {**GT_STATE, "temperature": 22.0, "preset_mode": "comfort"}, context=Context()
    )
    for _ in range(20):
        await _tick(hass, freezer, 30)
    assert room.override["source_device"] == gt_a
    assert room.override["target"]["kind"] == "preset"
    assert room.override["target"]["preset"] == "comfort"
    assert hass.states.get(gt_b).attributes["preset_mode"] == "comfort"
    # At most the preset, for each of the two: no loop.
    assert len(calls) <= 2, calls

    # 22.5 °C (no preset has it) on the second one: off its preset, the temperature for both.
    calls.clear()
    hass.states.async_set(
        gt_b, "heat", {**GT_STATE, "temperature": 22.5, "preset_mode": "none"}, context=Context()
    )
    for _ in range(20):
        await _tick(hass, freezer, 30)
    assert room.override["source_device"] == gt_b
    assert room.override["target"]["temperature"] == 22.5
    state = hass.states.get(gt_a)
    assert (state.attributes["temperature"], state.attributes["preset_mode"]) == (22.5, "none")
    # At most off its preset and the temperature, for each of the two: no loop.
    assert len(calls) <= 4, calls
    assert not [a for a in entry.runtime_data.active_alerts if a.startswith("commands_")]
    await _unload(hass, entry)


async def test_thermostats_turned_on_and_off_for_the_whole_room(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Commanded by on / off: a temperature set on one becomes the room target, so both heat."""
    modes = async_mock_service(hass, "climate", "set_hvac_mode")
    temperatures = async_mock_service(hass, "climate", "set_temperature")
    onoff = {"hvac_modes": ["heat", "off"], "current_temperature": 22.0, "temperature": 21.0}
    for entity_id in (LEFT, RIGHT):
        hass.states.async_set(entity_id, "off", onoff)
    entry = await _house(
        hass,
        freezer,
        [
            (
                "Living",
                {
                    "source": "climate",
                    "climates": [LEFT, RIGHT],
                    "command_mode": "hvac_mode",
                    "min_on_minutes": 0,
                    "min_off_minutes": 0,
                    "device_change": "room",
                },
            )
        ],
    )
    room = _room(entry, "Living")
    # 22 °C, above the 21 °C of the level: both off.
    assert not [m for m in modes if m.data["hvac_mode"] == "heat"]
    # Someone turns the left one on at 23 °C.
    hass.states.async_set(LEFT, "heat", {**onoff, "temperature": 23.0}, context=Context())
    await _tick(hass, freezer, 5)
    assert room.override["source_device"] == LEFT
    assert room.override["target"]["temperature"] == 23.0
    # The room is on: the right one, still off, is turned on too, heating as far as it can
    # (the room sensor turns them off), as the left one.
    assert {"entity_id": RIGHT, "hvac_mode": "heat"} in [m.data for m in modes]
    assert {c.data["entity_id"] for c in temperatures} == {LEFT, RIGHT}
    assert {c.data["temperature"] for c in temperatures} == {room.max_temp()}
    await _unload(hass, entry)


async def test_an_on_off_thermostat_left_off_is_turned_on_with_the_others(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """The room is on when one of its thermostats is: one that did not take the command follows."""
    modes = async_mock_service(hass, "climate", "set_hvac_mode")
    async_mock_service(hass, "climate", "set_temperature")
    cold = {"hvac_modes": ["heat", "off"], "current_temperature": 19.0, "temperature": 21.0}
    for entity_id in (LEFT, RIGHT):
        hass.states.async_set(entity_id, "off", cold)
    entry = await _house(
        hass,
        freezer,
        [
            (
                "Living",
                {
                    "source": "climate",
                    "climates": [LEFT, RIGHT],
                    "command_mode": "hvac_mode",
                    "min_on_minutes": 0,
                    "min_off_minutes": 0,
                },
            )
        ],
    )
    assert {"entity_id": RIGHT, "hvac_mode": "heat"} in [m.data for m in modes]
    # Only the left one took it; the right one stayed off.
    sent = len(modes)
    hass.states.async_set(LEFT, "heat", cold, context=Context())
    # The same command is not sent again before the verification delay (a TRV may
    # confirm late): it is at the next periodic evaluation after it (every 5 minutes
    # by default), a minute after that at the latest.
    for _ in range(max(VERIFY_DELAY // 60, HOUSE_DEFAULTS[CONF_REEVAL_MINUTES]) + 1):
        await _tick(hass, freezer, 60)
    room = _room(entry, "Living")
    assert {"entity_id": RIGHT, "hvac_mode": "heat"} in [m.data for m in modes[sent:]], (
        room.decision.rule if room.decision else None,
        room.decision.target if room.decision else None,
        room.override,
        room.relay_waiting,
        room.current_temp,
        room.pending_command,
        [m.data for m in modes],
        hass.states.get(LEFT).state,
        hass.states.get(RIGHT).state,
    )
    assert {"entity_id": LEFT, "hvac_mode": "heat"} not in [m.data for m in modes[sent:]]
    await _unload(hass, entry)


async def test_a_slow_trv_reporting_before_the_command_returns_is_no_manual_change(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """A TRV that reports the new target itself while the command still waits (#28).

    ZHA waits for a battery TRV to confirm a write, sometimes for half a minute;
    the TRV may report the new value meanwhile, with a context of its own. The
    value was sent: no manual change, neither on that TRV nor on the whole room.
    """
    import asyncio

    entry, _calls, _presets = await _living(hass, freezer, "room")
    room = _room(entry, "Living")
    sent: list[tuple[str, float]] = []

    async def slow_set_temperature(call: ServiceCall) -> None:
        entity_id = call.data["entity_id"]
        value = call.data["temperature"]
        sent.append((entity_id, value))
        if entity_id == RIGHT:
            # The TRV's own report, before the call returns.
            state = hass.states.get(RIGHT)
            hass.states.async_set(
                RIGHT, "heat", {**state.attributes, "temperature": value}, context=Context()
            )
            for _ in range(5):
                await asyncio.sleep(0)

    hass.services.async_register("climate", "set_temperature", slow_set_temperature)
    # Away: a new target for the room, sent to both TRVs.
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": "select.home_mode", "option": "away"},
        blocking=True,
    )
    await _tick(hass, freezer, 5)
    assert any(entity_id == RIGHT for entity_id, _value in sent)
    assert room.override is None
    assert hass.states.get("sensor.living_decision").state != "manual_override"
    await _unload(hass, entry)


async def test_a_slow_thermostat_does_not_hold_the_others_back(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """The thermostats of a room get their commands at once, not one after the other."""
    import asyncio

    entry, _calls, _presets = await _living(hass, freezer, "device")
    order: list[str] = []

    async def set_temperature(call: ServiceCall) -> None:
        entity_id = call.data["entity_id"]
        first = not order
        order.append(f"start {entity_id}")
        if first:
            # The first one called is slow: its call still waits.
            for _ in range(10):
                await asyncio.sleep(0)
        order.append(f"end {entity_id}")

    hass.services.async_register("climate", "set_temperature", set_temperature)
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": "select.home_mode", "option": "away"},
        blocking=True,
    )
    await _tick(hass, freezer, 5)
    assert f"start {LEFT}" in order and f"start {RIGHT}" in order
    # The other one started before the slow first one ended.
    slow = order[0].removeprefix("start ")
    other = RIGHT if slow == LEFT else LEFT
    assert order.index(f"start {other}") < order.index(f"end {slow}")
    await _unload(hass, entry)
