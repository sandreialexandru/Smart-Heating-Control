"""What a room tells about itself.

Why it does not heat, the diagnostics and the learned model.

Part of :class:`~.room.Room` (a mixin): the methods use the state the room
keeps (``self``), set up in ``Room.__init__``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.const import (
    STATE_OFF,
)

from .const import (
    COMMAND_HVAC,
    CONF_BOILER_MIN_ROOMS,
    CONF_CALIBRATION_ENTITIES,
    CONF_HUMIDITY_SENSOR,
    CONF_HYSTERESIS,
    CONF_LINKED_WINDOW_SENSORS,
    CONF_OCCUPANCY_SENSORS,
    CONF_TEMP_SENSORS,
    CONF_WINDOW_SENSORS,
    PRESETS,
    RULE_PAUSE,
    SOURCE_SWITCH,
)
from .engine import (
    KIND_OFF,
)
from .util import (
    as_list,
    delta_from_celsius,
    from_celsius,
    iso,
    valid,
)

if TYPE_CHECKING:
    from .house import House


class RoomStatus:
    """What a room tells about itself (mixin of the room)."""

    house: House

    def no_heat_reason(self) -> dict[str, Any] | None:
        """Why the room does not heat although it is below its target."""
        decision = self.decision
        if (
            decision is None
            or decision.target.kind == KIND_OFF
            or decision.rule == RULE_PAUSE
            or self.current_temp is None
            or self.target_temperature is None
            or self.current_temp >= self.target_temperature
            or self.heating
            or self._exercise_until is not None
            or self.opened_for_source
        ):
            return None
        house = self.house
        configured, source_on = house.heat_source_state()
        if self.heat_demand and self.uses_house_source:
            if configured and source_on is None:
                return {"code": "source_unknown"}
            if not self.starts_house_source:
                # A secondary room: it waits for a room that starts the heat source.
                return {"code": "secondary"}
            if self.circuit is not None and house.circuit_on(self.circuit) is not True:
                # The relay of its circuit (pump or valve) is off or unavailable.
                return {"code": "circuit_closed", "entity": self.circuit}
            if house.source_waiting:
                return {"code": f"source_{house.source_waiting}"}
            needed = max(1, int(house.options[CONF_BOILER_MIN_ROOMS]))
            count = sum(
                1 for room in house.rooms.values() if room.heat_demand and room.starts_house_source
            )
            if count < needed:
                return {"code": "rooms_needed", "count": count, "needed": needed}
            return {"code": "source_off"}
        if self.source == SOURCE_SWITCH or self.command_mode == COMMAND_HVAC or self.boost:
            if self.relay_waiting:
                return {"code": f"relay_{self.relay_waiting}"}
            if self.inertia_stop is not None:
                # Stopped early: the heat already given
                # takes the room this high by itself.
                return {
                    "code": "inertia",
                    "value": round(from_celsius(self.inertia_stop, house.unit), 1),
                }
            return {
                "code": "hysteresis",
                "value": round(
                    delta_from_celsius(float(self.config[CONF_HYSTERESIS]), house.unit), 2
                ),
            }
        states = [st for eid in self.climates if valid(st := self.hass.states.get(eid))]
        if states and all(st.state == STATE_OFF for st in states):  # type: ignore[union-attr]
            return {"code": "device_off"}
        return {"code": "tolerance"}

    def devices(self) -> list[list[str]]:
        """The entities the room uses, each with its role: [entity_id, role] (for the card)."""
        cfg = self.config
        groups = (
            ("thermostat", self.climates),
            ("switch", self.switches),
            ("temperature", as_list(cfg.get(CONF_TEMP_SENSORS))),
            ("humidity", as_list(cfg.get(CONF_HUMIDITY_SENSOR))),
            ("window", as_list(cfg.get(CONF_WINDOW_SENSORS))),
            ("window_linked", as_list(cfg.get(CONF_LINKED_WINDOW_SENSORS))),
            ("occupancy", as_list(cfg.get(CONF_OCCUPANCY_SENSORS))),
            ("calibration", as_list(cfg.get(CONF_CALIBRATION_ENTITIES))),
        )
        seen: set[str] = set()
        result: list[list[str]] = []
        for role, entity_ids in groups:
            for entity_id in entity_ids:
                if entity_id and entity_id not in seen:
                    seen.add(entity_id)
                    result.append([entity_id, role])
        return result

    def diagnostics(self) -> dict[str, Any]:
        """Diagnostics for this room."""
        return {
            "id": self.id,
            "config": self.config,
            "rule": self.rule,
            "decision": self.decision.as_dict() if self.decision else None,
            "current_temperature": self.current_temp,
            "target_temperature": self.target_temperature,
            "heat_demand": self.heat_demand,
            "kept_open": self.kept_open,
            "topped_up": self.topped_up,
            "window_open": self.window_open,
            "override": self.override_info(),
            "schedule_error": self.schedule_error,
            "schedule_state": (
                {
                    "preset": self.schedule_state.preset,
                    "profile": self.schedule_state.profile,
                    "next_change": iso(self.schedule_state.next_change),
                    "next_preset": self.schedule_state.next_preset,
                }
                if self.schedule_state
                else None
            ),
            "levels": {p: self.level_temp(p) for p in PRESETS},
            "thermal_model": self._model_info(),
            "runtime_hours": round(self.runtime_s / 3600, 2),
            "decisions": list(self.decisions),
        }

    def _model_info(self) -> dict[str, Any]:
        """The learned thermal model (°C), for the diagnostics."""
        learner, model = self.learner, self.learner.model
        return {
            "learned": model.learned,
            "heating_per_hour": model.h,
            "weather_curve": model.c,
            "sun_gain": model.s,
            "loss": model.k,
            "constant_loss": model.constant_loss,
            "inertia_minutes": model.tau,
            "heat_reaching_now": round(learner.q, 3),
            "error_per_hour": None if learner.error is None else round(learner.error, 3),
            "heating_stretches": round(learner.heat_windows, 1),
            "idle_stretches": round(learner.idle_windows, 1),
            "outdoor_mean": model.outdoor_mean,
            "candidates": [
                {
                    "inertia_minutes": fit.tau,
                    "heating_per_hour": None if (sol := fit.solve()) is None else round(sol[0], 4),
                    "loss": None if sol is None else round(sol[1], 5),
                    "weather_curve": None if sol is None else round(sol[2], 5),
                    "sun_gain": None if sol is None else round(sol[3], 4),
                    "sun_seen": round(fit.a44, 3),
                    "outdoor_spread": round(fit.spread(), 2),
                    "error": round(fit.error / fit.weight, 5) if fit.weight > 0 else None,
                }
                for fit in learner.fits
            ],
        }
