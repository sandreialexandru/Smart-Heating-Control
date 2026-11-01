"""Alert texts, categories and delivery rules for the notifications.

The card shows the alerts in its own language from their code and values; the
notifications use the same texts here, in the language of Home Assistant.
"""

from __future__ import annotations

from datetime import datetime, time
from typing import Any

# How much an alert matters: important ones are sent at once (also in the quiet
# hours), warnings are held until the quiet hours end, information too.
CATEGORY_CRITICAL = "critical"
CATEGORY_WARNING = "warning"
CATEGORY_INFO = "info"

CATEGORIES: dict[str, str] = {
    # No heating at all, or a room that cannot heat.
    "source_unavailable": CATEGORY_CRITICAL,
    "device_unavailable": CATEGORY_CRITICAL,
    # Something to look at.
    "sensor_unavailable": CATEGORY_WARNING,
    "outdoor_unavailable": CATEGORY_WARNING,
    "window_long": CATEGORY_WARNING,
    "battery_low": CATEGORY_WARNING,
    "not_accepted": CATEGORY_WARNING,
    "room_difference": CATEGORY_WARNING,
    "device_limit_max": CATEGORY_WARNING,
    "device_limit_min": CATEGORY_WARNING,
    "preset_missing": CATEGORY_WARNING,
    "schedule_invalid": CATEGORY_WARNING,
    "schedule_gap": CATEGORY_WARNING,
    "weather_without_source": CATEGORY_WARNING,
    "boiler_min_rooms": CATEGORY_WARNING,
    "frost_protection": CATEGORY_WARNING,
    "pause_long": CATEGORY_WARNING,
    # What the house did by itself.
    "auto_vacation_on": CATEGORY_INFO,
    "auto_vacation_off": CATEGORY_INFO,
    "season_on": CATEGORY_INFO,
    "season_off": CATEGORY_INFO,
    "guest_ended": CATEGORY_INFO,
    "vacation_started": CATEGORY_INFO,
    "vacation_preheat": CATEGORY_INFO,
}

# Alerts whose end is worth telling (a device back, a window closed); the others
# end because a setting changed, and no one waits for that.
RESOLVABLE = {
    "source_unavailable",
    "device_unavailable",
    "sensor_unavailable",
    "outdoor_unavailable",
    "window_long",
    "battery_low",
    "not_accepted",
    "frost_protection",
}

