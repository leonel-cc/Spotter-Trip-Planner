import { useState } from 'react';
import {
  ArrowRight,
  ChevronDown,
  Clock3,
  FileText,
  LoaderCircle,
  RotateCcw,
  Sparkles,
} from 'lucide-react';
import LocationInput from './LocationInput';
import type { Location, LogDetails, TripRequest } from '../types';

const sampleLocations: Location[] = [
  { label: 'Chicago, IL', latitude: 41.8781, longitude: -87.6298 },
  { label: 'Indianapolis, IN', latitude: 39.7684, longitude: -86.1581 },
  { label: 'Dallas, TX', latitude: 32.7767, longitude: -96.797 },
];

const emptyDetails: LogDetails = {
  driver_name: '',
  carrier_name: '',
  main_office_address: '',
  home_terminal_address: '',
  truck_number: '',
  trailer_number: '',
  shipping_document: '',
  shipper_name: '',
  commodity: '',
  co_driver_name: 'N/A',
  sample_details: false,
};
const sampleDetails: LogDetails = {
  driver_name: 'Alex Morgan',
  carrier_name: 'Example Freight Co.',
  main_office_address: 'Chicago, IL',
  home_terminal_address: 'Chicago, IL',
  truck_number: 'TRK-104',
  trailer_number: 'TRL-208',
  shipping_document: 'DEMO-1001',
  shipper_name: 'Example Supply Co.',
  commodity: 'Paper products',
  co_driver_name: 'N/A',
  sample_details: true,
};
const detailLabels: [keyof Omit<LogDetails, 'sample_details'>, string][] = [
  ['driver_name', 'Driver name'],
  ['carrier_name', 'Carrier name'],
  ['main_office_address', 'Main office address'],
  ['home_terminal_address', 'Home terminal address'],
  ['truck_number', 'Truck / tractor number'],
  ['trailer_number', 'Trailer number'],
  ['shipping_document', 'Shipping document / manifest'],
  ['shipper_name', 'Shipper name'],
  ['commodity', 'Commodity'],
  ['co_driver_name', 'Co-driver (N/A if none)'],
];

function initialDeparture(): string {
  const dateParts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Chicago',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(new Date());
  const value = (type: string) => dateParts.find((part) => part.type === type)?.value;
  return `${value('year')}-${value('month')}-${value('day')}T06:00`;
}

interface Props {
  loading: boolean;
  exportingPdf?: boolean;
  onSubmit: (trip: TripRequest) => Promise<void>;
}

