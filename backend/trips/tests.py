"""Regression tests for rules, calendar logs, and the public API contract."""

from datetime import datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.test import SimpleTestCase, override_settings
from rest_framework.test import APIClient

from .domain import METERS_PER_MILE, Location, RoutePath
from .logs import build_daily_logs
from .routing import (
    RoutingError,
    describe_route_location,
    normalize_ors_route,
    normalize_osrm_route,
    search_locations,
)
from .scheduler import TripScheduler
from .serializers import TripPlanSerializer

LOCATIONS = [
    Location("Chicago, IL", 41.8781, -87.6298),
    Location("Indianapolis, IN", 39.7684, -86.1581),
    Location("Dallas, TX", 32.7767, -96.797),
]


def example_route(driving_hours=20, distance_miles=1200, pickup_hours=3):
    return RoutePath(
        [[-87.6298, 41.8781], [-86.1581, 39.7684], [-96.797, 32.7767]],
        [0, pickup_hours * 3600, driving_hours * 3600],
        [
            0,
            distance_miles * METERS_PER_MILE * pickup_hours / driving_hours,
            distance_miles * METERS_PER_MILE,
        ],
        pickup_hours * 3600,
        driving_hours * 3600,
        [],
        "test",
        False,
    )


def example_payload():
    return {
        "current_location": LOCATIONS[0].as_dict(),
        "pickup_location": LOCATIONS[1].as_dict(),
        "dropoff_location": LOCATIONS[2].as_dict(),
        "cycle_used_hours": 12,
        "previous_daily_hours": [2, 2, 2, 2, 2, 1, 1],
        "departure_time": "2026-10-06T06:00",
        "terminal_timezone": "America/Chicago",
        "rest_status": "off_duty",
        "log_details": {
            "driver_name": "Example Driver",
            "carrier_name": "Example Carrier",
            "main_office_address": "Example Office",
            "home_terminal_address": "Example Terminal",
            "truck_number": "EX-1",
            "trailer_number": "EX-2",
            "shipping_document": "EX-BOL",
            "shipper_name": "Example Shipper",
            "commodity": "Example cargo",
            "sample_details": True,
        },
    }


