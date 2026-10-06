"""HOS rules independent of Django, HTTP, maps, and rendering.

Limits apply to driving, rather than preventing all non-driving work. Ordinary
breaks keep the 14-hour window running. A 10-hour rest resets the shift; a
34-hour rest also restarts the cycle. No split-sleeper exceptions are modelled.
"""

from datetime import UTC, datetime, timedelta
from math import floor
from zoneinfo import ZoneInfo

from .domain import METERS_PER_MILE, SECONDS_PER_HOUR, DutyEvent

MAX_SHIFT_DRIVING_SECONDS = 11 * SECONDS_PER_HOUR
MAX_SHIFT_WINDOW_SECONDS = 14 * SECONDS_PER_HOUR
MAX_DRIVING_BEFORE_BREAK_SECONDS = 8 * SECONDS_PER_HOUR
REQUIRED_BREAK_SECONDS = 30 * 60
REQUIRED_DAILY_REST_SECONDS = 10 * SECONDS_PER_HOUR
REQUIRED_CYCLE_RESTART_SECONDS = 34 * SECONDS_PER_HOUR
MAX_CYCLE_SECONDS = 70 * SECONDS_PER_HOUR
MAX_DISTANCE_BETWEEN_FUEL_MILES = 1000
SERVICE_SECONDS = SECONDS_PER_HOUR


