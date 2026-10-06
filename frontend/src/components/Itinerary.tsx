import { ArrowRight, Coffee, Fuel, Moon, Package, Truck } from 'lucide-react';
import type { TripPlan } from '../types';
import { formatDate, formatDuration, formatTime, localDateKey } from '../format';

const activityIcons = {
  drive: Truck,
  pickup: Package,
  dropoff: Package,
  fuel: Fuel,
  break: Coffee,
  daily_rest: Moon,
  cycle_restart: Moon,
};
const activityTitles: Record<string, string> = {
  drive: 'On the road',
  pickup: 'Pick up cargo',
  dropoff: 'Deliver cargo',
  fuel: 'Fuel stop',
  break: '30-minute break',
  daily_rest: '10-hour rest',
  cycle_restart: '34-hour restart',
};

export default function Itinerary({ plan }: { plan: TripPlan }) {
  const dates = [
    ...new Set(plan.events.map((event) => localDateKey(event.start_time, plan.terminal_timezone))),
  ];
  return (
    <div className="itinerary">
      <div className="section-header">
        <div>
          <span className="eyebrow">EVERY STOP, ACCOUNTED FOR</span>
          <h2>Your road ahead</h2>
        </div>
        <span className="pill">{plan.events.length} activities</span>
      </div>
      <p className="muted section-description">
        All times use your home terminal: {plan.terminal_timezone.replaceAll('_', ' ')}. Long
        activities can continue into the next day.
      </p>
      {dates.map((date, dayIndex) => (
        <section className="itinerary-day" key={date}>
          <div className="day-heading">
            <span>Day {dayIndex + 1}</span>
            <strong>
              {formatDate(
                plan.events.find(
                  (event) => localDateKey(event.start_time, plan.terminal_timezone) === date,
                )!.start_time,
                plan.terminal_timezone,
              )}
            </strong>
          </div>
          {plan.events
            .filter((event) => localDateKey(event.start_time, plan.terminal_timezone) === date)
            .map((event, index) => {
              const Icon = activityIcons[event.activity as keyof typeof activityIcons] ?? Truck;
              return (
                <div className={`timeline-event event-${event.activity}`} key={index}>
                  <div className="timeline-time">
                    {formatTime(event.start_time, plan.terminal_timezone)}
                    <span>{formatDuration(event.duration_seconds)}</span>
                  </div>
                  <div className="timeline-icon">
                    <Icon size={17} />
                  </div>
                  <div className="timeline-description">
                    <strong>{activityTitles[event.activity] ?? event.activity}</strong>
                    <p>{event.location.label}</p>
                    <span>{event.reason}</span>
                  </div>
                  <div className="timeline-metric">
                    {event.activity === 'drive'
                      ? `${Math.round(event.distance_miles)} mi`
                      : formatTime(event.end_time, plan.terminal_timezone)}
                    <span>
                      {event.activity === 'drive'
                        ? 'distance'
                        : `ends ${formatDate(event.end_time, plan.terminal_timezone)}`}
                    </span>
                  </div>
                </div>
              );
            })}
        </section>
      ))}
      <details className="directions">
        <summary>
          Turn-by-turn directions <ArrowRight size={16} />
        </summary>
        <ol>
          {plan.route.instructions.map((instruction, index) => (
            <li key={index}>
              <span className="direction-leg">
                {instruction.leg === 0 ? 'To pickup' : 'To delivery'}
              </span>
              <span>{instruction.text}</span>
              <strong>{instruction.distance_miles} mi</strong>
            </li>
          ))}
        </ol>
      </details>
    </div>
  );
}
