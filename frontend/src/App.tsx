import { useRef, useState } from 'react';
import {
  ArrowRight,
  Check,
  ChevronLeft,
  ChevronRight,
  Clock3,
  Download,
  FileText,
  Fuel,
  Info,
  Map,
  MapPin,
  Printer,
  Route,
  ShieldCheck,
  Truck,
} from 'lucide-react';
import TripForm from './components/TripForm';
import RouteMap from './components/RouteMap';
import Itinerary from './components/Itinerary';
import DailyLogSheet from './components/DailyLogSheet';
import { createTripPlan } from './api';
import { exportLogsPdf } from './exportLogsPdf';
import { formatDate, formatDuration, formatLogDate, formatTime } from './format';
import type { TripPlan, TripRequest } from './types';

export default function App() {
  const [plan, setPlan] = useState<TripPlan | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<'route' | 'logs'>('route');
  const [activeDay, setActiveDay] = useState(0);
  const [exportingPdf, setExportingPdf] = useState(false);
  const [pdfError, setPdfError] = useState('');
  const printableSheets = useRef<HTMLDivElement>(null);

  async function downloadLogsPdf() {
    if (!plan || !printableSheets.current || exportingPdf) return;
    setExportingPdf(true);
    setPdfError('');
    try {
      const pdfBlob = await exportLogsPdf(
        printableSheets.current,
        plan.daily_logs[0].date,
        plan.daily_logs[plan.daily_logs.length - 1].date,
      );
      const downloadUrl = URL.createObjectURL(pdfBlob);
      const downloadLink = document.createElement('a');
      downloadLink.href = downloadUrl;
      downloadLink.download = `daily-logs-${plan.daily_logs[0].date}-to-${plan.daily_logs[plan.daily_logs.length - 1].date}.pdf`;
      document.body.appendChild(downloadLink);
      downloadLink.click();
      downloadLink.remove();
      // Give the browser time to save the file before releasing the temporary URL.
      window.setTimeout(() => URL.revokeObjectURL(downloadUrl), 60_000);
    } catch (error) {
      setPdfError(
        error instanceof Error
          ? error.message
          : 'Could not download the daily logs. Please try again.',
      );
    } finally {
      setExportingPdf(false);
    }
  }

  async function generatePlan(trip: TripRequest) {
    setLoading(true);
    setError('');
    try {
      const result = await createTripPlan(trip);
      setPlan(result);
      setActiveTab('route');
      setActiveDay(0);
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Could not create the trip plan.');
    } finally {
      setLoading(false);
    }
  }

  function downloadPlan() {
    if (!plan) return;
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(plan, null, 2)], { type: 'application/json' }),
    );
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `trip-plan-${plan.daily_logs[0].date}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <>
      <div className="app-shell">
        <header className="app-header">
          <a className="brand" href="/" aria-label="Spotter trip planner home">
            <span className="brand-mark">
              <Truck size={22} />
            </span>
            <strong>
              spotter<span> / trip planner</span>
            </strong>
          </a>
          <div className="header-right">
            <span className="header-tag">
              <ShieldCheck size={15} /> Property carrying · 70/8
            </span>
            <span className="avatar">LP</span>
          </div>
        </header>
        <aside className="sidebar">
          <TripForm loading={loading} exportingPdf={exportingPdf} onSubmit={generatePlan} />
          <div className="sidebar-bottom">
            <span className="status-dot" />
            <span>Made for the miles ahead.</span>
          </div>
        </aside>
        <main className="workspace">
          <div className="workspace-heading">
            <div>
              <div className="breadcrumb">
                Workspace <ChevronRight size={12} /> Trip planner
              </div>
              <h1>{plan ? 'Your trip, mapped out.' : 'A clearer road ahead.'}</h1>
              <p>
                {plan
                  ? `${plan.locations[0].label} to ${plan.locations[2].label}`
                  : 'One route. Every stop. A log for every day.'}
              </p>
            </div>
            {plan ? (
              <div className="workspace-actions">
                <button
                  className="secondary-button icon-button"
                  onClick={downloadPlan}
                  title="Download trip data"
                  aria-label="Download trip data"
                >
                  <Download size={17} />
                </button>
                <button className="secondary-button" onClick={() => window.print()}>
                  <Printer size={16} /> Print logs
                </button>
                <button
                  className="secondary-button"
                  disabled={loading || exportingPdf}
                  onClick={() => void downloadLogsPdf()}
                >
                  <Download size={16} /> {exportingPdf ? 'Creating PDF…' : 'Download PDF'}
                </button>
              </div>
            ) : (
              <span className="workspace-note">
                <MapPin size={15} /> United States
              </span>
            )}
          </div>
          {pdfError && (
            <div className="error-banner" role="alert">
              <Info size={20} />
              <div>
                <strong>PDF download failed.</strong>
                <p>{pdfError}</p>
              </div>
            </div>
          )}
          {error && (
            <div className="error-banner" role="alert">
              <Info size={20} />
              <div>
                <strong>We couldn’t finish this plan.</strong>
                <p>{error}</p>
                {plan && <p>The previous plan remains visible below.</p>}
              </div>
            </div>
          )}
          {plan && (
            <div className="summary-grid">
              <div className="summary-card">
                <span>
                  <Route size={16} /> TOTAL DISTANCE
                </span>
                <strong>
                  {Math.round(plan.summary.distance_miles).toLocaleString()}
                  <small>mi</small>
                </strong>
                <p>Via pickup location</p>
              </div>
              <div className="summary-card">
                <span>
                  <Truck size={16} /> DRIVING TIME
                </span>
                <strong>{formatDuration(plan.summary.driving_seconds)}</strong>
                <p>{formatDuration(plan.summary.elapsed_seconds)} including stops</p>
              </div>
              <div className="summary-card">
                <span>
                  <Clock3 size={16} /> DELIVERY ARRIVAL
                </span>
                <strong>
                  {formatTime(plan.summary.arrival_time, plan.terminal_timezone)}
                  <small>{formatDate(plan.summary.arrival_time, plan.terminal_timezone)}</small>
                </strong>
                <p>Plus 1 hour to unload</p>
              </div>
              <div className="summary-card">
                <span>
                  <FileText size={16} /> DAILY LOGS
                </span>
                <strong>
                  {plan.summary.log_days}
                  <small>sheets</small>
                </strong>
                <p>
                  {plan.summary.rest_stops} rests · {plan.summary.fuel_stops} fuel stops
                </p>
              </div>
            </div>
          )}
          <nav className="view-tabs" aria-label="Plan views">
            <button
              className={activeTab === 'route' ? 'active' : ''}
              onClick={() => setActiveTab('route')}
            >
              <Map size={16} /> Route & itinerary
            </button>
            <button
              className={activeTab === 'logs' ? 'active' : ''}
              disabled={!plan}
              onClick={() => setActiveTab('logs')}
            >
              <FileText size={16} /> Daily log sheets {plan && <span>{plan.summary.log_days}</span>}
            </button>
            <div className="tabs-right">
              {plan ? (
                <>
                  <span className="status-dot" />
                  Plan generated
                </>
              ) : (
                <>
                  Ready when you are <ArrowRight size={14} />
                </>
              )}
            </div>
          </nav>
          {activeTab === 'route' && (
            <>
              <section className={`map-card ${!plan ? 'empty-map-card' : ''}`}>
                <RouteMap plan={plan} />
                {!plan && (
                  <div className="empty-map-overlay">
                    <span className="empty-map-icon">
                      <Route size={28} />
                    </span>
                    <h2>Your next journey starts here.</h2>
                    <p>
                      Add your locations or try the sample trip.
                      <br />
                      We’ll bring the route and daily logs together.
                    </p>
                    <div>
                      <span>
                        <Check size={14} /> Route instructions
                      </span>
                      <span>
                        <Check size={14} /> HOS-aware planning
                      </span>
                    </div>
                  </div>
                )}
              </section>
              {plan ? (
                <>
                  <div className="route-status">
                    <ShieldCheck size={17} />
                    <strong>Breaks built into your plan</strong>
                    <span>11h driving · 14h window · 70h cycle</span>
                  </div>
                  <Itinerary plan={plan} />
                  <details className="planning-notes">
                    <summary>
                      <Info size={16} /> Planning assumptions & map limitations
                    </summary>
                    <ul>
                      {plan.warnings.map((warning) => (
                        <li key={warning}>{warning}</li>
                      ))}
                    </ul>
                    <p>
                      The initial seven-day history is used for rolling recaps. No adverse-driving
                      or split-sleeper exceptions are applied.
                    </p>
                  </details>
                </>
              ) : (
                <div className="empty-features">
                  <div>
                    <span>
                      <Map size={19} />
                    </span>
                    <h3>The whole journey</h3>
                    <p>Current location, pickup and delivery on one map.</p>
                  </div>
                  <div>
                    <span>
                      <Fuel size={19} />
                    </span>
                    <h3>Stops that make sense</h3>
                    <p>Fuel, breaks and rest included in your schedule.</p>
                  </div>
                  <div>
                    <span>
                      <FileText size={19} />
                    </span>
                    <h3>Paperwork, planned</h3>
                    <p>Printable daily sheets with every status change.</p>
                  </div>
                </div>
              )}
            </>
          )}
          {activeTab === 'logs' && plan && (
            <section className="logs-view">
              <div className="log-toolbar">
                <div>
                  <span className="eyebrow">DRIVER’S DAILY LOG</span>
                  <h2>{formatLogDate(plan.daily_logs[activeDay].date)}</h2>
                </div>
                <div className="day-selector">
                  <button
                    aria-label="Previous log day"
                    disabled={activeDay === 0}
                    onClick={() => setActiveDay(activeDay - 1)}
                  >
                    <ChevronLeft size={17} />
                  </button>
                  <select
                    aria-label="Select log day"
                    value={activeDay}
                    onChange={(event) => setActiveDay(Number(event.target.value))}
                  >
                    {plan.daily_logs.map((log, index) => (
                      <option key={log.date} value={index}>
                        Day {index + 1} · {formatLogDate(log.date)}
                      </option>
                    ))}
                  </select>
                  <button
                    aria-label="Next log day"
                    disabled={activeDay === plan.daily_logs.length - 1}
                    onClick={() => setActiveDay(activeDay + 1)}
                  >
                    <ChevronRight size={17} />
                  </button>
                </div>
              </div>
              <div className="log-scroll">
                <DailyLogSheet log={plan.daily_logs[activeDay]} plan={plan} />
              </div>
              <p className="log-help">
                <Info size={15} /> Each numbered mark under the grid points to the location and
                activity below. Download PDF saves all daily sheets directly.
              </p>
            </section>
          )}
          <footer className="workspace-footer">
            <span>Spotter assessment · Trip planning estimates</span>
            <a
              href="https://www.fmcsa.dot.gov/regulations/hours-service/summary-hours-service-regulations"
              target="_blank"
              rel="noreferrer"
            >
              FMCSA hours of service <ArrowRight size={12} />
            </a>
          </footer>
        </main>
      </div>
      {plan && (
        <div className="print-logs" ref={printableSheets}>
          {plan.daily_logs.map((log) => (
            <DailyLogSheet key={log.date} log={log} plan={plan} />
          ))}
        </div>
      )}
    </>
  );
}
