"""Days in the life of a house, with the kinds of devices found in Zigbee2MQTT
and through clouds: no device may get more commands than a normal day needs.

Each problem of this kind found so far was a loop: a TRV switched between auto
and heat every second (#15), a heat pump sent a temperature below its minimum
again and again (#14), a top up started and stopped every few minutes, a heat
source refused a temperature outside its range, a thermostat left on away
after a vacation. Each has its own test; these catch a loop wherever a later
change would make one, by counting the commands of whole days.

The rooms warm while their valve is open (and the boiler runs, and their
circuit is open) and cool towards the outside; the sensors report tenths of a
degree; the devices answer as the kinds they stand for (some late, some going
back to their own schedule, some refusing a temperature on their preset).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.const import EVENT_CALL_SERVICE
from homeassistant.core import Context, Event, HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util

from tests.ha.test_ha_devices import _house, _tick, _unload

OUTDOOR = 5.0
HEAT_PER_HOUR = 1.5  # °C per hour with the valve open
LOSS_PER_HOUR = 0.05  # of the difference to the outside, per hour
STEP = 60  # seconds per step of the simulation

# A normal day: a few level changes, a few heating cycles. A loop is far above.
MAX_PER_HOUR = 6
MAX_PER_DAY = 40


@dataclass
class Trv:
    """A thermostat or TRV, answering as one kind of device does."""

    entity_id: str
    room: str
    state: str = "heat"
    target: float = 20.0
    modes: list[str] = field(default_factory=lambda: ["heat", "off"])
    presets: list[str] | None = None
    preset: str | None = None
    min_temp: float = 5.0
    max_temp: float = 30.0
    step: float | None = 0.5
    # Behaviour of the kind.
    reverts_to_auto_after: float | None = None  # seconds after heat (TRV602Z: 1)
    heat_on_temperature_for: float | None = None  # Netatmo: heat for N s, then auto
    schedule_target: float = 19.0  # what its own schedule holds
    refuses_on: tuple[str, ...] = ()  # presets on which it keeps its temperature
    preset_temps: dict[str, float] = field(default_factory=dict)
    report_delay: float = 0.0  # a cloud device reports late
    # Its own regulation: opens below target - band, closes above target + band.
    band: float = 0.2
    valve_open: bool = False


class House:
    """The simulated house: temperatures, devices, and every command counted."""

    def __init__(self, hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
        self.hass = hass
        self.freezer = freezer
        self.temps: dict[str, float] = {}
        self.loss: dict[str, float] = {}  # a room losing more (drafty), per hour
        self.trvs: dict[str, Trv] = {}
        self.relays: dict[str, str] = {}  # relay -> room
        self.boiler: str | None = None
        self.circuit_of: dict[str, str] = {}  # room -> circuit relay
        self.later: list[tuple[datetime, Callable[[], None]]] = []
        self.commands: list[tuple[datetime, str, str]] = []
        # Nobody touches a device here: a manual change seen is a misreading.
        self.manual: list[tuple[datetime, str]] = []
        # Rooms topped up while the heat source runs for others, how often.
        self.top_ups: dict[str, int] = {}
        self._topped: set[str] = set()
        hass.bus.async_listen(EVENT_CALL_SERVICE, self._count)
        for service in ("set_temperature", "set_hvac_mode", "set_preset_mode"):
            hass.services.async_register("climate", service, self._climate)

    @callback
    def _count(self, event: Event) -> None:
        data = event.data
        if data.get("domain") not in ("climate", "input_boolean", "switch"):
            return
        ids = (data.get("service_data") or {}).get("entity_id")
        for entity_id in [ids] if isinstance(ids, str) else ids or []:
            self.commands.append((dt_util.utcnow(), entity_id, data["service"]))

    # ------------------------------------------------------------------ devices
    def add_room(self, room: str, temperature: float) -> str:
        self.temps[room] = temperature
        sensor = f"sensor.{room}"
        self._report_sensor(room)
        return sensor

    def add_trv(self, trv: Trv) -> None:
        self.trvs[trv.entity_id] = trv
        self._report(trv)

    def _report_sensor(self, room: str) -> None:
        self.hass.states.async_set(
            f"sensor.{room}",
            f"{round(self.temps[room], 1):.1f}",
            {"unit_of_measurement": "°C", "device_class": "temperature"},
        )

    def _heats(self, trv: Trv) -> bool:
        if trv.state == "off":
            trv.valve_open = False
        elif self.temps[trv.room] <= trv.target - trv.band:
            trv.valve_open = True
        elif self.temps[trv.room] >= trv.target + trv.band:
            trv.valve_open = False
        return trv.valve_open

    def _attrs(self, trv: Trv) -> dict[str, Any]:
        attrs: dict[str, Any] = {
            "hvac_modes": trv.modes,
            "temperature": trv.target,
            "current_temperature": round(self.temps[trv.room], 1),
            "hvac_action": "heating" if self._heats(trv) else "idle",
            "min_temp": trv.min_temp,
            "max_temp": trv.max_temp,
            "supported_features": 17 if trv.presets else 1,
        }
        if trv.step:
            attrs["target_temp_step"] = trv.step
        if trv.presets is not None:
            attrs["preset_modes"] = trv.presets
            attrs["preset_mode"] = trv.preset
        return attrs

    def _report(self, trv: Trv, context: Context | None = None) -> None:
        self.hass.states.async_set(trv.entity_id, trv.state, self._attrs(trv), context=context)

    def _soon(self, delay: float, action: Callable[[], None]) -> None:
        self.later.append((dt_util.utcnow() + timedelta(seconds=delay), action))

    def _answer(self, trv: Trv, context: Context) -> None:
        # At once, as an entity does, with the context of the command; a cloud
        # device later, without it.
        if trv.report_delay:
            self._soon(trv.report_delay, lambda: self._report(trv))
        else:
            self._report(trv, context)

    @callback
    def _climate(self, call: ServiceCall) -> None:
        trv = self.trvs[call.data["entity_id"]]
        if call.service == "set_hvac_mode":
            trv.state = call.data["hvac_mode"]
            if trv.state == "heat" and trv.reverts_to_auto_after is not None:

                def back() -> None:
                    trv.state = "auto"
                    self._report(trv)

                self._soon(trv.reverts_to_auto_after, back)
        elif call.service == "set_preset_mode":
            trv.preset = call.data["preset_mode"]
            if trv.preset in trv.preset_temps:
                trv.target = trv.preset_temps[trv.preset]
        else:
            value = float(call.data["temperature"])
            if not trv.min_temp - 1e-9 <= value <= trv.max_temp + 1e-9:
                # As Home Assistant does, before the device.
                raise ServiceValidationError(f"{value} is outside {trv.min_temp}-{trv.max_temp}")
            if trv.preset not in trv.refuses_on:
                trv.target = float(call.data["temperature"])
                if trv.step:
                    trv.target = round(trv.target / trv.step) * trv.step
            if trv.heat_on_temperature_for is not None and trv.state == "auto":
                trv.state = "heat"

                def schedule() -> None:
                    trv.state = "auto"
                    trv.target = trv.schedule_target
                    self._report(trv)

                self._soon(trv.heat_on_temperature_for, schedule)
        self._answer(trv, call.context)

    # ------------------------------------------------------------------ time
    def _on(self, entity_id: str | None) -> bool:
        if entity_id is None:
            return True
        state = self.hass.states.get(entity_id)
        return state is not None and state.state not in ("off", "unavailable", "unknown")

    def _room_heats(self, room: str) -> bool:
        if not self._on(self.circuit_of.get(room)):
            return False
        valve = any(r == room and self._on(e) for e, r in self.relays.items()) or any(
            t.room == room and self._heats(t) for t in self.trvs.values()
        )
        return valve and self._on(self.boiler)

    async def run(self, hours: float) -> None:
        for _ in range(int(hours * 3600 / STEP)):
            for entry in self.hass.config_entries.async_entries("advanced_climate"):
                house = getattr(entry, "runtime_data", None)
                for room in house.rooms.values() if house else []:
                    if room.decision is not None and room.decision.rule == "manual_override":
                        self.manual.append((dt_util.utcnow(), room.name))
                    if room.topped_up and room.name not in self._topped:
                        self.top_ups[room.name] = self.top_ups.get(room.name, 0) + 1
                    if room.topped_up:
                        self._topped.add(room.name)
                    else:
                        self._topped.discard(room.name)
            now = dt_util.utcnow()
            due = [a for at, a in self.later if at <= now]
            self.later = [(at, a) for at, a in self.later if at > now]
            for action in due:
                action()
            for room in self.temps:
                heat = HEAT_PER_HOUR if self._room_heats(room) else 0.0
                loss = self.loss.get(room, LOSS_PER_HOUR) * (self.temps[room] - OUTDOOR)
                self.temps[room] += (heat - loss) * STEP / 3600
                self._report_sensor(room)
            for trv in self.trvs.values():
                old = self.hass.states.get(trv.entity_id)
                attrs = self._attrs(trv)
                if (
                    old is None
                    or old.attributes.get("current_temperature") != attrs["current_temperature"]
                    or old.attributes.get("hvac_action") != attrs["hvac_action"]
                ):
                    self.hass.states.async_set(
                        trv.entity_id,
                        old.state if old else trv.state,
                        {
                            **(old.attributes if old else {}),
                            **{k: attrs[k] for k in ("current_temperature", "hvac_action")},
                        },
                    )
            await _tick(self.hass, self.freezer, STEP)

    # ------------------------------------------------------------------ budget
    def worst(self) -> dict[str, tuple[int, int]]:
        """Per device: the most commands in an hour, and in all."""
        out: dict[str, tuple[int, int]] = {}
        by: dict[str, list[datetime]] = {}
        for at, entity_id, _service in self.commands:
            by.setdefault(entity_id, []).append(at)
        for entity_id, times in by.items():
            hour = max(
                sum(1 for t in times if start <= t < start + timedelta(hours=1)) for start in times
            )
            out[entity_id] = (hour, len(times))
        return out

    def check(self, days: float) -> None:
        assert not self.manual, self.manual[:5]
        worst = self.worst()
        for entity_id, (hour, total) in worst.items():
            assert hour <= MAX_PER_HOUR, (entity_id, hour, total, self._last(entity_id))
            assert total <= MAX_PER_DAY * days, (entity_id, hour, total, self._last(entity_id))

    def _last(self, entity_id: str) -> list[tuple[str, str]]:
        return [
            (at.strftime("%H:%M:%S"), service) for at, e, service in self.commands if e == entity_id
        ][-12:]


ROOM = {"command_mode": "temperature", "source": "climate"}


async def _sim(hass, freezer) -> House:
    assert await async_setup_component(
        hass,
        "input_boolean",
        {"input_boolean": {k: {} for k in ("boiler", "up", "down", "heater", "pump")}},
    )
    return House(hass, freezer)


def _trv_room(house: House, name: str, trv: Trv, **room: Any) -> tuple[str, dict]:
    sensor = house.add_room(name, 19.0)
    house.add_trv(trv)
    return (
        name.capitalize(),
        {**ROOM, "climates": [trv.entity_id], "temperature_sensors": [sensor], **room},
    )


KINDS: dict[str, Callable[[str], Trv]] = {
    # A TRV that keeps its mode and temperature (most).
    "plain": lambda r: Trv(f"climate.{r}", r),
    # Found in auto (its own schedule), takes heat (Sonoff TRVZB, Hive).
    "auto_takes_heat": lambda r: Trv(
        f"climate.{r}", r, state="auto", modes=["auto", "heat", "off"]
    ),
    # Cannot stay in heat: back in auto a second later (Tuya TRV602Z, #15).
    "auto_reverts_at_once": lambda r: Trv(
        f"climate.{r}", r, state="auto", modes=["auto", "heat", "off"], reverts_to_auto_after=1
    ),
    # Back in auto 7 minutes after heat.
    "auto_reverts_later": lambda r: Trv(
        f"climate.{r}",
        r,
        state="auto",
        modes=["auto", "heat", "off"],
        reverts_to_auto_after=7 * 60,
    ),
    # Takes heat by itself on a temperature, back to its schedule after 3 h (Netatmo, tado).
    "manual_time_ends": lambda r: Trv(
        f"climate.{r}",
        r,
        state="auto",
        modes=["auto", "heat", "off"],
        heat_on_temperature_for=3 * 3600,
    ),
    # On its schedule preset, with a manual one (Aqara, Tuya, Moes).
    "schedule_preset": lambda r: Trv(
        f"climate.{r}", r, presets=["schedule", "manual", "boost"], preset="schedule"
    ),
    # The same, refusing a temperature while on its schedule.
    "schedule_preset_refuses": lambda r: Trv(
        f"climate.{r}",
        r,
        presets=["schedule", "manual", "holiday"],
        preset="schedule",
        refuses_on=("schedule",),
    ),
    # Reports a minute late.
    "late": lambda r: Trv(f"climate.{r}", r, report_delay=60),
}


@pytest.mark.parametrize("kind", list(KINDS))
async def test_two_days_of_one_kind_of_trv(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, kind: str
) -> None:
    house = await _sim(hass, freezer)
    rooms = [_trv_room(house, "office", KINDS[kind]("office"))]
    entry = await _house(hass, freezer, rooms)
    await house.run(48)
    house.check(2)
    await _unload(hass, entry)


async def test_two_days_with_a_window(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    """A window opened twice a day for ten minutes, on a TRV without off that
    keeps its preset (commanded by preset)."""
    house = await _sim(hass, freezer)
    hass.states.async_set("binary_sensor.window", "off")
    trv = Trv(
        "climate.office",
        "office",
        modes=["heat"],
        presets=["comfort", "eco", "sleep", "away"],
        preset="comfort",
        min_temp=7.0,
        target=21.0,
    )
    rooms = [
        _trv_room(
            house,
            "office",
            trv,
            command_mode="preset",
            preset_map={"home": "comfort", "eco": "eco", "sleep": "sleep", "away": "away"},
            window_sensors=["binary_sensor.window"],
        )
    ]
    entry = await _house(hass, freezer, rooms)
    for _ in range(4):
        await house.run(5)
        hass.states.async_set("binary_sensor.window", "on")
        await house.run(1 / 6)
        hass.states.async_set("binary_sensor.window", "off")
        await house.run(7)
    house.check(2)
    await _unload(hass, entry)


async def test_two_days_of_a_boiler_with_top_up_and_circuits(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    house = await _sim(hass, freezer)
    house.boiler = "input_boolean.boiler"
    house.circuit_of = {
        "bedroom": "input_boolean.up",
        "office": "input_boolean.up",
        "living": "input_boolean.down",
    }
    # The bedroom wants it warmer and keeps the boiler running for long; the
    # office cools and warms fast, so it is often a little below its target
    # meanwhile, and topped up.
    house.loss["office"] = 0.04
    rooms = [
        _trv_room(
            house,
            "bedroom",
            Trv("climate.bedroom", "bedroom", band=0.5),
            circuit="input_boolean.up",
            levels={"home": 23.0, "sleep": 22.0, "eco": 22.0, "comfort": 23.0, "away": 22.0},
        ),
        _trv_room(
            house,
            "office",
            Trv("climate.office", "office", band=0.5),
            circuit="input_boolean.up",
            top_up=True,
        ),
        _trv_room(
            house,
            "living",
            Trv("climate.living", "living"),
            circuit="input_boolean.down",
            top_up=True,
        ),
    ]
    entry = await _house(
        hass,
        freezer,
        rooms,
        boiler_entity="input_boolean.boiler",
        circuits=["input_boolean.up", "input_boolean.down"],
    )
    await house.run(48)
    house.check(2)
    await _unload(hass, entry)


async def test_two_days_of_zone_valves_without_a_heat_source(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    house = await _sim(hass, freezer)
    house.circuit_of = {"bedroom": "input_boolean.up", "living": "input_boolean.down"}
    rooms = [
        _trv_room(house, "bedroom", Trv("climate.bedroom", "bedroom"), circuit="input_boolean.up"),
        _trv_room(house, "living", Trv("climate.living", "living"), circuit="input_boolean.down"),
    ]
    entry = await _house(hass, freezer, rooms, circuits=["input_boolean.up", "input_boolean.down"])
    await house.run(48)
    house.check(2)
    await _unload(hass, entry)


async def test_two_days_of_a_relay_room(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    house = await _sim(hass, freezer)
    sensor = house.add_room("office", 19.0)
    house.relays["input_boolean.heater"] = "office"
    rooms = [
        (
            "Office",
            {
                "source": "switch",
                "switches": ["input_boolean.heater"],
                "temperature_sensors": [sensor],
            },
        )
    ]
    entry = await _house(hass, freezer, rooms)
    await house.run(48)
    house.check(2)
    await _unload(hass, entry)


async def test_two_days_of_an_on_off_thermostat(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    house = await _sim(hass, freezer)
    trv = Trv("climate.office", "office", state="off", target=18.0)
    rooms = [_trv_room(house, "office", trv, command_mode="hvac_mode")]
    entry = await _house(hass, freezer, rooms)
    await house.run(48)
    house.check(2)
    await _unload(hass, entry)


async def test_a_week_with_a_vacation_on_a_cloud_heat_pump(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Commanded by preset (away for the vacation), temperatures otherwise, its
    minimum 16 °C, reporting a minute late, refusing a temperature on away (#14)."""
    house = await _sim(hass, freezer)
    trv = Trv(
        "climate.daikin",
        "living",
        presets=["none", "away"],
        preset="none",
        min_temp=16.0,
        report_delay=60,
        refuses_on=("away",),
        preset_temps={"away": 16.0},
    )
    rooms = [_trv_room(house, "living", trv, command_mode="preset", preset_map={"away": "away"})]
    entry = await _house(hass, freezer, rooms)
    await house.run(24)
    await entry.runtime_data.async_set_mode("vacation")
    await house.run(48)
    await entry.runtime_data.async_set_mode("auto")
    await house.run(24)
    house.check(4)
    state = hass.states.get("climate.daikin")
    assert state.attributes["preset_mode"] == "none"
    await _unload(hass, entry)


