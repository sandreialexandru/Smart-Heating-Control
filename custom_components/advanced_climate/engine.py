"""Decision engine (pure Python, no Home Assistant imports).

For every room the rules are evaluated from the top down; the first rule that
applies sets the target. Final adjustments (weather, tariff, solar gain) can
move a heating target by a few tenths of a degree and the result always goes
through the safety limits.

Rule order:
 1. safety (frost protection / maximum temperature) - always applied last,
    also to a manual change and in pause
 2. pause
 3. valve exercise (in every mode, not with a window open)
 4. global mode Off / Summer / out of season
 5. window open
 6. manual override
 7. vacation
 8. presence (far -> away, nearby -> eco or a fixed temperature)
 9. schedule (with optimal start / stop and room occupancy)
 Adjustments: outdoor cutoff, compensation, tariff, PV, solar gain.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .const import (
    MODE_OFF,
    MODE_SUMMER,
    MODE_VACATION,
    NEARBY_TEMPERATURE,
    PRESENCE_FAR,
    PRESENCE_NEARBY,
    PRESET_AWAY,
    PRESET_ECO,
    PRESET_FROST,
    RULE_CUTOFF,
    RULE_FAR,
    RULE_MAX,
    RULE_MODE_OFF,
    RULE_NEARBY,
    RULE_OPTIMAL_START,
    RULE_OPTIMAL_STOP,
    RULE_OUT_OF_SEASON,
    RULE_OVERRIDE,
    RULE_PAUSE,
    RULE_SAFETY,
    RULE_SCHEDULE,
    RULE_SENSOR_FALLBACK,
    RULE_SUMMER,
    RULE_UNOCCUPIED,
    RULE_VACATION,
    RULE_VALVE_EXERCISE,
    RULE_WINDOW,
    WINDOW_ACTION_OFF,
)

KIND_PRESET = "preset"
KIND_TEMPERATURE = "temperature"
KIND_OFF = "off"
KIND_NONE = "none"  # do not send any command

MAX_TOTAL_OFFSET = 3.0


def fmt_temp(value: float, unit: str = "°C") -> str:
    """A temperature (kept in °C) as text in the unit of the house."""
    if str(unit).strip().lower().endswith("f"):
        return f"{value * 1.8 + 32:.1f} °F"
    return f"{value:.1f} °C"


def fmt_delta(value: float, unit: str = "°C") -> str:
    """A temperature difference (kept in °C) as text in the unit of the house."""
    if str(unit).strip().lower().endswith("f"):
        value *= 1.8
    return f"{value:+.1f}"


@dataclass(slots=True)
class Target:
    """What the room should be set to."""

    kind: str
    preset: str | None = None
    temperature: float | None = None

    def as_dict(self) -> dict:
        """Serialize."""
        return {"kind": self.kind, "preset": self.preset, "temperature": self.temperature}

    def describe(self, unit: str = "°C") -> str:
        """Short text form."""
        if self.kind == KIND_PRESET:
            return f"preset {self.preset}"
        if self.kind == KIND_TEMPERATURE:
            label = f" ({self.preset})" if self.preset else ""
            return f"{fmt_temp(self.temperature or 0.0, unit)}{label}"
        if self.kind == KIND_OFF:
            return "off"
        return "no command"


@dataclass(slots=True)
class RoomInputs:
    """Everything the engine needs to decide for one room."""

    now: datetime
    mode: str
    paused: bool
    season_active: bool
    cutoff_active: bool
    valve_exercise: bool
    window_open: bool
    window_action: str
    override_active: bool
    vacation_active: bool
    presence: str
    arriving: bool
    room_unoccupied: bool
    sensor_failed: bool
    schedule_preset: str | None
    schedule_rule: str
    current_temp: float | None
    frost_temp: float
    max_temp: float
    nearby_mode: str
    nearby_temp: float | None
    level_temp: Callable[[str], float | None]
    offsets: list[tuple[str, float]] = field(default_factory=list)
    supports_off: bool = True
    exercise_temp: float | None = None
    # Highest temperature set on the thermostats now (a manual change keeps it).
    device_setpoint: float | None = None
    # Relays and thermostats commanded with hvac_mode: no set temperature to read,
    # the room temperature is checked against the maximum instead.
    on_off: bool = False
    # Nearby never above the schedule (the lower of the two applies).
    nearby_limit: bool = False
    unit: str = "°C"  # only for the texts; every value is in °C
    # The last hours of a vacation: the schedule applies, so the house is warm on return.
    vacation_preheat: bool = False
    # Frost protection is heating: it continues until the device stops asking for heat.
    frost_holding: bool = False


@dataclass(slots=True)
class Decision:
    """The result of the engine."""

    rule: str
    target: Target
    description: str
    offsets: list[tuple[str, float]] = field(default_factory=list)
    # The reason as a key and its values (temperatures in °C), so the card can
    # show it in its language; ``description`` is the English text.
    key: str = ""
    params: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        """Serialize."""
        return {
            "rule": self.rule,
            "target": self.target.as_dict(),
            "description": self.description,
            "offsets": [list(o) for o in self.offsets],
        }


def _heating(target: Target) -> bool:
    """True for targets that heat (a preset or a temperature)."""
    return target.kind in (KIND_PRESET, KIND_TEMPERATURE)


def _off(inputs: RoomInputs) -> Target:
    """Heating off, or frost temperature when the device cannot be turned off."""
    if inputs.supports_off:
        return Target(KIND_OFF)
    return Target(KIND_TEMPERATURE, temperature=inputs.frost_temp)


def base_decision(inputs: RoomInputs) -> Decision:
    """Evaluate rules 2-9 (without adjustments and safety)."""
    if inputs.paused:
        return Decision(RULE_PAUSE, Target(KIND_NONE), "Paused: only safety commands are sent", key="pause")
    # The valves are exercised in every mode (above all in summer), but not
    # with a window open.
    if inputs.valve_exercise and not inputs.window_open:
        return Decision(
            RULE_VALVE_EXERCISE,
            Target(
                KIND_TEMPERATURE,
                temperature=inputs.exercise_temp
                if inputs.exercise_temp is not None
                else inputs.max_temp,
            ),
            "Valve exercise: valves fully open for a few minutes",
            key="valve_exercise",
        )
    if inputs.mode == MODE_OFF:
        return Decision(
            RULE_MODE_OFF,
            Target(KIND_TEMPERATURE, temperature=inputs.frost_temp),
            "Mode off: frost protection only",
            key="mode_off",
        )
    if inputs.mode == MODE_SUMMER:
        return Decision(RULE_SUMMER, _off(inputs), "Summer mode: heating off", key="summer")
    if not inputs.season_active:
        return Decision(
            RULE_OUT_OF_SEASON, _off(inputs), "Outside the heating season: heating off",
            key="out_of_season",
        )
    if inputs.window_open:
        if inputs.window_action == WINDOW_ACTION_OFF:
            return Decision(RULE_WINDOW, _off(inputs), "Window open: heating off", key="window_off")
        return Decision(
            RULE_WINDOW,
            Target(KIND_TEMPERATURE, temperature=inputs.frost_temp),
            "Window open: frost protection",
            key="window_frost",
        )
    if inputs.override_active:
        return Decision(
            RULE_OVERRIDE, Target(KIND_NONE), "Manual change is respected", key="override"
        )
    if inputs.mode == MODE_VACATION or inputs.vacation_active:
        # A day without an active profile is frost protection: above away.
        if inputs.schedule_preset == PRESET_FROST:
            return _no_profile(inputs)
        return Decision(
            RULE_VACATION, Target(KIND_PRESET, preset=PRESET_AWAY), "Vacation", key="vacation"
        )
    if not inputs.arriving and not inputs.vacation_preheat:
        if inputs.presence == PRESENCE_FAR:
            if inputs.schedule_preset == PRESET_FROST:
                return _no_profile(inputs)
            return Decision(
                RULE_FAR,
                Target(KIND_PRESET, preset=PRESET_AWAY),
                "Everyone is far away (outside the nearby zones)",
                key="far",
            )
        if inputs.presence == PRESENCE_NEARBY:
            fixed = inputs.nearby_mode == NEARBY_TEMPERATURE and inputs.nearby_temp is not None
            near = inputs.nearby_temp if fixed else inputs.level_temp(PRESET_ECO)
            scheduled = _schedule_temp(inputs)
            if (
                inputs.nearby_limit
                and near is not None
                and scheduled is not None
                and scheduled < near
            ):
                # Not above the schedule: the schedule is lower, it applies.
                if inputs.schedule_preset == PRESET_FROST:
                    return _no_profile(inputs)
                return Decision(
                    RULE_NEARBY,
                    Target(KIND_PRESET, preset=inputs.schedule_preset),
                    f"Nobody home, someone nearby: the schedule ({inputs.schedule_preset}) is lower",
                    key="nearby_schedule",
                    params={"preset": inputs.schedule_preset},
                )
            if fixed:
                return Decision(
                    RULE_NEARBY,
                    Target(KIND_TEMPERATURE, temperature=inputs.nearby_temp),
                    "Nobody home, someone nearby: fixed temperature",
                    key="nearby_temperature",
                    params={"temperature": inputs.nearby_temp},
                )
            return Decision(
                RULE_NEARBY,
                Target(KIND_PRESET, preset=PRESET_ECO),
                "Nobody home, someone nearby",
                key="nearby",
            )
    arriving = (
        " (vacation ends soon: preheating)"
        if inputs.vacation_preheat
        else " (someone is on the way home)"
        if inputs.arriving
        else ""
    )
    if inputs.schedule_preset is None:
        return Decision(RULE_SCHEDULE, Target(KIND_NONE), "No schedule available", key="no_schedule")
    if inputs.schedule_preset == PRESET_FROST:
        return _no_profile(inputs)
    preset = inputs.schedule_preset
    if inputs.sensor_failed:
        # Eco until they recover, but never above the schedule.
        if _warmer(inputs, preset, PRESET_ECO):
            return Decision(
                RULE_SENSOR_FALLBACK,
                Target(KIND_PRESET, preset=PRESET_ECO),
                "Temperature sensors unavailable: eco until they recover",
                key="sensor_fallback",
            )
        return Decision(
            RULE_SENSOR_FALLBACK,
            Target(KIND_PRESET, preset=preset),
            f"Temperature sensors unavailable: the schedule ({preset}), lower than eco",
            key="sensor_fallback_schedule",
            params={"preset": preset},
        )
    if inputs.room_unoccupied and _warmer(inputs, preset, PRESET_ECO):
        return Decision(
            RULE_UNOCCUPIED,
            Target(KIND_PRESET, preset=PRESET_ECO),
            f"Room unoccupied (schedule: {preset})",
            key="unoccupied",
            params={"preset": preset},
        )
    descriptions = {
        RULE_SCHEDULE: f"Schedule: {preset}",
        RULE_OPTIMAL_START: f"Optimal start: heating early for {preset}",
        RULE_OPTIMAL_STOP: f"Optimal stop: lowering early to {preset}",
    }
    keys = {RULE_OPTIMAL_START: "optimal_start", RULE_OPTIMAL_STOP: "optimal_stop"}
    params: dict = {"preset": preset}
    if inputs.vacation_preheat:
        params["extra"] = "vacation_preheat"
    elif inputs.arriving:
        params["extra"] = "arriving"
    return Decision(
        inputs.schedule_rule,
        Target(KIND_PRESET, preset=preset),
        descriptions.get(inputs.schedule_rule, f"Schedule: {preset}") + arriving,
        key=keys.get(inputs.schedule_rule, "schedule"),
        params=params,
    )


def _no_profile(inputs: RoomInputs) -> Decision:
    """No active profile covers this day: frost protection only."""
    return Decision(
        RULE_SCHEDULE,
        Target(KIND_TEMPERATURE, temperature=inputs.frost_temp),
        "No active schedule profile for this day: frost protection",
        key="no_profile",
    )


def _schedule_temp(inputs: RoomInputs) -> float | None:
    """Temperature the schedule asks for now (None without a schedule)."""
    if inputs.schedule_preset is None:
        return None
    if inputs.schedule_preset == PRESET_FROST:
        return inputs.frost_temp
    return inputs.level_temp(inputs.schedule_preset)


def _warmer(inputs: RoomInputs, preset: str, than: str) -> bool:
    """True when ``preset`` is warmer than ``than`` (by name when a temperature is unknown)."""
    a = inputs.level_temp(preset)
    b = inputs.level_temp(than)
    if a is None or b is None:
        return preset not in (than, PRESET_AWAY)
    return a > b


def decide(inputs: RoomInputs) -> Decision:
    """Run the full decision: rules, adjustments, safety."""
    decision = base_decision(inputs)
    target = decision.target

    # Frost protection for a day without an active profile is not adjusted,
    # like the other frost protections.
    adjustable = decision.rule not in (
        RULE_PAUSE,
        RULE_MODE_OFF,
        RULE_VALVE_EXERCISE,
        RULE_WINDOW,
        RULE_OVERRIDE,
        # Heating off (frost protection on a device that cannot be turned off).
        RULE_SUMMER,
        RULE_OUT_OF_SEASON,
    ) and decision.key != "no_profile"
    # Outdoor cutoff: heating is not needed when it is warm outside.
    if adjustable and inputs.cutoff_active and _heating(target):
        decision = Decision(
            RULE_CUTOFF,
            _off(inputs),
            f"Warm outside: heating off (would be {target.describe(inputs.unit)})",
            key="cutoff",
            params={
                "preset": target.preset,
                "temperature": target.temperature
                if target.kind == KIND_TEMPERATURE
                else inputs.level_temp(target.preset or ""),
            },
        )
        target = decision.target
    elif adjustable and _heating(target) and inputs.offsets:
        total = sum(delta for _label, delta in inputs.offsets)
        total = max(-MAX_TOTAL_OFFSET, min(MAX_TOTAL_OFFSET, total))
        if abs(total) >= 0.05:
            base = (
                target.temperature
                if target.kind == KIND_TEMPERATURE
                else inputs.level_temp(target.preset or "")
            )
            if base is not None:
                target = Target(
                    KIND_TEMPERATURE,
                    preset=target.preset,
                    temperature=round(base + total, 1),
                )
                labels = ", ".join(
                    f"{label} {fmt_delta(delta, inputs.unit)}" for label, delta in inputs.offsets
                )
                decision = Decision(
                    decision.rule,
                    target,
                    f"{decision.description} ({labels})",
                    list(inputs.offsets),
                    key=decision.key,
                    params=decision.params,
                )

    return apply_safety(decision, inputs)


def apply_safety(decision: Decision, inputs: RoomInputs) -> Decision:
    """Clamp to the safety limits and enforce frost protection."""
    target = decision.target
    frost, maximum = inputs.frost_temp, inputs.max_temp
    if target.kind == KIND_TEMPERATURE and target.temperature is not None:
        clamped = min(max(target.temperature, frost), maximum)
        if decision.rule == RULE_VALVE_EXERCISE:
            clamped = target.temperature
        if clamped != target.temperature:
            target = Target(KIND_TEMPERATURE, preset=target.preset, temperature=clamped)
            decision = Decision(
                decision.rule,
                target,
                f"{decision.description} (limited to {fmt_temp(clamped, inputs.unit)})",
                decision.offsets,
                key=decision.key,
                params={**decision.params, "limited": clamped},
            )
        return decision
    if target.kind == KIND_PRESET:
        level = inputs.level_temp(target.preset or "")
        if level is not None and level > maximum:
            return Decision(
                RULE_MAX,
                Target(KIND_TEMPERATURE, preset=target.preset, temperature=maximum),
                f"Maximum temperature ({target.preset} is above {fmt_temp(maximum, inputs.unit)})",
                key="max_level",
                params={"preset": target.preset, "max": maximum},
            )
        if level is not None and level < frost:
            return Decision(
                RULE_SAFETY,
                Target(KIND_TEMPERATURE, preset=target.preset, temperature=frost),
                f"Frost protection ({target.preset} is below {fmt_temp(frost, inputs.unit)})",
                key="frost_level",
                params={"preset": target.preset, "frost": frost},
            )
        return decision
    # No command (manual change, pause): the maximum temperature still applies
    # to what is set on the thermostats.
    if (
        target.kind == KIND_NONE
        and inputs.device_setpoint is not None
        and inputs.device_setpoint > maximum
    ):
        return Decision(
            RULE_MAX,
            Target(KIND_TEMPERATURE, temperature=maximum),
            f"Maximum temperature: {fmt_temp(inputs.device_setpoint, inputs.unit)} is above "
            f"{fmt_temp(maximum, inputs.unit)}",
            key="max_device",
            params={"value": inputs.device_setpoint, "max": maximum},
        )
    # No command for a relay / hvac_mode room (manual change, pause): it is turned
    # off while the room is at the maximum or above. Below it nothing is sent
    # again, so it stays off (it does not heat back up to the maximum).
    if (
        target.kind == KIND_NONE
        and inputs.on_off
        and inputs.current_temp is not None
        and inputs.current_temp >= maximum
    ):
        return Decision(
            RULE_MAX,
            _off(inputs),
            f"Maximum temperature: the room is {fmt_temp(inputs.current_temp, inputs.unit)}, "
            f"at or above {fmt_temp(maximum, inputs.unit)}",
            key="max_room",
            params={"current": inputs.current_temp, "max": maximum},
        )
    # Off or no command: protect against frost. Once started it continues while the
    # device still heats, so it does not switch on and off around the limit.
    if inputs.current_temp is not None and (inputs.current_temp < frost or inputs.frost_holding):
        text = (
            f"Frost protection: {fmt_temp(inputs.current_temp, inputs.unit)} is below "
            f"{fmt_temp(frost, inputs.unit)}"
            if inputs.current_temp < frost
            else f"Frost protection: heating up to {fmt_temp(frost, inputs.unit)}"
        )
        return Decision(
            RULE_SAFETY,
            Target(KIND_TEMPERATURE, temperature=frost),
            text,
            key="frost_below" if inputs.current_temp < frost else "frost_holding",
            params={"current": inputs.current_temp, "frost": frost},
        )
    return decision


def optimal_stop_state(
    started: bool, cancelled: bool, current_temp: float | None, floor: float | None
) -> tuple[bool, bool, bool]:
    """Return (allowed, started, cancelled) for the optimal stop of one change.

    ``floor`` is the comfort of the current level (level minus tolerance). An
    optimal stop that began is cancelled when the room falls below it, and does
    not start again before that change: the current level stays until the
    scheduled time. While the room is below it no optimal stop starts.
    """
    below = current_temp is not None and floor is not None and current_temp < floor
    if cancelled or (started and below):
        return False, False, True
    return not below, started, False


# Passes over the optimal start / stop period to match it to the expected weather.
ESTIMATE_PASSES = 3


def optimal_period(
    limit: float,
    minutes_for: Callable[[float | None], float | None],
    outdoor_for: Callable[[float], tuple[float | None, str]],
    outdoor_now: float | None,
    passes: int = ESTIMATE_PASSES,
) -> tuple[float, float | None, str]:
    """Length of an optimal start / stop and the outdoor temperature it was found with.

    ``minutes_for(outdoor)`` is the time needed at that outdoor temperature
    (None when not learned: the longest time, ``limit``, is used).
    ``outdoor_for(minutes)`` is the outdoor temperature expected during the
    last ``minutes`` before the change. The length depends on that temperature,
    so it is worked out again from the period found before, a few times.
    """
    outdoor, source = outdoor_now, "now"
    minutes = 0.0
    for index in range(passes):
        needed = minutes_for(outdoor)
        minutes = limit if needed is None else max(0.0, min(needed, limit))
        if minutes <= 0 or index == passes - 1:
            break
        found = outdoor_for(minutes)
        if found[0] is None or found == (outdoor, source):
            break
        outdoor, source = found
    return minutes, outdoor, source


def optimal_schedule(
    now: datetime,
    current_preset: str,
    next_change: datetime | None,
    next_preset: str | None,
    current_temp: float | None,
    level_temp: Callable[[str], float | None],
    start_needed: float | None,
    start_enabled: bool,
    start_max_minutes: float,
    stop_enabled: bool,
    stop_minutes: float,
    started: bool = False,
    stop_needed: float | None = None,
    stop_started: bool = False,
) -> tuple[str, str]:
    """Return (preset, rule) applying optimal start / stop.

    ``started`` / ``stop_started`` are True when the optimal start / stop for
    this change already began: it then continues until the change (no switching
    back and forth). The other rules can still override it.

    ``start_needed`` is how many minutes the room needs to heat up to the next
    level (from the learned heating); ``start_max_minutes`` caps it.

    ``stop_minutes`` is the longest optimal stop. ``stop_needed`` is how long the
    room can cool and still stay in the comfort of the current level (from the
    learned cooling); before any cooling is learned the longest stop is used.
    """
    if next_change is None or next_preset is None or next_change <= now:
        return current_preset, RULE_SCHEDULE
    now_temp = level_temp(current_preset)
    next_temp = level_temp(next_preset)
    if now_temp is None or next_temp is None:
        return current_preset, RULE_SCHEDULE
    remaining = next_change - now
    if start_enabled and next_temp > now_temp and started:
        return next_preset, RULE_OPTIMAL_START
    if (
        start_enabled
        and next_temp > now_temp
        and current_temp is not None
        and current_temp < next_temp
        and start_needed is not None
        and start_needed > 0
    ):
        needed = timedelta(minutes=min(start_needed, start_max_minutes))
        if remaining <= needed:
            return next_preset, RULE_OPTIMAL_START
    if stop_enabled and next_temp < now_temp:
        if stop_started:
            return next_preset, RULE_OPTIMAL_STOP
        window = stop_minutes if stop_needed is None else min(stop_needed, stop_minutes)
        if window > 0 and remaining <= timedelta(minutes=window):
            return next_preset, RULE_OPTIMAL_STOP
    return current_preset, RULE_SCHEDULE