class TripScheduler:
    def __init__(
        self,
        route,
        locations,
        departure,
        terminal_timezone,
        cycle_used_hours,
        previous_daily_hours=None,
        rest_status="off_duty",
    ):
        self.route = route
        self.locations = locations
        self.current_time = departure.astimezone(UTC)
        self.departure = self.current_time
        self.terminal_timezone = ZoneInfo(terminal_timezone)
        self.driving_progress_seconds = 0
        self.shift_start_time = None
        self.shift_driving_seconds = 0
        self.driving_since_break_seconds = 0
        self.last_fuel_distance_meters = 0.0
        self.rest_status = rest_status
        self.events = []
        self.non_driving_seconds = 0
        self.initial_cycle_seconds = round(cycle_used_hours * SECONDS_PER_HOUR)
        self.previous_daily_hours = previous_daily_hours
        self.restart_times = []

    def plan(self):
        self._drive_until(self.route.pickup_driving_seconds)
        self._add_event(
            SERVICE_SECONDS, "on_duty", "pickup", "Load cargo (1 hour)", self.locations[1]
        )
        self._drive_until(self.route.total_driving_seconds)
        self._add_event(
            SERVICE_SECONDS, "on_duty", "dropoff", "Unload cargo (1 hour)", self.locations[2]
        )
        return self.events

    def cycle_seconds_at(self, instant):
        """Use actual terminal calendar days when a seven-day history is supplied."""
        instant_day = instant.astimezone(self.terminal_timezone).date()
        cutoff_day = instant_day - timedelta(days=7)
        valid_restarts = [
            restart_time for restart_time in self.restart_times if restart_time <= instant
        ]
        latest_restart = valid_restarts[-1] if valid_restarts else None
        total_seconds = 0
        if self.previous_daily_hours is None:
            if latest_restart is None:
                total_seconds = self.initial_cycle_seconds
        else:
            departure_day = self.departure.astimezone(self.terminal_timezone).date()
            if latest_restart is None:
                for index, used_hours in enumerate(self.previous_daily_hours):
                    history_day = departure_day - timedelta(days=7 - index)
                    if cutoff_day <= history_day <= instant_day:
                        total_seconds += round(used_hours * SECONDS_PER_HOUR)
        cutoff_time = datetime.combine(
            cutoff_day, datetime.min.time(), self.terminal_timezone
        ).astimezone(UTC)
        if latest_restart:
            cutoff_time = max(cutoff_time, latest_restart)
        for event in self.events:
            if event.duty_status not in ("driving", "on_duty"):
                continue
            start_time = max(event.start_time, cutoff_time)
            end_time = min(event.end_time, instant)
            if end_time > start_time:
                total_seconds += int((end_time - start_time).total_seconds())
        return total_seconds

    def _drive_until(self, target_driving_seconds):
        while self.driving_progress_seconds < target_driving_seconds:
            if len(self.events) > 500:
                raise ValueError("Trip exceeds the supported planning length.")
            if self.shift_start_time is None:
                self.shift_start_time = self.current_time
            remaining_cycle_seconds = MAX_CYCLE_SECONDS - self.cycle_seconds_at(self.current_time)
            if remaining_cycle_seconds <= 0:
                self._rest(
                    REQUIRED_CYCLE_RESTART_SECONDS,
                    "cycle_restart",
                    "34-hour restart: cycle capacity exhausted",
                )
                continue
            remaining_window_seconds = MAX_SHIFT_WINDOW_SECONDS - int(
                (self.current_time - self.shift_start_time).total_seconds()
            )
            remaining_shift_driving_seconds = MAX_SHIFT_DRIVING_SECONDS - self.shift_driving_seconds
            if min(remaining_window_seconds, remaining_shift_driving_seconds) <= 0:
                self._rest(
                    REQUIRED_DAILY_REST_SECONDS,
                    "daily_rest",
                    "10-hour rest: driving shift limit reached",
                )
                continue
            distance_since_fuel_meters = (
                self.route.meters_at(self.driving_progress_seconds) - self.last_fuel_distance_meters
            )
            if (
                distance_since_fuel_meters
                >= MAX_DISTANCE_BETWEEN_FUEL_MILES * METERS_PER_MILE - 0.01
            ):
                self._add_event(
                    REQUIRED_BREAK_SECONDS,
                    "on_duty",
                    "fuel",
                    "Refuel (30 minutes); also satisfies the driving break",
                )
                self.last_fuel_distance_meters = self.route.meters_at(self.driving_progress_seconds)
                continue
            if self.driving_since_break_seconds >= MAX_DRIVING_BEFORE_BREAK_SECONDS:
                self._add_event(
                    REQUIRED_BREAK_SECONDS,
                    "off_duty",
                    "break",
                    "30-minute break after 8 cumulative driving hours",
                )
                continue

            next_fuel_distance_meters = (
                self.last_fuel_distance_meters + MAX_DISTANCE_BETWEEN_FUEL_MILES * METERS_PER_MILE
            )
            next_fuel_driving_seconds = self.route.seconds_at_meters(next_fuel_distance_meters)
            fuel_capacity_seconds = max(
                0, floor(next_fuel_driving_seconds) - self.driving_progress_seconds
            )
            # An integer-second schedule may stop a fraction of a second early.
            if (
                fuel_capacity_seconds == 0
                and next_fuel_distance_meters < self.route.cumulative_meters[-1] - 0.01
            ):
                self._add_event(
                    REQUIRED_BREAK_SECONDS, "on_duty", "fuel", "Refuel before reaching 1,000 miles"
                )
                self.last_fuel_distance_meters = self.route.meters_at(self.driving_progress_seconds)
                continue
            capacities = [
                target_driving_seconds - self.driving_progress_seconds,
                remaining_cycle_seconds,
                remaining_window_seconds,
                remaining_shift_driving_seconds,
                MAX_DRIVING_BEFORE_BREAK_SECONDS - self.driving_since_break_seconds,
            ]
            if next_fuel_distance_meters < self.route.cumulative_meters[-1] - 0.01:
                capacities.append(fuel_capacity_seconds)
            duration_seconds = int(min(capacities))
            # Crossing midnight can release old cycle hours. Recompute at that boundary.
            next_midnight = datetime.combine(
                self.current_time.astimezone(self.terminal_timezone).date() + timedelta(days=1),
                datetime.min.time(),
                self.terminal_timezone,
            ).astimezone(UTC)
            duration_seconds = min(
                duration_seconds, int((next_midnight - self.current_time).total_seconds())
            )
            self._add_event(duration_seconds, "driving", "drive", "Drive along the planned route")

    def _rest(self, duration_seconds, activity, reason):
        self._add_event(duration_seconds, self.rest_status, activity, reason)
        self.shift_start_time = None
        self.shift_driving_seconds = 0
        self.driving_since_break_seconds = 0
        if duration_seconds >= REQUIRED_CYCLE_RESTART_SECONDS:
            self.restart_times.append(self.current_time)
            self.events[-1].cycle_used_hours = 0

    def _add_event(self, duration_seconds, duty_status, activity, reason, location=None):
        if duration_seconds <= 0:
            raise ValueError("A scheduled event must have a positive duration.")
        if duty_status in ("driving", "on_duty") and self.shift_start_time is None:
            self.shift_start_time = self.current_time
        start_progress = self.driving_progress_seconds
        if location is None:
            if start_progress == 0:
                location = self.locations[0]
            elif start_progress == self.route.pickup_driving_seconds:
                location = self.locations[1]
            elif start_progress == self.route.total_driving_seconds:
                location = self.locations[2]
            else:
                location = self.route.location_at(start_progress)
        start_time = self.current_time
        self.current_time += timedelta(seconds=duration_seconds)
        if duty_status == "driving":
            self.driving_progress_seconds += duration_seconds
            self.shift_driving_seconds += duration_seconds
            self.driving_since_break_seconds += duration_seconds
            self.non_driving_seconds = 0
        else:
            self.non_driving_seconds += duration_seconds
            if self.non_driving_seconds >= REQUIRED_BREAK_SECONDS:
                self.driving_since_break_seconds = 0
        distance_miles = (
            self.route.meters_at(self.driving_progress_seconds)
            - self.route.meters_at(start_progress)
        ) / METERS_PER_MILE
        event = DutyEvent(
            start_time,
            self.current_time,
            duty_status,
            activity,
            reason,
            location,
            start_progress,
            self.driving_progress_seconds,
            distance_miles,
            0,
        )
        self.events.append(event)
        event.cycle_used_hours = self.cycle_seconds_at(self.current_time) / SECONDS_PER_HOUR
