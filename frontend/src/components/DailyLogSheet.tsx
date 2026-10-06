import type { DailyLog, DutyStatus, TripPlan } from '../types';
import { formatLogDate } from '../format';

const dutyStatuses: DutyStatus[] = ['off_duty', 'sleeper_berth', 'driving', 'on_duty'];
const dutyLabels = ['1. Off duty', '2. Sleeper berth', '3. Driving', '4. On duty'];
const gridLeft = 128;
const gridWidth = 756;
const rowHeight = 36;
const rowTop = 60;
const timePosition = (seconds: number) => gridLeft + (seconds / 86400) * gridWidth;
const statusPosition = (status: DutyStatus) =>
  rowTop + dutyStatuses.indexOf(status) * rowHeight + rowHeight / 2;

function formatDutyDuration(seconds: number): string {
  const totalMinutes = Math.floor(seconds / 60);
  return `${String(Math.floor(totalMinutes / 60)).padStart(2, '0')}:${String(totalMinutes % 60).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`;
}

function SheetField({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="sheet-field">
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  );
}

export default function DailyLogSheet({ log, plan }: { log: DailyLog; plan: TripPlan }) {
  const details = plan.log_details;
  const graphPath = log.segments
    .map((segment, index) => {
      const startX = timePosition(segment.start_seconds);
      const endX = timePosition(segment.end_seconds);
      const lineY = statusPosition(segment.duty_status);
      return `${index === 0 ? `M ${startX} ${lineY}` : `L ${startX} ${lineY}`} L ${endX} ${lineY}`;
    })
    .join(' ');
  const totalSeconds = Object.values(log.totals_seconds).reduce(
    (total, seconds) => total + seconds,
    0,
  );
  const shortLocation = (location: string) =>
    location.replace(' (estimated)', '').replace('Near ', '');

  return (
    <article className="daily-log-sheet">
      <header className="sheet-heading">
        <div>
          <h3>Driver’s Daily Log</h3>
          <p>One calendar day · 24 hours · 70 hours / 8 days</p>
        </div>
        <div>
          <strong>{formatLogDate(log.date)}</strong>
          <span>
            Month / day / year: {log.date.slice(5, 7)} / {log.date.slice(8)} /{' '}
            {log.date.slice(0, 4)}
          </span>
        </div>
      </header>
      <div className="sheet-disclaimer">
        PLANNING ESTIMATE · UNSIGNED
        {details.sample_details ? ' · FICTIONAL EXAMPLE DRIVER DETAILS' : ''}
      </div>
      <div className="sheet-route">
        <SheetField label="From" value={plan.locations[0].label} />
        <SheetField label="To" value={plan.locations[2].label} />
      </div>
      <div className="sheet-details">
        <div>
          <div className="sheet-mileage">
            <SheetField label="Total miles driving today" value={log.distance_miles.toFixed(1)} />
            <SheetField
              label="Total truck miles today (this plan)"
              value={log.distance_miles.toFixed(1)}
            />
          </div>
          <SheetField
            label="Truck / tractor and trailer numbers"
            value={`${details.truck_number} / ${details.trailer_number}`}
          />
          <SheetField
            label="Driver / co-driver"
            value={`${details.driver_name} / ${details.co_driver_name}`}
          />
        </div>
        <div>
          <SheetField label="Name of carrier" value={details.carrier_name} />
          <SheetField label="Main office address" value={details.main_office_address} />
          <SheetField
            label="Home terminal address / time zone"
            value={`${details.home_terminal_address} · ${plan.terminal_timezone}`}
          />
        </div>
      </div>
      <svg
        className="log-grid"
        viewBox="0 0 1000 260"
        role="img"
        aria-label={`24-hour duty status graph for ${log.date}. ${formatDutyDuration(log.totals_seconds.driving)} driving, ${formatDutyDuration(log.totals_seconds.on_duty)} on duty.`}
      >
        <rect x={gridLeft} y="26" width={gridWidth} height="26" fill="#252e2b" />
        {Array.from({ length: 25 }, (_, hour) => (
          <text
            key={`hour-${hour}`}
            x={timePosition(hour * 3600) + (hour === 0 ? 2 : hour === 24 ? -2 : 0)}
            y="43"
            fill="white"
            fontSize={hour === 0 || hour === 24 ? 7 : 10}
            textAnchor={hour === 0 ? 'start' : hour === 24 ? 'end' : 'middle'}
          >
            {hour === 0 ? '00:00' : hour === 24 ? '24:00' : hour === 12 ? 'Noon' : hour}
          </text>
        ))}
        <text x="927" y="38" fontSize="11" textAnchor="middle" fill="#444">
          TOTAL HOURS
        </text>
        {dutyStatuses.map((status, rowIndex) => (
          <g key={status}>
            <rect
              x={gridLeft}
              y={rowTop + rowIndex * rowHeight}
              width={gridWidth}
              height={rowHeight}
              fill={rowIndex % 2 === 0 ? '#fafbf9' : 'white'}
              stroke="#9fa8a2"
              strokeWidth="0.7"
            />
            <text x="7" y={statusPosition(status) + 4} fontSize="12" fill="#343e38">
              {dutyLabels[rowIndex]}
            </text>
            {rowIndex === 3 && (
              <text x="7" y={statusPosition(status) + 17} fontSize="9" fill="#69716c">
                (not driving)
              </text>
            )}
            {Array.from({ length: 97 }, (_, quarterHour) => {
              const tickX = timePosition(quarterHour * 900);
              const tickLength = quarterHour % 4 === 0 ? rowHeight : quarterHour % 2 === 0 ? 14 : 7;
              return (
                <line
                  key={quarterHour}
                  x1={tickX}
                  x2={tickX}
                  y1={rowTop + (rowIndex + 1) * rowHeight - tickLength}
                  y2={rowTop + (rowIndex + 1) * rowHeight}
                  stroke="#9fa8a2"
                  strokeWidth="0.65"
                />
              );
            })}
            <text
              x="927"
              y={statusPosition(status) + 5}
              fontSize="13"
              textAnchor="middle"
              fill="#252e2b"
              fontWeight="600"
            >
              {formatDutyDuration(log.totals_seconds[status])}
            </text>
          </g>
        ))}
        <path d={graphPath} fill="none" stroke="#243a30" strokeWidth="3" strokeLinejoin="miter" />
        <text x="7" y="231" fontSize="11" fontWeight="600" fill="#343e38">
          REMARKS ↓
        </text>
        <line
          x1={gridLeft}
          x2={gridLeft + gridWidth}
          y1="219"
          y2="219"
          stroke="#9fa8a2"
          strokeWidth="0.6"
        />
        {log.remarks.map((remark, index) => (
          <g key={index}>
            <line
              x1={timePosition(remark.seconds)}
              x2={timePosition(remark.seconds)}
              y1="214"
              y2="230"
              stroke="#42564b"
            />
            <text
              x={timePosition(remark.seconds)}
              y={239 + (index % 2) * 13}
              textAnchor="middle"
              fontSize="9"
              fill="#42564b"
            >
              {index + 1}
            </text>
          </g>
        ))}
        <text x="927" y="236" fontSize="12" textAnchor="middle" fill="#252e2b">
          Σ {formatDutyDuration(totalSeconds)}
        </text>
      </svg>
      <div className="sheet-remarks">
        {log.remarks.length ? (
          log.remarks.map((remark, index) => (
            <div key={index}>
              <span className="remark-number">{index + 1}</span>
              <div>
                <strong>
                  {remark.time} · {shortLocation(remark.location)}
                </strong>
                <p>{remark.activity}</p>
              </div>
            </div>
          ))
        ) : (
          <p>
            Continuing {log.segments[0].duty_status.replaceAll('_', ' ')} from the previous day at{' '}
            {log.segments[0].location.label}. No change of duty status today.
          </p>
        )}
      </div>
      <div className="sheet-shipping">
        <SheetField label="Shipping document / manifest no." value={details.shipping_document} />
        <SheetField
          label="Shipper & commodity"
          value={`${details.shipper_name} · ${details.commodity}`}
        />
      </div>
      <div className="sheet-recap">
        <div>
          <h4>Recap · 70 hours / 8 days</h4>
          <div className="recap-values">
            <SheetField
              label="On-duty hours today (3 + 4)"
              value={log.recap.on_duty_hours.toFixed(2)}
            />
            <SheetField
              label="A. Total last 7 days incl. today"
              value={log.recap.last_seven_days_hours.toFixed(2)}
            />
            <SheetField
              label="B. Hours available tomorrow*"
              value={log.recap.hours_available_tomorrow.toFixed(2)}
            />
            <SheetField
              label="C. Total last 8 days incl. today"
              value={log.recap.last_eight_days_hours.toFixed(2)}
            />
          </div>
        </div>
        <div>
          <h4>60 hours / 7 days</h4>
          <div className="recap-na">
            <span>A. N/A</span>
            <span>B. N/A</span>
            <span>C. N/A</span>
          </div>
          <p>Not applicable: 70/8 schedule.</p>
        </div>
        <div>
          <h4>34-hour restart</h4>
          <strong>
            {log.recap.restart_completed_today ? 'Completed today' : 'Not completed today'}
          </strong>
          <p>{log.recap.cycle_remaining_hours.toFixed(2)} cycle hours available at end of day.</p>
        </div>
      </div>
      <footer className="sheet-footer">
        <span>
          *Available hours account for completed restarts and hours rolling out of the cycle.
        </span>
        <span>
          All locations are in home-terminal time. Original / duplicate: unsigned planning copies.
        </span>
      </footer>
    </article>
  );
}
