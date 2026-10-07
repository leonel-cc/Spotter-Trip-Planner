# Spotter HOS Trip Planner

[Live application](https://spotter-trip-planner-rosy.vercel.app) · [GitHub repository](https://github.com/leonel-cc/Spotter-Trip-Planner)

A Django and React trip planner that calculates a road route, driving schedule, required stops, and daily driver logs from the trip locations and cycle history. Includes an interactive map, a timed itinerary, PDF downloads, and JSON export.

## Run locally on Windows

Requirements: Python 3.12+, Node.js 22.12+ (tested with Node 24), and an internet connection for map tiles/routing.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
Copy-Item backend\.env.example backend\.env
Set-Location frontend
npm ci
Set-Location ..
```

Open two terminals in the project root:

```powershell
# Terminal 1
.\scripts\start-dev.ps1 backend
# Terminal 2
.\scripts\start-dev.ps1 frontend
```

Open http://127.0.0.1:5173 and choose **Try a sample trip**, then **Generate trip plan**. The example uses Chicago → Indianapolis → Dallas and fictional carrier/driver information. Replace it to plan another trip. Search is explicit: enter a city/address, click the magnifying glass, and select a result.

On macOS/Linux, create/activate a virtual environment, install the same requirements, run `DEBUG=true python backend/manage.py runserver`, and run `npm ci && npm run dev` from `frontend` in a second terminal.

## Planning a trip

- Current location, pickup, and delivery, selected from search results.
- Current cycle used, from 0 to 70 hours.
- Departure date/time and home-terminal time zone.
- Seven previous daily on-duty totals, oldest first. Their sum must match the cycle used; these values are used to calculate the rolling recap.
- Driver/co-driver, carrier, office, terminal, tractor/trailer, shipping document, shipper, and commodity. Enter `N/A` only where it actually applies.
- Off-duty or sleeper-berth status for long rests.

The resulting screen includes estimated arrival/completion, distance, route instructions, timed stops, map markers, and one sheet per terminal calendar day. Each sheet covers all 24 hours, totals all four duty statuses, lists each planned status change with its location below the graph, and completes the applicable 70/8 recap. The 60/7 fields are explicitly N/A. **Download PDF** directly downloads all daily sheets, one Letter page per day, without a print dialog. It preserves the visual sheet as a high-resolution image, so sheet text is not selectable in the PDF. **Print logs** remains available for physical printing. JSON export includes the route, event timeline, sheets, assumptions, and entered log details.

## Maps and external data

Trip locations are entered in the form. The backend requests a road route from the configured provider and calculates the driving schedule from that route and the cycle history.

| Configuration | Behavior |
| --- | --- |
| `ORS_API_KEY` set | OpenRouteService `driving-hgv` route. API key stays on the server. |
| `ORS_API_KEY` empty | Public OSRM general-driving route, with a visible provider label and truck-restriction warning. |
| `GEOCODING_PROVIDER` | Defaults to Photon on Vercel and Nominatim for local/Docker deployments. |
| `PHOTON_BASE_URL` | Photon address search and estimated intermediate place names; defaults to the public Photon demo. |
| `NOMINATIM_BASE_URL` | Nominatim address search and intermediate place names when selected. |
| `MAP_USER_AGENT` | Set a descriptive application name and your public project URL/contact before public deployment. |
| `REVERSE_GEOCODING=false` | Skip intermediate place-name lookup; show estimated route coordinates. |

The default OSRM profile provides general driving routes without truck restrictions. OpenRouteService supports the `driving-hgv` profile, but the form does not collect truck dimensions or hazardous cargo details. Stops are positions along the road geometry, **not verified stations or parking facilities**. If place-name lookup fails, coordinates are retained. Provider failures are displayed as errors in the application.

Geocoding is manual and cached. Nominatim requests are serialized at less than one request per second within a single deployment instance; Vercel uses Photon instead. The hosted demo uses public providers. For higher traffic/multiple replicas, use your own geocoder/routing service and shared rate limiting/cache. Public provider availability and limits are external dependencies.

## Scheduling rules and limitations

- Property-carrying driver on the **70-hour / 8-day** schedule; no adverse-driving or split-sleeper exceptions.
- Driver starts after at least 10 consecutive hours of rest, has no earlier work on the departure date, and starts with a full tank. Previous daily totals represent the current active cycle (work before a prior restart should not be supplied).
- At most 11 driving hours per shift, within a 14-hour elapsed window. Ordinary breaks and work do not pause the 14-hour clock.
- At least 30 consecutive non-driving minutes after eight cumulative driving hours. Pickup, unloading, or fuel can satisfy the break.
- Pickup and unloading each take one hour; fuel takes 30 minutes. Fuel is scheduled before driving 1,000 miles since the previous fill.
- Driving stops when the 70-hour cycle capacity is exhausted. A 34-hour rest restarts the cycle; a daily rest takes 10 hours. Old history rolls off at home-terminal midnight. The policy chooses a restart when exhausted rather than optimizing a wait for the next midnight.
- Non-driving work counts toward cycle hours. The 70-hour restriction prevents further **driving**, not all non-driving duties.
- All calculations use seconds and actual route distance; daily totals display HH:MM:SS. Arrival is before the one-hour unload, completion is after it.
- Time before departure and after completion is assumed off duty. Sheets are unsigned planning estimates, not records of activities that actually happened.
- Trips crossing a 23/25-hour daylight-saving calendar day are rejected because the log uses a 24-hour paper grid. Ambiguous/nonexistent departure times are rejected too. Maximum route length: 6,000 miles.

Rules reference: [FMCSA HOS summary](https://www.fmcsa.dot.gov/regulations/hours-service/summary-hours-service-regulations).

## Architecture

```text
frontend/src/components/TripForm.tsx       user input and validation
frontend/src/components/RouteMap.tsx       Leaflet route and stop markers
frontend/src/components/Itinerary.tsx      schedule and road instructions
frontend/src/components/DailyLogSheet.tsx  SVG grid, fields, remarks, recap
backend/trips/serializers.py              API validation and terminal times
backend/trips/routing.py                  OSRM/ORS/geocoding adapters
backend/trips/domain.py                   route interpolation and event types
backend/trips/scheduler.py                HOS event scheduling
backend/trips/logs.py                     calendar-day clipping and recap
backend/trips/views.py                    orchestration and JSON response
```

The scheduler has no dependency on HTTP, Django, or React. Provider responses are normalized before scheduling. This keeps changes to rules, providers, and visual rendering independent. The application is stateless. Trip data is not persisted; cache entries contain map results and throttle counters.

API: `GET /api/health`, `GET /api/locations?q=Chicago`, `POST /api/trips/plan`. A representative request is available in `example_payload()` in `backend/trips/tests.py`. Invalid input returns 400; unavailable map providers return 503; throttling returns 429. Requests are same-origin in production, and Vite proxies `/api` locally.

## Verify and build

```powershell
$env:DEBUG = 'true'
.\.venv\Scripts\python.exe backend\manage.py test trips
Set-Location frontend
npm run build
Set-Location ..
.\.venv\Scripts\python.exe backend\manage.py collectstatic --noinput
.\.venv\Scripts\python.exe backend\serve.py
```

The built app is served at http://127.0.0.1:8000 by Django + WhiteNoise + Waitress. GitHub Actions runs backend tests and the TypeScript/production build. Backend tests cover long trips, driving/break/window/cycle/fuel invariants, midnight rolling hours, restart history, sleeper status, 24-hour sheet coverage, API validation, and DST rejection. Live provider access is deliberately excluded from deterministic tests.

## Deploy

The multi-stage Dockerfile builds React, collects static files, and runs the backend as a non-root user. Both frontend and API share one public origin. Docker deployment requires a generated `SECRET_KEY`, `DEBUG=false`, your exact hostname in `ALLOWED_HOSTS`, and your map settings. `PORT` defaults to 8000. Configure `TRUSTED_PROXY` for the reverse proxy; `*` is appropriate only behind a trusted platform proxy, not for direct unrestricted deployment.

For Render, push this repository to your GitHub account, create a Blueprint from `render.yaml`, and supply a descriptive `MAP_USER_AGENT`. It uses the clearly labeled OSRM demo by default. To enable heavy-vehicle routes, add `ORS_API_KEY` in the service's environment settings. Render's external hostname is automatically allowed. The blueprint explicitly selects the free plan; check availability/terms in your account. It enables HTTPS redirects behind Render's proxy and generates the secret. The Docker configuration has not been verified with a local container build. The compiled application was verified with Waitress and `DEBUG=false`. Reference: [Render Blueprint specification](https://render.com/docs/blueprint-spec).

Code formatting: install `backend/requirements-dev.txt` and run `ruff check backend` / `ruff format backend`; from `frontend`, run `npm run format`. CI checks both formatting and the application build/tests.

## Preview

![Trip planner](docs/screenshots/trip-planner.jpg)

## Deploy on Vercel

Import this repository from GitHub and keep the Root Directory at the repository root. `vercel.json` selects Django and builds the React frontend; the root `requirements.txt` installs backend dependencies. Vercel discovers `backend/manage.py`, runs Django's `collectstatic`, serves assets from its CDN, and runs the Django API as a Python function. The frontend and API share one origin. The function timeout is 180 seconds.

Set these environment variables for Production and Preview before deployment:

- `SECRET_KEY`: a randomly generated secret, stored only in Vercel.
- `DEBUG=false`.
- `MAP_USER_AGENT=SpotterTripPlanner/1.0 (https://github.com/leonel-cc/Spotter-Trip-Planner)`.

Vercel deployment hostnames are added to `ALLOWED_HOSTS` automatically. For a custom domain, also set `ALLOWED_HOSTS` to include it. `ORS_API_KEY` remains optional; without it, the app uses OSRM general driving routes.

Vercel's filesystem is read-only outside the temporary directory. Cache files and geocoder locks therefore use `/tmp/spotter-trip-planner` on Vercel. These are temporary and local to each function instance; throttles and caches are not shared globally. The hosted demo uses per-instance caching and throttling; these counters are not shared across instances.

Vercel defaults to the public Photon geocoder for manual searches and estimated stop descriptions. This avoids relying on Nominatim's single-instance request lock in a serverless deployment. Photon allows reasonable demo usage without availability guarantees. Responses are cached for seven days per instance. Set `PHOTON_BASE_URL` to a private instance for higher traffic. Local and Docker deployments continue using Nominatim by default. Set `GEOCODING_PROVIDER` explicitly to override either default.

After deployment, verify `/api/health`, location search, the sample trip, map tiles, both daily logs, and PDF download from the public production URL. Reference: [Django on Vercel](https://vercel.com/docs/frameworks/full-stack/django), [Photon API and demo policy](https://github.com/komoot/photon).
