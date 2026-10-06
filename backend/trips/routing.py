"""Provider adapters: normalize external data before it reaches the scheduler."""

import hashlib
import os
import time

import requests
from django.conf import settings
from django.core.cache import cache

from .domain import Location, RoutePath, distance_between_coordinates


class RoutingError(Exception):
    pass


COMMON_LOCATIONS = [
    Location("Chicago, IL", 41.8781, -87.6298),
    Location("Indianapolis, IN", 39.7684, -86.1581),
    Location("Dallas, TX", 32.7767, -96.7970),
    Location("Los Angeles, CA", 34.0522, -118.2437),
    Location("New York, NY", 40.7128, -74.0060),
    Location("Denver, CO", 39.7392, -104.9903),
    Location("Atlanta, GA", 33.7490, -84.3880),
    Location("Miami, FL", 25.7617, -80.1918),
    Location("Seattle, WA", 47.6062, -122.3321),
    Location("Green Bay, WI", 44.5133, -88.0133),
    Location("Richmond, VA", 37.5407, -77.4360),
    Location("Newark, NJ", 40.7357, -74.1724),
]


def request_json(method, url, **kwargs):
    try:
        response = requests.request(method, url, timeout=(5, 35), **kwargs)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as error:
        status = getattr(getattr(error, "response", None), "status_code", None)
        if status in (401, 403):
            raise RoutingError(
                "Map provider rejected the credentials. Check the server API key."
            ) from error
        if status == 429:
            raise RoutingError(
                "The map provider's request limit was reached. Please try again later."
            ) from error
        raise RoutingError(
            "The map provider is temporarily unavailable or could not find this route. Try again or choose another location."
        ) from error


def nominatim_request(endpoint, params):
    """Serialize public requests across threads/processes and respect 1 request/s.

    This is manual search, never autocomplete. Cache search and reverse results.
    For higher traffic, configure a separate geocoding provider/deployment.
    """
    cache_key = (
        "geocode:" + hashlib.sha256(repr((endpoint, sorted(params.items()))).encode()).hexdigest()
    )
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return cached_result
    lock_directory = settings.RUNTIME_DIRECTORY
    lock_directory.mkdir(parents=True, exist_ok=True)
    lock_path = lock_directory / "geocoder.lock"
    deadline = time.monotonic() + 40
    lock_descriptor = None
    while lock_descriptor is None:
        try:
            lock_descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                if time.time() - lock_path.stat().st_mtime > 60:
                    lock_path.unlink(missing_ok=True)
            except FileNotFoundError:
                continue
            if time.monotonic() > deadline:
                raise RoutingError("Location lookup is busy. Please try again shortly.")
            else:
                time.sleep(0.1)
    try:
        last_request_time = cache.get("geocode:last_request", 0)
        time.sleep(max(0, 1.1 - (time.time() - last_request_time)))
        base_url = os.getenv("NOMINATIM_BASE_URL", "https://nominatim.openstreetmap.org").rstrip(
            "/"
        )
        try:
            result = request_json(
                "GET",
                f"{base_url}/{endpoint}",
                params=params,
                headers={
                    "User-Agent": os.getenv(
                        "MAP_USER_AGENT", "SpotterTripPlanner/1.0 (assessment demo)"
                    )
                },
            )
        finally:
            cache.set("geocode:last_request", time.time(), 86400)
        cache.set(cache_key, result, 7 * 86400)
        return result
    finally:
        os.close(lock_descriptor)
        lock_path.unlink(missing_ok=True)


def photon_request(endpoint, params):
    """Cache the public Photon demo responses for this low-traffic assessment."""
    base_url = os.getenv("PHOTON_BASE_URL", "https://photon.komoot.io").rstrip("/")
    cache_key = (
        "photon:"
        + hashlib.sha256(repr((base_url, endpoint, sorted(params.items()))).encode()).hexdigest()
    )
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return cached_result
    result = request_json(
        "GET",
        f"{base_url}/{endpoint}/",
        params=params,
        headers={
            "User-Agent": os.getenv("MAP_USER_AGENT", "SpotterTripPlanner/1.0 (assessment demo)")
        },
    )
    cache.set(cache_key, result, 7 * 86400)
    return result


