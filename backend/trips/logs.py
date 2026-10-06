"""Turn the event timeline into calendar-day sheets and auditable recaps."""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from .domain import METERS_PER_MILE

DUTY_STATUSES = ("off_duty", "sleeper_berth", "driving", "on_duty")


def build_daily_logs(scheduler):
    events = scheduler.events
    terminal_zone = ZoneInfo(scheduler.terminal_timezone.key)
    first_day = scheduler.departure.astimezone(terminal_zone).date()
    last_day = (events[-1].end_time - timedelta(microseconds=1)).astimezone(terminal_zone).date()
    history = {
        first_day - timedelta(days=7 - index): hours
        for index, hours in enumerate(scheduler.previous_daily_hours or [0] * 7)
    }
    daily_logs = []
    day = first_day
    while day <= last_day:
        day_start = datetime.combine(day, datetime.min.time(), terminal_zone).astimezone(UTC)
        day_end = datetime.combine(
            day + timedelta(days=1), datetime.min.time(), terminal_zone
        ).astimezone(UTC)
        if int((day_end - day_start).total_seconds()) != 86400:
            raise ValueError(
                "This trip crosses a daylight-saving clock change. Choose another departure date; 23/25-hour logs are outside this assessment's 24-hour sheet model."
            )
        segments = []
        remarks = []
        for event_index, event in enumerate(events):
            start_time, end_time = max(day_start, event.start_time), min(day_end, event.end_time)
            if start_time >= end_time:
                continue
            total_duration = event.duration_seconds
            fraction_start = (start_time - event.start_time).total_seconds() / total_duration
            fraction_end = (end_time - event.start_time).total_seconds() / total_duration
            progress_start = (
                event.start_driving_seconds
                + (event.end_driving_seconds - event.start_driving_seconds) * fraction_start
            )
            progress_end = (
                event.start_driving_seconds
                + (event.end_driving_seconds - event.start_driving_seconds) * fraction_end
            )
            segments.append(
                {
                    "start_seconds": int((start_time - day_start).total_seconds()),
                    "end_seconds": int((end_time - day_start).total_seconds()),
                    "duty_status": event.duty_status,
                    "activity": event.activity,
                    "location": event.location.as_dict(),
                    "distance_miles": (
                        scheduler.route.meters_at(progress_end)
                        - scheduler.route.meters_at(progress_start)
                    )
                    / METERS_PER_MILE,
                }
            )
            previous_event = events[event_index - 1] if event_index else None
            status_changed = (
                previous_event is None or previous_event.duty_status != event.duty_status
            )
            if event.start_time >= day_start and status_changed:
                remarks.append(
                    {
                        "seconds": int((event.start_time - day_start).total_seconds()),
                        "time": event.start_time.astimezone(terminal_zone).strftime("%H:%M"),
                        "location": event.location.label,
                        "activity": event.reason,
                    }
                )
        if segments[0]["start_seconds"] > 0:
            segments.insert(
                0,
                {
                    "start_seconds": 0,
                    "end_seconds": segments[0]["start_seconds"],
                    "duty_status": "off_duty",
                    "activity": "before_trip",
                    "location": scheduler.locations[0].as_dict(),
                    "distance_miles": 0,
                },
            )
        if segments[-1]["end_seconds"] < 86400:
            off_duty_start = segments[-1]["end_seconds"]
            if segments[-1]["duty_status"] != "off_duty":
                remarks.append(
                    {
                        "seconds": off_duty_start,
                        "time": (day_start + timedelta(seconds=off_duty_start))
                        .astimezone(terminal_zone)
                        .strftime("%H:%M"),
                        "location": scheduler.locations[2].label,
                        "activity": "Trip completed; off duty for the remainder of the day (assumed)",
                    }
                )
            segments.append(
                {
                    "start_seconds": off_duty_start,
                    "end_seconds": 86400,
                    "duty_status": "off_duty",
                    "activity": "after_trip",
                    "location": scheduler.locations[2].as_dict(),
                    "distance_miles": 0,
                }
            )
        totals = {
            status: sum(
                segment["end_seconds"] - segment["start_seconds"]
                for segment in segments
                if segment["duty_status"] == status
            )
            for status in DUTY_STATUSES
        }
        history[day] = (totals["driving"] + totals["on_duty"]) / 3600
        seven_day_hours = sum(history.get(day - timedelta(days=offset), 0) for offset in range(7))
        eight_day_hours = sum(history.get(day - timedelta(days=offset), 0) for offset in range(8))
        restarted_today = any(
            restart_time.astimezone(terminal_zone).date() == day
            for restart_time in scheduler.restart_times
        )
        end_of_day_cycle = (
            scheduler.cycle_seconds_at(
                min(day_end - timedelta(microseconds=1), events[-1].end_time)
            )
            / 3600
        )
        tomorrow_cycle = scheduler.cycle_seconds_at(day_end) / 3600
        daily_logs.append(
            {
                "date": day.isoformat(),
                "segments": segments,
                "remarks": remarks,
                "totals_seconds": totals,
                "distance_miles": round(sum(segment["distance_miles"] for segment in segments), 3),
                "recap": {
                    "on_duty_hours": round(history[day], 3),
                    "last_seven_days_hours": round(seven_day_hours, 3),
                    "last_eight_days_hours": round(eight_day_hours, 3),
                    "hours_available_tomorrow": round(max(0, 70 - tomorrow_cycle), 3),
                    "cycle_remaining_hours": round(max(0, 70 - end_of_day_cycle), 3),
                    "restart_completed_today": restarted_today,
                    "sixty_hour_schedule": "N/A — 70-hour / 8-day schedule",
                },
            }
        )
        day += timedelta(days=1)
    return daily_logs
