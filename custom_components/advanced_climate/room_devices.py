"""Commands to the devices of a room.

Thermostats, TRVs and relays, the TRV boost, the learned device limits, the
check of every command and the calibration.

Part of :class:`~.room.Room` (a mixin): the methods use the state the room
keeps (``self``), set up in ``Room.__init__``.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_TEMPERATURE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import State
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import (
    entity_registry as er,
)
from homeassistant.helpers.event import async_call_later
from homeassistant.util import dt as dt_util

from .const import (
    CALIBRATION_EXTERNAL,
    CALIBRATION_OFFSET,
    CALIBRATION_REFRESH_MINUTES,
    COMMAND_HVAC,
    COMMAND_PRESET,
    COMMAND_TEMPERATURE,
    CONF_CALIBRATION_ENTITIES,
    CONF_CALIBRATION_MODE,
    CONF_HYSTERESIS,
    CONF_INERTIA_CONTROL,
    CONF_MIN_OFF,
    CONF_MIN_ON,
    CONF_TEMP_SENSORS,
    CONF_TRV_BOOST_TEMP,
    CONF_VERIFY_COMMANDS,
    PRESET_NONE,
    PRESETS,
    RULE_OVERRIDE,
    SOURCE_CLIMATE,
    SOURCE_GT,
    SOURCE_SWITCH,
    VERIFY_DELAY,
)
from .device_echo import close, limit_kind, step_margin
from .engine import (
    KIND_NONE,
    KIND_OFF,
    KIND_PRESET,
    KIND_TEMPERATURE,
    Target,
    on_off_wanted,
)
from .room_common import (
    SENT_RECENT,
)
from .util import (
    as_list,
    climate_temp,
    delta_from_celsius,
    finite,
    float_attr,
    from_celsius,
    heat_mode,
    system_unit,
    to_celsius,
    valid,
)

if TYPE_CHECKING:
    from .house import House

# The same logger as the rest of the room, so the log lines keep their name.
_LOGGER = logging.getLogger(__name__.rsplit(".", 1)[0] + ".room")
# Back in auto within this time after being put in heat: the thermostat keeps auto.
AUTO_RETURN_WINDOW = timedelta(minutes=5)


class RoomDevices:
    """Commands to the devices of a room (mixin of the room)."""

    house: House

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------
    async def _call(self, domain: str, service: str, data: dict[str, Any]) -> bool:
        """Call a service with the context of the integration; False when it fails."""
        try:
            await self.hass.services.async_call(
                domain, service, data, blocking=True, context=self.house.new_context()
            )
        except (HomeAssistantError, ValueError) as err:
            _LOGGER.warning("Room %s: %s.%s failed: %s", self.name, domain, service, err)
            return False
        return True

    async def _async_apply(self, target: Target, *, force: bool = False) -> None:
        """Send the commands needed to reach ``target``."""
        on_off = self.source == SOURCE_SWITCH or self.command_mode == COMMAND_HVAC
        if target.kind == KIND_NONE:
            # Nothing is sent (pause, no schedule) unless a manual change applies.
            self.relay_waiting = None
            self._relay_wait_until = None
            if self.decision is None or self.decision.rule != RULE_OVERRIDE or not self.override:
                await self._async_boost_without_target(target)
                return
            stored = self._override_target()
            if stored is None:
                await self._async_boost_without_target(target)
                # Changed on the device: set again only after an interruption.
                if self.override.get("interrupted"):
                    self.override["interrupted"] = False
                    for entity_id, values in (self.override.get("devices") or {}).items():
                        if not await self._async_restore_device(entity_id, values):
                            # The minimum on / off time runs: set again when it ends.
                            self.override["interrupted"] = True
                return
            # Set by the card or a service: kept on the devices (relays regulate around it).
            self.override["interrupted"] = False
            target = stored
        if self._boost_capable:
            # The demand first, so the TRVs get the right temperature now. Kept
            # open for the heat source the room asks for no heat (nor remembers
            # it, so it does not go on asking once that ends).
            heat = (
                target.kind != KIND_OFF
                and self._exercise_until is None
                and not self.opened_for_source
            )
            temperature = self._resolve_temperature(target)
            if self.boost:
                self._boost_demand = heat and self._boost_wanted(temperature)
            elif (
                self._frost_boost_possible()
                and temperature is not None
                and temperature <= self.frost_temp() + 1e-9
            ):
                self._boost_demand = heat and self._frost_wanted(temperature)
            else:
                self._boost_demand = False
        sent = False
        if on_off:
            sent = await self._async_apply_relay(target)
        else:
            for entity_id in self.climates:
                sent |= await self._async_apply_climate(entity_id, target, force)
        if self._boost_capable:
            self._boosted = self._boost_demand
            self._boost_base = (
                None if target.kind == KIND_OFF else self._target_temperature_of(target)
            )
        if sent and self.house.options[CONF_VERIFY_COMMANDS]:
            self._schedule_verify(target)

    @property
    def boost_active(self) -> bool:
        """The TRVs hold the boost temperature now (the TRV boost or frost protection)."""
        return self._boost_capable and self._boosted

    @property
    def _boost_capable(self) -> bool:
        """TRVs commanded with a temperature or a preset can be boosted."""
        return self.source == SOURCE_CLIMATE and self.command_mode != COMMAND_HVAC

    def _frost_boost_possible(self) -> bool:
        """A TRV room without the boost, with its own room sensor (frost protection).

        The TRV next to the radiator reads warmer than the room: at the frost
        protection temperature it would not open, so it is boosted like the TRV
        boost while the room sensor is below the frost protection.
        """
        return (
            not self.boost
            and self._boost_capable
            and bool(as_list(self.config.get(CONF_TEMP_SENSORS)))
            and not self.external_failed
        )

    def _frost_wanted(self, frost: float) -> bool:
        """Frost protection demand from the room sensor: below it, until it + hysteresis."""
        if self.current_temp is None:
            return False
        if self.current_temp < frost:
            return True
        if self.current_temp >= frost + float(self.config[CONF_HYSTERESIS]):
            return False
        return self._boost_demand  # between the limits: as it was

    def _boost_wanted(self, temperature: float | None) -> bool:
        """The room asks for heat (boost rooms): the room sensor with the hysteresis.

        Between the limits it stays as it was, or follows the learned inertia
        (as a relay).
        """
        if temperature is None or self.current_temp is None:
            self.inertia_stop = None
            return False
        hysteresis = float(self.config[CONF_HYSTERESIS])
        want, by_model = on_off_wanted(
            self._boost_demand,
            self.current_temp,
            temperature,
            hysteresis,
            self._inertia_extreme(dt_util.utcnow()),
        )
        if want:
            self.inertia_stop = None
        elif by_model:
            self.inertia_stop = self._inertia_peak
        return want

    def boost_temperature(self, temperature: float) -> float:
        """Temperature the TRVs get while the room asks for heat (°C).

        The boost temperature of the room (the maximum of the house when empty),
        never below the target, never above the maximum of the house nor of the TRVs.
        """
        chosen = self.config.get(CONF_TRV_BOOST_TEMP) if self.boost else None
        value = float(chosen) if chosen not in (None, "") else self.max_temp()
        value = min(value, self.max_temp())
        device_max = self.device_max_temp()
        if device_max is not None:
            value = min(value, device_max)
        return max(value, temperature)

    def _learned_max(self) -> float | None:
        """Lowest maximum learned from the thermostats of the room (°C)."""
        unit = system_unit(self.hass)
        values = [
            float(to_celsius(v, unit))
            for eid in self.climates
            if (v := self._device_limit(eid, "max")) is not None
        ]
        return min(values) if values else None

    def _target_temperature_of(self, target: Target) -> float | None:
        """Temperature of a target, before the boost."""
        if target.kind == KIND_TEMPERATURE:
            return target.temperature
        if target.kind == KIND_PRESET:
            return self.level_temp(target.preset or "")
        return None

    def _climate_temperature(self, target: Target) -> float | None:
        """Temperature a thermostat gets for ``target`` (with the TRV boost)."""
        temperature = self._target_temperature_of(target)
        if temperature is not None and self._boost_capable and self._boost_demand:
            return self.boost_temperature(temperature)
        return temperature

    async def _async_boost_without_target(self, target: Target) -> None:
        """Boost rooms when nothing is sent (pause, no schedule, a change on the TRV).

        A boost we left on the TRVs is taken back to the target, so a TRV never
        keeps the boost temperature while nobody regulates it; the heat demand
        follows the room sensor against what the TRV is set to.
        """
        if not self._boost_capable:
            return
        # Until the TRVs report it, the temperature they hold is the one taken back.
        temperature = self._resolve_temperature(target)
        if self._boosted and self._boost_base is not None:
            temperature = self._boost_base
            for entity_id in self.climates:
                state = self.hass.states.get(entity_id)
                if valid(state):
                    assert state is not None
                    await self._send(
                        entity_id,
                        "set_temperature",
                        ATTR_TEMPERATURE,
                        self._device_value(state, self._boost_base),
                    )
        self._boosted = False
        heat = self._exercise_until is None
        # Without the TRV boost the demand comes from the TRVs again.
        self._boost_demand = self.boost and heat and self._boost_wanted(temperature)

    async def _async_restore_device(self, entity_id: str, values: dict[str, Any]) -> bool:
        """Set again what a person set on a device (after an interruption).

        False while the minimum on / off time of a relay (or on / off thermostat)
        runs: it is set again when that time ends.
        """
        state = self.hass.states.get(entity_id)
        if not valid(state) or not values:
            return True
        assert state is not None
        domain = entity_id.split(".", 1)[0]
        wanted = values.get("state")
        on_off = self.source == SOURCE_SWITCH or self.command_mode == COMMAND_HVAC
        if on_off and wanted and state.state != wanted:
            actual = self._relay_actual()
            now = dt_util.utcnow()
            if actual is not None:
                self._note_relay_state(actual, now)
                if (wanted != STATE_OFF) != actual and self._relay_must_wait(actual, now):
                    return False
        if domain != "climate":
            if (
                wanted in (STATE_ON, STATE_OFF)
                and state.state != wanted
                and await self._call(
                    domain,
                    SERVICE_TURN_ON if wanted == STATE_ON else SERVICE_TURN_OFF,
                    {ATTR_ENTITY_ID: entity_id},
                )
            ):
                self.sent.set_last(entity_id, {"state": wanted})
                if entity_id in self.switches:
                    self._relay_on = wanted == STATE_ON
                    self._relay_changed = dt_util.utcnow()
            return True
        if (
            wanted
            and state.state != wanted
            and await self._send(entity_id, "set_hvac_mode", "hvac_mode", wanted, "state")
            and on_off
        ):
            self._relay_on = wanted != STATE_OFF
            self._relay_changed = dt_util.utcnow()
        if wanted == STATE_OFF:
            return True
        preset = values.get("preset_mode")
        if preset not in (None, PRESET_NONE):
            if state.attributes.get("preset_mode") != preset:
                await self._send(entity_id, "set_preset_mode", "preset_mode", preset)
            return True
        temperature = values.get("temperature")
        if temperature is not None and float_attr(state, ATTR_TEMPERATURE) != temperature:
            await self._send(entity_id, "set_temperature", ATTR_TEMPERATURE, temperature)
        return True

    def sends_preset(self, preset: str) -> bool:
        """The level is sent to the device as a preset (else as a temperature)."""
        if self.source not in (SOURCE_GT, SOURCE_CLIMATE) or self.command_mode != COMMAND_PRESET:
            return False
        for entity_id in self.climates:
            state = self.hass.states.get(entity_id)
            if valid(state):
                available = list(state.attributes.get("preset_modes") or [])  # type: ignore[union-attr]
                return self._device_preset(preset, available) is not None
        return self.source == SOURCE_GT

    def _device_preset(self, preset: str, available: list[str]) -> str | None:
        """Map a level to the device preset name."""
        if self.source == SOURCE_GT:
            return preset if preset in available else None
        if self.preset_map is None:
            return None
        candidates = [self.preset_map.get(preset)]
        if self._legacy_map:
            candidates.append(preset)
        for candidate in candidates:
            if candidate and candidate in available:
                return candidate
        return None

    def _own_schedule_mode(self, state: State) -> bool:
        """A thermostat driven by temperature, left in auto (its own schedule) while it has heat.

        In auto a TRV follows the schedule stored in it and changes its target
        by itself; with the Temperature command it is put in heat, so it keeps
        the temperature sent. Only once it took the temperature and stayed in
        auto (``_holds``): many thermostats leave auto by themselves when a
        temperature is set (Netatmo, Tado), and for some heat means a boost to
        the maximum. A device with only auto keeps it (that is its heating
        mode), and the Preset command leaves the mode alone (presets may need
        auto).
        """
        if not (
            self.command_mode == COMMAND_TEMPERATURE
            and state.state == "auto"
            and "heat" in (state.attributes.get("hvac_modes") or [])
        ):
            return False
        entity_id = state.entity_id
        if entity_id in self.keeps_auto:
            return False
        left = self.auto_left_at.get(entity_id)
        if left is not None and dt_util.utcnow() - left < AUTO_RETURN_WINDOW:
            # Put in heat a moment ago and back in auto by itself (some Tuya TRVs
            # cannot be put in heat from Home Assistant): left in auto from now
            # on, as before 2.6.4, instead of being put in heat again and again.
            self.keeps_auto.add(entity_id)
            _LOGGER.info(
                "Room %s: %s goes back to auto by itself, it is left in auto", self.name, entity_id
            )
            return False
        return True

    def _holds(self, state: State, target: Target) -> bool:
        """The thermostat holds the temperature of the target (in its own unit)."""
        temperature = self._climate_temperature(target)
        if temperature is None:
            return False
        current = float_attr(state, ATTR_TEMPERATURE)
        wanted = self._device_value(state, temperature)
        return current is not None and abs(current - wanted) < 0.05

    def _matches(self, state: State, target: Target) -> bool:
        """Return True if the climate state already matches the target."""
        if target.kind == KIND_OFF:
            if STATE_OFF in (state.attributes.get("hvac_modes") or []):
                return state.state == STATE_OFF
            return float_attr(state, ATTR_TEMPERATURE) == float_attr(state, "min_temp")
        if state.state == STATE_OFF:
            return False
        if target.kind == KIND_PRESET and self.command_mode == COMMAND_PRESET:
            name = self._device_preset(
                target.preset or "", list(state.attributes.get("preset_modes") or [])
            )
            if name is not None:
                return state.attributes.get("preset_mode") == name
        # A level the thermostat has no preset for, and whose temperature is
        # unknown, is not reached, so the room says so (``preset_missing``).
        # Compared in the unit of the thermostat, as sent; taken in auto (its own
        # schedule) it still has to be put in heat.
        return self._holds(state, target) and not self._own_schedule_mode(state)

    async def _async_apply_climate(self, entity_id: str, target: Target, force: bool) -> bool:
        """Bring one thermostat to the target (mode, preset or temperature)."""
        state = self.hass.states.get(entity_id)
        if not valid(state):
            return False
        assert state is not None
        if not force and self._matches(state, target):
            return False
        self.sent.start(entity_id)
        modes = list(state.attributes.get("hvac_modes") or [])
        # Turned on only with a mode that heats (no guess when there is none).
        on_mode = heat_mode(modes) if {"heat", "auto"} & set(modes) else None

        if target.kind == KIND_OFF:
            if STATE_OFF in modes:
                return await self._send(entity_id, "set_hvac_mode", "hvac_mode", STATE_OFF, "state")
            minimum = float_attr(state, "min_temp")
            if minimum is None:
                return False
            return await self._send(entity_id, "set_temperature", ATTR_TEMPERATURE, minimum)

        if (state.state == STATE_OFF and on_mode) or (
            self._own_schedule_mode(state) and self._holds(state, target)
        ):
            if state.state != STATE_OFF:
                self.auto_left_at[entity_id] = dt_util.utcnow()
            await self._send(entity_id, "set_hvac_mode", "hvac_mode", on_mode or "heat", "state")

        if target.kind == KIND_PRESET and self.command_mode == COMMAND_PRESET:
            available = list(state.attributes.get("preset_modes") or [])
            name = self._device_preset(target.preset or "", available)
            if name is not None:
                self.house.clear_alert(f"preset_{self.id}_{target.preset}")
                return await self._send(entity_id, "set_preset_mode", "preset_mode", name)
        temperature = self._climate_temperature(target)
        if temperature is None:
            self.house.notify(
                f"preset_{self.id}_{target.preset}",
                f"{self.name}: the level '{self.display_name(target.preset)}' is not "
                f"available on {entity_id} and its temperature is unknown. "
                "Configure this preset in the thermostat.",
                code="preset_missing",
                params={"level": self.display_name(target.preset), "entity": entity_id},
                room=self.id,
            )
            return False
        return await self._send(
            entity_id, "set_temperature", ATTR_TEMPERATURE, self._device_value(state, temperature)
        )

    def _device_value(self, state: State, temperature: float) -> float:
        """Temperature to send, in the unit of the thermostat.

        A thermostat rounds to its own step; where that would take a value
        within the maximum of the house above it, the value is rounded down to
        the step instead, so the thermostat never holds more than the maximum.
        A value meant to be above the maximum (the valve exercise) is sent as
        it is.
        """
        unit = system_unit(self.hass)
        value = round(float(from_celsius(temperature, unit)), 1)
        step = float_attr(state, "target_temp_step")
        if step:
            maximum = float(from_celsius(self.max_temp(), unit))
            if value <= maximum + 1e-9 < round(value / step) * step:
                value = round(math.floor(maximum / step + 1e-9) * step, 2)
        # The limits the device applies by itself: sent within them, so what it
        # reports is what was sent (not a manual change).
        high = self._device_limit(state.entity_id, "max")
        low = self._device_limit(state.entity_id, "min")
        if high is not None:
            value = min(value, high)
        if low is not None:
            value = max(value, low)
        return self._within_entity_range(state, value)

    def _within_entity_range(self, state: State, value: float) -> float:
        """The value within the range of the entity (Home Assistant refuses any other).

        Below its minimum (e.g. a heat pump that goes no lower than 16 for a
        vacation at 12) the room is held at that minimum, and told so once.
        """
        entity_id = state.entity_id
        high = float_attr(state, "max_temp")
        low = float_attr(state, "min_temp")
        told = self.range_min_told.get(entity_id)
        if told is not None and (low is None or low < told - 1e-9):
            # The minimum was lowered on the device: the alert no longer applies.
            del self.range_min_told[entity_id]
            self.house.clear_alert(f"range_{entity_id}_min")
        if high is not None and value > high:
            value = high
        if low is not None and value < low - 1e-9:
            if told is None or told != low:
                self.range_min_told[entity_id] = low
                unit = system_unit(self.hass)
                self.house.notify(
                    f"range_{entity_id}_min",
                    f"{self.name}: {entity_id} accepts at least {low:g} {unit}, so the room "
                    f"is held at {low:g} {unit} instead of {value:g} {unit}: lower the "
                    "minimum on the device (or in its app) if you want it lower.",
                    code="device_range_min",
                    params={
                        "entity": entity_id,
                        "value": f"{low:g} {unit}",
                        "target": f"{value:g} {unit}",
                    },
                    room=self.id,
                )
            value = low
        return value

    def _device_limit(self, entity_id: str, kind: str) -> float | None:
        """A limit learned from the device (its unit); forgotten after a day, to see a new setting."""
        value, expired = self.limits.get(entity_id, kind, dt_util.utcnow())
        if expired:
            self.house.clear_alert(f"limit_{entity_id}_{kind}")
        return value

    def _check_device_limit(self, entity_id: str, old: State | None, new: State | None) -> bool:
        """True when a thermostat reports its own limit instead of the value sent.

        After a boost or the valve exercise (a value above the target) it may
        report less, but at least the target: that is its own maximum. After
        frost protection or off (a value below every level) it may report more,
        but below the lowest level: that is its own minimum. Neither is a
        manual change; the limit is kept for the next commands and told.
        """
        if old is None or new is None or not valid(new):
            return False
        if float_attr(new, ATTR_TEMPERATURE) == float_attr(old, ATTR_TEMPERATURE):
            return False
        return self._learn_device_limit(entity_id, new, reported_now=True)

    def _learn_device_limit(
        self, entity_id: str, new: State | None, *, reported_now: bool = False
    ) -> bool:
        """True when what a thermostat shows now is its own limit for the last value sent.

        Also used without a change of the device (the verification, the next
        command): a TRV that already held its limit reports nothing new.
        """
        if new is None or not valid(new) or new.state == STATE_OFF:
            return False
        sent = self.sent.last_value(entity_id, ATTR_TEMPERATURE)
        reported = float_attr(new, ATTR_TEMPERATURE)
        if sent is None or reported is None:
            return False
        try:
            sent = float(sent)
        except (TypeError, ValueError):
            return False
        # A TRV that has shown the value sent accepted it: any other value after
        # that is a person's, not its limit.
        if self.sent.is_confirmed(entity_id, ATTR_TEMPERATURE):
            return False
        now = dt_util.utcnow()
        # Only right after the command: a TRV holds its limit when it gets it.
        sent_at = self.sent.last_sent_at(entity_id, ATTR_TEMPERATURE)
        if sent_at is None or now - sent_at > SENT_RECENT:
            return False
        # A value sent before, reported now (late, or once more after the new one),
        # is an echo, not a limit. (At the check, the TRV has held what it shows
        # since before the command was sent again.)
        margin = step_margin(new)
        earlier = self.sent.recent_values(entity_id, ATTR_TEMPERATURE, now)
        if (
            reported_now
            and any(close(reported, v, margin) for v in earlier)
            and not close(reported, sent, margin)
        ):
            return False
        unit = system_unit(self.hass)
        base = self._target_temperature_of(self.decision.target) if self.decision else None
        levels = [self.level_temp(p) for p in PRESETS]
        lowest = min((v for v in levels if v is not None), default=None)
        kind = limit_kind(
            sent,
            reported,
            margin,
            target=None if base is None else float(from_celsius(base, unit)),
            exercising=self._exercise_until is not None,
            lowest_level=None if lowest is None else float(from_celsius(lowest, unit)),
        )
        if kind is None:
            return False
        previous = self.limits.learn(entity_id, kind, reported, now)
        if previous is not None and abs(previous - reported) > margin:
            # The limit changed on the device: the alert tells the new value.
            self.house.clear_alert(f"limit_{entity_id}_{kind}")
        self.sent.replace(entity_id, ATTR_TEMPERATURE, reported)
        shown = f"{reported:g} {unit}"
        self.house.notify(
            f"limit_{entity_id}_{kind}",
            f"{self.name}: {entity_id} accepts at {'most' if kind == 'max' else 'least'} {shown}; "
            f"{'raise its Max temperature' if kind == 'max' else 'lower its Min temperature'} "
            "on the device if the room needs more.",
            code=f"device_limit_{kind}",
            params={"entity": entity_id, "value": shown},
            room=self.id,
        )
        return True

    async def _send(
        self, entity_id: str, service: str, key: str, value: Any, field: str | None = None
    ) -> bool:
        """Send one climate command and remember the value it sets."""
        name = field or key
        # What the device shows before the command: some TRVs report it once more
        # after showing the new value, however long ago it was set. Only for the
        # temperature and the preset: turning a device off by hand right after it
        # was turned on stays a manual change.
        before = self.hass.states.get(entity_id)
        shown = None
        if valid(before) and name != "state":
            shown = before.state if name == "state" else before.attributes.get(name)  # type: ignore[union-attr]
        ok = await self._call("climate", service, {ATTR_ENTITY_ID: entity_id, key: value})
        if ok:
            self.sent.record(entity_id, name, value, shown, dt_util.utcnow())
        return ok

    async def _async_apply_relay(self, target: Target) -> bool:
        """On/off control for switches or climates in hvac_mode command mode."""
        now = dt_util.utcnow()
        self.relay_waiting = None
        self._relay_wait_until = None
        # The real state first: inside the hysteresis band it stays as it is
        # (also when a person switched it by hand).
        actual = self._relay_actual()
        if actual is None:
            return False
        self._note_relay_state(actual, now)
        held = self.opened_for_source
        # Just kept open for the heat source: the TRV was on only for it. The
        # band starts again from off, without the minimum on time.
        released = self._relay_held and not held
        band_from = False if released else actual
        if target.kind == KIND_OFF:
            want = False
        else:
            temperature = self._resolve_temperature(target)
            if temperature is None or self.current_temp is None:
                want = False
            else:
                hysteresis = float(self.config[CONF_HYSTERESIS])
                want, by_model = on_off_wanted(
                    band_from,
                    self.current_temp,
                    temperature,
                    hysteresis,
                    self._inertia_extreme(now),
                )
                if by_model and not want:
                    self.inertia_stop = self._inertia_peak
        if want or target.kind == KIND_OFF:
            self.inertia_stop = None
        if want == actual:
            self._relay_held = held and want
            return False
        if not released and self._relay_must_wait(actual, now):
            return False
        ok = True
        if self.source == SOURCE_SWITCH:
            for entity_id in self.switches:
                sent = await self._call(
                    entity_id.split(".", 1)[0],
                    SERVICE_TURN_ON if want else SERVICE_TURN_OFF,
                    {ATTR_ENTITY_ID: entity_id},
                )
                if sent:
                    self.sent.set_last(entity_id, {"state": STATE_ON if want else STATE_OFF})
                ok &= sent
        else:
            for entity_id in self.climates:
                state = self.hass.states.get(entity_id)
                on_mode = heat_mode(state.attributes.get("hvac_modes") if valid(state) else None)  # type: ignore[union-attr]
                self.sent.start(entity_id)
                ok &= await self._send(
                    entity_id, "set_hvac_mode", "hvac_mode", on_mode if want else STATE_OFF, "state"
                )
        if ok:
            self._relay_on = want
            self._relay_held = held and want
            if not held:
                # Kept open is no start of the room: no minimum on time after it.
                self._relay_changed = now
        return ok

    def _inertia_extreme(self, now: datetime) -> Callable[[bool], float] | None:
        """The learned model for starting and stopping by the inertia (None: the band only).

        Only once the room learned its model and with *Use the learned
        inertia* on.
        """
        if not self.config.get(CONF_INERTIA_CONTROL, True) or self.current_temp is None:
            return None
        learner = self.learner
        if not learner.model.learned:
            return None
        house = self.house
        outdoor = house.outdoor_now
        sun = house.sun_ahead(now)
        current = self.current_temp

        def extreme(heating: bool) -> float:
            value = learner.model.extreme(current, outdoor, learner.q, heating, sun)
            if not heating:
                self._inertia_peak = value
            return value

        return extreme

    def _note_relay_state(self, actual: bool, now: datetime) -> None:
        """Remember the real relay state; a switch from outside starts the minimum time."""
        if self._relay_on is not None and actual != self._relay_on:
            self._relay_changed = now
        self._relay_on = actual

    def _relay_must_wait(self, actual: bool, now: datetime) -> bool:
        """True while the minimum on / off time of the relay runs (and note until when)."""
        if self._relay_changed is None:
            return False
        minimum = timedelta(
            minutes=float(self.config[CONF_MIN_ON] if actual else self.config[CONF_MIN_OFF])
        )
        if now - self._relay_changed < minimum:
            self.relay_waiting = "min_on" if actual else "min_off"
            self._relay_wait_until = self._relay_changed + minimum
            return True
        return False

    def _relay_actual(self) -> bool | None:
        """True when a relay (or on / off thermostat) is on now."""
        entities = self.switches if self.source == SOURCE_SWITCH else self.climates
        states = [self.hass.states.get(eid) for eid in entities]
        usable = [s for s in states if valid(s)]
        if not usable:
            return None
        return any(s.state not in (STATE_OFF,) for s in usable)  # type: ignore[union-attr]

    def _schedule_verify(self, target: Target) -> None:
        """Check later that the devices accepted the command; retry once, then alert."""
        if self._verify_unsub:
            self._verify_unsub()
            self._verify_unsub = None
        if self._stopped:
            return
        expected = target

        async def _verify(_now: datetime) -> None:
            """Compare the devices with the command sent."""
            self._verify_unsub = None
            # A manual change set by the card or a service has no target in the
            # decision (it is "respected"); its stored target is checked instead.
            current = (
                self._override_target()
                if self.decision is not None and self.decision.rule == RULE_OVERRIDE
                else self.decision.target
                if self.decision is not None
                else None
            )
            if current != expected:
                self._verify_attempts = 0
                return
            if self.source == SOURCE_SWITCH or self.command_mode == COMMAND_HVAC:
                self._verify_attempts = 0
                return
            mismatched = []
            for eid in self.climates:
                state = self.hass.states.get(eid)
                if not valid(state) or self._matches(state, expected):  # type: ignore[arg-type]
                    continue
                # Still not there after the command was sent again: a TRV that
                # holds its own limit (it may have held it already, so it reported
                # no change) is learned instead of the alert. Not at the first
                # check: a TRV may just not have reported yet.
                if (
                    self._verify_attempts >= 1
                    and self._learn_device_limit(eid, state)
                    and self._matches(state, expected)  # type: ignore[arg-type]
                ):
                    continue
                mismatched.append(eid)
            if not mismatched:
                self._verify_attempts = 0
                self.house.clear_alert(f"verify_{self.id}")
                return
            self._verify_attempts += 1
            if self._verify_attempts == 1:
                await self._async_apply(expected, force=True)
            else:
                self._verify_attempts = 0
                self.house.notify(
                    f"verify_{self.id}",
                    f"{self.name}: {', '.join(mismatched)} did not accept "
                    f"{expected.describe(self.house.unit)}.",
                    repeat=timedelta(hours=6),
                    code="not_accepted",
                    params={"entities": mismatched, "target": expected.describe(self.house.unit)},
                    room=self.id,
                )

        self._verify_unsub = async_call_later(self.hass, VERIFY_DELAY, _verify)

    async def async_apply_manual(self, target: Target, hours: float | None) -> None:
        """Service: set a manual target and keep it as an override.

        A temperature is kept between the frost protection and the maximum.
        The new manual change ends the earlier one (and what it kept).
        """
        if target.kind == KIND_TEMPERATURE and target.temperature is not None:
            limited = min(max(target.temperature, self.frost_temp()), self.max_temp())
            target = Target(KIND_TEMPERATURE, preset=target.preset, temperature=limited)
        # Sent by the decision that follows, only when the manual change applies
        # (not in a pause, with a window open, in mode Off...).
        self.set_override(
            f"set by service: {target.describe(self.house.unit)}", hours=hours, target=target
        )

    # ------------------------------------------------------------------
    # Calibration
    # ------------------------------------------------------------------
    async def _async_calibrate(self, now: datetime) -> None:
        """Write the external temperature (or the offset) to the TRV calibration entities."""
        mode = self.config[CONF_CALIBRATION_MODE]
        if mode not in (CALIBRATION_OFFSET, CALIBRATION_EXTERNAL) or self.house.paused:
            return
        external = self.external_temperature()
        if external is None:
            return
        entity_reg = er.async_get(self.hass)
        for number_id in as_list(self.config.get(CONF_CALIBRATION_ENTITIES)):
            number = self.hass.states.get(number_id)
            if not valid(number):
                continue
            assert number is not None
            last = self._calibration_written.get(number_id)
            interval = timedelta(minutes=10 if mode == CALIBRATION_OFFSET else 5)
            if last is not None and now - last < interval:
                continue
            step = float_attr(number, "step") or 0.1
            minimum = float_attr(number, "min")
            maximum = float_attr(number, "max")
            if (current := finite(number.state)) is None:
                continue  # not a number: this entity is skipped
            # The TRV number has its own unit (usually °C).
            number_unit = number.attributes.get("unit_of_measurement") or system_unit(self.hass)
            if mode == CALIBRATION_EXTERNAL:
                value = float(from_celsius(external, number_unit))
            else:
                climate_id = self._climate_on_same_device(entity_reg, number_id)
                device_temp = (
                    climate_temp(self.hass, self.hass.states.get(climate_id), "current_temperature")
                    if climate_id
                    else None
                )
                if device_temp is None:
                    continue
                value = current + float(delta_from_celsius(external - device_temp, number_unit))
            value = round(round(value / step) * step, 2)
            if minimum is not None:
                value = max(minimum, value)
            if maximum is not None:
                value = min(maximum, value)
            # A change smaller than a step (or 0.1) is not sent, with a small
            # tolerance: in floating point 19.7 − 19.6 is 0.0999999… In the
            # external temperature mode the value is sent again at least every
            # CALIBRATION_REFRESH_MINUTES even when unchanged: some TRVs (Sonoff
            # TRVZB: after about 2 hours) go back to their own sensor when no
            # value comes.
            small = abs(value - current) < max(step, 0.1) - 1e-6
            refresh_due = mode == CALIBRATION_EXTERNAL and (
                last is None or now - last >= timedelta(minutes=CALIBRATION_REFRESH_MINUTES)
            )
            if small and not refresh_due:
                continue
            if await self._call("number", "set_value", {ATTR_ENTITY_ID: number_id, "value": value}):
                self._calibration_written[number_id] = now

    def _climate_on_same_device(self, registry: er.EntityRegistry, entity_id: str) -> str | None:
        """Thermostat on the same device as a calibration entity."""
        entry = registry.async_get(entity_id)
        if entry is None or entry.device_id is None:
            return self.climates[0] if len(self.climates) == 1 else None
        for climate_id in self.climates:
            climate_entry = registry.async_get(climate_id)
            if climate_entry is not None and climate_entry.device_id == entry.device_id:
                return climate_id
        return None

    # ------------------------------------------------------------------
    # Setters used by entities and services
    # ------------------------------------------------------------------
    async def async_set_level(self, preset: str, value: float) -> None:
        """Set the temperature of a custom level."""
        if preset == "nearby":
            self.nearby_temp = value
        else:
            self.levels[preset] = value
        await self.house.async_evaluate_or_notify()

    async def async_set_child_lock(self, on: bool) -> None:
        """Enable or disable the child lock."""
        self.child_lock = on
        await self.house.async_evaluate_or_notify()