TEXTS: dict[str, dict[str, str]] = {
    "en": {
        "source_unavailable": "The heat source {entity} has been unavailable for more than {minutes} min: no heating, not even frost protection.",
        "room_difference": "Some rooms stay cold while others are warm: {rooms}.",
        "preset_missing": "The level {level} is not available on {entity} and its temperature is unknown.",
        "not_accepted": "{entities} did not accept {target}.",
        "window_long": "A window has been open for more than {minutes} min.",
        "device_unavailable": "{entity} has been unavailable for more than {minutes} min.",
        "sensor_unavailable_device": "The temperature sensors are unavailable; the device sensor is used.",
        "sensor_unavailable_eco": "The temperature sensors are unavailable; eco is used.",
        "schedule_invalid": "The schedule is invalid ({error}); the default schedule is used.",
        "schedule_gap": "No active schedule profile: {days}; the room keeps its frost protection on those days.",
        "battery_low": "Low battery on {device} ({level}%).",
        "device_limit_max": "{entity} accepts at most {value}: raise its Max temperature on the device if the room needs more.",
        "device_limit_min": "{entity} accepts at least {value}: lower its Min temperature on the device for a lower frost protection.",
        "weather_without_source": "On but not working without an outdoor temperature sensor or a weather entity: {features}.",
        "boiler_min_rooms": "Rooms needed to start the heat source is {needed}, but the house has {rooms} rooms that heat from it: the heat source starts only for frost protection.",
        "outdoor_unavailable": "No outdoor temperature from {entities} for more than {minutes} min: the cutoff, the automatic season, the compensation and the optimal stop cannot use it.",
        "auto_vacation_on": "Everyone has been away for a long time: the automatic vacation started.",
        "auto_vacation_off": "The automatic vacation ended.",
        "frost_protection": "The room is {current}°, below the frost protection temperature ({frost}°): the heating cannot keep it.",
        "pause_long": "The heating has been paused for more than {hours} h: only frost protection works.",
        "season_on": "The heating season started.",
        "season_off": "The heating season ended: no heating until it starts again.",
        "guest_ended": "Guest mode ended by itself: the house follows the people again.",
        "vacation_started": "The vacation started: every room is set to away.",
        "vacation_preheat": "The vacation ends soon: the house is warmed up for your return.",
        # Resolved.
        "resolved_source_unavailable": "The heat source {entity} works again.",
        "resolved_device_unavailable": "{entity} is available again.",
        "resolved_sensor_unavailable": "The temperature sensors work again.",
        "resolved_outdoor_unavailable": "The outdoor temperature is available again.",
        "resolved_window_long": "The window is closed again.",
        "resolved_battery_low": "The battery of {device} is fine again.",
        "resolved_not_accepted": "{entities} follow the target again.",
        "resolved_frost_protection": "The room is back at the frost protection temperature.",
        # Values.
        "free_days": "free days (holidays)",
        "weekend_workdays": "workdays on the weekend",
        "wf_cutoff": "turn heating off when warm",
        "wf_season_auto": "automatic season",
        "wf_compensation": "outdoor compensation",
        "wf_window_ignore": "ignore windows above",
        "wf_forecast": "use the forecast (needs a weather entity and the cutoff)",
    },
    "ro": {
        "source_unavailable": "Sursa de căldură {entity} e indisponibilă de peste {minutes} min: nu se încălzește, nici pentru antiîngheț.",
        "room_difference": "Unele camere rămân reci, altele sunt calde: {rooms}.",
        "preset_missing": "Nivelul {level} nu există pe {entity} și temperatura lui e necunoscută.",
        "not_accepted": "{entities} nu a acceptat {target}.",
        "window_long": "O fereastră e deschisă de peste {minutes} min.",
        "device_unavailable": "{entity} e indisponibil de peste {minutes} min.",
        "sensor_unavailable_device": "Senzorii de temperatură sunt indisponibili; se folosește senzorul dispozitivului.",
        "sensor_unavailable_eco": "Senzorii de temperatură sunt indisponibili; se folosește eco.",
        "schedule_invalid": "Programul e invalid ({error}); se folosește programul implicit.",
        "schedule_gap": "Fără profil activ în program: {days}; în acele zile camera rămâne pe antiîngheț.",
        "battery_low": "Baterie descărcată la {device} ({level}%).",
        "device_limit_max": "{entity} acceptă cel mult {value}: ridică Max temperature pe dispozitiv dacă e nevoie de mai mult.",
        "device_limit_min": "{entity} acceptă cel puțin {value}: coboară Min temperature pe dispozitiv pentru un antiîngheț mai jos.",
        "weather_without_source": "Pornite, dar nu funcționează fără senzor de temperatură exterioară sau entitate meteo: {features}.",
        "boiler_min_rooms": "Camere necesare pentru pornirea sursei de căldură: {needed}, dar casa are {rooms} camere care se încălzesc din ea: sursa de căldură pornește doar pentru antiîngheț.",
        "outdoor_unavailable": "Nicio temperatură de afară de la {entities} de peste {minutes} min: oprirea când e cald, sezonul automat, compensarea și oprirea anticipată nu o pot folosi.",
        "auto_vacation_on": "Toată lumea e plecată de mult: a pornit vacanța automată.",
        "auto_vacation_off": "Vacanța automată s-a încheiat.",
        "frost_protection": "Camera are {current}°, sub temperatura de antiîngheț ({frost}°): încălzirea nu o poate menține.",
        "pause_long": "Încălzirea e în pauză de peste {hours} h: funcționează doar antiînghețul.",
        "season_on": "A început sezonul de încălzire.",
        "season_off": "S-a încheiat sezonul de încălzire: nu se mai încălzește până nu reîncepe.",
        "guest_ended": "Modul oaspeți s-a oprit singur: casa urmează din nou persoanele.",
        "vacation_started": "A început vacanța: toate camerele sunt pe away.",
        "vacation_preheat": "Vacanța se termină curând: casa se încălzește pentru întoarcerea voastră.",
        "resolved_source_unavailable": "Sursa de căldură {entity} funcționează din nou.",
        "resolved_device_unavailable": "{entity} e din nou disponibil.",
        "resolved_sensor_unavailable": "Senzorii de temperatură funcționează din nou.",
        "resolved_outdoor_unavailable": "Temperatura de afară e din nou disponibilă.",
        "resolved_window_long": "Fereastra e închisă din nou.",
        "resolved_battery_low": "Bateria de la {device} e din nou în regulă.",
        "resolved_not_accepted": "{entities} urmează din nou ținta.",
        "resolved_frost_protection": "Camera a revenit la temperatura de antiîngheț.",
        "free_days": "zilele libere (sărbători)",
        "weekend_workdays": "zilele lucrătoare din weekend",
        "wf_cutoff": "oprirea când e cald",
        "wf_season_auto": "sezonul automat",
        "wf_compensation": "compensarea exterioară",
        "wf_window_ignore": "ignorarea ferestrelor peste",
        "wf_forecast": "prognoza (cere o entitate meteo și oprirea când e cald)",
    },
}