def search_photon_locations(query):
    result = photon_request(
        "api", {"q": query, "limit": 5, "lang": "en", "bbox": "-125,24,-66,50", "countrycode": "US"}
    )
    locations = []
    for feature in result.get("features", []):
        properties = feature.get("properties", {})
        longitude, latitude = feature["geometry"]["coordinates"]
        if properties.get("countrycode", "").upper() != "US":
            continue
        if not (24 <= latitude <= 50 and -125 <= longitude <= -66):
            continue
        address_parts = [
            properties.get("name"),
            " ".join(filter(None, [properties.get("housenumber"), properties.get("street")])),
            properties.get("city") or properties.get("county"),
            properties.get("state"),
        ]
        label = ", ".join(dict.fromkeys(part for part in address_parts if part))
        if label:
            locations.append(Location(label, latitude, longitude).as_dict())
    return locations


def describe_photon_location(location):
    result = photon_request(
        "reverse",
        {
            "lat": round(location.latitude, 4),
            "lon": round(location.longitude, 4),
            "limit": 1,
            "lang": "en",
        },
    )
    features = result.get("features", [])
    if not features:
        return location
    properties = features[0].get("properties", {})
    municipality = properties.get("city") or properties.get("county") or properties.get("name")
    state = properties.get("state")
    if municipality and state:
        return Location(
            f"Near {municipality}, {state} (estimated)", location.latitude, location.longitude
        )
    return location


def search_locations(query):
    local_matches = [
        location.as_dict()
        for location in COMMON_LOCATIONS
        if query.casefold() in location.label.casefold()
    ]
    if local_matches:
        return local_matches
    if settings.GEOCODING_PROVIDER == "photon":
        return search_photon_locations(query)
    results = nominatim_request(
        "search",
        {"q": query, "format": "jsonv2", "addressdetails": 1, "countrycodes": "us", "limit": 5},
    )
    return [
        {
            "label": result["display_name"],
            "latitude": float(result["lat"]),
            "longitude": float(result["lon"]),
        }
        for result in results
    ]


def describe_route_location(location):
    if "estimated route position" not in location.label:
        return location
    if settings.GEOCODING_PROVIDER == "photon":
        return describe_photon_location(location)
    result = nominatim_request(
        "reverse",
        {
            "lat": round(location.latitude, 4),
            "lon": round(location.longitude, 4),
            "format": "jsonv2",
            "zoom": 10,
            "addressdetails": 1,
        },
    )
    address = result.get("address", {})
    municipality = (
        address.get("city")
        or address.get("town")
        or address.get("village")
        or address.get("municipality")
        or address.get("county")
    )
    state_code = address.get("ISO3166-2-lvl4", "").removeprefix("US-") or address.get("state")
    if municipality and state_code:
        return Location(
            f"Near {municipality}, {state_code} (estimated)", location.latitude, location.longitude
        )
    return location


def get_route(locations):
    api_key = os.getenv("ORS_API_KEY", "").strip()
    provider = "openrouteservice" if api_key else "osrm"
    coordinates = [[location.longitude, location.latitude] for location in locations]
    cache_key = "route:" + hashlib.sha256(repr((provider, coordinates)).encode()).hexdigest()
    cached_route = cache.get(cache_key)
    if cached_route is not None:
        return cached_route
    if api_key:
        data = request_json(
            "POST",
            "https://api.openrouteservice.org/v2/directions/driving-hgv/geojson",
            json={"coordinates": coordinates, "instructions": True},
            headers={"Authorization": api_key},
        )
        route = normalize_ors_route(data)
    else:
        coordinate_path = ";".join(f"{longitude},{latitude}" for longitude, latitude in coordinates)
        base_url = os.getenv("OSRM_BASE_URL", "https://router.project-osrm.org").rstrip("/")
        data = request_json(
            "GET",
            f"{base_url}/route/v1/driving/{coordinate_path}",
            params={
                "steps": "true",
                "overview": "full",
                "geometries": "geojson",
                "annotations": "distance,duration",
            },
        )
        try:
            route = normalize_osrm_route(data)
        except (KeyError, IndexError, TypeError) as error:
            raise RoutingError("The route provider returned an unexpected response.") from error
    if route.distance_miles > 6000:
        raise RoutingError(
            "This planner supports trips of at most 6,000 miles. Split the journey into smaller trips."
        )
    cache.set(cache_key, route, 86400)
    return route


