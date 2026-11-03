"""Manual changes of a room.

Noticed on the devices or set from the card / service, how long they last and
what applies after them.

Part of :class:`~.room.Room` (a mixin): the methods use the state the room
keeps (``self``), set up in ``Room.__init__``.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.const import (
    ATTR_TEMPERATURE,
    STATE_OFF,
)
from homeassistant.core import Event, State
from homeassistant.util import dt as dt_util

from .const import (
    CONF_OVERRIDE_HOURS,
    CONF_OVERRIDE_MODE,
    OVERRIDE_FIXED,
    OVERRIDE_NEXT,
    PRESET_NONE,
    RULE_VACATION,
)
from .engine import (
    KIND_PRESET,
    KIND_TEMPERATURE,
    Target,
)
from .room_common import (
    device_values,
)
from .util import (
    climate_temp,
    from_celsius,
    iso,
    system_unit,
    to_celsius,
    valid,
)

if TYPE_CHECKING:
    from .house import House

# The same logger as the rest of the room, so the log lines keep their name.
_LOGGER = logging.getLogger(__name__.rsplit(".", 1)[0] + ".room")


class RoomOverride:
    """Manual changes of a room (mixin of the room)."""

    house: House

    def _remember_preset_temp(self, state: State | None) -> None:
        """Learn the temperatures of the thermostat presets from the climate state."""
        if not valid(state):
            return
        preset = self.level_of_device_preset(state.attributes.get("preset_mode"))  # type: ignore[union-attr]
        temperature = climate_temp(self.hass, state, ATTR_TEMPERATURE)
        if preset is not None and temperature is not None:
            self.observed_temps[preset] = temperature

    def _is_manual_change(self, event: Event, old: State | None, new: State | None) -> bool:
        """True when a person changed the thermostat (not the integration, nor a late confirmation)."""
        if old is None or new is None or not valid(old) or not valid(new):
            return False
        if self.house.is_own_context(event.context):
            return False
        if not self.house.started:
            return False
        if self.sent.is_echo(event.data["entity_id"], old, new, dt_util.utcnow()):
            return False
        if old.state != new.state:
            return True
        for attr in ("preset_mode", ATTR_TEMPERATURE):
            if old.attributes.get(attr) != new.attributes.get(attr):
                return True
        return False

    def _handle_manual_change(self, entity_id: str, new: State | None) -> None:
        """Respect a manual change (or revert it with the child lock)."""
        # From now on the device shows a person's values, not ours: if the person
        # later sets the value we sent before, that is a manual change too.
        self.sent.forget(entity_id)
        self._boosted = False  # the person's value replaced the boost
        # In a pause the change is kept (it applies after the pause); the child
        # lock does not undo it then, since a pause sends nothing.
        if self.child_lock and self.decision is not None and not self.house.paused:
            _LOGGER.debug("Room %s: child lock reverts a manual change", self.name)
            self.hass.async_create_task(self._async_apply(self.decision.target, force=True))
            return
        description = "manual change"
        if new is not None:
            if new.state == STATE_OFF:
                description = "turned off"
            elif new.attributes.get("preset_mode") not in (None, PRESET_NONE):
                description = f"preset {new.attributes.get('preset_mode')}"
            elif (value := climate_temp(self.hass, new, ATTR_TEMPERATURE)) is not None:
                unit = self.house.unit
                description = f"{from_celsius(value, unit):.1f} {unit}"
            elif entity_id in self.switches:
                description = f"switch {new.state}"
        # What the person set is kept, to set it again after an interruption
        # (a window opened, frost protection).
        devices = {entity_id: device_values(new)} if new is not None else None
        if self.house.override_scope_house:
            for room in self.house.rooms.values():
                room.set_override(
                    description, source=self.name, devices=devices if room is self else None
                )
        else:
            self.set_override(description, devices=devices)

    def set_override(
        self,
        description: str,
        *,
        source: str | None = None,
        hours: float | None = None,
        target: Target | None = None,
        devices: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        """Start a manual override.

        ``target`` is a level or temperature set by the card or a service: it is
        sent while the manual change applies. ``devices`` are the values a
        person set on the devices: they are only set again after an
        interruption (a higher rule changed the devices meanwhile).
        """
        now = dt_util.utcnow()
        kept: dict[str, dict[str, Any]] = {}
        if target is None and self.override and not self.override.get("target"):
            # Another device of the room changed by hand: keep the earlier ones too.
            kept = dict(self.override.get("devices") or {})
        kept.update(devices or {})
        mode = self.house.options[CONF_OVERRIDE_MODE]
        if hours is None and mode == OVERRIDE_FIXED:
            hours = float(self.house.options[CONF_OVERRIDE_HOURS])
        until = now + timedelta(hours=hours) if hours else None
        self.override = {
            "description": description if source is None else f"{description} ({source})",
            "since": now,
            "until": until,
            "mode": OVERRIDE_FIXED if until else OVERRIDE_NEXT,
            "signature": list(self.signature) if self.signature else None,
            "target": target.as_dict() if target else None,
            "devices": kept if target is None else {},
            "interrupted": False,
            # A change made on a device is already there; one from the card or
            # a service is sent when the manual change applies.
            "applied": target is None,
        }
        self.house.async_save()

    def clear_override(self) -> None:
        """Clear the manual override."""
        self.override = None
        self.house.async_save()

    def _check_override(self, now: datetime, signature: tuple) -> None:
        """End the manual change when its time is over or something relevant changed."""
        if self.override is None:
            return
        until = self.override.get("until")
        if until is not None:
            if now >= until:
                self.override = None
            return
        stored = self.override.get("signature")
        if stored is None:
            self.override["signature"] = list(signature)
        elif tuple(stored) != tuple(signature):
            # Something relevant changed: the override ends.
            self.override = None

    def _override_target(self) -> Target | None:
        """Level or temperature of a manual change set by the card or a service."""
        stored = (self.override or {}).get("target")
        if not isinstance(stored, dict) or stored.get("kind") not in (
            KIND_TEMPERATURE,
            KIND_PRESET,
        ):
            return None
        return Target(
            stored["kind"], preset=stored.get("preset"), temperature=stored.get("temperature")
        )

    # ------------------------------------------------------------------
    # Diagnostics / attributes
    # ------------------------------------------------------------------
    def override_info(self) -> dict[str, Any] | None:
        """Override details for attributes."""
        if not self.override:
            return None
        return {
            "description": self.override.get("description"),
            "since": iso(self.override.get("since")),
            "until": iso(self.override.get("until")),
            "mode": self.override.get("mode"),
            # Set by the card / a service, or on the device itself.
            "origin": "card" if self.override.get("target") else "device",
            "devices": list((self.override.get("devices") or {}).keys()),
            # A higher rule changed the devices: the manual value comes back after it.
            "interrupted": bool(self.override.get("interrupted")),
            # False while a higher rule has kept it from the devices so far.
            "applied": bool(self.override.get("applied", True)),
            # What the manual change holds (°C), also while a higher rule interrupts it.
            **self._override_level(),
        }

    def _override_level(self) -> dict[str, Any]:
        """Level and temperature (°C) a manual change holds, when known."""
        stored = self._override_target()
        if stored is not None:
            return {"preset": stored.preset, "temperature": self._resolve_temperature(stored)}
        for values in (self.override or {}).get("devices", {}).values():
            if values.get("state") == STATE_OFF:
                return {"preset": None, "temperature": None}
            level = self.level_of_device_preset(values.get("preset_mode"))
            if level is not None:
                return {"preset": level, "temperature": self.level_temp(level)}
            if values.get("temperature") is not None:
                try:
                    value = to_celsius(float(values["temperature"]), system_unit(self.hass))
                except (TypeError, ValueError):
                    continue
                return {"preset": None, "temperature": value}
        return {"preset": None, "temperature": None}

    def hold_until(self, now: datetime) -> datetime | None:
        """Until when the current level holds before the schedule applies, when known.

        A planned vacation ends when its preheating starts; a calendar event
        at its end. (The card plans the rest from the decision and the schedule.)
        """
        rule = self.decision.rule if self.decision else None
        if rule == RULE_VACATION:
            return self.house.vacation_until(now)
        end = self.house.calendar_end
        if self._calendar_preset() is not None and end is not None and end > now:
            return end
        return None
