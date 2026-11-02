"""Alerts and messages of the house: who gets them, when, and in which language.

The house and the rooms say what happened (``notify`` for an alert that lasts
while it applies, ``inform`` for something the house did by itself); this
module keeps the alerts for the card and sends them to the notify services or
entities chosen in the options, holding what is not critical for the end of
the quiet hours and telling the end of an alert when worth it.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.components import persistent_notification
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util

from . import alerts as alert_texts
from .const import (
    CONF_NOTIFY_CRITICAL,
    CONF_NOTIFY_INFO,
    CONF_NOTIFY_RESOLVED,
    CONF_NOTIFY_SERVICE,
    CONF_NOTIFY_WARNING,
    CONF_QUIET_END,
    CONF_QUIET_START,
    DOMAIN,
)

if TYPE_CHECKING:
    from .house import House
    from .room import Room

_LOGGER = logging.getLogger(__name__)


class Notifier:
    """The alerts of one house and their delivery."""

    def __init__(self, house: House) -> None:
        """Nothing sent yet."""
        self.house = house
        self.hass = house.hass
        # When each alert was last sent (an alert is sent once, or again after its repeat).
        self.sent_at: dict[str, datetime] = {}
        # Alerts that still apply (for the card): code, values, room, text.
        self.active: dict[str, dict[str, Any]] = {}
        # Alerts sent to notify targets, by key: what is needed to tell their end.
        self.delivered: dict[str, dict[str, Any]] = {}
        # Messages held by the quiet hours, in order: (key or None, message dict).
        self.deferred: list[tuple[str | None, dict[str, Any]]] = []

    @property
    def options(self) -> dict[str, Any]:
        """The options of the house (read each time: they may change)."""
        return self.house.options

    # -- what happened ----------------------------------------------------
    def notify(
        self,
        key: str,
        message: str,
        *,
        title: str = "Smart Heating Control",
        repeat: timedelta | None = None,
        code: str | None = None,
        params: dict[str, Any] | None = None,
        room: str | None = None,
    ) -> None:
        """Send an alert once (or again after ``repeat``).

        ``code`` and ``params`` let the card and the notifications show it in
        their language; ``room`` is the room it belongs to (None: the whole
        house). ``message`` is the English text, used when a code is unknown.
        """
        now = dt_util.utcnow()
        self.active[key] = {
            "code": code,
            "params": params or {},
            "room": room,
            "message": message,
        }
        last = self.sent_at.get(key)
        if last is not None and (repeat is None or now - last < repeat):
            return
        self.sent_at[key] = now
        _LOGGER.info("%s: %s", title, message)
        self._deliver(key, {"code": code, "params": params or {}, "room": room, "message": message})

    def inform(self, code: str, params: dict[str, Any] | None = None) -> None:
        """Tell what the house did by itself (information, not an alert of the card)."""
        message = alert_texts.alert_text("en", code, params, code)
        _LOGGER.info("%s: %s", self.house.entry.title, message)
        self._deliver(
            None, {"code": code, "params": params or {}, "room": None, "message": message}
        )

    def clear(self, key: str) -> None:
        """The alert no longer applies: tell it when worth it, allow it again."""
        self.active.pop(key, None)
        sent = self.sent_at.pop(key, None) is not None
        item = self.delivered.pop(key, None)
        if not sent:
            return
        persistent_notification.async_dismiss(self.hass, f"{DOMAIN}_{key}")
        held = [k for k, i in self.deferred if k == key and not i.get("resolved")]
        if held:
            # Never sent (the quiet hours held it): no end to tell either.
            self.deferred = [(k, i) for k, i in self.deferred if k != key]
            return
        if (
            item is not None
            and item.get("code") in alert_texts.RESOLVABLE
            and self.options.get(CONF_NOTIFY_RESOLVED, True)
        ):
            self._deliver(key, item, resolved=True)

    def alerts_for(self, room: Room) -> list[dict[str, Any]]:
        """Alerts that apply to a room: its own and those of the whole house.

        Cold rooms (while others are warm) are told only in those rooms.
        """
        result = []
        for key, alert in self.active.items():
            if alert.get("room") not in (None, room.id):
                continue
            if alert.get("code") == "room_difference" and room.name not in [
                name for name, _gap in alert["params"].get("rooms", [])
            ]:
                continue
            result.append({"key": key, **{k: v for k, v in alert.items() if k != "room"}})
        return result

    # -- the quiet hours --------------------------------------------------
    def quiet(self, now: datetime) -> bool:
        """True in the quiet hours of the options."""
        return alert_texts.in_quiet_hours(
            dt_util.as_local(now),
            alert_texts.parse_time(self.options.get(CONF_QUIET_START)),
            alert_texts.parse_time(self.options.get(CONF_QUIET_END)),
        )

    def quiet_end(self, now: datetime) -> datetime | None:
        """When the current quiet hours end (UTC), None outside them."""
        end = alert_texts.parse_time(self.options.get(CONF_QUIET_END))
        if end is None or not self.quiet(now):
            return None
        local = dt_util.as_local(now)
        moment = local.replace(hour=end.hour, minute=end.minute, second=0, microsecond=0)
        if moment <= local:
            moment += timedelta(days=1)
        return dt_util.as_utc(moment)

    def flush(self, now: datetime) -> None:
        """After the quiet hours: send what they held and still applies."""
        if not self.deferred or self.quiet(now):
            return
        held, self.deferred = self.deferred, []
        for key, item in held:
            resolved = bool(item.pop("resolved", False))
            if key is not None and not resolved and key not in self.active:
                continue  # it ended meanwhile
            category = alert_texts.category(item.get("code"))
            targets = self.targets(category)
            if targets:
                self._send(key, item, targets, resolved=resolved)

    # -- delivery ---------------------------------------------------------
    def targets(self, category: str) -> list[str]:
        """Notify services or entities for a category of alerts.

        Before 2.5 one service got every alert: it still does until the
        options are saved again.
        """
        opts = self.options
        keys = {
            alert_texts.CATEGORY_CRITICAL: CONF_NOTIFY_CRITICAL,
            alert_texts.CATEGORY_WARNING: CONF_NOTIFY_WARNING,
            alert_texts.CATEGORY_INFO: CONF_NOTIFY_INFO,
        }
        if not any(k in opts for k in keys.values()):
            legacy = alert_texts.targets(opts.get(CONF_NOTIFY_SERVICE))
            return legacy if category != alert_texts.CATEGORY_INFO else []
        return alert_texts.targets(opts.get(keys[category]))

    def text(self, item: dict[str, Any], *, resolved: bool = False) -> str:
        """The text of an alert in the language of Home Assistant, with its room."""
        lang = alert_texts.language(self.hass.config.language)
        text = alert_texts.alert_text(
            lang, item.get("code"), item.get("params"), "", resolved=resolved
        )
        if not text:
            return str(item["message"])  # no text for its code: the English one, as written
        room = self.house.rooms.get(item.get("room") or "")
        if room is not None and not text.startswith(room.name):
            text = f"{room.name}: {text}"
        return text

    def _deliver(self, key: str | None, item: dict[str, Any], *, resolved: bool = False) -> None:
        """Send an alert (or its end) now, or hold it for the end of the quiet hours."""
        category = alert_texts.category(item.get("code"))
        targets = self.targets(category)
        if not targets:
            if category == alert_texts.CATEGORY_INFO or resolved:
                return
            # No one chosen: a notification in Home Assistant, as always.
            persistent_notification.async_create(
                self.hass,
                self.text(item),
                title=self.house.entry.title,
                notification_id=f"{DOMAIN}_{key}",
            )
            return
        if category != alert_texts.CATEGORY_CRITICAL and self.quiet(dt_util.utcnow()):
            self.deferred.append((key, {**item, "resolved": resolved}))
            return
        self._send(key, item, targets, resolved=resolved)

    def _send(
        self, key: str | None, item: dict[str, Any], targets: list[str], *, resolved: bool
    ) -> None:
        """Send one message to every target of its category."""
        message = self.text(item, resolved=resolved)
        if key is not None and not resolved:
            self.delivered[key] = item
        for target in targets:
            self.hass.async_create_task(
                self._async_call_notify(target, self.house.entry.title, message, key)
            )

    async def _async_call_notify(
        self, recipient: str, title: str, message: str, key: str | None
    ) -> None:
        """Send with a notify service or entity (persistent notification if it fails).

        Email addresses written after the service go as its ``target``.
        """
        target, addresses = alert_texts.split_recipient(recipient)
        domain, _, name = target.partition(".")
        try:
            if self.hass.states.get(target) is not None and domain == "notify":
                # A notify entity (the newer kind): it knows where it sends.
                await self.hass.services.async_call(
                    "notify",
                    "send_message",
                    {"entity_id": target, "title": title, "message": message},
                    blocking=True,
                )
                return
            data: dict[str, Any] = {"title": title, "message": message}
            if addresses:
                data["target"] = addresses
            if name.startswith("mobile_app_") and key is not None:
                # The phone replaces the alert with its end (same tag).
                data["data"] = {"tag": f"{DOMAIN}_{key}", "group": DOMAIN}
            await self.hass.services.async_call(domain, name, data, blocking=True)
        except (HomeAssistantError, ValueError) as err:
            _LOGGER.warning("Notification via %s failed: %s", target, err)
            persistent_notification.async_create(self.hass, message, title=title)
