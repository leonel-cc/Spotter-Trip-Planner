"""Small, explicit data structures shared by routing and the HOS scheduler."""

from bisect import bisect_right
from dataclasses import dataclass
from datetime import datetime
from math import asin, cos, radians, sin, sqrt

METERS_PER_MILE = 1609.344
SECONDS_PER_HOUR = 3600


@dataclass
class Location:
    label: str
    latitude: float
    longitude: float

    def as_dict(self):
        return {"label": self.label, "latitude": self.latitude, "longitude": self.longitude}


def distance_between_coordinates(first, second):
    first_longitude, first_latitude = map(radians, first)
    second_longitude, second_latitude = map(radians, second)
    latitude_difference = second_latitude - first_latitude
    longitude_difference = second_longitude - first_longitude
    haversine = (
        sin(latitude_difference / 2) ** 2
        + cos(first_latitude) * cos(second_latitude) * sin(longitude_difference / 2) ** 2
    )
    return 6_371_000 * 2 * asin(min(1, sqrt(haversine)))


@dataclass
class RoutePath:
    coordinates: list
    cumulative_seconds: list[float]
    cumulative_meters: list[float]
    pickup_driving_seconds: int
    total_driving_seconds: int
    instructions: list[dict]
    provider: str
    truck_profile: bool

    @property
    def distance_miles(self):
        return self.cumulative_meters[-1] / METERS_PER_MILE

    def meters_at(self, driving_seconds):
        return self._interpolate(self.cumulative_seconds, self.cumulative_meters, driving_seconds)

    def seconds_at_meters(self, distance_meters):
        return self._interpolate(self.cumulative_meters, self.cumulative_seconds, distance_meters)

    def location_at(self, driving_seconds):
        edge_index, fraction = self._edge_at(self.cumulative_seconds, driving_seconds)
        first, second = self.coordinates[edge_index : edge_index + 2]
        longitude = first[0] + (second[0] - first[0]) * fraction
        latitude = first[1] + (second[1] - first[1]) * fraction
        return Location(
            f"{latitude:.4f}, {longitude:.4f} (estimated route position)", latitude, longitude
        )

    @staticmethod
    def _edge_at(cumulative_values, target):
        edge_index = max(
            0, min(bisect_right(cumulative_values, target) - 1, len(cumulative_values) - 2)
        )
        edge_length = cumulative_values[edge_index + 1] - cumulative_values[edge_index]
        fraction = (target - cumulative_values[edge_index]) / edge_length if edge_length else 0
        return edge_index, max(0, min(1, fraction))

    def _interpolate(self, source_values, destination_values, target):
        edge_index, fraction = self._edge_at(source_values, target)
        return (
            destination_values[edge_index]
            + (destination_values[edge_index + 1] - destination_values[edge_index]) * fraction
        )


@dataclass
class DutyEvent:
    start_time: datetime
    end_time: datetime
    duty_status: str
    activity: str
    reason: str
    location: Location
    start_driving_seconds: int
    end_driving_seconds: int
    distance_miles: float
    cycle_used_hours: float

    @property
    def duration_seconds(self):
        return int((self.end_time - self.start_time).total_seconds())

    def as_dict(self):
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duty_status": self.duty_status,
            "activity": self.activity,
            "reason": self.reason,
            "location": self.location.as_dict(),
            "duration_seconds": self.duration_seconds,
            "distance_miles": round(self.distance_miles, 3),
            "cycle_used_hours": round(self.cycle_used_hours, 3),
        }
