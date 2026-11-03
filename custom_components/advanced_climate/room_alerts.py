"""Alerts of a room: mold risk, devices, windows, schedule, batteries.

Part of :class:`~.room.Room` (a mixin): the methods use the state the room
keeps (``self``), set up in ``Room.__init__``.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from homeassistant.core import callback
from homeassistant.helpers import (
    device_registry as dr,
)
from homeassistant.helpers import (
    entity_registry as er,
)

from .const import (
    CONF_ALERT_WINDOW_MINUTES,
    CONF_BATTERY_THRESHOLD,
    CONF_HUMIDITY_SENSOR,
    CONF_OCCUPANCY_SENSORS,
    CONF_SCHEDULE_HELPER,
    CONF_SCHEDULE_SOURCE,
    CONF_TEMP_SENSORS,
    CONF_WINDOW_SENSORS,
    MODE_OFF,
    MODE_SUMMER,
    SCHEDULE_HELPER,
)
from .mold import MOLD_CLEAR_RH, MOLD_MINUTES, MOLD_SURFACE_RH, surface_humidity
from .room_common import (
    FROST_ALERT_MARGIN,
)
from .schedule import (
    uncovered_days,
)
from .util import (
    as_list,
    finite,
    float_state,
    from_celsius,
    valid,
)

if TYPE_CHECKING:
    from .house import House


class RoomAlerts:
    """Alerts of a room (mixin of the room)."""

    house: House

    # ------------------------------------------------------------------
    # Alerts
    # ------------------------------------------------------------------
    def _check_mold(self, now: datetime) -> None:
        """Mold risk alert: only with a humidity sensor and a known outdoor temperature.

        Without a humidity sensor or without an outdoor source in the house
        there is no alert. While a value is unknown for a moment (a sensor
        unavailable), an alert already told stays as it is: ending it would
        tell that the risk is over, and it is not known.
        """
        house = self.house
        key = f"mold_{self.id}"
        humidity = float_state(self.hass, self.config.get(CONF_HUMIDITY_SENSOR))
        self.humidity = humidity if humidity is not None and 0 <= humidity <= 100 else None
        if not self.config.get(CONF_HUMIDITY_SENSOR) or not house.outdoor_configured:
            self.surface_humidity = None
            self._mold_since = None
            house.clear_alert(key)
            return
        outdoor = house.outdoor_now
        if (
            humidity is None
            or not 0 <= humidity <= 100
            or outdoor is None
            or self.current_temp is None
        ):
            self.surface_humidity = None
            self._mold_since = None
            return
        surface = surface_humidity(self.current_temp, humidity, outdoor)
        self.surface_humidity = round(surface, 1)
        if surface >= MOLD_SURFACE_RH:
            since = self._mold_since = self._mold_since or now
            if now - since >= timedelta(minutes=MOLD_MINUTES):
                house.notify(
                    key,
                    f"{self.name}: mold risk, the coldest wall is at about {surface:.0f}% "
                    f"humidity (room {humidity:.0f}%).",
                    code="mold_risk",
                    params={"surface": round(surface), "humidity": round(humidity)},
                    room=self.id,
                )
        elif surface < MOLD_CLEAR_RH:
            self._mold_since = None
            house.clear_alert(key)

    def _check_alerts(self, now: datetime) -> None:
        """Alerts for long open windows, unavailable devices, failed sensors and schedule errors."""
        house = self.house
        # Window open for too long while heating matters.
        if self.window_open and self.window.opened_at is not None:
            minutes = float(house.options[CONF_ALERT_WINDOW_MINUTES])
            heating_relevant = house.mode not in (MODE_OFF, MODE_SUMMER) and house.season_active
            if heating_relevant and now - self.window.opened_at >= timedelta(minutes=minutes):
                house.notify(
                    f"window_{self.id}",
                    f"{self.name}: a window has been open for more than {minutes:.0f} minutes.",
                    code="window_long",
                    params={"minutes": round(minutes)},
                    room=self.id,
                )
        # The room fell clearly below the frost protection temperature (the heating
        # cannot keep it); told once, until the room is back at it.
        frost = self.frost_temp()
        if self.current_temp is not None and self.current_temp <= frost - FROST_ALERT_MARGIN:
            unit = house.unit
            house.notify(
                f"frost_{self.id}",
                f"{self.name}: the room is below the frost protection temperature "
                f"({from_celsius(frost, unit):.1f} {unit}).",
                code="frost_protection",
                params={
                    "current": f"{from_celsius(self.current_temp, unit):.1f}",
                    "frost": f"{from_celsius(frost, unit):.1f}",
                },
                room=self.id,
            )
        elif self.current_temp is not None and self.current_temp >= frost:
            house.clear_alert(f"frost_{self.id}")
        self._check_mold(now)
        # Unavailable devices.
        limit = timedelta(minutes=house.alert_unavailable_minutes)
        for entity_id in self.climates + self.switches:
            state = self.hass.states.get(entity_id)
            if valid(state):
                if self._unavailable_since.pop(entity_id, None) is not None:
                    house.clear_alert(f"unavailable_{entity_id}")
                continue
            since = self._unavailable_since.setdefault(entity_id, now)
            if now - since >= limit:
                house.notify(
                    f"unavailable_{entity_id}",
                    f"{self.name}: {entity_id} has been unavailable for more than "
                    f"{limit.total_seconds() / 60:.0f} minutes.",
                    code="device_unavailable",
                    params={"entity": entity_id, "minutes": round(limit.total_seconds() / 60)},
                    room=self.id,
                )
        # External sensors.
        if self.external_failed:
            fallback = "the device sensor" if not self.sensor_failed else "eco"
            house.notify(
                f"sensor_{self.id}",
                f"{self.name}: the temperature sensors are unavailable; using {fallback}.",
                code="sensor_unavailable",
                params={"fallback": "eco" if self.sensor_failed else "device"},
                room=self.id,
            )
        else:
            house.clear_alert(f"sensor_{self.id}")
        # Schedule errors.
        if self.schedule_error:
            house.notify(
                f"schedule_{self.id}",
                f"{self.name}: the schedule is invalid ({self.schedule_error}); "
                "the default schedule is used.",
                code="schedule_invalid",
                params={"error": self.schedule_error},
                room=self.id,
            )
        else:
            house.clear_alert(f"schedule_{self.id}")
        # Days without an active profile (frost protection on those days).
        gaps = (
            uncovered_days(self.schedule.profile_days)
            if not (
                self.config.get(CONF_SCHEDULE_SOURCE) == SCHEDULE_HELPER
                and self.config.get(CONF_SCHEDULE_HELPER)
            )
            else {"days": [], "free_days": False, "workdays": False}
        )
        if gaps["days"] or gaps["free_days"] or gaps["workdays"]:
            house.notify(
                f"schedule_gap_{self.id}",
                f"{self.name}: no active schedule profile on "
                + ", ".join(
                    [
                        *gaps["days"],
                        *(["free days"] if gaps["free_days"] else []),
                        *(["workdays on the weekend"] if gaps["workdays"] else []),
                    ]
                )
                + "; the room keeps its frost protection on those days.",
                code="schedule_gap",
                params=dict(gaps),
                room=self.id,
            )
        else:
            house.clear_alert(f"schedule_gap_{self.id}")

    @callback
    def check_batteries(self) -> None:
        """Alert about low batteries of the room devices."""
        threshold = float(self.house.options[CONF_BATTERY_THRESHOLD])
        entity_reg = er.async_get(self.hass)
        device_reg = dr.async_get(self.hass)
        devices: set[str] = set()
        related = (
            self.climates
            + self.switches
            + as_list(self.config.get(CONF_TEMP_SENSORS))
            + as_list(self.config.get(CONF_WINDOW_SENSORS))
            + as_list(self.config.get(CONF_OCCUPANCY_SENSORS))
        )
        for entity_id in related:
            entry = entity_reg.async_get(entity_id)
            if entry is not None and entry.device_id:
                devices.add(entry.device_id)
        for device_id in devices:
            device = device_reg.async_get(device_id)
            for entry in er.async_entries_for_device(entity_reg, device_id):
                if entry.domain != "sensor":
                    continue
                if (entry.device_class or entry.original_device_class) != "battery":
                    continue
                state = self.hass.states.get(entry.entity_id)
                if not valid(state):
                    continue
                level = finite(state.state)  # type: ignore[union-attr]
                if level is None:
                    continue
                key = f"battery_{entry.entity_id}"
                if level < threshold:
                    name = (device.name_by_user or device.name) if device else entry.entity_id
                    self.house.notify(
                        key,
                        f"{self.name}: low battery on {name} ({level:.0f}%).",
                        repeat=timedelta(days=1),
                        code="battery_low",
                        params={"device": name, "level": round(level)},
                        room=self.id,
                    )
                else:
                    self.house.clear_alert(key)
