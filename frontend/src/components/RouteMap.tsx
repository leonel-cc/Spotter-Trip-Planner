import { useEffect } from 'react';
import { divIcon } from 'leaflet';
import {
  MapContainer,
  TileLayer,
  Polyline,
  Marker,
  Popup,
  ZoomControl,
  useMap,
} from 'react-leaflet';
import type { TripPlan } from '../types';
import { formatDate, formatTime, formatDuration } from '../format';

function FitRoute({ plan }: { plan: TripPlan | null }) {
  const map = useMap();
  useEffect(() => {
    if (plan)
      map.fitBounds(
        plan.route.geometry.map(([longitude, latitude]) => [latitude, longitude]),
        { padding: [50, 50], maxZoom: 12 },
      );
    const observer = new ResizeObserver(() => map.invalidateSize());
    observer.observe(map.getContainer());
    return () => observer.disconnect();
  }, [map, plan]);
  return null;
}

function markerIcon(label: string, kind: string) {
  // Labels are fixed application symbols, never user-entered HTML.
  return divIcon({
    html: `<span class="map-marker marker-${kind}">${label}</span>`,
    className: 'marker-wrapper',
    iconSize: [30, 30],
    iconAnchor: [15, 15],
  });
}

export default function RouteMap({ plan }: { plan: TripPlan | null }) {
  return (
    <div className="route-map">
      <MapContainer center={[38.5, -95]} zoom={4} scrollWheelZoom zoomControl={false}>
        <ZoomControl position="topright" />
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
          referrerPolicy="strict-origin-when-cross-origin"
        />
        <FitRoute plan={plan} />
        {plan && (
          <>
            <Polyline
              positions={plan.route.geometry.map(([longitude, latitude]) => [latitude, longitude])}
              pathOptions={{ color: '#ffffff', weight: 9, opacity: 0.9 }}
            />
            <Polyline
              positions={plan.route.geometry.map(([longitude, latitude]) => [latitude, longitude])}
              pathOptions={{ color: '#d86145', weight: 5, opacity: 1 }}
            />
            {plan.events
              .filter((event) =>
                ['fuel', 'break', 'daily_rest', 'cycle_restart'].includes(event.activity),
              )
              .map((event, index) => (
                <Marker
                  key={`stop-${index}`}
                  position={[event.location.latitude, event.location.longitude]}
                  icon={markerIcon(
                    event.activity === 'fuel' ? 'F' : 'R',
                    event.activity === 'fuel' ? 'fuel' : 'rest',
                  )}
                >
                  <Popup>
                    <strong>{event.activity.replaceAll('_', ' ')}</strong>
                    <p>{event.location.label}</p>
                    <p>
                      {formatDate(event.start_time, plan.terminal_timezone)} ·{' '}
                      {formatTime(event.start_time, plan.terminal_timezone)} ·{' '}
                      {formatDuration(event.duration_seconds)}
                    </p>
                    <small>Estimated route position; facility not verified.</small>
                  </Popup>
                </Marker>
              ))}
            {plan.locations.map((location, index) => (
              <Marker
                key={`waypoint-${index}`}
                position={[location.latitude, location.longitude]}
                icon={markerIcon(['A', 'B', 'C'][index], ['start', 'pickup', 'dropoff'][index])}
              >
                <Popup>
                  <strong>{['Current location', 'Pickup', 'Drop-off'][index]}</strong>
                  <p>{location.label}</p>
                </Popup>
              </Marker>
            ))}
          </>
        )}
      </MapContainer>
      <div className="map-label">
        <span className="live-dot" />
        {plan
          ? `${plan.route.provider === 'osrm' ? 'OSRM · General driving' : 'OpenRouteService · Heavy vehicle'}`
          : 'OpenStreetMap · US routes'}
      </div>
      <div className="map-legend">
        <span>
          <i className="legend-route" /> Route
        </span>
        <span>
          <i className="legend-fuel" /> Fuel
        </span>
        <span>
          <i className="legend-rest" /> Rest
        </span>
      </div>
    </div>
  );
}
