from datetime import UTC, datetime
from math import isfinite
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from rest_framework import serializers


class LocationSerializer(serializers.Serializer):
    label = serializers.CharField(max_length=240)
    latitude = serializers.FloatField(min_value=24, max_value=50)
    longitude = serializers.FloatField(min_value=-125, max_value=-66)

    def validate(self, data):
        if not all(isfinite(data[field]) for field in ("latitude", "longitude")):
            raise serializers.ValidationError("Coordinates must be finite numbers.")
        return data


class LogDetailsSerializer(serializers.Serializer):
    driver_name = serializers.CharField(max_length=80)
    carrier_name = serializers.CharField(max_length=100)
    main_office_address = serializers.CharField(max_length=160)
    home_terminal_address = serializers.CharField(max_length=160)
    truck_number = serializers.CharField(max_length=60)
    trailer_number = serializers.CharField(max_length=60)
    shipping_document = serializers.CharField(max_length=100)
    shipper_name = serializers.CharField(max_length=100)
    commodity = serializers.CharField(max_length=100)
    co_driver_name = serializers.CharField(max_length=80, default="N/A")
    sample_details = serializers.BooleanField(default=False)


class TripPlanSerializer(serializers.Serializer):
    current_location = LocationSerializer()
    pickup_location = LocationSerializer()
    dropoff_location = LocationSerializer()
    cycle_used_hours = serializers.FloatField(min_value=0, max_value=70)
    departure_time = serializers.CharField(max_length=40)
    terminal_timezone = serializers.CharField(max_length=64, default="America/Chicago")
    previous_daily_hours = serializers.ListField(
        child=serializers.FloatField(min_value=0, max_value=24), min_length=7, max_length=7
    )
    rest_status = serializers.ChoiceField(choices=["off_duty", "sleeper_berth"], default="off_duty")
    log_details = LogDetailsSerializer()

    def validate(self, data):
        if not all(
            isfinite(value) for value in [data["cycle_used_hours"], *data["previous_daily_hours"]]
        ):
            raise serializers.ValidationError("Duty hours must be finite numbers.")
        try:
            terminal_zone = ZoneInfo(data["terminal_timezone"])
        except ZoneInfoNotFoundError as error:
            raise serializers.ValidationError(
                {"terminal_timezone": "Choose a valid IANA time zone."}
            ) from error
        try:
            departure = datetime.fromisoformat(data["departure_time"])
            if departure.tzinfo is not None:
                raise ValueError("Expected a local terminal time, without offset.")
            departure = departure.replace(tzinfo=terminal_zone)
            if departure.astimezone(UTC).astimezone(terminal_zone).replace(
                tzinfo=None
            ) != departure.replace(tzinfo=None):
                raise ValueError("This local time does not exist because of a clock change.")
            if departure.replace(fold=0).utcoffset() != departure.replace(fold=1).utcoffset():
                raise ValueError(
                    "Choose an unambiguous time outside the daylight-saving clock change."
                )
        except ValueError as error:
            raise serializers.ValidationError({"departure_time": str(error)}) from error
        if abs(sum(data["previous_daily_hours"]) - data["cycle_used_hours"]) > 0.001:
            raise serializers.ValidationError(
                {
                    "previous_daily_hours": "The seven previous days must add up to Current Cycle Used. The trip starts after 10 hours of rest, with no earlier work on the departure date."
                }
            )
        data["departure"] = departure
        return data