class SchedulerTests(SimpleTestCase):
    def scheduler(
        self,
        route=None,
        used_hours=12,
        history=None,
        departure="2026-10-06T06:00",
        rest_status="off_duty",
    ):
        scheduler = TripScheduler(
            route or example_route(),
            LOCATIONS,
            datetime.fromisoformat(departure).replace(tzinfo=ZoneInfo("America/Chicago")),
            "America/Chicago",
            used_hours,
            history if history is not None else [2, 2, 2, 2, 2, 1, 1],
            rest_status,
        )
        scheduler.plan()
        return scheduler

    def assert_valid_driving_limits(self, scheduler):
        shift_start = None
        shift_driving = 0
        driving_since_break = 0
        non_driving = 0
        fuel_distance = 0
        for event in scheduler.events:
            self.assertGreater(event.duration_seconds, 0)
            if event.duty_status in ("on_duty", "driving") and shift_start is None:
                shift_start = event.start_time
            if event.duty_status == "driving":
                shift_driving += event.duration_seconds
                driving_since_break += event.duration_seconds
                self.assertLessEqual(shift_driving, 11 * 3600)
                self.assertLessEqual(driving_since_break, 8 * 3600)
                self.assertLessEqual((event.end_time - shift_start).total_seconds(), 14 * 3600)
                self.assertLessEqual(
                    scheduler.cycle_seconds_at(event.end_time - timedelta(microseconds=1)),
                    70 * 3600,
                )
                non_driving = 0
                self.assertLessEqual(
                    scheduler.route.meters_at(event.end_driving_seconds) - fuel_distance,
                    1000 * METERS_PER_MILE + 0.01,
                )
            else:
                non_driving += event.duration_seconds
                if non_driving >= 1800:
                    driving_since_break = 0
                if event.duration_seconds >= 10 * 3600 and event.duty_status in (
                    "off_duty",
                    "sleeper_berth",
                ):
                    shift_start, shift_driving = None, 0
            if event.activity == "fuel":
                fuel_distance = scheduler.route.meters_at(event.start_driving_seconds)

    def test_long_trip_limits_and_complete_calendar_logs(self):
        scheduler = self.scheduler(example_route(60, 3500))
        self.assert_valid_driving_limits(scheduler)
        self.assertEqual(
            sum(
                event.duration_seconds
                for event in scheduler.events
                if event.duty_status == "driving"
            ),
            60 * 3600,
        )
        self.assertEqual(
            [
                event.duration_seconds
                for event in scheduler.events
                if event.activity in ("pickup", "dropoff")
            ],
            [3600, 3600],
        )
        logs = build_daily_logs(scheduler)
        self.assertGreater(len(logs), 3)
        self.assertAlmostEqual(sum(log["distance_miles"] for log in logs), 3500, places=2)
        for log in logs:
            self.assertEqual(sum(log["totals_seconds"].values()), 86400)
            self.assertEqual(log["segments"][0]["start_seconds"], 0)
            self.assertEqual(log["segments"][-1]["end_seconds"], 86400)
            for first, second in zip(log["segments"], log["segments"][1:]):
                self.assertEqual(first["end_seconds"], second["start_seconds"])
            for remark in log["remarks"]:
                self.assertTrue(remark["location"])

    def test_cycle_exhaustion_restarts_and_historical_recap_is_not_erased(self):
        scheduler = self.scheduler(used_hours=70, history=[10] * 7)
        self.assertEqual(scheduler.events[0].activity, "cycle_restart")
        self.assertEqual(scheduler.events[0].duration_seconds, 34 * 3600)
        self.assertEqual(scheduler.cycle_seconds_at(scheduler.departure), 70 * 3600)
        self.assertEqual(scheduler.cycle_seconds_at(scheduler.events[0].end_time), 0)
        self.assert_valid_driving_limits(scheduler)
        self.assertTrue(
            any(log["recap"]["restart_completed_today"] for log in build_daily_logs(scheduler))
        )

    def test_oldest_cycle_hours_roll_off_at_terminal_midnight(self):
        scheduler = self.scheduler(
            example_route(5, 250, 1),
            used_hours=69,
            history=[24, 24, 21, 0, 0, 0, 0],
            departure="2026-10-06T23:00",
        )
        self.assertFalse(any(event.activity == "cycle_restart" for event in scheduler.events))
        self.assert_valid_driving_limits(scheduler)

    def test_pickup_satisfies_break_without_resetting_shift(self):
        scheduler = self.scheduler(example_route(10, 500, 8), used_hours=0, history=[0] * 7)
        self.assertFalse(
            any(event.activity in ("break", "daily_rest") for event in scheduler.events)
        )
        self.assert_valid_driving_limits(scheduler)

    def test_elapsed_window_limits_driving_even_with_capacity_remaining(self):
        # Frequent refuelling uses the elapsed window without consuming driving hours.
        scheduler = self.scheduler(example_route(20, 10000), used_hours=0, history=[0] * 7)
        first_rest_index = next(
            index for index, event in enumerate(scheduler.events) if event.activity == "daily_rest"
        )
        driving_before_rest = sum(
            event.duration_seconds
            for event in scheduler.events[:first_rest_index]
            if event.duty_status == "driving"
        )
        self.assertLess(driving_before_rest, 11 * 3600)
        self.assert_valid_driving_limits(scheduler)

    def test_sleeper_status_and_multi_day_restart_sheets(self):
        scheduler = self.scheduler(used_hours=70, history=[10] * 7, rest_status="sleeper_berth")
        self.assertEqual(scheduler.events[0].duty_status, "sleeper_berth")
        self.assertTrue(
            all(sum(log["totals_seconds"].values()) == 86400 for log in build_daily_logs(scheduler))
        )

    def test_daylight_saving_sheet_is_explicitly_rejected(self):
        scheduler = self.scheduler(example_route(30, 1500), departure="2026-10-31T06:00")
        with self.assertRaisesRegex(ValueError, "daylight-saving"):
            build_daily_logs(scheduler)


@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}})
class ApiTests(SimpleTestCase):
    def test_plan_response_contains_filled_logs_and_real_route_contract(self):
        with (
            patch("trips.views.get_route", return_value=example_route()),
            patch("trips.views.describe_route_location", side_effect=lambda location: location),
        ):
            response = APIClient().post("/api/trips/plan", example_payload(), format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["summary"]["distance_miles"], 1200)
        self.assertEqual(response.data["summary"]["fuel_stops"], 1)
        self.assertEqual(response.data["log_details"]["co_driver_name"], "N/A")
        self.assertTrue(response.data["daily_logs"])

    def test_inconsistent_history_is_rejected_before_provider_request(self):
        payload = example_payload()
        payload["cycle_used_hours"] = 40
        with patch("trips.views.get_route") as provider:
            response = APIClient().post("/api/trips/plan", payload, format="json")
        self.assertEqual(response.status_code, 400)
        provider.assert_not_called()

    def test_ambiguous_and_nonexistent_departure_times_are_rejected(self):
        for departure in ("2026-11-01T01:30", "2026-03-08T02:30"):
            payload = example_payload()
            payload["departure_time"] = departure
            serializer = TripPlanSerializer(data=payload)
            self.assertFalse(serializer.is_valid())
            self.assertIn("departure_time", serializer.errors)

    def test_nonfinite_hours_and_coordinates_are_rejected(self):
        for field in ("hours", "coordinates"):
            payload = example_payload()
            if field == "hours":
                payload["cycle_used_hours"] = float("nan")
            else:
                payload["current_location"]["latitude"] = float("nan")
            self.assertFalse(TripPlanSerializer(data=payload).is_valid())

    def test_provider_failure_has_clear_service_unavailable_response(self):
        with patch("trips.views.get_route", side_effect=RoutingError("Map service unavailable")):
            response = APIClient().post("/api/trips/plan", example_payload(), format="json")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data["error"], "Map service unavailable")