WEEKDAYS: dict[str, dict[str, str]] = {
    "en": {
        "mon": "Monday", "tue": "Tuesday", "wed": "Wednesday", "thu": "Thursday",
        "fri": "Friday", "sat": "Saturday", "sun": "Sunday",
    },
    "ro": {
        "mon": "luni", "tue": "marți", "wed": "miercuri", "thu": "joi",
        "fri": "vineri", "sat": "sâmbătă", "sun": "duminică",
    },
}  # fmt: skip


def language(hass_language: str | None) -> str:
    """The language of the texts: Romanian for Romanian, English otherwise."""
    return "ro" if str(hass_language or "").lower().startswith("ro") else "en"


def category(code: str | None) -> str:
    """How much an alert matters (an unknown one is a warning)."""
    return CATEGORIES.get(str(code), CATEGORY_WARNING)


def _values(lang: str, code: str, params: dict[str, Any]) -> dict[str, str]:
    """The values of an alert as text."""
    texts = TEXTS[lang]
    values = {k: str(v) for k, v in params.items()}
    if isinstance(params.get("entities"), list):
        values["entities"] = ", ".join(str(e) for e in params["entities"])
    if isinstance(params.get("rooms"), list):
        values["rooms"] = ", ".join(
            f"{name} (−{gap}°)" for name, gap in params["rooms"] if name is not None
        )
    if isinstance(params.get("features"), list):
        values["features"] = ", ".join(texts.get(f"wf_{f}", str(f)) for f in params["features"])
    if code == "schedule_gap":
        days = [WEEKDAYS[lang].get(str(d), str(d)) for d in params.get("days") or []]
        if params.get("free_days"):
            days.append(texts["free_days"])
        if params.get("workdays"):
            days.append(texts["weekend_workdays"])
        values["days"] = ", ".join(days)
    return values


def alert_text(
    lang: str,
    code: str | None,
    params: dict[str, Any] | None,
    fallback: str,
    *,
    resolved: bool = False,
) -> str:
    """The text of an alert (or of its end) in a language; ``fallback`` when unknown."""
    if not code:
        return fallback
    params = params or {}
    key = code
    if code == "sensor_unavailable" and not resolved:
        key = f"sensor_unavailable_{params.get('fallback') or 'device'}"
    if resolved:
        key = f"resolved_{code}"
    template = TEXTS[lang].get(key)
    if template is None:
        return fallback
    try:
        return template.format(**_values(lang, code, params))
    except (KeyError, IndexError, ValueError, TypeError):
        return fallback


def parse_time(value: Any) -> time | None:
    """A time of the options ("HH:MM[:SS]"), None when empty or invalid."""
    if not value:
        return None
    try:
        parts = [int(p) for p in str(value).split(":")]
        return time(parts[0], parts[1] if len(parts) > 1 else 0)
    except (ValueError, IndexError):
        return None


def in_quiet_hours(local_now: datetime, start: time | None, end: time | None) -> bool:
    """True in the quiet hours (they may go past midnight; equal times: none)."""
    if start is None or end is None or start == end:
        return False
    now = local_now.time().replace(second=0, microsecond=0)
    if start < end:
        return start <= now < end
    return now >= start or now < end


def targets(value: Any) -> list[str]:
    """The recipients chosen for a category, as written (duplicates dropped).

    A recipient is a notify service or entity, optionally followed by the email
    addresses it sends to: ``notify.me_gmail_com: ana@example.com, ion@example.com``
    (Google Mail and other mail services need them).
    """
    if not value:
        return []
    if isinstance(value, str):
        value = [value]
    result = []
    for item in value:
        item = str(item).strip()
        if not item:
            continue
        name, _, addresses = item.partition(":")
        # Services and entities are lower case (a phone keyboard may write "Notify.").
        name = name.strip().lower()
        if "." not in name:
            name = f"notify.{name}"
        recipient = f"{name}: {addresses.strip()}" if addresses.strip() else name
        if recipient not in result:
            result.append(recipient)
    return result


def split_recipient(recipient: str) -> tuple[str, list[str]]:
    """The notify service or entity of a recipient and its email addresses."""
    name, _, addresses = recipient.partition(":")
    found = [a.strip() for a in addresses.replace(";", ",").split(",") if a.strip()]
    return name.strip().lower(), found


def invalid_recipient(recipient: str) -> str | None:
    """The first part of a recipient that cannot be used, None when it is fine."""
    name, addresses = split_recipient(recipient)
    if not name.startswith("notify.") or len(name) <= len("notify.") or " " in name:
        return name or recipient
    for address in addresses:
        local, at, domain = address.partition("@")
        if not at or not local or "." not in domain or " " in address:
            return address
    return None
