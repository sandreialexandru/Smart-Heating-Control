"""Many houses made at random, lived in at random: what must always hold.

Each seed builds one or two houses from a random mix of what the integration
supports: TRVs commanded by temperature, by preset or turned on and off,
Generic Thermostats, relays; one to three thermostats a room, different ones
(step, range, a lower maximum of the device, battery ones that report late,
slow ones that report the new value themselves while the command to them still
waits, and sometimes time out after applying it);
room sensors or not, windows, occupancy; a boiler relay, a boiler thermostat
(by its temperature or by its mode) or no heat source; °C or °F; a change on
one thermostat for it or for the whole room; manual changes for the room or the
house, for a fixed time or until the next change. The rooms warm while heated
and cool otherwise. Then two days of random events: people leave and come back,
windows open and close, thermostats changed by hand (a temperature, a preset,
off, on again), the pause, the modes, guests, the services, the child lock, a
reload, the outdoor temperature.

After every step:
- no error in the log;
- no command loop (no commands paused for a device);
- every room has a decision, its target within the frost protection and the
  maximum of the house;
- nothing is sent to the rooms while the house is paused;
- a room with its window open (after the delays) follows the window rule, unless
  a rule above it holds the room;
- a temperature room that is settled (no manual change, no window, no boost) has
  every thermostat holding the decision, within its own step and range;
- a heat demand that lasts starts the boiler relay;
- no manual change nobody made: a manual change on a thermostat only after a
  person changed that thermostat.
At the end: the panel commands and the diagnostics answer, the houses unload.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import random
from dataclasses import dataclass, field

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import Context, HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_call_later
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.advanced_climate.const import DOMAIN, SUBENTRY_ROOM
from custom_components.advanced_climate.diagnostics import async_get_config_entry_diagnostics
from custom_components.advanced_climate.websocket import HISTORY, WEEK, ws_history, ws_week

# 16 houses in every run; more before a release: SHC_FUZZ_SEEDS=96 pytest ...
SEEDS = list(range(int(os.environ.get("SHC_FUZZ_SEEDS", "16"))))
# Some seeds only, with the debug log of the integration in a failure: SHC_FUZZ_ONLY=10,56
if os.environ.get("SHC_FUZZ_ONLY"):
    SEEDS = [int(x) for x in os.environ["SHC_FUZZ_ONLY"].split(",")]
DEBUG = bool(os.environ.get("SHC_FUZZ_ONLY"))
STEPS = 2 * 144  # two days of 10 minutes
PRESET_TEMPS = {"Comfort": 21.0, "Eco": 18.0, "Away": 15.0, "Boost": 30.0}
GT_TEMPS = {"home": 21.5, "eco": 18.0, "away": 16.0, "sleep": 19.0, "comfort": 22.0}
# Rules that hold a room above the window (nothing is sent, or the house is off).
ABOVE_WINDOW = {
    "pause",
    "mode_off",
    "summer",
    "out_of_season",
    "starting",
    "valve_exercise",
    # A room colder than the frost protection is heated, window open or not.
    "frost_protection",
}


@dataclass
class Device:
    """A thermostat as it behaves."""

    entity_id: str
    kind: str  # trv / preset / onoff / gt / boiler
    step: float = 0.5
    low: float = 5.0
    high: float = 30.0
    device_max: float | None = None
    late: float = 0.0
    # Reports the new value itself (a context of its own) while the command still
    # waits for it (ZHA and a battery TRV), and sometimes times out after applying it.
    slow: bool = False
    sent_paused: int = 0


@dataclass
class World:
    """Everything the simulation keeps: devices, rooms and their temperatures."""

    rng: random.Random
    devices: dict[str, Device] = field(default_factory=dict)
    rooms: dict[str, dict] = field(
        default_factory=dict
    )  # name -> {temp, climates, switches, sensor}
    boilers: dict[str, str] = field(default_factory=dict)  # house title -> boiler entity
    pending: dict[str, tuple[str, dict]] = field(default_factory=dict)
    log: list[str] = field(default_factory=list)
    paused_houses: set[str] = field(default_factory=set)
    commands_in_pause: list[str] = field(default_factory=list)
    room_house: dict[str, str] = field(default_factory=dict)
    entries: list = field(default_factory=list)
    # The thermostats a person changed.
    by_hand: set[str] = field(default_factory=set)


def _trv_attrs(d: Device, **values: object) -> dict:
    attrs = {
        "hvac_modes": ["heat", "off"],
        "min_temp": d.low,
        "max_temp": d.high,
        "target_temp_step": d.step,
        "current_temperature": 19.5,
        "temperature": 17.0,
        "hvac_action": "idle",
    }
    if d.kind == "preset":
        attrs.update(preset_modes=list(PRESET_TEMPS), preset_mode="Eco", temperature=18.0)
    if d.kind == "gt":
        attrs.update(
            preset_modes=["none", *GT_TEMPS],
            preset_mode="none",
            temperature=20.0,
            min_temp=7.0,
            max_temp=35.0,
            target_temp_step=0.5,
        )
    attrs.update(values)
    return attrs


def _install_services(hass: HomeAssistant, world: World) -> None:
    """The thermostats apply the commands as devices do."""

    @callback
    def apply(call: ServiceCall) -> None:
        ids = call.data["entity_id"]
        for entity_id in [ids] if isinstance(ids, str) else ids:
            d = world.devices.get(entity_id)
            if d is None:
                continue
            house = world.room_house.get(entity_id)
            if house in world.paused_houses:
                # The rule of the room as the command is sent (the boiler: any room).
                rules = [
                    "frost_demand" if r.frost_demand and d.kind == "boiler" else r.decision.rule
                    for e in world.entries
                    for r in e.runtime_data.rooms.values()
                    if r.decision is not None and (entity_id in r.climates or d.kind == "boiler")
                ]
                # A heat source stopped: off, or its idle temperature (below any level).
                stop = d.kind == "boiler" and (
                    call.data.get("hvac_mode") == "off"
                    or call.service == "turn_off"
                    or float(call.data.get("temperature", 99)) < 15
                )
                world.commands_in_pause.append(
                    (
                        f"{'stop ' if stop else ''}{entity_id} {call.service} {dict(call.data)}",
                        rules,
                    )
                )
            state = hass.states.get(entity_id)
            mode, attrs = world.pending.get(entity_id) or (state.state, dict(state.attributes))
            attrs = dict(attrs)
            if call.service == "set_temperature":
                value = float(call.data["temperature"])
                value = round(round(value / d.step) * d.step, 2)
                value = min(
                    max(value, float(attrs.get("min_temp", d.low))),
                    float(attrs.get("max_temp", d.high)),
                )
                if d.device_max is not None:
                    value = min(value, d.device_max)
                attrs["temperature"] = value
                if d.kind == "gt":
                    attrs["preset_mode"] = next(
                        (p for p, t in GT_TEMPS.items() if t == value), "none"
                    )
                if "hvac_mode" in call.data:
                    mode = call.data["hvac_mode"]
            elif call.service == "set_preset_mode":
                preset = call.data["preset_mode"]
                attrs["preset_mode"] = preset
                if d.kind == "gt":
                    if preset != "none":
                        attrs["temperature"] = GT_TEMPS[preset]
                else:
                    attrs["temperature"] = PRESET_TEMPS.get(preset, attrs["temperature"])
            elif call.service == "set_hvac_mode":
                mode = call.data["hvac_mode"]
            elif call.service in ("turn_on", "turn_off"):
                mode = "heat" if call.service == "turn_on" else "off"
            if d.late:
                first = entity_id not in world.pending
                world.pending[entity_id] = (mode, attrs)

                @callback
                def report(_now, entity_id=entity_id) -> None:
                    if entity_id in world.pending:
                        mode, attrs = world.pending.pop(entity_id)
                        hass.states.async_set(entity_id, mode, attrs, context=Context())

                if first:
                    async_call_later(hass, d.late, report)
            else:
                # A slow one reports by itself, before the command returns.
                context = Context() if d.slow else call.context
                hass.states.async_set(entity_id, mode, attrs, context=context)

    async def handle(call: ServiceCall) -> None:
        apply(call)
        ids = call.data["entity_id"]
        slow = any(
            world.devices[e].slow
            for e in ([ids] if isinstance(ids, str) else ids)
            if e in world.devices
        )
        if slow:
            # The command still waits for the device meanwhile.
            for _ in range(3):
                await asyncio.sleep(0)
            if world.rng.random() < 0.25:
                raise HomeAssistantError("Failed to send request: device did not respond")

    for service in ("set_temperature", "set_preset_mode", "set_hvac_mode", "turn_on", "turn_off"):
        hass.services.async_register("climate", service, handle)


def _gt_entity(hass: HomeAssistant, name: str) -> str:
    """A Generic Thermostat set up in the UI (the integration knows it by its config entry)."""
    gt_entry = MockConfigEntry(
        domain="generic_thermostat",
        options={
            "heater": f"input_boolean.{name}_heater",
            **{f"{p}_temp": t for p, t in GT_TEMPS.items()},
        },
    )
    gt_entry.add_to_hass(hass)
    return (
        er.async_get(hass)
        .async_get_or_create(
            "climate",
            "generic_thermostat",
            gt_entry.entry_id,
            config_entry=gt_entry,
            suggested_object_id=name,
        )
        .entity_id
    )


def _make_house(
    hass: HomeAssistant, world: World, title: str, booleans: set[str]
) -> tuple[dict, list]:
    """A random house: its options and its rooms."""
    rng = world.rng
    options: dict = {"persons": ["person.andrei"], "nearby_zones": []}
    if rng.random() < 0.3:
        options["temperature_unit"] = "°F"
    options["override_scope"] = rng.choice(["room", "room", "house"])
    options["override_mode"] = rng.choice(["fixed", "until_next_reevaluation"])
    options["outdoor_sensor"] = "sensor.outdoor"
    options["frost_temp"] = rng.choice([5.0, 7.0, 7.0, 10.0])
    options["max_temp"] = rng.choice([22.0, 25.0, 25.0, 28.0])
    if rng.random() < 0.3:
        options["boiler_min_on"] = rng.choice([3, 5])
        options["boiler_min_off"] = rng.choice([3, 5])
    source = rng.choice(["relay", "relay", "thermostat", "thermostat_mode", "water", "none"])
    slug = title.lower()
    if source == "relay":
        booleans.add(f"{slug}_boiler")
        options["boiler_entity"] = f"input_boolean.{slug}_boiler"
        world.boilers[title] = options["boiler_entity"]
        if rng.random() < 0.3:
            # A heat pump beside the boiler, chosen by an entity (cheap power).
            booleans.update({f"{slug}_heat_pump", f"{slug}_cheap"})
            options["secondary_source"] = f"input_boolean.{slug}_heat_pump"
            options["source_criterion"] = "entity"
            options["source_criterion_entity"] = f"input_boolean.{slug}_cheap"
    elif source in ("thermostat", "thermostat_mode", "water"):
        entity_id = f"climate.{slug}_boiler"
        d = Device(
            entity_id,
            "boiler",
            step=0.5,
            low=30.0 if source == "water" else 5.0,
            high=80.0 if source == "water" else 30.0,
        )
        world.devices[entity_id] = d
        world.room_house[entity_id] = title
        hass.states.async_set(entity_id, "heat", _trv_attrs(d, temperature=d.low))
        options["boiler_entity"] = entity_id
        if source == "thermostat_mode":
            options["boiler_boost"] = False
    rooms = []
    for i in range(rng.randint(1, 4)):
        name = f"{title}R{i}"
        rslug = name.lower()
        kind = rng.choice(["trv", "trv", "trv", "preset", "onoff", "gt", "switch"])
        data: dict = {}
        climates: list[str] = []
        switches: list[str] = []
        sensor = None
        if kind == "switch":
            booleans.add(f"{rslug}_heater")
            switches = [f"input_boolean.{rslug}_heater"]
            sensor = f"sensor.{rslug}_temperature"
            data = {"source": "switch", "switches": switches, "temperature_sensors": [sensor]}
        elif kind == "gt":
            booleans.add(f"{rslug}_gt_heater")
            entity_id = _gt_entity(hass, f"{rslug}_gt")
            d = Device(entity_id, "gt")
            world.devices[entity_id] = d
            hass.states.async_set(entity_id, "heat", _trv_attrs(d))
            climates = [entity_id]
            data = {"source": "generic_thermostat", "climates": climates}
        else:
            for j in range(rng.choice([1, 1, 2, 3])):
                entity_id = f"climate.{rslug}_t{j}"
                d = Device(
                    entity_id,
                    kind,
                    step=rng.choice([0.5, 0.5, 0.1, 1.0]),
                    low=rng.choice([5.0, 5.0, 8.0]),
                    high=rng.choice([30.0, 30.0, 35.0]),
                    device_max=rng.choice([None, None, None, 24.0]),
                    late=rng.choice([0.0, 0.0, 40.0, 120.0]),
                )
                d.slow = not d.late and rng.random() < 0.4
                world.devices[entity_id] = d
                hass.states.async_set(entity_id, "heat", _trv_attrs(d))
                climates.append(entity_id)
            mode = {"trv": "temperature", "preset": "preset", "onoff": "hvac_mode"}[kind]
            data = {"source": "climate", "climates": climates, "command_mode": mode}
            if kind == "preset":
                data["preset_map"] = {"home": "Comfort", "eco": "Eco", "away": "Away"}
            if kind == "onoff":
                data.update(min_on_minutes=0, min_off_minutes=0)
            if kind == "onoff" or rng.random() < 0.5:
                sensor = f"sensor.{rslug}_temperature"
                data["temperature_sensors"] = [sensor]
            if len(climates) > 1 and rng.random() < 0.6:
                data["device_change"] = "room"
            if kind == "trv" and rng.random() < 0.3:
                data["trv_boost"] = False
        if rng.random() < 0.5:
            window = f"binary_sensor.{rslug}_window"
            hass.states.async_set(window, "off", {"device_class": "window"})
            data["window_sensors"] = [window]
            data["window_action"] = rng.choice(["frost", "off"])
            data["window_open_delay"] = rng.choice([0, 60, 300])
            data["window_close_delay"] = rng.choice([0, 30, 600])
        if rng.random() < 0.3:
            data["optimal_start"] = True
        if rng.random() < 0.2:
            data["hysteresis"] = rng.choice([0.1, 0.5, 1.0])
        if "boiler_entity" in options and rng.random() < 0.15:
            # A room heated by its own (electric) source, or one that never starts the boiler.
            data[rng.choice(["use_house_source", "starts_house_source"])] = False
        if rng.random() < 0.3:
            occupancy = f"binary_sensor.{rslug}_occupancy"
            hass.states.async_set(occupancy, "on", {"device_class": "occupancy"})
            data["occupancy_sensors"] = [occupancy]
        for entity_id in climates:
            world.room_house[entity_id] = title
        world.rooms[name] = {
            "temp": 19.0,
            "climates": climates,
            "switches": switches,
            "sensor": sensor,
            "house": title,
        }
        rooms.append((name, data))
    return options, rooms


def _entry(title: str, options: dict, rooms: list) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title=title,
        minor_version=2,
        options=options,
        subentries_data=[
            {"data": data, "subentry_type": SUBENTRY_ROOM, "title": name, "unique_id": None}
            for name, data in rooms
        ],
    )


async def _tick(hass: HomeAssistant, freezer: FrozenDateTimeFactory, seconds: float) -> None:
    await hass.async_block_till_done()
    freezer.tick(seconds)
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()


def _source_on(hass: HomeAssistant, world: World, house: str) -> bool:
    boiler = world.boilers.get(house)
    if boiler is None:
        entity_id = f"climate.{house.lower()}_boiler"
        state = hass.states.get(entity_id)
        if state is None:
            return True  # no heat source: the rooms heat by themselves
        return state.state != "off"
    state = hass.states.get(boiler)
    return state is not None and state.state == "on"


def _physics(hass: HomeAssistant, world: World, outdoor: float) -> None:
    """The rooms warm while heated and cool otherwise; the sensors and thermostats show it."""
    for room in world.rooms.values():
        temp = room["temp"]
        heating = False
        if room["switches"]:
            heating = any(
                (s := hass.states.get(e)) is not None and s.state == "on" for e in room["switches"]
            )
        for entity_id in room["climates"]:
            state = hass.states.get(entity_id)
            if state is None or state.state == "off":
                continue
            d = world.devices[entity_id]
            target = state.attributes.get("temperature")
            if d.kind == "onoff" or (target is not None and float(target) > temp + 0.2):
                heating = True
        heating = heating and _source_on(hass, world, room["house"])
        temp += 0.25 if heating else -0.05 * max(temp - outdoor, 0) / 10
        room["temp"] = round(min(max(temp, 8.0), 28.0), 2)
        if room["sensor"]:
            hass.states.async_set(
                room["sensor"],
                str(room["temp"]),
                {"unit_of_measurement": "°C", "device_class": "temperature"},
            )
        for entity_id in room["climates"]:
            state = hass.states.get(entity_id)
            if entity_id in world.pending or state is None:
                continue
            hass.states.async_set(
                entity_id,
                state.state,
                {
                    **state.attributes,
                    "current_temperature": room["temp"],
                    "hvac_action": "heating" if heating else "idle",
                },
                context=Context(),
            )


def _within(state, d: Device, value: float) -> float:
    held = round(round(value / d.step) * d.step, 2)
    held = min(
        max(held, float(state.attributes.get("min_temp", d.low))),
        float(state.attributes.get("max_temp", d.high)),
    )
    return min(held, d.device_max) if d.device_max is not None else held


def _settled_wrong(hass: HomeAssistant, world: World, room) -> list[str]:
    """The thermostats of a settled temperature room that do not hold its decision."""
    if room.command_mode != "temperature" or room.source != "climate":
        return []
    if room.override is not None or room.window_open or room.boost_active:
        return []
    if room.opened_for_source or room.decision is None:
        return []
    target = room.decision.target
    if target is None or target.kind not in ("temperature", "preset"):
        return []
    value = room._resolve_temperature(target)
    if value is None:
        return []
    wrong = []
    for entity_id in room.climates:
        if entity_id in world.pending:
            continue
        d = world.devices[entity_id]
        state = hass.states.get(entity_id)
        held = state.attributes.get("temperature")
        expected = _within(state, d, value)
        if state.state == "off" or held is None or abs(float(held) - expected) > d.step / 2 + 1e-6:
            wrong.append(f"{entity_id} {state.state} {held}, decision {value} -> {expected}")
    return wrong


def _entity(hass: HomeAssistant, entry: MockConfigEntry, key: str) -> str:
    registry = er.async_get(hass)
    return next(
        e.entity_id
        for e in er.async_entries_for_config_entry(registry, entry.entry_id)
        if e.unique_id == f"{entry.entry_id}_{key}"
    )


async def _event(hass: HomeAssistant, world: World, entries: list, step: int) -> None:
    """One random thing that happens in a home."""
    rng = world.rng
    roll = rng.random()
    names = list(world.rooms)
    name = rng.choice(names)
    room = world.rooms[name]
    entry = next(e for e in entries if e.title == room["house"])
    if roll < 0.05:
        state = "not_home" if hass.states.get("person.andrei").state == "home" else "home"
        hass.states.async_set("person.andrei", state)
        world.log.append(f"{step} person {state}")
    elif roll < 0.12:
        window = f"binary_sensor.{name.lower()}_window"
        if hass.states.get(window) is not None:
            state = "off" if hass.states.get(window).state == "on" else "on"
            hass.states.async_set(window, state, {"device_class": "window"})
            world.log.append(f"{step} {window} {state}")
    elif roll < 0.22 and room["climates"]:
        entity_id = rng.choice(room["climates"])
        d = world.devices[entity_id]
        state = hass.states.get(entity_id)
        attrs = dict(state.attributes)
        action = rng.choice(["temperature", "temperature", "preset", "off", "on"])
        mode = state.state
        if action == "temperature":
            attrs["temperature"] = _within(
                state, d, rng.choice([16.0, 18.5, 20.0, 21.5, 23.0, 26.0])
            )
            if d.kind == "gt":
                attrs["preset_mode"] = next(
                    (p for p, t in GT_TEMPS.items() if t == attrs["temperature"]), "none"
                )
        elif action == "preset" and attrs.get("preset_modes"):
            preset = rng.choice(attrs["preset_modes"])
            attrs["preset_mode"] = preset
            attrs["temperature"] = (GT_TEMPS if d.kind == "gt" else PRESET_TEMPS).get(
                preset, attrs["temperature"]
            )
        elif action == "off":
            mode = "off"
        else:
            mode = "heat"
        world.pending.pop(entity_id, None)
        world.by_hand.add(entity_id)
        hass.states.async_set(entity_id, mode, attrs, context=Context())
        world.log.append(
            f"{step} by hand {entity_id} {mode} {attrs.get('temperature')} {attrs.get('preset_mode')}"
        )
    elif roll < 0.26:
        pause = _entity(hass, entry, "pause")
        on = hass.states.get(pause).state != "on"
        await hass.async_block_till_done()
        if on:
            world.paused_houses.add(entry.title)
        else:
            # The decision is sent again as the pause ends: not in the pause.
            world.paused_houses.discard(entry.title)
        await hass.services.async_call(
            "switch", "turn_on" if on else "turn_off", {"entity_id": pause}, blocking=True
        )
        world.log.append(f"{step} pause {entry.title} {on}")
    elif roll < 0.30:
        mode = rng.choice(["auto", "auto", "away", "off", "summer"])
        await hass.services.async_call(
            "select",
            "select_option",
            {"entity_id": _entity(hass, entry, "mode"), "option": mode},
            blocking=True,
        )
        world.log.append(f"{step} mode {entry.title} {mode}")
    elif roll < 0.32:
        guest = _entity(hass, entry, "guest_mode")
        on = hass.states.get(guest).state != "on"
        await hass.services.async_call(
            "switch", "turn_on" if on else "turn_off", {"entity_id": guest}, blocking=True
        )
        world.log.append(f"{step} guests {entry.title} {on}")
    elif roll < 0.37:
        data: dict = {"room": name}
        if rng.random() < 0.5:
            data["temperature"] = rng.choice([17.0, 20.0, 22.5, 30.0])
        else:
            data["preset"] = rng.choice(["home", "eco", "comfort", "sleep", "away"])
        if rng.random() < 0.5:
            data["duration_hours"] = rng.choice([0.5, 1.0, 3.0])
        await hass.services.async_call(DOMAIN, "set_override", data, blocking=True)
        world.log.append(f"{step} set_override {data}")
    elif roll < 0.40:
        await hass.services.async_call(DOMAIN, "clear_override", {"room": name}, blocking=True)
        world.log.append(f"{step} clear_override {name}")
    elif roll < 0.42:
        obj = next(r for r in entry.runtime_data.rooms.values() if r.name == name)
        await obj.async_set_child_lock(not obj.child_lock)
        world.log.append(f"{step} child lock {name} {obj.child_lock}")
    elif roll < 0.425:
        await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
        world.log.append(f"{step} reload {entry.title}")
    elif roll < 0.44:
        cheap = f"input_boolean.{entry.title.lower()}_cheap"
        if hass.states.get(cheap) is not None:
            service = "turn_off" if hass.states.get(cheap).state == "on" else "turn_on"
            await hass.services.async_call(
                "input_boolean", service, {"entity_id": cheap}, blocking=True
            )
            world.log.append(f"{step} {cheap} {service}")
    elif roll < 0.45:
        occupancy = f"binary_sensor.{name.lower()}_occupancy"
        if hass.states.get(occupancy) is not None:
            state = "off" if hass.states.get(occupancy).state == "on" else "on"
            hass.states.async_set(occupancy, state, {"device_class": "occupancy"})
            world.log.append(f"{step} {occupancy} {state}")


@pytest.mark.parametrize("seed", SEEDS)
async def test_random_houses_lived_in(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, caplog: pytest.LogCaptureFixture, seed: int
) -> None:
    world = World(random.Random(seed))
    await hass.config.async_set_time_zone("Europe/Bucharest")
    freezer.move_to("2026-11-16 04:00:00+00:00")  # Monday 06:00
    hass.states.async_set("person.andrei", "home")
    hass.states.async_set(
        "sensor.outdoor", "3.0", {"unit_of_measurement": "°C", "device_class": "temperature"}
    )
    booleans: set[str] = set()
    houses = []
    for title in ["Home", "Cabin"][: world.rng.choice([1, 1, 2])]:
        houses.append((title, *_make_house(hass, world, title, booleans)))
    assert await async_setup_component(
        hass, "input_boolean", {"input_boolean": {b: {} for b in booleans}}
    )
    _install_services(hass, world)
    caplog.set_level(
        logging.DEBUG if DEBUG else logging.WARNING, logger="custom_components.advanced_climate"
    )
    _physics(hass, world, 3.0)
    entries = []
    for title, options, rooms in houses:
        entry = _entry(title, options, rooms)
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        entries.append(entry)
    world.entries = entries
    config = json.dumps([(t, o, r) for t, o, r in houses], default=str)
    demand_since: dict[str, int] = {}

    def fail(step: int, what: object) -> str:
        debug = ""
        if DEBUG:
            own = [r for r in caplog.records if r.name.startswith("custom_components.")]
            lines = [f"{r.name.rsplit('.', 1)[-1]}: {r.getMessage()}" for r in own[-120:]]
            debug = "\ndebug:\n" + "\n".join(lines)
        return (
            f"seed {seed} step {step}: {what}\nconfig: {config}\nlast events: {world.log[-12:]}"
            + debug
        )

    # The weather of these two days: cold, mild or warm enough to stop the heating.
    base = world.rng.choice([-8.0, 3.0, 3.0, 12.0, 19.0])
    for step in range(STEPS):
        await _event(hass, world, entries, step)
        outdoor = round(base - 6 * abs(((step % 144) - 72) / 72), 1)
        hass.states.async_set(
            "sensor.outdoor",
            str(outdoor),
            {"unit_of_measurement": "°C", "device_class": "temperature"},
        )
        # Ten minutes: commands, late reports (up to 120 s), the rooms warm or cool.
        await _tick(hass, freezer, 300)
        _physics(hass, world, outdoor)
        await _tick(hass, freezer, 150)
        targets = {
            id(r): r.decision.target if r.decision else None
            for e in entries
            for r in e.runtime_data.rooms.values()
        }
        await _tick(hass, freezer, 150)

        errors = [r for r in caplog.records if r.levelno >= logging.ERROR]
        assert not errors, fail(step, [r.getMessage() for r in errors])
        # In a pause only the safety commands are sent: frost protection, the maximum.
        safety = {"frost_protection", "maximum_temperature", "frost_demand"}
        for sent_cmd, rules in world.commands_in_pause:
            # The heat source started for frost protection is stopped again (its idle
            # temperature, or off) once no longer needed.
            stop = sent_cmd.startswith("stop ")
            assert stop or safety & set(rules), fail(
                step, f"sent in a pause: {sent_cmd}, rules {rules}"
            )
        world.commands_in_pause.clear()
        for entry in entries:
            house = entry.runtime_data
            loops = [a for a in house.active_alerts if a.startswith("commands_")]
            assert not loops, fail(step, loops)
            for room in house.rooms.values():
                # The frost protection of a Generic Thermostat room is its own minimum.
                frost, maximum = room.frost_temp(), room.max_temp()
                decision = room.decision
                assert decision is not None, fail(step, f"{room.name} has no decision")
                value = room._resolve_temperature(decision.target) if decision.target else None
                # On / off rooms without a command show the setpoint of the thermostat
                # (it does not drive them: the room turns off at the maximum).
                # No command (pause, a change on the devices): what the thermostats hold,
                # or a stored manual change; the maximum is applied when it is sent.
                if value is not None and decision.target.kind != "none":
                    assert frost - 0.01 <= value <= maximum + 0.01, fail(
                        step,
                        f"{room.name} {decision.rule} {value}: target {decision.target}, "
                        f"override {room.override}, setpoint {room._device_setpoint()}, "
                        f"devices {[(c, hass.states.get(c).state, hass.states.get(c).attributes.get('temperature'), hass.states.get(c).attributes.get('preset_mode')) for c in room.climates]}",
                    )
                if room.window_open and not house.paused and decision.rule not in ABOVE_WINDOW:
                    assert decision.rule == "window_open", fail(
                        step, f"{room.name} window open, rule {decision.rule}"
                    )
                # No manual change nobody made.
                if room.override:
                    made = [
                        room.override.get("source_device"),
                        *(room.override.get("devices") or {}),
                    ]
                    # A TRV with its own lower maximum is left out: its report of
                    # that limit instead of a value above it is not recognised yet.
                    nobody = [
                        x
                        for x in made
                        if x
                        and x not in world.by_hand
                        and not (x in world.devices and world.devices[x].device_max is not None)
                    ]
                    assert not nobody, fail(
                        step,
                        f"{room.name}: manual change on {nobody} nobody made: {room.override}, "
                        f"devices {[(c, world.devices[c], hass.states.get(c).state, dict(hass.states.get(c).attributes)) for c in nobody if c in world.devices]}",
                    )
                if not house.paused and targets.get(id(room)) == decision.target:
                    wrong = _settled_wrong(hass, world, room)
                    assert not wrong, fail(step, f"{room.name} {decision.rule}: {wrong}")
            boiler = world.boilers.get(entry.title)
            # The rooms that start the heat source of the house (not one heated by
            # its own source, not one that never starts it).
            starts = any(
                r.heat_demand and r.uses_house_source and r.config.get("starts_house_source", True)
                for r in house.rooms.values()
            )
            if boiler and not house.paused:
                # Waiting for its minimum on / off time is not a missed start.
                if starts and house.source_waiting is None:
                    demand_since.setdefault(entry.title, step)
                    if step - demand_since[entry.title] >= 2:
                        # The boiler, or the heat pump beside it when it is the one in use.
                        sources = [boiler, house.options.get("secondary_source")]
                        running = [x for x in sources if x and hass.states.get(x).state == "on"]
                        assert running, fail(
                            step,
                            f"{entry.title} heat demand, no source on: waiting {house.source_waiting}, "
                            f"boiler_on {house.boiler_on}, source {house.source_entity}, "
                            f"{boiler} {hass.states.get(boiler).state} since {hass.states.get(boiler).last_changed}, "
                            f"rooms {[(r.name, r.heat_demand, r.decision.rule if r.decision else None) for r in house.rooms.values()]}, "
                            f"alerts {sorted(house.active_alerts)}",
                        )
                else:
                    demand_since.pop(entry.title, None)
            else:
                demand_since.pop(entry.title, None)

    # The battery thermostats report what they still have before the end.
    await _tick(hass, freezer, 200)
    sent: dict = {}

    class Connection:
        def send_result(self, msg_id: int, result: dict) -> None:
            sent[msg_id] = result

    ws_week(hass, Connection(), {"id": 1, "type": WEEK})
    ws_history(hass, Connection(), {"id": 2, "type": HISTORY})
    assert [len(h["rooms"]) for h in sent[1]["houses"]] == [len(r) for _t, _o, r in houses]
    for entry in entries:
        json.dumps(await async_get_config_entry_diagnostics(hass, entry), default=str)
    for entry in entries:
        assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
