"""House controller: global state, presence, weather, energy and the boiler."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Iterable
from datetime import date, datetime, time, timedelta
from typing import Any

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    EVENT_HOMEASSISTANT_STARTED,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_ON,
)
from homeassistant.core import (
    Context,
    Event,
    EventStateChangedData,
    HomeAssistant,
    State,
    callback,
)
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import (
    async_call_later,
    async_track_point_in_time,
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    CONF_ALERT_UNAVAILABLE_MINUTES,
    CONF_ARRIVAL_DELAY,
    CONF_ARRIVAL_DISTANCE,
    CONF_ARRIVAL_MINUTES,
    CONF_AUTO_VACATION_HOURS,
    CONF_BOILER_ENTITY,
    CONF_BOILER_MIN_OFF,
    CONF_BOILER_MIN_ON,
    CONF_BOILER_MIN_ROOMS,
    CONF_CALENDAR,
    CONF_COMP_BELOW,
    CONF_COMP_ENABLED,
    CONF_COMP_OFFSET,
    CONF_CUTOFF_AVG_HOURS,
    CONF_CUTOFF_ENABLED,
    CONF_CUTOFF_HYSTERESIS,
    CONF_CUTOFF_TEMP,
    CONF_DAY_BOUNDARY,
    CONF_DEPARTURE_DELAY,
    CONF_FORECAST_ENABLED,
    CONF_FORECAST_HOURS,
    CONF_GUEST_EXPIRE_HOURS,
    CONF_HOME_RULE,
    CONF_NEARBY_GEOMETRIC,
    CONF_NEARBY_ZONES,
    CONF_NOTIFY_SERVICE,
    CONF_OPTIMAL_START,
    CONF_OPTIMAL_STOP,
    CONF_OUTDOOR_SENSOR,
    CONF_OVERRIDE_SCOPE,
    CONF_PERSONS,
    CONF_PRESENCE_SENSORS,
    CONF_PRICE_HIGH,
    CONF_PRICE_HIGH_OFFSET,
    CONF_PRICE_LOW,
    CONF_PRICE_LOW_OFFSET,
    CONF_PRICE_SENSOR,
    CONF_PROXIMITY_DIRECTION,
    CONF_PROXIMITY_DISTANCE,
    CONF_PV_OFFSET,
    CONF_PV_SENSOR,
    CONF_PV_THRESHOLD,
    CONF_REEVAL_MINUTES,
    CONF_REFERENCE_ROOM,
    CONF_ROOM_DIFF_ALERT,
    CONF_SEASON_DAYS,
    CONF_SEASON_END,
    CONF_SEASON_MODE,
    CONF_SEASON_START,
    CONF_SEASON_TEMP,
    CONF_TEMP_UNIT,
    CONF_TRAVEL_TIME,
    CONF_VACATION_PREHEAT,
    CONF_WEATHER,
    CONF_WINDOW_IGNORE_ABOVE,
    CONF_WORKDAY_SENSOR,
    DOMAIN,
    HOUSE_DEFAULTS,
    MODE_AUTO,
    MODE_VACATION,
    MODES,
    OVERRIDE_SCOPE_HOUSE,
    PRESENCE_FAR,
    PRESENCE_HOME,
    SEASON_AUTO,
    SIGNAL_UPDATE,
    STARTUP_DELAY,
    STORAGE_VERSION,
    SUBENTRY_ROOM,
)
from .outdoor import OutdoorTracker, expected_outdoor
from .presence import (
    PersonInfo,
    PresenceDebouncer,
    ZoneInfo,
    classify_person,
    is_arriving,
    raw_house_presence,
)
from .room import Room
from .util import (
    CELSIUS,
    FAHRENHEIT,
    as_list,
    calendar_moment,
    delta_from_celsius,
    distance_km,
    float_attr,
    float_state,
    from_iso,
    heat_mode,
    is_fahrenheit,
    iso,
    minutes_value,
    parse_clock,
    system_unit,
    temp_state,
    to_celsius,
    valid,
)

_LOGGER = logging.getLogger(__name__)

# Days of calendar events read ahead: today and the next 7, like the Workday days.
CALENDAR_DAYS = 8


class House:
    """Controller for one Smart Heating Control config entry (the house)."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize."""
        self.hass = hass
        self.entry = entry
        self.options: dict[str, Any] = {**HOUSE_DEFAULTS, **entry.data, **entry.options}
        self.store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}"
        )
        self.rooms: dict[str, Room] = {}
        self.device_id: str | None = None
        self.config_snapshot: tuple | None = None
        self.started = False

        # Persisted state
        self.mode = MODE_AUTO
        self.paused = False
        self.guest = False
        self.guest_until: datetime | None = None
        self.vacation_start: datetime | None = None
        self.vacation_end: datetime | None = None
        self.auto_vacation = False
        # Last time an arrival ended the automatic vacation (far time counts from it).
        self.auto_vacation_reset: datetime | None = None
        self.presence = PresenceDebouncer()
        self.outdoor = OutdoorTracker()
        self.boiler_runtime_s = 0.0
        self.workday_cache: dict[str, bool] = {}

        # Runtime state
        self.person_classes: dict[str, str | None] = {}
        self.arriving = False
        # End of the current calendar event (its level holds until then).
        self.calendar_end: datetime | None = None
        # Hourly forecast (UTC moment, °C), for the optimal start / stop.
        self.hourly_forecast: list[tuple[datetime, float]] = []
        self.calendar_message: str | None = None
        # Events of the next days (start, end, summary): profiles of the coming days.
        self.calendar_events: list[tuple[datetime, datetime, str]] = []
        self.heat_demand = False
        self.boiler_on: bool | None = None
        self.boiler_changed: datetime | None = None
        self._source_running_since: datetime | None = None
        self._frost_started = False  # heat source started for frost protection while paused
        self._source_wait_until: datetime | None = None
        self._source_unavailable_since: datetime | None = None
        self._outdoor_unavailable_since: datetime | None = None
        self._alerts: dict[str, datetime] = {}
        # Alerts that still apply (for the card): code, values, room, text.
        self.active_alerts: dict[str, dict[str, Any]] = {}
        # Why the heat source waits: "min_on" / "min_off" (minimum times), else None.
        self.source_waiting: str | None = None
        self._unsubs: list[Callable[[], None]] = []
        self._timer_unsub: Callable[[], None] | None = None
        self._eval_unsub: Callable[[], None] | None = None
        self._presence_due: datetime | None = None
        self._last_eval: datetime | None = None
        self._own_contexts: dict[str, None] = {}  # ordered set
        self._started_unsub: Callable[[], None] | None = None
        # Evaluations never run at the same time (timer, events and services).
        self._eval_lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Setup / teardown
    # ------------------------------------------------------------------
    async def async_setup(self) -> None:
        """Load state, create rooms and start listening."""
        data = await self.store.async_load() or {}
        house = data.get("house", {})
        self.mode = house.get("mode", MODE_AUTO) if house.get("mode") in MODES else MODE_AUTO
        self.paused = bool(house.get("paused", False))
        self.guest = bool(house.get("guest", False))
        self.guest_until = from_iso(house.get("guest_until"))
        self.vacation_start = from_iso(house.get("vacation_start"))
        self.vacation_end = from_iso(house.get("vacation_end"))
        self.auto_vacation = bool(house.get("auto_vacation", False))
        self.auto_vacation_reset = from_iso(house.get("auto_vacation_reset"))
        self.presence = PresenceDebouncer.from_dict(house.get("presence"))
        self.outdoor = OutdoorTracker.from_dict(house.get("outdoor"))
        if not self.outdoor_configured:
            # No outdoor sensor or weather: the saved outdoor values are not used.
            season = self.outdoor.season_active
            self.outdoor = OutdoorTracker()
            self.outdoor.season_active = season
        # Daily means are per local calendar day.
        self.outdoor.tz = dt_util.get_default_time_zone()
        # Without a new value for the averaging window of the cutoff, the outdoor
        # temperature is unknown.
        self.outdoor.max_age = timedelta(hours=self.average_hours)
        self.boiler_runtime_s = float(house.get("boiler_runtime_s", 0.0))
        self._frost_started = bool(house.get("frost_started", False))
        self.boiler_changed = from_iso(house.get("boiler_changed"))
        self.workday_cache = dict(house.get("workday_cache", {}))

        room_data = data.get("rooms", {})
        for subentry in self.entry.subentries.values():
            if subentry.subentry_type != SUBENTRY_ROOM:
                continue
            room = Room(self, subentry, room_data.get(subentry.subentry_id, {}))
            self.rooms[subentry.subentry_id] = room

        self._subscribe()
        for room in self.rooms.values():
            room.async_start()

        if self.hass.is_running:
            self._unsubs.append(async_call_later(self.hass, STARTUP_DELAY, self._async_start))
        else:
            self._started_unsub = self.hass.bus.async_listen_once(
                EVENT_HOMEASSISTANT_STARTED, self._async_on_ha_started
            )

    async def _async_on_ha_started(self, _event: Event) -> None:
        """Start controlling a little after Home Assistant has started."""
        self._started_unsub = None
        self._unsubs.append(async_call_later(self.hass, STARTUP_DELAY, self._async_start))

    async def _async_start(self, _now: datetime | None = None) -> None:
        """Start controlling after Home Assistant is up."""
        self.started = True
        minutes = max(1, int(self.options[CONF_REEVAL_MINUTES]))
        self._unsubs.append(
            async_track_time_interval(self.hass, self._async_periodic, timedelta(minutes=minutes))
        )
        self._unsubs.append(
            async_track_time_interval(self.hass, self._async_hourly, timedelta(hours=1))
        )
        if self._forecast_needed():
            self._unsubs.append(
                async_track_time_interval(
                    self.hass, self._async_refresh_forecast, timedelta(minutes=30)
                )
            )
            await self._async_refresh_forecast()
        await self._async_refresh_workdays()
        await self._async_refresh_calendar()
        await self.async_evaluate()

    async def async_unload(self) -> None:
        """Stop listening and save."""
        if self._started_unsub is not None:
            self._started_unsub()
            self._started_unsub = None
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        if self._timer_unsub:
            self._timer_unsub()
            self._timer_unsub = None
        if self._eval_unsub:
            self._eval_unsub()
            self._eval_unsub = None
        for room in self.rooms.values():
            room.async_stop()
        await self.store.async_save(self._data_to_save())

    def _subscribe(self) -> None:
        """Track the house level entities."""
        opts = self.options
        entities: list[str] = []
        entities += as_list(opts.get(CONF_PERSONS))
        entities += as_list(opts.get(CONF_PRESENCE_SENSORS))
        for key in (
            CONF_PROXIMITY_DISTANCE,
            CONF_PROXIMITY_DIRECTION,
            CONF_TRAVEL_TIME,
            CONF_WORKDAY_SENSOR,
            CONF_CALENDAR,
            CONF_OUTDOOR_SENSOR,
            CONF_WEATHER,
            CONF_PRICE_SENSOR,
            CONF_PV_SENSOR,
        ):
            if opts.get(key):
                entities.append(opts[key])
        if entities:
            self._unsubs.append(
                async_track_state_change_event(
                    self.hass, sorted(set(entities)), self._async_house_entity_changed
                )
            )
        if opts.get(CONF_BOILER_ENTITY):
            self._unsubs.append(
                async_track_state_change_event(
                    self.hass, [opts[CONF_BOILER_ENTITY]], self._async_boiler_changed
                )
            )

    @callback
    def _async_house_entity_changed(self, event: Event[EventStateChangedData]) -> None:
        """A house entity changed (person, sensor, weather...): evaluate again."""
        entity_id = event.data["entity_id"]
        new = event.data["new_state"]
        if entity_id in (self.options.get(CONF_OUTDOOR_SENSOR), self.options.get(CONF_WEATHER)):
            self._sample_outdoor()
        if entity_id == self.options.get(CONF_WORKDAY_SENSOR) and valid(new):
            self.hass.async_create_task(self._async_refresh_workdays())
        if entity_id == self.options.get(CONF_CALENDAR):
            self.hass.async_create_task(self._async_refresh_calendar())
        self.async_request_evaluate()

    @callback
    def _async_boiler_changed(self, event: Event[EventStateChangedData]) -> None:
        """The heat source started or stopped (by us or not): evaluate again.

        The learning and the heating time follow the real state of the heat
        source, so they start and stop when it changes.
        """
        self.async_request_evaluate()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def _data_to_save(self) -> dict[str, Any]:
        """State kept between restarts."""
        return {
            "house": {
                "mode": self.mode,
                "paused": self.paused,
                "guest": self.guest,
                "guest_until": iso(self.guest_until),
                "vacation_start": iso(self.vacation_start),
                "vacation_end": iso(self.vacation_end),
                "auto_vacation": self.auto_vacation,
                "auto_vacation_reset": iso(self.auto_vacation_reset),
                "presence": self.presence.as_dict(),
                "outdoor": self.outdoor.as_dict(),
                "boiler_runtime_s": round(self.boiler_runtime_s, 1),
                # Kept over a restart: a heat source started for frost protection
                # in a pause is stopped again, and the minimum on / off time holds.
                "frost_started": self._frost_started,
                "boiler_changed": iso(self.boiler_changed),
                "workday_cache": dict(list(self.workday_cache.items())[-20:]),
            },
            "rooms": {room_id: room.as_dict() for room_id, room in self.rooms.items()},
        }

    @callback
    def async_save(self) -> None:
        """Schedule a save."""
        self.store.async_delay_save(self._data_to_save, 10)

    # ------------------------------------------------------------------
    # Evaluation scheduling
    # ------------------------------------------------------------------
    @callback
    def async_request_evaluate(self, delay: float = 1.0) -> None:
        """Debounced evaluation request."""
        if not self.started:
            self.async_notify_listeners()
            return
        if self._eval_unsub is not None:
            return

        async def _run(_now: datetime) -> None:
            """Run the requested evaluation."""
            self._eval_unsub = None
            await self.async_evaluate()

        self._eval_unsub = async_call_later(self.hass, delay, _run)

    async def _async_periodic(self, _now: datetime) -> None:
        """Periodic evaluation, in addition to the events."""
        await self.async_evaluate()

    async def _async_hourly(self, _now: datetime) -> None:
        """Hourly checks: batteries, the Workday calendar and the calendar events."""
        for room in self.rooms.values():
            room.check_batteries()
        await self._async_refresh_workdays()
        await self._async_refresh_calendar()

    async def async_evaluate(self) -> None:
        """Evaluate the house and all rooms, then send commands."""
        if not self.started:
            return
        async with self._eval_lock:
            await self._async_evaluate_locked()

    async def _async_evaluate_locked(self) -> None:
        """Evaluate the house and every room, then send the commands."""
        now = dt_util.utcnow()
        self._last_eval = now
        self._sample_outdoor()
        self._update_weather(now)
        self._update_guest(now)
        self._update_presence(now)
        self._update_calendar()
        self._update_vacation(now)

        for room in list(self.rooms.values()):
            try:
                await room.async_evaluate(now)
            except Exception:
                _LOGGER.exception("Error evaluating room %s", room.name)

        # An unexpected error of the heat source or of the checks does not stop
        # the timer, the saving and the update of the entities.
        # Each on its own: an error of one does not skip the others.
        try:
            await self._async_control_boiler(now)
        except Exception:
            _LOGGER.exception("Error controlling the heat source of %s", self.entry.title)
        try:
            self._check_room_difference()
            self._check_weather_alerts(now)
        except Exception:
            _LOGGER.exception("Error in the checks of %s", self.entry.title)
        self._schedule_timer(now)
        self.async_save()
        self.async_notify_listeners()

    @callback
    def async_notify_listeners(self) -> None:
        """Tell the entities to refresh."""
        async_dispatcher_send(self.hass, SIGNAL_UPDATE.format(self.entry.entry_id))

    def _schedule_timer(self, now: datetime) -> None:
        """Wake up at the next known change (schedule, presence delay...)."""
        candidates = [t for t in (room.next_wakeup for room in self.rooms.values()) if t]
        if self._presence_due:
            candidates.append(self._presence_due)
        if self.guest_until:
            candidates.append(self.guest_until)
        # The end of the minimum on / off time the heat source waits for.
        if self.source_waiting and self._source_wait_until is not None:
            candidates.append(self._source_wait_until)
        for moment in (self.vacation_start, self._vacation_resume(), self.vacation_end):
            if moment and moment > now:
                candidates.append(moment)
        candidates = [t for t in candidates if t > now]
        if self._timer_unsub:
            self._timer_unsub()
            self._timer_unsub = None
        if not candidates:
            return
        when = min(candidates) + timedelta(seconds=1)

        async def _fire(_now: datetime) -> None:
            """Evaluate at the planned moment."""
            self._timer_unsub = None
            await self.async_evaluate()

        self._timer_unsub = async_track_point_in_time(self.hass, _fire, when)

    # ------------------------------------------------------------------
    # Presence
    # ------------------------------------------------------------------
    def _zones(self) -> list[ZoneInfo]:
        """Every zone of Home Assistant with its position and radius."""
        zones = []
        for state in self.hass.states.async_all("zone"):
            zones.append(
                ZoneInfo(
                    state.entity_id,
                    str(state.attributes.get("friendly_name", state.object_id)),
                    float_attr(state, "latitude"),
                    float_attr(state, "longitude"),
                    float_attr(state, "radius") or 0.0,
                )
            )
        return zones

    def _update_presence(self, now: datetime) -> None:
        """Classify the people, debounce the house presence and detect who is coming home."""
        opts = self.options
        zones = self._zones()
        nearby_ids = set(as_list(opts.get(CONF_NEARBY_ZONES)))
        nearby = [z for z in zones if z.entity_id in nearby_ids]
        classes: dict[str, str | None] = {}
        for entity_id in as_list(opts.get(CONF_PERSONS)):
            state = self.hass.states.get(entity_id)
            info = PersonInfo(
                entity_id,
                state.state if state else None,
                float_attr(state, "latitude"),
                float_attr(state, "longitude"),
            )
            result = classify_person(info, nearby, zones, bool(opts[CONF_NEARBY_GEOMETRIC]))
            if result is None:
                # Unknown: keep what we knew before.
                result = self.person_classes.get(entity_id)
            classes[entity_id] = result
        self.person_classes = classes

        sensors_home = any(
            (st := self.hass.states.get(eid)) is not None and st.state in (STATE_ON, "home")
            for eid in as_list(opts.get(CONF_PRESENCE_SENSORS))
        )
        raw = raw_house_presence(
            list(classes.values()), opts[CONF_HOME_RULE], sensors_home, self.guest
        )
        if raw is None and self.presence.current is None:
            raw = PRESENCE_HOME  # no information at all: assume home (safe for comfort)
        # A departure counts from when the last person really moved, so a restart
        # or a change of the settings does not start the departure delay again.
        raw_since = None
        if raw is not None and raw != PRESENCE_HOME:
            changes = [
                st.last_changed
                for entity_id in as_list(opts.get(CONF_PERSONS))
                if (st := self.hass.states.get(entity_id)) is not None
            ]
            raw_since = max(changes) if changes else None
        self._presence_due = self.presence.update(
            raw,
            now,
            timedelta(minutes=float(opts[CONF_ARRIVAL_DELAY])),
            timedelta(minutes=float(opts[CONF_DEPARTURE_DELAY])),
            raw_since,
        )

        # On the way home (preheat).
        self.arriving = False
        if self.presence.current != PRESENCE_HOME:
            distance = None
            if opts.get(CONF_PROXIMITY_DISTANCE):
                distance = distance_km(self.hass.states.get(opts[CONF_PROXIMITY_DISTANCE]))
            direction = None
            if opts.get(CONF_PROXIMITY_DIRECTION):
                dstate = self.hass.states.get(opts[CONF_PROXIMITY_DIRECTION])
                direction = dstate.state if valid(dstate) else None
            travel = None
            if opts.get(CONF_TRAVEL_TIME):
                travel = minutes_value(self.hass.states.get(opts[CONF_TRAVEL_TIME]))
            if distance is not None or travel is not None:
                self.arriving = is_arriving(
                    distance,
                    direction,
                    travel,
                    float(opts[CONF_ARRIVAL_DISTANCE]),
                    float(opts[CONF_ARRIVAL_MINUTES]),
                    bool(opts.get(CONF_PROXIMITY_DIRECTION)),
                )

        # Automatic vacation after a long time far away.
        hours = float(opts[CONF_AUTO_VACATION_HOURS] or 0)
        if self.guest:
            # Guests make the house home, not the people: the automatic vacation
            # waits (it does not apply while they are there) and goes on after
            # them, unless one of the people came near or home meanwhile (the
            # people only: presence sensors in the house see the guests too).
            people = raw_house_presence(list(classes.values()), opts[CONF_HOME_RULE], False, False)
            if people is not None and people != PRESENCE_FAR:
                self.auto_vacation = False
                self.auto_vacation_reset = None
        elif self.presence.current != PRESENCE_FAR:
            self.auto_vacation = False
            self.auto_vacation_reset = None
        elif self.arriving:
            # On the way home: the automatic vacation ends (the house preheats)
            # and the time far away counts again from now.
            self.auto_vacation = False
            self.auto_vacation_reset = now
        elif hours > 0:
            far = self.presence.far_for(now)
            if self.auto_vacation_reset is not None:
                far = min(far, now - self.auto_vacation_reset)
            if far >= timedelta(hours=hours):
                self.auto_vacation = True

    @property
    def presence_state(self) -> str | None:
        """Effective house presence."""
        return self.presence.current

    def _update_guest(self, now: datetime) -> None:
        """End guest mode when it expires."""
        if self.guest and self.guest_until and now >= self.guest_until:
            self.guest = False
            self.guest_until = None

    async def async_set_guest(self, on: bool) -> None:
        """Turn guest mode on or off."""
        self.guest = on
        hours = float(self.options[CONF_GUEST_EXPIRE_HOURS] or 0)
        self.guest_until = dt_util.utcnow() + timedelta(hours=hours) if on and hours > 0 else None
        await self.async_evaluate_or_notify()

    async def async_set_pause(self, on: bool) -> None:
        """Pause or resume."""
        self.paused = on
        await self.async_evaluate_or_notify()

    async def async_set_mode(self, mode: str) -> None:
        """Set the global mode."""
        if mode not in MODES:
            raise HomeAssistantError(f"Unknown mode {mode}")
        self.mode = mode
        if mode != MODE_VACATION:
            self.auto_vacation = False
        await self.async_evaluate_or_notify()

    async def async_set_vacation(
        self, start: datetime | None, end: datetime | None, *, partial: bool = False
    ) -> None:
        """Set the vacation period. With ``partial`` only given values change."""
        if not partial or start is not None:
            self.vacation_start = start
        if not partial or end is not None:
            self.vacation_end = end
        await self.async_evaluate_or_notify()

    async def async_evaluate_or_notify(self) -> None:
        """Evaluate if started, else just refresh the entities."""
        self.async_save()
        if self.started:
            await self.async_evaluate()
        else:
            self.async_notify_listeners()

    # ------------------------------------------------------------------
    # Vacation
    # ------------------------------------------------------------------
    def _vacation_resume(self) -> datetime | None:
        """When the heating starts again before the end of the vacation."""
        if self.vacation_end is None:
            return None
        # In UTC, so the preheating lasts the real number of hours across a DST change.
        return dt_util.as_utc(self.vacation_end) - timedelta(
            hours=float(self.options[CONF_VACATION_PREHEAT])
        )

    def _update_vacation(self, now: datetime) -> None:
        """Forget a vacation period that has ended."""
        if self.vacation_end and now >= self.vacation_end:
            self.vacation_start = None
            self.vacation_end = None

    def vacation_until(self, now: datetime) -> datetime | None:
        """When the vacation level ends (the preheating starts); None when unknown."""
        if self.mode == MODE_VACATION:
            return None  # the mode, until it is changed
        resume = self._vacation_resume()
        return resume if resume is not None and resume > now else None

    def vacation_active(self, now: datetime | None = None) -> bool:
        """Return True when the vacation level applies.

        Guest mode wins over every vacation (planned, automatic or the mode):
        while it is on the rooms follow the schedule; the vacation goes on
        when it is turned off.
        """
        if self.guest:
            return False
        return self._vacation_set(now)

    def vacation_suspended(self, now: datetime | None = None) -> bool:
        """A vacation would apply, but guest mode is on."""
        return self.guest and self._vacation_set(now)

    def _vacation_set(self, now: datetime | None = None) -> bool:
        """A vacation applies (mode, automatic or planned), guests aside."""
        now = now or dt_util.utcnow()
        if self.mode == MODE_VACATION:
            return True
        # The preheating before the end of a planned vacation wins over the
        # automatic vacation (everyone has been far away for a long time).
        if self.vacation_preheating(now):
            return False
        if self.auto_vacation:
            return True
        if self.vacation_start is None and self.vacation_end is None:
            return False
        # Only an end: the vacation runs from now until then.
        start_ok = self.vacation_start is None or now >= self.vacation_start
        resume = self._vacation_resume()
        end_ok = resume is None or now < resume
        return start_ok and end_ok

    def vacation_preheating(self, now: datetime | None = None) -> bool:
        """The last hours before the end of a vacation: the schedule applies again."""
        now = now or dt_util.utcnow()
        if self.mode == MODE_VACATION or self.vacation_end is None:
            return False
        resume = self._vacation_resume()
        started = self.vacation_start is None or now >= self.vacation_start
        return started and resume is not None and resume <= now < self.vacation_end

    # ------------------------------------------------------------------
    # Calendar / workday
    # ------------------------------------------------------------------
    def _update_calendar(self) -> None:
        """Read the current calendar event (profile or level name)."""
        calendar = self.options.get(CONF_CALENDAR)
        self.calendar_message = None
        self.calendar_end = None
        if not calendar:
            return
        state = self.hass.states.get(calendar)
        if state is not None and state.state == STATE_ON:
            message = state.attributes.get("message")
            self.calendar_message = str(message).strip() if message else None
            self.calendar_end = from_iso(state.attributes.get("end_time"))

    async def _async_refresh_calendar(self) -> None:
        """Read the calendar events from the start of today to the next days.

        An event titled with a profile name selects it for the whole schedule
        day it covers part of, today and the coming days alike, so the plan
        and the optimal start match what happens on that day.
        """
        calendar = self.options.get(CONF_CALENDAR)
        if not calendar or not self.hass.services.has_service("calendar", "get_events"):
            self.calendar_events = []
            return
        now = dt_util.now()
        boundary = timedelta(minutes=self.day_boundary_minutes)
        # The start of the schedule day of now (an event that ended today counts).
        day_start = datetime.combine((now - boundary).date(), time(0), tzinfo=now.tzinfo) + boundary
        try:
            response = await self.hass.services.async_call(
                "calendar",
                "get_events",
                {
                    "start_date_time": day_start.isoformat(),
                    "end_date_time": (day_start + timedelta(days=CALENDAR_DAYS)).isoformat(),
                },
                target={"entity_id": calendar},
                blocking=True,
                return_response=True,
            )
        except (HomeAssistantError, ValueError) as err:
            _LOGGER.debug("calendar.get_events failed: %s", err)
            return
        events: list[tuple[datetime, datetime, str]] = []
        for item in ((response or {}).get(calendar) or {}).get("events") or []:
            start, end = calendar_moment(item.get("start")), calendar_moment(item.get("end"))
            summary = str(item.get("summary") or "").strip()
            if start is not None and end is not None and summary:
                events.append((start, end, summary))
        self.calendar_events = sorted(events)

    def calendar_profile(self, day: date, profiles: Iterable[str]) -> str | None:
        """Profile named by a calendar event that covers part of a schedule day."""
        names = {name.lower() for name in profiles}
        boundary = timedelta(minutes=self.day_boundary_minutes)
        zone = dt_util.get_default_time_zone()
        start = datetime.combine(day, time(0), tzinfo=zone) + boundary
        end = datetime.combine(day + timedelta(days=1), time(0), tzinfo=zone) + boundary
        for event_start, event_end, summary in self.calendar_events:
            if summary.lower() in names and event_start < end and event_end > start:
                return summary.lower()
        return None

    def is_workday(self, day: date) -> bool:
        """Return whether a day is a workday."""
        today = dt_util.now().date()  # local calendar day
        sensor = self.options.get(CONF_WORKDAY_SENSOR)
        if sensor and day == today:
            state = self.hass.states.get(sensor)
            if valid(state):
                return state.state == STATE_ON  # type: ignore[union-attr]
        cached = self.workday_cache.get(day.isoformat())
        if cached is not None:
            return cached
        return day.weekday() < 5

    async def _async_refresh_workdays(self) -> None:
        """Ask the Workday integration about the next days (holidays)."""
        sensor = self.options.get(CONF_WORKDAY_SENSOR)
        if not sensor or not self.hass.services.has_service("workday", "check_date"):
            return
        today = dt_util.now().date()  # local calendar day
        for offset in range(CALENDAR_DAYS):
            day = today + timedelta(days=offset)
            key = day.isoformat()
            if key in self.workday_cache:
                continue
            try:
                response = await self.hass.services.async_call(
                    "workday",
                    "check_date",
                    {"check_date": day},
                    target={"entity_id": sensor},
                    blocking=True,
                    return_response=True,
                )
            except (HomeAssistantError, ValueError) as err:
                _LOGGER.debug("workday.check_date failed: %s", err)
                return
            result = (response or {}).get(sensor, {})
            if isinstance(result, dict) and "workday" in result:
                self.workday_cache[key] = bool(result["workday"])
        # Drop old days.
        for key in [k for k in self.workday_cache if k < today.isoformat()]:
            del self.workday_cache[key]

    @property
    def day_boundary_minutes(self) -> int:
        """Return the schedule day boundary in minutes."""
        boundary = parse_clock(self.options[CONF_DAY_BOUNDARY])
        return boundary.hour * 60 + boundary.minute

    # ------------------------------------------------------------------
    # Weather, season and energy
    # ------------------------------------------------------------------
    def outdoor_temperature(self) -> float | None:
        """Return the current outdoor temperature."""
        sensor = self.options.get(CONF_OUTDOOR_SENSOR)
        if sensor:
            value = temp_state(self.hass, sensor, self.unit)
            if value is not None:
                return value
        weather = self.options.get(CONF_WEATHER)
        if weather:
            state = self.hass.states.get(weather)
            return to_celsius(float_attr(state, "temperature"), self._weather_unit(state))
        return None

    @property
    def outdoor_now(self) -> float | None:
        """Latest outdoor temperature, None when unknown (or older than the window)."""
        return self.outdoor.latest(dt_util.utcnow())

    @property
    def outdoor_configured(self) -> bool:
        """An outdoor temperature sensor or a weather entity is set for the house."""
        return bool(self.options.get(CONF_OUTDOOR_SENSOR) or self.options.get(CONF_WEATHER))

    def _weather_unit(self, state: State | None) -> str:
        """Temperature unit of the weather entity."""
        unit = state.attributes.get("temperature_unit") if state is not None else None
        return str(unit) if unit else system_unit(self.hass)

    @property
    def unit(self) -> str:
        """Temperature unit of this house for the user (°C or °F)."""
        return FAHRENHEIT if is_fahrenheit(self.options.get(CONF_TEMP_UNIT)) else CELSIUS

    def _sample_outdoor(self) -> None:
        """Record the current outdoor temperature."""
        value = self.outdoor_temperature()
        if value is not None:
            self.outdoor.add(dt_util.utcnow(), value)

    def _update_weather(self, now: datetime) -> None:
        """Update the outdoor cutoff and the heating season."""
        opts = self.options
        average = self.outdoor.average(now, self.average_hours)
        self.outdoor.update_cutoff(
            average, float(opts[CONF_CUTOFF_TEMP]), float(opts[CONF_CUTOFF_HYSTERESIS])
        )
        self.outdoor.update_forecast_cutoff(
            self.forecast_mean if opts[CONF_CUTOFF_ENABLED] else None,
            float(opts[CONF_CUTOFF_TEMP]),
            float(opts[CONF_CUTOFF_HYSTERESIS]),
        )
        self.outdoor.update_season(
            dt_util.as_local(now).date(),
            opts[CONF_SEASON_MODE],
            str(opts[CONF_SEASON_START]),
            str(opts[CONF_SEASON_END]),
            int(opts[CONF_SEASON_DAYS]),
            float(opts[CONF_SEASON_TEMP]),
        )

    @property
    def outdoor_average(self) -> float | None:
        """Outdoor average used by the cutoff."""
        return self.outdoor.average(dt_util.utcnow(), self.average_hours)

    @property
    def average_hours(self) -> float:
        """Averaging time of the outdoor temperature (at least 1 hour)."""
        return max(1.0, float(self.options[CONF_CUTOFF_AVG_HOURS]))

    @property
    def forecast_mean(self) -> float | None:
        """Mean outdoor temperature forecast for the next forecast hours (None without one).

        Used only with "Use the forecast" on. Each hourly value holds for its
        hour; until the next forecast hour the measured temperature is used.
        """
        opts = self.options
        if not (opts.get(CONF_WEATHER) and opts[CONF_FORECAST_ENABLED] and self.hourly_forecast):
            return None
        now = dt_util.utcnow()
        end = now + timedelta(hours=float(opts[CONF_FORECAST_HOURS]))
        mean, source = expected_outdoor(now, now, end, self.outdoor_now, self.hourly_forecast)
        return mean if source == "forecast" else None

    @property
    def cutoff_reason(self) -> str | None:
        """Why the heating is off because it is warm outside, or why it may run.

        Only means are used, no single forecast hour.
        ``measured``: the measured average reached the threshold (heating off
        until it falls to threshold − hysteresis);
        ``forecast_warm``: the measured average is below the threshold but the
        forecast mean of the next forecast hours reached it (heating off
        earlier, until that mean falls to threshold − hysteresis);
        ``forecast_cold``: the measured average keeps the heating off but the
        forecast mean is at or below threshold − hysteresis (heating may run);
        None: heating may run.
        """
        opts = self.options
        if not opts[CONF_CUTOFF_ENABLED]:
            return None
        threshold = float(opts[CONF_CUTOFF_TEMP])
        resume = threshold - float(opts[CONF_CUTOFF_HYSTERESIS])
        mean = self.forecast_mean
        # An unknown outdoor temperature does not cut the heating off.
        if self.outdoor_average is not None and self.outdoor.cutoff_active:
            return "forecast_cold" if mean is not None and mean <= resume else "measured"
        if mean is not None and self.outdoor.forecast_cutoff_active:
            return "forecast_warm"
        return None

    @property
    def cutoff_active(self) -> bool:
        """Return True when heating is cut off by warm weather."""
        return self.cutoff_reason in ("measured", "forecast_warm")

    @property
    def forecast_cutoff(self) -> bool:
        """The heating is off earlier because the forecast mean is warm."""
        return self.cutoff_reason == "forecast_warm"

    @property
    def season_active(self) -> bool:
        """Return True inside the heating season.

        The automatic season needs an outdoor temperature: without a sensor or
        a weather entity it counts as always on (it can never stay off).
        """
        if self.options[CONF_SEASON_MODE] == SEASON_AUTO and not self.outdoor_configured:
            return True
        return self.outdoor.season_active

    def _forecast_needed(self) -> bool:
        """The hourly forecast is read for the cutoff or an optimal start / stop."""
        if not self.options.get(CONF_WEATHER):
            return False
        return bool(self.options[CONF_FORECAST_ENABLED]) or any(
            room.config.get(CONF_OPTIMAL_START) or room.config.get(CONF_OPTIMAL_STOP)
            for room in self.rooms.values()
        )

    async def _async_refresh_forecast(self, _now: datetime | None = None) -> None:
        """Read the hourly forecast; on the timer, apply it right away."""
        await self._async_read_forecast()
        if _now is not None:
            # The forecast decides the cutoff and the optimal start / stop.
            await self.async_evaluate()

    async def _async_read_forecast(self) -> None:
        """Read the hourly forecast: for the cutoff and the optimal start / stop."""
        weather = self.options.get(CONF_WEATHER)
        if not weather or not self._forecast_needed():
            self.hourly_forecast = []
            return
        try:
            response = await self.hass.services.async_call(
                "weather",
                "get_forecasts",
                {"type": "hourly"},
                target={"entity_id": weather},
                blocking=True,
                return_response=True,
            )
        except (HomeAssistantError, ValueError) as err:
            _LOGGER.debug("Forecast not available: %s", err)
            self.hourly_forecast = []
            return
        forecast = ((response or {}).get(weather) or {}).get("forecast") or []
        unit = self._weather_unit(self.hass.states.get(weather))
        hourly: list[tuple[datetime, float]] = []
        for item in forecast:
            moment = from_iso(item.get("datetime"))
            temp = item.get("temperature")
            if moment is None or temp is None:
                continue
            try:
                value = float(to_celsius(float(temp), unit))
            except (TypeError, ValueError):
                continue
            hourly.append((dt_util.as_utc(moment), value))
        self.hourly_forecast = sorted(hourly)

    def forecast_ahead(self, hours: float = 12) -> list[tuple[datetime, float]]:
        """Hourly forecast for the next hours (the hour that holds now included)."""
        now = dt_util.utcnow()
        end = now + timedelta(hours=hours)
        return [
            (t, v) for t, v in self.hourly_forecast if t + timedelta(hours=1) > now and t <= end
        ]

    def outdoor_between(self, start: datetime, end: datetime) -> tuple[float | None, str]:
        """Mean outdoor temperature expected between two moments ("forecast" or "now")."""
        return expected_outdoor(
            dt_util.utcnow(),
            dt_util.as_utc(start),
            dt_util.as_utc(end),
            self.outdoor_now,
            self.hourly_forecast,
        )

    @property
    def windows_ignored(self) -> bool:
        """Windows are ignored when it is warm outside."""
        limit = self.options.get(CONF_WINDOW_IGNORE_ABOVE)
        if limit in (None, ""):
            return False
        current = self.outdoor_now
        return current is not None and current >= float(limit)

    def house_offsets(self) -> list[tuple[str, float]]:
        """Adjustments shared by all rooms."""
        opts = self.options
        offsets: list[tuple[str, float]] = []
        outdoor = self.outdoor_now
        if (
            opts[CONF_COMP_ENABLED]
            and outdoor is not None
            and outdoor < float(opts[CONF_COMP_BELOW])
        ):
            offsets.append(("compensation", float(opts[CONF_COMP_OFFSET])))
        price = float_state(self.hass, opts.get(CONF_PRICE_SENSOR))
        if price is not None:
            high = opts.get(CONF_PRICE_HIGH)
            low = opts.get(CONF_PRICE_LOW)
            if high not in (None, "") and price >= float(high):
                offsets.append(("tariff_high", float(opts[CONF_PRICE_HIGH_OFFSET])))
            elif low not in (None, "") and price <= float(low):
                offsets.append(("tariff_low", float(opts[CONF_PRICE_LOW_OFFSET])))
        surplus = float_state(self.hass, opts.get(CONF_PV_SENSOR))
        if surplus is not None and surplus >= float(opts[CONF_PV_THRESHOLD]):
            offsets.append(("pv_surplus", float(opts[CONF_PV_OFFSET])))
        return offsets

    def sunny(self) -> bool:
        """Return True when the sun is up and the sky is clear."""
        sun = self.hass.states.get("sun.sun")
        elevation = float_attr(sun, "elevation")
        if elevation is None or elevation < 10:
            return False
        weather = self.options.get(CONF_WEATHER)
        if not weather:
            return False  # solar gain needs the weather entity
        state = self.hass.states.get(weather)
        return valid(state) and state.state in ("sunny", "clear", "partlycloudy")  # type: ignore[union-attr]

    # ------------------------------------------------------------------
    # Overrides
    # ------------------------------------------------------------------
    @property
    def override_scope_house(self) -> bool:
        """Return True if a manual change applies to every room."""
        return self.options[CONF_OVERRIDE_SCOPE] == OVERRIDE_SCOPE_HOUSE

    async def async_clear_overrides(self) -> None:
        """Clear all manual overrides."""
        for room in self.rooms.values():
            room.clear_override()
        await self.async_evaluate_or_notify()

    # ------------------------------------------------------------------
    # Boiler / heat demand
    # ------------------------------------------------------------------
    async def _async_control_boiler(self, now: datetime) -> None:
        """Switch the boiler from the heat demand of the rooms, with minimum on / off times."""
        opts = self.options
        reference = opts.get(CONF_REFERENCE_ROOM)
        needed = max(1, int(opts[CONF_BOILER_MIN_ROOMS]))
        if reference and reference in self.rooms:
            demand = self.rooms[reference].heat_demand
        else:
            count = sum(1 for room in self.rooms.values() if room.heat_demand)
            demand = count >= needed if self.rooms else False
        # More rooms needed than the house has (rooms were removed): the heat
        # source would start only for frost protection.
        if (
            opts.get(CONF_BOILER_ENTITY)
            and not (reference and reference in self.rooms)
            and needed > len(self.rooms)
        ):
            self.notify(
                "boiler_min_rooms",
                f"Rooms needed to start the heat source is {needed}, but the house has "
                f"{len(self.rooms)} rooms: the heat source starts only for frost protection.",
                code="boiler_min_rooms",
                params={"needed": needed, "rooms": len(self.rooms)},
            )
        else:
            self.clear_alert("boiler_min_rooms")
        # Frost protection of any room starts the heat source on its own (no
        # rooms needed, no reference room, also while paused).
        frost = any(room.frost_demand for room in self.rooms.values())
        demand = demand or frost
        self.heat_demand = demand
        # Heating time of the house: while the heat source runs (its real state),
        # without one while at least one room heats.
        configured, source_on = self.heat_source_state()
        running = bool(source_on) if configured else any(r.heating for r in self.rooms.values())
        self._check_source_available(now, configured, source_on)
        if self._source_running_since is not None:
            self.boiler_runtime_s += (now - self._source_running_since).total_seconds()
            self._source_running_since = None
        if running:
            self._source_running_since = now

        self.source_waiting = None
        self._source_wait_until = None
        boiler = opts.get(CONF_BOILER_ENTITY)
        if not boiler:
            return
        want = demand
        if not self.paused:
            # Frost protection of a pause is over once the pause ends.
            self._frost_started = False
        else:
            # Paused: only frost protection; a heat source started for it is
            # stopped again when it is no longer needed.
            if frost:
                want = True
            elif self._frost_started:
                want = False
            else:
                return
        state = self.hass.states.get(boiler)
        if not valid(state):
            return
        is_on = state.state not in ("off",)  # type: ignore[union-attr]
        if is_on == want:
            return
        if self.boiler_changed is not None:
            minimum = timedelta(
                minutes=float(opts[CONF_BOILER_MIN_ON] if is_on else opts[CONF_BOILER_MIN_OFF])
            )
            if now - self.boiler_changed < minimum:
                self.source_waiting = "min_on" if is_on else "min_off"
                self._source_wait_until = self.boiler_changed + minimum
                return
        context = self.new_context()
        domain = boiler.split(".", 1)[0]
        try:
            if domain == "climate":
                on_mode = heat_mode(state.attributes.get("hvac_modes"))  # type: ignore[union-attr]
                await self.hass.services.async_call(
                    "climate",
                    "set_hvac_mode",
                    {"entity_id": boiler, "hvac_mode": on_mode if want else "off"},
                    blocking=True,
                    context=context,
                )
            else:
                await self.hass.services.async_call(
                    domain,
                    SERVICE_TURN_ON if want else SERVICE_TURN_OFF,
                    {"entity_id": boiler},
                    blocking=True,
                    context=context,
                )
        except (HomeAssistantError, ValueError) as err:
            _LOGGER.warning("Could not switch the boiler %s: %s", boiler, err)
            return
        self.boiler_on = want
        self.boiler_changed = now
        self._frost_started = bool(want and self.paused)

    def _check_source_available(
        self, now: datetime, configured: bool, source_on: bool | None
    ) -> None:
        """Alert when the heat source has been unavailable for the configured time."""
        entity_id = self.options.get(CONF_BOILER_ENTITY)
        key = f"unavailable_{entity_id}"
        if not configured or source_on is not None:
            if self._source_unavailable_since is not None:
                self._source_unavailable_since = None
                self.clear_alert(key)
            return
        if self._source_unavailable_since is None:
            self._source_unavailable_since = now
        limit = timedelta(minutes=self.alert_unavailable_minutes)
        if now - self._source_unavailable_since >= limit:
            self.notify(
                key,
                f"The heat source {entity_id} has been unavailable for more than "
                f"{limit.total_seconds() / 60:.0f} minutes: the rooms cannot be heated, "
                "not even for frost protection.",
                code="source_unavailable",
                params={"entity": entity_id, "minutes": round(limit.total_seconds() / 60)},
            )

    def _check_weather_alerts(self, now: datetime) -> None:
        """Weather functions without an outdoor temperature, and an unavailable outdoor source."""
        opts = self.options
        unused: list[str] = []
        if not self.outdoor_configured:
            if opts[CONF_CUTOFF_ENABLED]:
                unused.append("cutoff")
            if opts[CONF_SEASON_MODE] == SEASON_AUTO:
                unused.append("season_auto")
            if opts[CONF_COMP_ENABLED]:
                unused.append("compensation")
            if opts.get(CONF_WINDOW_IGNORE_ABOVE) not in (None, ""):
                unused.append("window_ignore")
        if opts[CONF_FORECAST_ENABLED] and not (
            opts.get(CONF_WEATHER) and opts[CONF_CUTOFF_ENABLED]
        ):
            unused.append("forecast")
        if unused:
            self.notify(
                "weather_without_source",
                "Weather options are on but cannot work: "
                f"{', '.join(unused)} (they need an outdoor temperature sensor or a weather "
                "entity; the forecast needs a weather entity and the cutoff).",
                code="weather_without_source",
                params={"features": unused},
            )
        else:
            self.clear_alert("weather_without_source")
        # No configured source gives an outdoor temperature (the sensor, else the
        # temperature of the weather entity) for too long.
        sources = [s for s in (opts.get(CONF_OUTDOOR_SENSOR), opts.get(CONF_WEATHER)) if s]
        if not sources or self.outdoor_temperature() is not None:
            if self._outdoor_unavailable_since is not None:
                self._outdoor_unavailable_since = None
                self.clear_alert("unavailable_outdoor")
            return
        if self._outdoor_unavailable_since is None:
            self._outdoor_unavailable_since = now
        limit = timedelta(minutes=self.alert_unavailable_minutes)
        if now - self._outdoor_unavailable_since >= limit:
            names = ", ".join(sources)
            self.notify(
                "unavailable_outdoor",
                f"No outdoor temperature from {names} for more than "
                f"{limit.total_seconds() / 60:.0f} minutes: the cutoff, the automatic season, "
                "the compensation and the optimal stop cannot use it.",
                code="outdoor_unavailable",
                params={
                    "entity": sources[0],
                    "entities": sources,
                    "minutes": round(limit.total_seconds() / 60),
                },
            )

    def heat_source_state(self) -> tuple[bool, bool | None]:
        """(configured, running) of the heat source of the house (the boiler entity).

        ``running`` is None while the entity is unavailable or unknown.
        """
        entity_id = self.options.get(CONF_BOILER_ENTITY)
        if not entity_id:
            return False, None
        state = self.hass.states.get(entity_id)
        if not valid(state):
            return True, None
        if entity_id.startswith("climate.") and "hvac_action" in state.attributes:  # type: ignore[union-attr]
            # A thermostat in heat mode may be idle: it runs only while heating.
            return True, state.attributes["hvac_action"] == "heating"  # type: ignore[union-attr]
        return True, state.state != "off"  # type: ignore[union-attr]

    def _check_room_difference(self) -> None:
        """Alert when some rooms stay cold while others reached their target."""
        limit = float(self.options[CONF_ROOM_DIFF_ALERT] or 0)
        if limit <= 0 or len(self.rooms) < 2:
            return
        gaps = {
            room.name: gap
            for room in self.rooms.values()
            if (gap := room.temperature_gap()) is not None
        }
        if not gaps:
            return
        cold = {name: gap for name, gap in gaps.items() if gap > limit}
        reached = [name for name, gap in gaps.items() if gap <= 0]
        if cold and reached:
            text = ", ".join(
                f"{name} ({delta_from_celsius(gap, self.unit):.1f} {self.unit} below target)"
                for name, gap in cold.items()
            )
            self.notify(
                "room_difference",
                f"Some rooms stay cold while others are warm: {text}.",
                repeat=timedelta(hours=6),
                code="room_difference",
                params={
                    "rooms": [
                        [name, round(delta_from_celsius(gap, self.unit), 1)]
                        for name, gap in cold.items()
                    ]
                },
            )
        else:
            self.clear_alert("room_difference")

    # ------------------------------------------------------------------
    # Contexts & notifications
    # ------------------------------------------------------------------
    def new_context(self) -> Context:
        """Create a context for our own service calls."""
        context = Context()
        self._own_contexts[context.id] = None
        while len(self._own_contexts) > 500:
            self._own_contexts.pop(next(iter(self._own_contexts)))
        return context

    def is_own_context(self, context: Context | None) -> bool:
        """Return True if the context was created by us."""
        if context is None:
            return False
        return context.id in self._own_contexts or (
            context.parent_id is not None and context.parent_id in self._own_contexts
        )

    @property
    def alert_unavailable_minutes(self) -> float:
        """Minutes before an unavailable device triggers an alert."""
        return float(self.options[CONF_ALERT_UNAVAILABLE_MINUTES])

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

        ``code`` and ``params`` let the card show it in its language; ``room``
        is the room it belongs to (None: the whole house).
        """
        now = dt_util.utcnow()
        self.active_alerts[key] = {
            "code": code,
            "params": params or {},
            "room": room,
            "message": message,
        }
        last = self._alerts.get(key)
        if last is not None and (repeat is None or now - last < repeat):
            return
        self._alerts[key] = now
        service = self.options.get(CONF_NOTIFY_SERVICE)
        if service:
            domain, _, name = str(service).partition(".")
            if not name:
                domain, name = "notify", domain
            self.hass.async_create_task(self._async_call_notify(domain, name, title, message))
        else:
            persistent_notification.async_create(
                self.hass, message, title=title, notification_id=f"{DOMAIN}_{key}"
            )
        _LOGGER.info("%s: %s", title, message)

    async def _async_call_notify(self, domain: str, name: str, title: str, message: str) -> None:
        """Send an alert with the notify service (persistent notification if it fails)."""
        try:
            await self.hass.services.async_call(
                domain, name, {"title": title, "message": message}, blocking=True
            )
        except HomeAssistantError as err:
            _LOGGER.warning("Notification via %s.%s failed: %s", domain, name, err)
            persistent_notification.async_create(self.hass, message, title=title)

    def alerts_for(self, room: Room) -> list[dict[str, Any]]:
        """Alerts that apply to a room: its own and those of the whole house.

        Cold rooms (while others are warm) are told only in those rooms.
        """
        result = []
        for key, alert in self.active_alerts.items():
            if alert.get("room") not in (None, room.id):
                continue
            if alert.get("code") == "room_difference" and room.name not in [
                name for name, _gap in alert["params"].get("rooms", [])
            ]:
                continue
            result.append({"key": key, **{k: v for k, v in alert.items() if k != "room"}})
        return result

    def clear_alert(self, key: str) -> None:
        """Allow an alert to be sent again."""
        self.active_alerts.pop(key, None)
        if self._alerts.pop(key, None) is not None and not self.options.get(CONF_NOTIFY_SERVICE):
            persistent_notification.async_dismiss(self.hass, f"{DOMAIN}_{key}")

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------
    def diagnostics(self) -> dict[str, Any]:
        """Return diagnostics data."""
        return {
            "mode": self.mode,
            "paused": self.paused,
            "guest": self.guest,
            "presence": self.presence.current,
            "presence_history": self.presence.history,
            "person_classes": self.person_classes,
            "arriving": self.arriving,
            "vacation_active": self.vacation_active(),
            "vacation_preheating": self.vacation_preheating(),
            "vacation_start": iso(self.vacation_start),
            "vacation_end": iso(self.vacation_end),
            "outdoor_latest": self.outdoor_now,
            "outdoor_average": self.outdoor_average,
            "cutoff_active": self.cutoff_active,
            "forecast_cutoff": self.forecast_cutoff,
            "season_active": self.season_active,
            "daily_means": self.outdoor.daily_means,
            "heat_demand": self.heat_demand,
            "house_offsets": self.house_offsets(),
            "calendar_message": self.calendar_message,
            "last_evaluation": iso(self._last_eval),
            "rooms": {room.name: room.diagnostics() for room in self.rooms.values()},
        }
