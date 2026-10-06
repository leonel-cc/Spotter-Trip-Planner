import math
import os

from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from .domain import Location
from .logs import build_daily_logs
from .routing import RoutingError, describe_route_location, get_route, search_locations
from .scheduler import TripScheduler
from .serializers import TripPlanSerializer


class PlanThrottle(AnonRateThrottle):
    scope = "plan"


class LocationThrottle(AnonRateThrottle):
    scope = "locations"


@api_view(["GET"])
def health(request):
    return Response(
        {
            "status": "ok",
            "route_provider": "openrouteservice"
            if os.getenv("ORS_API_KEY", "").strip()
            else "osrm",
            "truck_profile": bool(os.getenv("ORS_API_KEY", "").strip()),
        }
    )


@api_view(["GET"])
@throttle_classes([LocationThrottle])
def locations(request):
    query = request.query_params.get("q", "").strip()
    if not 3 <= len(query) <= 160:
        return Response({"error": "Enter a location between 3 and 160 characters."}, status=400)
    try:
        return Response({"results": search_locations(query)})
    except RoutingError as error:
        return Response({"error": str(error)}, status=503)


@api_view(["POST"])
@throttle_classes([PlanThrottle])
def plan_trip(request):
    serializer = TripPlanSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    trip = serializer.validated_data
    trip_locations = [
        Location(**trip[name])
        for name in ("current_location", "pickup_location", "dropoff_location")
    ]
    warnings = []
    try:
        route = get_route(trip_locations)
        scheduler = TripScheduler(
            route,
            trip_locations,
            trip["departure"],
            trip["terminal_timezone"],
            trip["cycle_used_hours"],
            trip["previous_daily_hours"],
            trip["rest_status"],
        )
        events = scheduler.plan()
        resolved_locations = {}
        if os.getenv("REVERSE_GEOCODING", "true").lower() == "true":
            for event in events:
                if "estimated route position" not in event.location.label:
                    continue
                coordinate_key = (
                    round(event.location.latitude, 4),
                    round(event.location.longitude, 4),
                )
                if coordinate_key not in resolved_locations:
                    try:
                        resolved_locations[coordinate_key] = describe_route_location(event.location)
                    except RoutingError:
                        warnings.append(
                            "Some intermediate locations could not be named. Their estimated coordinates are shown instead."
                        )
                        # Avoid repeated provider timeouts on a long trip.
                        break
                event.location = resolved_locations[coordinate_key]
        logs = build_daily_logs(scheduler)
    except RoutingError as error:
        return Response({"error": str(error)}, status=503)
    except ValueError as error:
        return Response({"error": str(error)}, status=400)
    if not route.truck_profile:
        warnings.append(
            "OSRM uses general driving routes, not truck height, weight, or hazardous-load restrictions. Configure ORS_API_KEY for the heavy-vehicle profile."
        )
    warnings.append(
        "Intermediate stops are estimated positions on the route, not verified fuel stations or legal parking locations."
    )
    warnings.append(
        "Planning estimate: the driver starts after 10 hours of rest, with a full tank and no earlier work on the departure date. Off-duty time before and after the trip is assumed."
    )
    if trip["log_details"]["sample_details"]:
        warnings.append(
            "Example driver, carrier, vehicle, and shipping details are fictional. Replace them before using this plan for your own trip."
        )
    display_step = max(1, math.ceil(len(route.coordinates) / 3500))
    geometry = route.coordinates[::display_step]
    if geometry[-1] != route.coordinates[-1]:
        geometry.append(route.coordinates[-1])
    return Response(
        {
            "locations": [location.as_dict() for location in trip_locations],
            "route": {
                "geometry": geometry,
                "provider": route.provider,
                "truck_profile": route.truck_profile,
                "instructions": route.instructions,
            },
            "events": [event.as_dict() for event in events],
            "daily_logs": logs,
            "summary": {
                "distance_miles": round(route.distance_miles, 1),
                "driving_seconds": route.total_driving_seconds,
                "elapsed_seconds": int((events[-1].end_time - scheduler.departure).total_seconds()),
                "arrival_time": events[-1].start_time.isoformat(),
                "completion_time": events[-1].end_time.isoformat(),
                "log_days": len(logs),
                "fuel_stops": sum(event.activity == "fuel" for event in events),
                "rest_stops": sum(
                    event.activity in ("break", "daily_rest", "cycle_restart") for event in events
                ),
            },
            "log_details": trip["log_details"],
            "terminal_timezone": trip["terminal_timezone"],
            "warnings": list(dict.fromkeys(warnings)),
        }
    )