async def test_two_days_of_a_water_range_heat_source(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """A heat source thermostat with the range of the water (30-80 °C)."""
    house = await _sim(hass, freezer)
    source = Trv("climate.boiler", "plant", state="off", target=45.0, min_temp=30.0, max_temp=80.0)
    house.temps["plant"] = 40.0
    house.trvs[source.entity_id] = source
    house._report(source)
    rooms = [_trv_room(house, "office", Trv("climate.office", "office"))]
    entry = await _house(hass, freezer, rooms, boiler_entity="climate.boiler")
    await house.run(48)
    house.check(2)
    await _unload(hass, entry)


async def test_a_week_with_a_vacation_on_a_heat_pump_with_a_minimum(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Commanded by temperature, its entity going no lower than 16 °C, a vacation
    at 12 °C: Home Assistant refuses 12 (#14). Held at 16, not sent again and again."""
    house = await _sim(hass, freezer)
    trv = Trv("climate.daikin", "living", min_temp=16.0, report_delay=60)
    rooms = [_trv_room(house, "living", trv)]
    entry = await _house(hass, freezer, rooms)
    await house.run(24)
    await entry.runtime_data.async_set_mode("vacation")
    await house.run(48)
    await entry.runtime_data.async_set_mode("auto")
    await house.run(24)
    house.check(4)
    await _unload(hass, entry)


async def test_two_days_of_a_relay_room_topped_up(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """A relay room topped up while the boiler runs for a room that wants it
    warmer: a sensor of a tenth of a degree, the relay not switched every few
    minutes."""
    house = await _sim(hass, freezer)
    house.boiler = "input_boolean.boiler"
    sensor = house.add_room("office", 19.0)
    house.loss["office"] = 0.04
    house.relays["input_boolean.heater"] = "office"
    rooms = [
        _trv_room(
            house,
            "bedroom",
            Trv("climate.bedroom", "bedroom", band=0.5),
            levels={"home": 23.0, "sleep": 22.0, "eco": 22.0, "comfort": 23.0, "away": 22.0},
        ),
        (
            "Office",
            {
                "source": "switch",
                "switches": ["input_boolean.heater"],
                "temperature_sensors": [sensor],
                "top_up": True,
            },
        ),
    ]
    entry = await _house(hass, freezer, rooms, boiler_entity="input_boolean.boiler")
    await house.run(48)
    house.check(2)
    # And it is topped up indeed, again and again (never in 2.6.5rc21-24).
    assert house.top_ups.get("Office", 0) >= 5, house.top_ups
    await _unload(hass, entry)