export default function TripForm({ loading, exportingPdf = false, onSubmit }: Props) {
  const busy = loading || exportingPdf;
  const [locations, setLocations] = useState<(Location | null)[]>([null, null, null]);
  const [cycleUsedHours, setCycleUsedHours] = useState(0);
  const [departureTime, setDepartureTime] = useState(initialDeparture);
  const [terminalTimezone, setTerminalTimezone] = useState('America/Chicago');
  const [restStatus, setRestStatus] = useState<'off_duty' | 'sleeper_berth'>('off_duty');
  const [previousDailyHours, setPreviousDailyHours] = useState([0, 0, 0, 0, 0, 0, 0]);
  const [logDetails, setLogDetails] = useState<LogDetails>(emptyDetails);
  const [showDetails, setShowDetails] = useState(false);
  const [showSchedule, setShowSchedule] = useState(false);
  const [formError, setFormError] = useState('');
  const [formVersion, setFormVersion] = useState(0);
  const filledDetails = detailLabels.filter(([name]) => logDetails[name].trim()).length;
  const historyTotal = previousDailyHours.reduce((total, hours) => total + hours, 0);

  function loadSample() {
    setLocations(sampleLocations);
    setCycleUsedHours(12);
    setPreviousDailyHours([2, 2, 2, 2, 2, 1, 1]);
    setLogDetails(sampleDetails);
    setFormError('');
    setFormVersion((version) => version + 1);
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (locations.some((location) => !location)) {
      setFormError('Search and select all three locations first.');
      return;
    }
    if (filledDetails !== detailLabels.length) {
      setShowDetails(true);
      setFormError('Complete every log detail. Use N/A only for fields that do not apply.');
      return;
    }
    if (Math.abs(historyTotal - cycleUsedHours) > 0.001) {
      setShowSchedule(true);
      setFormError('The seven previous days must add up to Current Cycle Used.');
      return;
    }
    setFormError('');
    await onSubmit({
      current_location: locations[0]!,
      pickup_location: locations[1]!,
      dropoff_location: locations[2]!,
      cycle_used_hours: cycleUsedHours,
      departure_time: departureTime,
      terminal_timezone: terminalTimezone,
      previous_daily_hours: previousDailyHours,
      rest_status: restStatus,
      log_details: logDetails,
    });
  }

  return (
    <form className="trip-form" onSubmit={(event) => void submit(event)}>
      <div className="panel-heading">
        <div>
          <span className="eyebrow">YOUR NEXT TRIP</span>
          <h2>Let’s plan your route.</h2>
        </div>
        <span className="small-icon">
          <ArrowRight size={18} />
        </span>
      </div>
      <p className="muted intro-copy">
        Tell us where you’re headed. We’ll work out the road ahead.
      </p>
      <button type="button" className="sample-button" onClick={loadSample} disabled={busy}>
        <Sparkles size={15} /> Try a sample trip <ArrowRight size={14} />
      </button>
      <fieldset disabled={busy} className="route-fields">
        {['Current location', 'Pickup location', 'Drop-off location'].map((label, index) => (
          <LocationInput
            key={`${formVersion}-${index}`}
            label={label}
            marker={['A', 'B', 'C'][index]}
            location={locations[index]}
            onChange={(location) =>
              setLocations((current) =>
                current.map((value, position) => (position === index ? location : value)),
              )
            }
          />
        ))}
      </fieldset>
      <div className="cycle-field">
        <label htmlFor="cycle-hours">
          Current cycle used <span>70-hour / 8-day</span>
        </label>
        <div className="number-input">
          <Clock3 size={17} />
          <input
            id="cycle-hours"
            type="number"
            min="0"
            max="70"
            step="0.01"
            value={cycleUsedHours}
            disabled={busy}
            onChange={(event) => setCycleUsedHours(Number(event.target.value))}
          />
          <span>hours</span>
        </div>
        <div className="cycle-meter">
          <span style={{ width: `${(cycleUsedHours / 70) * 100}%` }} />
        </div>
        <p className="microcopy">
          {Math.max(0, 70 - cycleUsedHours).toFixed(1)} hours available at departure
        </p>
      </div>
      <div className="form-disclosure">
        <button
          type="button"
          aria-expanded={showSchedule}
          onClick={() => setShowSchedule(!showSchedule)}
        >
          <span>
            <Clock3 size={16} /> Schedule & cycle history
          </span>
          <ChevronDown size={16} className={showSchedule ? 'rotated' : ''} />
        </button>
        {showSchedule && (
          <div className="disclosure-body">
            <label>
              Departure at home terminal
              <input
                type="datetime-local"
                value={departureTime}
                required
                disabled={busy}
                onChange={(event) => setDepartureTime(event.target.value)}
              />
            </label>
            <label>
              Home terminal time zone
              <select
                value={terminalTimezone}
                disabled={busy}
                onChange={(event) => setTerminalTimezone(event.target.value)}
              >
                <option value="America/New_York">Eastern — New York</option>
                <option value="America/Chicago">Central — Chicago</option>
                <option value="America/Denver">Mountain — Denver</option>
                <option value="America/Los_Angeles">Pacific — Los Angeles</option>
                <option value="America/Phoenix">Arizona — Phoenix</option>
              </select>
            </label>
            <label>
              Long rest status
              <select
                value={restStatus}
                disabled={busy}
                onChange={(event) => setRestStatus(event.target.value as typeof restStatus)}
              >
                <option value="off_duty">Off duty</option>
                <option value="sleeper_berth">Sleeper berth (truck has a sleeper)</option>
              </select>
            </label>
            <p className="microcopy">
              On-duty hours for the seven days before departure, oldest first. These complete the
              recap and must total {cycleUsedHours} hours. Assumes 10 hours of rest before starting,
              with no earlier work on the departure date.
            </p>
            <div className="history-grid">
              {previousDailyHours.map((hours, index) => (
                <label key={index}>
                  Day −{7 - index}
                  <input
                    aria-label={`On-duty hours ${7 - index} days before departure`}
                    type="number"
                    min="0"
                    max="24"
                    step="0.01"
                    value={hours}
                    disabled={busy}
                    onChange={(event) =>
                      setPreviousDailyHours((current) =>
                        current.map((value, position) =>
                          position === index ? Number(event.target.value) : value,
                        ),
                      )
                    }
                  />
                </label>
              ))}
            </div>
            <p
              className={`microcopy ${Math.abs(historyTotal - cycleUsedHours) > 0.001 ? 'field-error' : ''}`}
            >
              History total: {historyTotal.toFixed(2)} hours
            </p>
          </div>
        )}
      </div>
      <div className="form-disclosure">
        <button
          type="button"
          aria-expanded={showDetails}
          onClick={() => setShowDetails(!showDetails)}
        >
          <span>
            <FileText size={16} /> Daily log details{' '}
            <span className="count-badge">
              {filledDetails}/{detailLabels.length}
            </span>
          </span>
          <ChevronDown size={16} className={showDetails ? 'rotated' : ''} />
        </button>
        {showDetails && (
          <div className="disclosure-body">
            {detailLabels.map(([name, label]) => (
              <label key={name}>
                {label}
                <input
                  value={logDetails[name]}
                  maxLength={name.includes('address') ? 160 : 80}
                  disabled={busy}
                  onChange={(event) =>
                    setLogDetails((details) => ({ ...details, [name]: event.target.value }))
                  }
                />
              </label>
            ))}
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={logDetails.sample_details}
                onChange={(event) =>
                  setLogDetails((details) => ({ ...details, sample_details: event.target.checked }))
                }
              />
              These are fictional example details
            </label>
            <p className="microcopy">
              Logs are planning estimates, not signed records. No signature is generated.
            </p>
          </div>
        )}
      </div>
      {logDetails.sample_details && (
        <p className="sample-notice">
          Example driver and carrier details loaded. Replace them for your own trip.
        </p>
      )}
      {formError && (
        <p className="form-error" role="alert">
          {formError}
        </p>
      )}
      <button className="primary-button" type="submit" disabled={busy}>
        {busy ? (
          <>
            <LoaderCircle size={18} className="spin" />{' '}
            {exportingPdf ? 'Creating your PDF…' : 'Planning your trip…'}
          </>
        ) : (
          <>
            Generate trip plan <ArrowRight size={18} />
          </>
        )}
      </button>
      {loading && (
        <p className="microcopy">Finding the route and naming stops may take a minute.</p>
      )}
      <div className="form-footnote">
        <RotateCcw size={15} />
        <span>
          11h driving · 14h window · 30m break
          <br />
          Fuel every 1,000 mi · 1h pickup & drop-off
        </span>
      </div>
    </form>
  );
}