def build_route_path(
    coordinates,
    edge_distances,
    edge_durations,
    pickup_seconds,
    total_seconds,
    instructions,
    provider,
):
    if (
        len(coordinates) < 2
        or len(edge_distances) != len(coordinates) - 1
        or len(edge_durations) != len(edge_distances)
    ):
        raise RoutingError("The provider returned inconsistent route geometry. Please retry.")
    cumulative_meters, cumulative_seconds = [0.0], [0.0]
    time_scale = total_seconds / sum(edge_durations) if sum(edge_durations) else 1
    for distance_meters, duration_seconds in zip(edge_distances, edge_durations):
        cumulative_meters.append(cumulative_meters[-1] + distance_meters)
        cumulative_seconds.append(cumulative_seconds[-1] + duration_seconds * time_scale)
    if total_seconds == 0:
        # Identical locations are valid: service events still need to be logged.
        cumulative_seconds[-1] = 0
    return RoutePath(
        coordinates,
        cumulative_seconds,
        cumulative_meters,
        pickup_seconds,
        total_seconds,
        instructions,
        provider,
        provider == "openrouteservice",
    )


def normalize_osrm_route(data):
    if data.get("code") != "Ok" or not data.get("routes"):
        raise RoutingError("No road route was found between the selected locations.")
    result = data["routes"][0]
    edge_distances, edge_durations, instructions = [], [], []
    for leg_index, leg in enumerate(result["legs"]):
        edge_distances.extend(leg["annotation"]["distance"])
        edge_durations.extend(leg["annotation"]["duration"])
        for step in leg["steps"]:
            maneuver = step["maneuver"]
            action = maneuver["type"].replace("_", " ").capitalize()
            modifier = maneuver.get("modifier", "")
            road = step.get("name") or step.get("ref") or "the road"
            instruction = f"{action}{' ' + modifier if modifier else ''} on {road}"
            if maneuver["type"] == "arrive":
                instruction = "Arrive at pickup" if leg_index == 0 else "Arrive at drop-off"
            instructions.append(
                {
                    "leg": leg_index,
                    "text": instruction,
                    "distance_miles": round(step["distance"] / 1609.344, 2),
                    "duration_seconds": round(step["duration"]),
                }
            )
    return build_route_path(
        result["geometry"]["coordinates"],
        edge_distances,
        edge_durations,
        round(result["legs"][0]["duration"]),
        round(result["duration"]),
        instructions,
        "osrm",
    )


def normalize_ors_route(data):
    try:
        feature = data["features"][0]
        coordinates = feature["geometry"]["coordinates"]
        segments = feature["properties"]["segments"]
        edge_distances = [0.0] * (len(coordinates) - 1)
        edge_durations = [0.0] * (len(coordinates) - 1)
        instructions = []
        for leg_index, segment in enumerate(segments):
            for step in segment["steps"]:
                first_index, last_index = step["way_points"]
                geometry_distances = [
                    distance_between_coordinates(coordinates[index], coordinates[index + 1])
                    for index in range(first_index, last_index)
                ]
                geometry_total = sum(geometry_distances)
                for offset, geometry_distance in enumerate(geometry_distances):
                    fraction = (
                        geometry_distance / geometry_total
                        if geometry_total
                        else 1 / len(geometry_distances)
                    )
                    edge_distances[first_index + offset] += step["distance"] * fraction
                    edge_durations[first_index + offset] += step["duration"] * fraction
                instructions.append(
                    {
                        "leg": leg_index,
                        "text": step["instruction"],
                        "distance_miles": round(step["distance"] / 1609.344, 2),
                        "duration_seconds": round(step["duration"]),
                    }
                )
        total_seconds = round(feature["properties"]["summary"]["duration"])
        return build_route_path(
            coordinates,
            edge_distances,
            edge_durations,
            round(segments[0]["duration"]),
            total_seconds,
            instructions,
            "openrouteservice",
        )
    except (KeyError, IndexError, TypeError) as error:
        raise RoutingError("The route provider returned an unexpected response.") from error
