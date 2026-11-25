"""Before a release: two houses, many rooms and thermostats that behave like real ones.

The thermostats here apply the commands as devices do: each rounds to its own
step, keeps its own limits (a lower maximum on the device than on its entity),
and battery ones report late, with a context of their own. Over three days
people leave and come back, change thermostats by hand (one thermostat, the
whole room, presets, boost, off), open windows, pause the house, set the child
lock, reload, and call the services. After each event what the rooms hold is
checked, and at the end: no error in the log, no command loop (no commands
paused for a device), every room with a valid decision, the devices holding the
decision, the panel commands and the diagnostics of both houses, a clean unload.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import Context, HomeAssistant, ServiceCall, callback
from homeassistant.helpers.event import async_call_later
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.advanced_climate.const import DOMAIN, SUBENTRY_ROOM
from custom_components.advanced_climate.diagnostics import async_get_config_entry_diagnostics
from custom_components.advanced_climate.websocket import HISTORY, WEEK, ws_history, ws_week

# The temperatures of the presets of the preset thermostats (their own, as a device has them).
PRESET_TEMPS = {"Comfort": 21.0, "Eco": 18.0, "Away": 15.0, "Boost": 30.0}


@dataclass
class Device:
    """A thermostat as it behaves."""

    entity_id: str
    step: float = 0.5
    low: float = 5.0  # its entity range
    high: float = 30.0
    device_max: float | None = None  # its own lower maximum (set on the device)
    late: float = 0.0  # seconds before it reports a command (battery TRVs)
    presets: list[str] | None = None
    received: list[tuple] = field(default_factory=list)


DEVICES = [
    # Home: the living room, two different TRVs, a change on one is for the whole room.
    Device("climate.living_left", step=0.5, late=90),
    Device("climate.living_right", step=0.1, device_max=25.0),
    # The kids' room, two TRVs, a change on one stays on it (the default).
    Device("climate.kids_a", step=0.5, late=40),
    Device("climate.kids_b", step=0.5),
    # The bedroom, two preset thermostats, whole room.
    Device("climate.bed_a", presets=list(PRESET_TEMPS), late=60),
    Device("climate.bed_b", presets=list(PRESET_TEMPS)),
    # The office, one TRV.
    Device("climate.office", step=0.5),
    # Cabin (another house, °F, whole-house scope): three TRVs in the lounge, one with a higher minimum.
    Device("climate.lounge_a", step=0.5, late=120),
    Device("climate.lounge_b", step=0.5, low=8.0),
    Device("climate.lounge_c", step=0.1),
    Device("climate.loft", step=0.5),
]
BY_ID = {d.entity_id: d for d in DEVICES}


def _attrs(d: Device, **values: object) -> dict:
    attrs = {
        "hvac_modes": ["heat", "off"],
        "min_temp": d.low,
        "max_temp": d.high,
        "target_temp_step": d.step,
        "current_temperature": 19.5,
        "temperature": 17.0,
        "hvac_action": "idle",
    }
    if d.presets:
        attrs.update(preset_modes=d.presets, preset_mode="Eco", temperature=PRESET_TEMPS["Eco"])
    attrs.update(values)
    return attrs


def _install(hass: HomeAssistant) -> None:
    """The thermostats and the services that change them."""
    for d in DEVICES:
        hass.states.async_set(d.entity_id, "heat", _attrs(d))

    pending: dict[str, tuple[str, dict]] = {}

    @callback
    def apply(call: ServiceCall) -> None:
        for entity_id in (
            [call.data["entity_id"]]
            if isinstance(call.data["entity_id"], str)
            else call.data["entity_id"]
        ):
            d = BY_ID[entity_id]
            d.received.append((call.service, dict(call.data), dt_util.utcnow()))
            state = hass.states.get(entity_id)
            # A battery TRV not yet reported keeps every command it got meanwhile.
            mode, attrs = pending.get(entity_id) or (state.state, dict(state.attributes))
            attrs = dict(attrs)
            if call.service == "set_temperature":
                value = round(round(float(call.data["temperature"]) / d.step) * d.step, 2)
                value = min(max(value, d.low), d.high)
                if d.device_max is not None:
                    value = min(value, d.device_max)
                attrs["temperature"] = value
            elif call.service == "set_preset_mode":
                attrs["preset_mode"] = call.data["preset_mode"]
                attrs["temperature"] = PRESET_TEMPS.get(
                    call.data["preset_mode"], attrs["temperature"]
                )
            elif call.service == "set_hvac_mode":
                mode = call.data["hvac_mode"]
            if d.late:
                # A battery TRV: it shows the values when it wakes up, with a context of its own.
                first = entity_id not in pending
                pending[entity_id] = (mode, attrs)

                @callback
                def report(_now, entity_id=entity_id) -> None:
                    mode, attrs = pending.pop(entity_id)
                    hass.states.async_set(entity_id, mode, attrs, context=Context())

                if first:
                    async_call_later(hass, d.late, report)
            else:
                hass.states.async_set(entity_id, mode, attrs, context=call.context)

    for service in ("set_temperature", "set_preset_mode", "set_hvac_mode"):
        hass.services.async_register("climate", service, apply)


def _by_hand(
    hass: HomeAssistant, entity_id: str, state: str | None = None, **values: object
) -> None:
    """A person changes a thermostat."""
    current = hass.states.get(entity_id)
    hass.states.async_set(
        entity_id, state or current.state, {**current.attributes, **values}, context=Context()
    )


def _room(data: dict, *climates: str, **extra: object) -> dict:
    return {**data, "climates": list(climates), **extra}


TRV_ROOM = {"source": "climate", "command_mode": "temperature"}
PRESET_ROOM = {
    "source": "climate",
    "command_mode": "preset",
    "preset_map": {"home": "Comfort", "eco": "Eco", "away": "Away"},
}


def _entry(title: str, options: dict, rooms: list[tuple[str, dict]]) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title=title,
        minor_version=2,
        options={"persons": ["person.andrei"], "nearby_zones": [], **options},
        subentries_data=[
            {"data": data, "subentry_type": SUBENTRY_ROOM, "title": name, "unique_id": None}
            for name, data in rooms
        ],
    )


HOME = (
    "Home",
    {"boiler_entity": "input_boolean.boiler", "outdoor_sensor": "sensor.outdoor"},
    [
        (
            "Living",
            _room(
                TRV_ROOM,
                "climate.living_left",
                "climate.living_right",
                device_change="room",
                window_sensors=["binary_sensor.living_window"],
            ),
        ),
        ("Kids", _room(TRV_ROOM, "climate.kids_a", "climate.kids_b")),
        ("Bedroom", _room(PRESET_ROOM, "climate.bed_a", "climate.bed_b", device_change="room")),
        ("Office", _room(TRV_ROOM, "climate.office")),
        (
            "Bath",
            {
                "source": "switch",
                "switches": ["input_boolean.bath_heater"],
                "temperature_sensors": ["sensor.bath_temperature"],
            },
        ),
    ],
)
CABIN = (
    "Cabin",
    {
        "boiler_entity": "input_boolean.cabin_boiler",
        "temperature_unit": "°F",
        "override_scope": "house",
        "override_mode": "until_next_reevaluation",
    },
    [
        (
            "Lounge",
            _room(
                TRV_ROOM,
                "climate.lounge_a",
                "climate.lounge_b",
                "climate.lounge_c",
                device_change="room",
            ),
        ),
        ("Loft", _room(TRV_ROOM, "climate.loft")),
    ],
)


async def _tick(hass: HomeAssistant, freezer: FrozenDateTimeFactory, seconds: float) -> None:
    await hass.async_block_till_done()
    freezer.tick(seconds)
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()


async def _steps(hass, freezer, n: int, seconds: float = 30) -> None:
    for _ in range(n):
        await _tick(hass, freezer, seconds)


def _room_of(entry: MockConfigEntry, name: str):
    return next(r for r in entry.runtime_data.rooms.values() if r.name == name)


def _temp(hass: HomeAssistant, entity_id: str) -> float:
    return float(hass.states.get(entity_id).attributes["temperature"])


def _within(d: Device, value: float) -> float:
    """What the device holds when it is asked for ``value`` (°C)."""
    held = min(max(round(round(value / d.step) * d.step, 2), d.low), d.high)
    return min(held, d.device_max) if d.device_max is not None else held


def _holds_decision(hass: HomeAssistant, room) -> list[str]:
    """The thermostats of a temperature room that do not hold its decision."""
    target = room.decision.target if room.decision else None
    if (
        room.command_mode != "temperature"
        or target is None
        or target.kind not in ("temperature", "preset")
    ):
        return []
    value = room._resolve_temperature(target)
    if value is None:
        return []
    wrong = []
    for entity_id in room.climates:
        d = BY_ID[entity_id]
        state = hass.states.get(entity_id)
        if state.state == "off":
            wrong.append(f"{entity_id} off, decision {value}")
            continue
        expected = _within(d, value)
        if abs(float(state.attributes["temperature"]) - expected) > d.step / 2 + 1e-6:
            wrong.append(f"{entity_id} holds {state.attributes['temperature']}, decision {value}")
    return wrong


async def test_two_houses_for_three_days(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, caplog
) -> None:
    await hass.config.async_set_time_zone("Europe/Bucharest")
    freezer.move_to("2026-10-12 04:00:00+00:00")  # Monday 07:00
    assert await async_setup_component(
        hass,
        "input_boolean",
        {"input_boolean": {b: {} for b in ("boiler", "cabin_boiler", "bath_heater")}},
    )
    hass.states.async_set("person.andrei", "home")
    hass.states.async_set("binary_sensor.living_window", "off", {"device_class": "window"})
    hass.states.async_set(
        "sensor.outdoor", "3.0", {"unit_of_measurement": "°C", "device_class": "temperature"}
    )
    hass.states.async_set(
        "sensor.bath_temperature",
        "21.0",
        {"unit_of_measurement": "°C", "device_class": "temperature"},
    )
    _install(hass)
    caplog.set_level(logging.DEBUG, logger="custom_components.advanced_climate")
    entries = []
    for title, options, rooms in (HOME, CABIN):
        entry = _entry(title, options, rooms)
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        entries.append(entry)
    home, cabin = entries
    await _steps(hass, freezer, 10)  # 5 minutes: every device got the decision and reported it

    living = _room_of(home, "Living")
    kids = _room_of(home, "Kids")
    bedroom = _room_of(home, "Bedroom")
    lounge = _room_of(cabin, "Lounge")
    loft = _room_of(cabin, "Loft")
    for entry in entries:
        for room in entry.runtime_data.rooms.values():
            assert not _holds_decision(hass, room), (room.name, _holds_decision(hass, room))

    # A temperature on the left TRV of the living room: the whole room, also the TRV with a
    # lower maximum of its own (25 °C on the device), within it.
    _by_hand(hass, "climate.living_left", temperature=26.0)
    await _steps(hass, freezer, 6)
    assert living.override["source_device"] == "climate.living_left"
    assert living.override["target"]["temperature"] == 25.0  # the maximum of the house
    assert _temp(hass, "climate.living_right") == 25.0
    assert hass.states.get("sensor.living_decision").state == "manual_override"
    # The left one (battery) reported late: no new change.
    assert living.override["source_device"] == "climate.living_left"
    assert _temp(hass, "climate.living_left") == 25.0

    # A temperature on one TRV of the kids' room: that one only.
    before = _temp(hass, "climate.kids_b")
    _by_hand(hass, "climate.kids_a", temperature=22.5)
    await _steps(hass, freezer, 6)
    assert kids.override["devices"].keys() == {"climate.kids_a"}
    assert _temp(hass, "climate.kids_b") == before
    assert _temp(hass, "climate.kids_a") == 22.5

    # A level preset on a preset thermostat: the level in the whole bedroom.
    _by_hand(hass, "climate.bed_b", preset_mode="Away", temperature=15.0)
    await _steps(hass, freezer, 6)
    dbg = "\n".join(
        f"{r.name.rsplit('.', 1)[-1]}: {r.getMessage()}"
        for r in caplog.records
        if r.name.startswith("custom_components") and ("Bedroom" in r.getMessage() or "bed_" in r.getMessage())
    )
    assert bedroom.override is not None, "DBGSTART\n" + dbg[-6000:] + "\nDBGEND"
    assert bedroom.override["target"] == {"kind": "preset", "preset": "away", "temperature": None}
    assert hass.states.get("climate.bed_a").attributes["preset_mode"] == "Away"
    # Boost on one: that one only; the other keeps Away.
    _by_hand(hass, "climate.bed_b", preset_mode="Boost", temperature=30.0)
    await _steps(hass, freezer, 6)
    assert bedroom.override.get("source_device") is None
    assert hass.states.get("climate.bed_a").attributes["preset_mode"] == "Away"
    assert hass.states.get("climate.bed_b").attributes["preset_mode"] == "Boost"

    # A window opens in the living room, someone sets 22 °C on the right TRV meanwhile:
    # it applies after the window.
    hass.states.async_set("binary_sensor.living_window", "on", {"device_class": "window"})
    await _steps(hass, freezer, 6)
    _by_hand(hass, "climate.living_right", temperature=22.0)
    await _steps(hass, freezer, 4)
    assert living.override["source_device"] == "climate.living_right"
    hass.states.async_set("binary_sensor.living_window", "off", {"device_class": "window"})
    await _steps(hass, freezer, 8)
    assert hass.states.get("sensor.living_decision").state == "manual_override", hass.states.get(
        "sensor.living_decision"
    ).attributes.get("reason")
    assert _temp(hass, "climate.living_left") == 22.0
    assert _temp(hass, "climate.living_right") == 22.0

    # The cabin (°F, whole-house scope): a change on one TRV of the lounge.
    _by_hand(hass, "climate.lounge_c", temperature=21.3)
    await _steps(hass, freezer, 8)
    assert lounge.override["source_device"] == "climate.lounge_c"
    assert _temp(hass, "climate.lounge_a") == 21.5  # its step is 0.5
    assert _temp(hass, "climate.lounge_b") == 21.5
    assert loft.override is not None  # the whole house has a manual change
    assert _temp(hass, "climate.loft") != 21.3  # but nothing is sent to the loft

    # The child lock in the lounge: a change is undone, on that TRV only.
    await lounge.async_set_child_lock(True)
    b_before = _temp(hass, "climate.lounge_b")
    _by_hand(hass, "climate.lounge_a", temperature=27.0)
    await _steps(hass, freezer, 8)
    assert lounge.override["source_device"] == "climate.lounge_c"
    assert _temp(hass, "climate.lounge_a") == 21.5
    assert _temp(hass, "climate.lounge_b") == b_before
    await lounge.async_set_child_lock(False)

    # The pause in the home: a change meanwhile is no manual change.
    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": "switch.home_pause"}, blocking=True
    )
    await _steps(hass, freezer, 4)
    _by_hand(hass, "climate.living_left", temperature=19.0)
    await _steps(hass, freezer, 4)
    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": "switch.home_pause"}, blocking=True
    )
    await _steps(hass, freezer, 10)
    assert living.override["source_device"] == "climate.living_right"
    assert _temp(hass, "climate.living_left") == 22.0

    # Off on one TRV of the whole room: that one only. Then a temperature on the other:
    # the whole room again, the first one on again.
    _by_hand(hass, "climate.living_left", "off")
    await _steps(hass, freezer, 6)
    assert living.override.get("source_device") is None
    assert _temp(hass, "climate.living_right") == 22.0
    caplog.set_level(logging.DEBUG, logger="custom_components.advanced_climate")
    mark = len(caplog.records)
    _by_hand(hass, "climate.living_right", temperature=20.5)
    await _steps(hass, freezer, 8)
    assert living.override["source_device"] == "climate.living_right", (
        living.override,
        hass.states.get("climate.living_right").attributes.get("temperature"),
        BY_ID["climate.living_right"].received[-3:],
        [r.getMessage() for r in caplog.records[mark:] if "Living" in r.getMessage()][:30],
    )
    caplog.set_level(logging.DEBUG, logger="custom_components.advanced_climate")
    assert hass.states.get("climate.living_left").state == "heat"
    assert _temp(hass, "climate.living_left") == 20.5

    # The services and the buttons; then everything back to automatic.
    await hass.services.async_call(
        DOMAIN,
        "set_override",
        {"room": "Living", "temperature": 19.0, "duration_hours": 1},
        blocking=True,
    )
    await _steps(hass, freezer, 6)
    assert living.override.get("source_device") is None
    assert (
        _temp(hass, "climate.living_left") == 19.0 and _temp(hass, "climate.living_right") == 19.0
    )
    await hass.services.async_call(DOMAIN, "clear_override", {}, blocking=True)
    await _steps(hass, freezer, 10)
    for entry in entries:
        for room in entry.runtime_data.rooms.values():
            assert room.override is None, room.name
            assert not _holds_decision(hass, room), (room.name, _holds_decision(hass, room))

    # Three days: people leave and come back, the outdoor temperature moves, a reload.
    for step in range(3 * 144):
        if step % 144 == 8:
            hass.states.async_set("person.andrei", "not_home")
        if step % 144 == 60:
            hass.states.async_set("person.andrei", "home")
        if step % 144 == 70:  # in the evening someone changes the living room
            _by_hand(hass, "climate.living_left", temperature=22.5)
        if step == 150:
            assert await hass.config_entries.async_reload(home.entry_id)
            await hass.async_block_till_done()
            living = _room_of(home, "Living")
        hass.states.async_set(
            "sensor.outdoor",
            str(round(3.0 - 4 * ((step % 144) / 144), 1)),
            {"unit_of_measurement": "°C", "device_class": "temperature"},
        )
        # Ten minutes; the last 150 s let the battery TRVs report (they take up to 120 s).
        await _tick(hass, freezer, 450)
        targets = {
            room.id: room.decision.target if room.decision else None
            for e in entries
            for room in e.runtime_data.rooms.values()
        }
        await _tick(hass, freezer, 150)
        for entry in entries:
            for room in entry.runtime_data.rooms.values():
                if (
                    room.override is None
                    and not room.window_open
                    and room.decision
                    and targets[room.id] == room.decision.target
                ):
                    assert not _holds_decision(hass, room), (
                        step,
                        room.name,
                        room.decision.rule,
                        _holds_decision(hass, room),
                    )

    errors = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert not errors, [r.getMessage() for r in errors]
    for entry in entries:
        alerts = entry.runtime_data.active_alerts
        assert not [a for a in alerts if a.startswith("commands_")], alerts
        for room in entry.runtime_data.rooms.values():
            decision = hass.states.get(f"sensor.{room.name.lower()}_decision")
            assert decision.state not in ("unknown", "unavailable"), room.name
    sent: dict = {}

    class Connection:
        def send_result(self, msg_id: int, result: dict) -> None:
            sent[msg_id] = result

    ws_week(hass, Connection(), {"id": 1, "type": WEEK})
    ws_history(hass, Connection(), {"id": 2, "type": HISTORY})
    assert [h["name"] for h in sent[1]["houses"]] == ["Home", "Cabin"]
    assert [len(h["rooms"]) for h in sent[2]["houses"]] == [5, 2]
    for entry in entries:
        json.dumps(await async_get_config_entry_diagnostics(hass, entry), default=str)
    for entry in entries:
        assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
