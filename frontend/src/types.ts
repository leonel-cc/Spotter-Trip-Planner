export type DutyStatus = 'off_duty' | 'sleeper_berth' | 'driving' | 'on_duty';

export interface Location {
  label: string;
  latitude: number;
  longitude: number;
}

export interface LogDetails {
  driver_name: string;
  carrier_name: string;
  main_office_address: string;
  home_terminal_address: string;
  truck_number: string;
  trailer_number: string;
  shipping_document: string;
  shipper_name: string;
  commodity: string;
  co_driver_name: string;
  sample_details: boolean;
}

export interface TripRequest {
  current_location: Location;
  pickup_location: Location;
  dropoff_location: Location;
  cycle_used_hours: number;
  departure_time: string;
  terminal_timezone: string;
  previous_daily_hours: number[];
  rest_status: 'off_duty' | 'sleeper_berth';
  log_details: LogDetails;
}

export interface DutyEvent {
  start_time: string;
  end_time: string;
  duty_status: DutyStatus;
  activity: string;
  reason: string;
  location: Location;
  duration_seconds: number;
  distance_miles: number;
  cycle_used_hours: number;
}

export interface LogSegment {
  start_seconds: number;
  end_seconds: number;
  duty_status: DutyStatus;
  activity: string;
  location: Location;
  distance_miles: number;
}

export interface DailyLog {
  date: string;
  segments: LogSegment[];
  remarks: { seconds: number; time: string; location: string; activity: string }[];
  totals_seconds: Record<DutyStatus, number>;
  distance_miles: number;
  recap: {
    on_duty_hours: number;
    last_seven_days_hours: number;
    last_eight_days_hours: number;
    hours_available_tomorrow: number;
    cycle_remaining_hours: number;
    restart_completed_today: boolean;
    sixty_hour_schedule: string;
  };
}

export interface TripPlan {
  locations: Location[];
  route: {
    geometry: [number, number][];
    provider: string;
    truck_profile: boolean;
    instructions: { leg: number; text: string; distance_miles: number; duration_seconds: number }[];
  };
  events: DutyEvent[];
  daily_logs: DailyLog[];
  summary: {
    distance_miles: number;
    driving_seconds: number;
    elapsed_seconds: number;
    arrival_time: string;
    completion_time: string;
    log_days: number;
    fuel_stops: number;
    rest_stops: number;
  };
  log_details: LogDetails;
  terminal_timezone: string;
  warnings: string[];
}