class RouteAdapterTests(SimpleTestCase):
    def test_osrm_annotations_preserve_distance_and_pickup_leg(self):
        provider_response = {
            "code": "Ok",
            "routes": [
                {
                    "duration": 3600,
                    "geometry": {"coordinates": [[-88, 42], [-87, 41], [-86, 40]]},
                    "legs": [
                        {
                            "duration": 1200,
                            "annotation": {"distance": [10000], "duration": [1200]},
                            "steps": [],
                        },
                        {
                            "duration": 2400,
                            "annotation": {"distance": [20000], "duration": [2400]},
                            "steps": [],
                        },
                    ],
                }
            ],
        }
        route = normalize_osrm_route(provider_response)
        self.assertEqual(route.pickup_driving_seconds, 1200)
        self.assertEqual(route.cumulative_meters[-1], 30000)
        self.assertEqual(route.location_at(1200).latitude, 41)
        self.assertEqual(route.meters_at(2400), 20000)

    def test_ors_step_geometry_is_normalized_for_heavy_vehicle_profile(self):
        provider_response = {
            "features": [
                {
                    "geometry": {"coordinates": [[-88, 42], [-87, 41], [-86, 40]]},
                    "properties": {
                        "summary": {"duration": 3600},
                        "segments": [
                            {
                                "duration": 1200,
                                "steps": [
                                    {
                                        "way_points": [0, 1],
                                        "distance": 10000,
                                        "duration": 1200,
                                        "instruction": "Drive to pickup",
                                    }
                                ],
                            },
                            {
                                "duration": 2400,
                                "steps": [
                                    {
                                        "way_points": [1, 2],
                                        "distance": 20000,
                                        "duration": 2400,
                                        "instruction": "Drive to drop-off",
                                    }
                                ],
                            },
                        ],
                    },
                }
            ]
        }
        route = normalize_ors_route(provider_response)
        self.assertTrue(route.truck_profile)
        self.assertEqual(route.cumulative_meters[-1], 30000)
        self.assertEqual(route.cumulative_seconds[-1], 3600)
        self.assertEqual(route.instructions[1]["leg"], 1)


@override_settings(GEOCODING_PROVIDER="photon")
class PhotonGeocodingTests(SimpleTestCase):
    def test_search_keeps_only_supported_us_locations(self):
        provider_response = {
            "features": [
                {
                    "properties": {"name": "Boston", "state": "Massachusetts", "countrycode": "US"},
                    "geometry": {"coordinates": [-71.0589, 42.3601]},
                },
                {
                    "properties": {"name": "Boston", "countrycode": "GB"},
                    "geometry": {"coordinates": [-0.02, 52.97]},
                },
                {
                    "properties": {"name": "Anchorage", "countrycode": "US"},
                    "geometry": {"coordinates": [-149.9, 61.2]},
                },
            ]
        }
        with patch("trips.routing.photon_request", return_value=provider_response) as lookup:
            locations = search_locations("Boston")
        self.assertEqual(len(locations), 1)
        self.assertEqual(locations[0]["label"], "Boston, Massachusetts")
        self.assertEqual(locations[0]["latitude"], 42.3601)
        self.assertEqual(lookup.call_args.args[1]["countrycode"], "US")

    def test_reverse_label_preserves_route_coordinates(self):
        route_location = Location("estimated route position", 35.1, -90.2)
        provider_response = {
            "features": [
                {
                    "properties": {"city": "Memphis", "state": "Tennessee"},
                    "geometry": {"coordinates": [-90.05, 35.15]},
                }
            ]
        }
        with patch("trips.routing.photon_request", return_value=provider_response):
            described_location = describe_route_location(route_location)
        self.assertEqual(described_location.label, "Near Memphis, Tennessee (estimated)")
        self.assertEqual(described_location.latitude, route_location.latitude)
        self.assertEqual(described_location.longitude, route_location.longitude)

    def test_empty_reverse_result_keeps_coordinate_description(self):
        route_location = Location("estimated route position", 35.1, -90.2)
        with patch("trips.routing.photon_request", return_value={"features": []}):
            self.assertEqual(describe_route_location(route_location), route_location)
