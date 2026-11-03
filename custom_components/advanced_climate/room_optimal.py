"""Optimal start and stop of a room.

The band of its prediction, the Generic Thermostat tolerances and the time to
the target.

Part of :class:`~.room.Room` (a mixin): the methods use the state the room
keeps (``self``), set up in ``Room.__init__``.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.util import dt as dt_util

from .const import (
    COMMAND_HVAC,
    CONF_HYSTERESIS,
    CONF_INERTIA_CONTROL,
    CONF_OPTIMAL_START,
    CONF_OPTIMAL_START_MAX,
    CONF_OPTIMAL_STOP,
    CONF_OPTIMAL_STOP_MINUTES,
    CONF_STOP_TOLERANCE,
    RULE_OPTIMAL_START,
    RULE_OPTIMAL_STOP,
    SOURCE_GT,
    SOURCE_SWITCH,
)
from .engine import (
    KIND_OFF,
    optimal_period,
)
from .learning import MAX_MINUTES, SunAhead
from .schedule import (
    ScheduleState,
)
from .util import (
    delta_to_celsius,
    system_unit,
    valid,
)

if TYPE_CHECKING:
    from .house import House


class RoomOptimal:
    """Optimal start and stop of a room (mixin of the room)."""

    house: House

    def _gt_cold_tolerance(self) -> float:
        """The cold tolerance of the Generic Thermostat of the room (°C), 0 when unknown."""
        value = self._gt_tolerance("cold_tolerance")
        return 0.0 if value is None else value

    def _gt_tolerance(self, key: str) -> float | None:
        """A tolerance of the Generic Thermostat of the room (°C), None when it cannot be read.

        Only a Generic Thermostat set up in the user interface has its settings
        in a config entry; one from YAML does not say.
        """
        value = self._gt_options().get(key)
        if value is None:
            return None
        try:
            return float(delta_to_celsius(float(value), system_unit(self.hass)))
        except (TypeError, ValueError):
            return None

    def prediction_band(self) -> tuple[float, float, bool] | None:
        """How the heating of the room is switched around the target, for the prediction.

        (°C below the target where it starts, °C above where it stops, whether
        the learned inertia starts and stops it inside). Generic Thermostat:
        its cold and hot tolerance (None when they cannot be read: not known);
        relays,
        on / off control and the TRV boost: the hysteresis, with the learned
        inertia when on; thermostats without hvac_action: the hysteresis. None
        for the other thermostats and TRVs: they regulate by themselves, with a
        band nobody knows, and hold the target.
        """
        if self.source == SOURCE_GT:
            cold = self._gt_tolerance("cold_tolerance")
            hot = self._gt_tolerance("hot_tolerance")
            return None if cold is None or hot is None else (cold, hot, False)
        hysteresis = float(self.config[CONF_HYSTERESIS])
        if self.source == SOURCE_SWITCH or self.command_mode == COMMAND_HVAC or self.boost:
            return hysteresis, hysteresis, bool(self.config.get(CONF_INERTIA_CONTROL, True))
        if self.lacks_hvac_action():
            return hysteresis, hysteresis, False
        return None

    def stop_tolerance(self) -> float:
        """How far below a level the room may fall during an optimal stop (its comfort)."""
        if self.source == SOURCE_GT:
            return self._gt_cold_tolerance()
        if (
            self.source == SOURCE_SWITCH
            or self.command_mode == COMMAND_HVAC
            or self.boost
            or self.lacks_hvac_action()
        ):
            return float(self.config[CONF_HYSTERESIS])
        return float(self.config.get(CONF_STOP_TOLERANCE, 0.0))

    def lacks_hvac_action(self) -> bool:
        """A thermostat of the room does not report hvac_action (or cannot be checked now).

        Such thermostats are handled like relays: their heat demand and the
        comfort of the optimal stop use the hysteresis.
        """
        return any(
            not valid(state := self.hass.states.get(entity_id))
            or "hvac_action" not in state.attributes  # type: ignore[union-attr]
            for entity_id in self.climates
        )

    def comfort_floor(self, preset: str) -> float | None:
        """Lowest temperature still in the comfort of ``preset`` (optimal stop)."""
        level = self.level_temp(preset)
        return None if level is None else level - max(0.0, self.stop_tolerance())

    def stop_needed(self, preset: str, outdoor: float | None) -> float | None:
        """Minutes the room can cool and stay in the comfort of ``preset``.

        None before any cooling is learned (the longest optimal stop is used).
        """
        floor = self.comfort_floor(preset)
        if floor is None or self.current_temp is None:
            return None
        return self.learner.model.minutes_to_fall(
            self.current_temp,
            floor,
            outdoor,
            self.learner.q,
            self.house.sun_ahead(dt_util.utcnow()),
        )

    def optimal_estimate(
        self, now: datetime, state: ScheduleState, outdoor_known: bool, stop_allowed: bool
    ) -> dict[str, Any] | None:
        """When the optimal start / stop for the next change begins, and with what.

        The outdoor temperature is the one expected while it runs (hourly
        forecast), else the one of now. The period depends on that temperature,
        so it is worked out again a few times from the period found before.
        """
        change, next_preset = state.next_change, state.next_preset
        if change is None or next_preset is None or change <= now or self.current_temp is None:
            return None
        now_temp = self.level_temp(state.preset)
        next_temp = self.level_temp(next_preset)
        if now_temp is None or next_temp is None:
            return None
        house = self.house
        if next_temp > now_temp and self.config[CONF_OPTIMAL_START]:
            kind = RULE_OPTIMAL_START
            limit = float(self.config[CONF_OPTIMAL_START_MAX])
        elif (
            next_temp < now_temp
            and self.config[CONF_OPTIMAL_STOP]
            and outdoor_known
            and stop_allowed
        ):
            kind = RULE_OPTIMAL_STOP
            limit = float(self.config[CONF_OPTIMAL_STOP_MINUTES])
        else:
            return None
        gap = next_temp - self.current_temp
        floor = self.comfort_floor(state.preset)
        # The period starts now at first, then as long before the change as
        # found before: the sun of that time of day is counted.
        begins = [now]

        def minutes_for(outdoor: float | None) -> float | None:
            model, q = self.learner.model, self.learner.q
            sun = house.sun_ahead(begins[0])
            if kind == RULE_OPTIMAL_START:
                if gap <= 0:
                    return 0.0
                return self._minutes_to_heat(next_temp, outdoor, sun)
            if floor is None:
                return None
            return model.minutes_to_fall(self.current_temp, floor, outdoor, q, sun)

        def outdoor_for(length: float) -> tuple[float | None, str]:
            begins[0] = max(now, change - timedelta(minutes=length))
            return house.outdoor_between(change - timedelta(minutes=length), change)

        minutes, outdoor, source = optimal_period(
            limit, minutes_for, outdoor_for, house.outdoor_now
        )
        needed = minutes_for(outdoor)
        return {
            "kind": kind,
            "change": change,
            "preset": next_preset,
            "minutes": minutes,
            "needed": needed,
            "outdoor": outdoor,
            "outdoor_source": source,
            "learned": self.learner.model.learned,
        }

    def stop_forecast(self, now: datetime) -> dict[str, Any] | None:
        """During an optimal stop: the expected temperature at the scheduled change."""
        state = self.schedule_state
        if (
            self.decision is None
            or self.decision.rule != RULE_OPTIMAL_STOP
            or state is None
            or state.next_change is None
            or self.current_temp is None
        ):
            return None
        minutes = max(0.0, (state.next_change - now).total_seconds() / 60)
        outdoor, _ = self.house.outdoor_between(now, state.next_change)
        model = self.learner.model
        if not model.learned:
            return None
        value = model.simulate(
            self.current_temp, outdoor, self.learner.q, False, minutes, self.house.sun_ahead(now)
        )
        return {"at": state.next_change.isoformat(), "temperature": value}

    def _start_needed(
        self, preset: str | None, outdoor: float | None, now: datetime
    ) -> float | None:
        """Minutes the room needs to heat up to the level of ``preset`` (learned)."""
        if preset is None or self.current_temp is None:
            return None
        level = self.level_temp(preset)
        if level is None or level <= self.current_temp:
            return None
        return self._minutes_to_heat(level, outdoor, self.house.sun_ahead(now))

    def _minutes_to_heat(
        self, target: float, outdoor: float | None, sun: SunAhead | None = None
    ) -> float:
        """Minutes to heat up to ``target``; a whole day when the model never gets there.

        The heating may be too weak for that target at that outdoor
        temperature: the optimal start then begins as early as it may.
        """
        if self.current_temp is None:
            return float(MAX_MINUTES)
        minutes = self.learner.model.minutes_to_heat(
            self.current_temp, target, outdoor, self.learner.q, sun
        )
        return float(MAX_MINUTES) if minutes is None else minutes

    def time_to_target(self, outdoor: float | None) -> int | None:
        """Minutes until the target is reached, as learned (None when not heating up)."""
        if self.current_temp is None or self.target_temperature is None:
            return None
        if self.decision is None or self.decision.target.kind == KIND_OFF or self.window_open:
            return None
        gap = self.target_temperature - self.current_temp
        if gap <= 0:
            return None
        minutes = self.learner.model.minutes_to_heat(
            self.current_temp,
            self.target_temperature,
            outdoor,
            self.learner.q,
            self.house.sun_ahead(dt_util.utcnow()),
        )
        return None if minutes is None else max(1, round(minutes))
