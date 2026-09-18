# WeatherGPT Provider Integration & Verification

This document provides the definitive, audit-verified record of all external and internal providers in WeatherGPT as verified during the **Live Provider Verification & Production Integration** phase.

## 1. Provider Status Matrix

| Provider Domain | Provider Name | Source Class | Credential Status | Integration Status | Live Verified Endpoints / Capabilities | Failure / Fallback Behavior |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Primary Weather** | Open-Meteo API | `commercial_open` (Non-authoritative) | **None Required** (Public open endpoint) | **LIVE / VERIFIED** | `https://api.open-meteo.com/v1/forecast` (hourly temp, precip, humidity, wind speed, wind gusts, visibility, WMO weather code) | Raises `RuntimeError`/degrades to `TripStatus.weather_unavailable`. Non-blocking retries on 5xx. |
| **Secondary Weather** | WeatherAPI | `secondary` (Non-authoritative) | **Missing / Pending** (`WEATHERAPI_API_KEY` not set) | **PENDING CREDENTIALS** (Adapter complete) | Controlled client raises `ValueError` if key missing. When configured: secondary comparison & confidence down-weighting. | Degrades silently in `TripService`; comparison runs with `secondary=None` without failing trip. |
| **Routing** | Google Routes API | `commercial` | **Missing / Pending** (`GOOGLE_MAPS_API_KEY` not set) | **PENDING CREDENTIALS** (Adapter complete) | Offline/unit tests pass with mocked payloads. Live calls raise `ConfigurationError` when key missing. | `TripService` cleanly sets `TripStatus.routing_unavailable`, `risk = None`, `routes = []`, records `Routing [unavailable]`. |
| **Routing (Demo/Mock)** | Mock Routing API | `demo` | None | **VERIFIED (Mock)** | Synthetic multi-route corridors (1 to 3 routes) in Delhi-NCR with polyline geometry and realistic static durations. | Always available in demo/fallback mode. |
| **Traffic** | Mock Traffic Provider | `demo/mock` | None | **VERIFIED (Mock)** | Rush-hour vs. off-peak delays, mode-based zero delay (walk/metro), traffic-aware durations, segments. | Labeled `status=mock`, `provenance="demo/mock"`. |
| **Traffic (Production)** | TomTom / Google Traffic | `primary` | **Pending** | **PENDING CREDENTIALS** | Adapter architecture ready; `UnavailableTrafficProvider` active when live provider is not configured. | `TripStatus.success` preserved with `delaySeconds = 0.0` and `status = unavailable`. |
| **Official Alerts** | IMD / NDMA CAP | `authoritative` | Whitelist Pending | **UNAVAILABLE (Direct)** | Direct government API blocked by government IP whitelisting constraints. | Blocked from direct access; authoritative CAP feed will be hooked when gateway access is granted. |
| **Alerts (Demo/Mock)** | WeatherGPT Internal Mock | `demo` | None | **VERIFIED (Mock)** | Emergency alerts, advisory warnings, closure polygons. | Subject to application-level override policy: demo alerts cannot trigger emergency overrides in production mode. |
| **Curated Hazards** | Delhi-NCR Hazard Repository | `curated_historical` | Local | **VERIFIED (Curated)** | Spatially mapped flood hotspots, waterlogging underpasses, landslide corridors activated by live precipitation triggers. | Retained in local memory repository. |

---

## 2. Provenance Guarantees & Enforcement

WeatherGPT enforces strict provenance invariants to guarantee that fake, mock, or secondary data is never disguised as authoritative or live:

1. **`live ≠ mock`**:
   - Every provider output includes a typed status and provenance string (e.g. `status = TrafficStatus.mock`, `provenance = "demo/mock"` vs `status = TrafficStatus.live`, `provenance = "google_routes"`).
   - Contradictory combinations (e.g., claiming `status = live` while having `provenance = "demo/mock"`) are strictly rejected at the Pydantic schema validation level.

2. **`mock ≠ authoritative`**:
   - Mock alerts are assigned `source_class = AlertSourceClass.demo`.
   - The decision engine's alert policy strictly prohibits `demo` alerts from triggering emergency override logic when running in production mode (`settings.DEMO_MODE = False`).

3. **`secondary ≠ authoritative`**:
   - Commercial aggregators (e.g. WeatherAPI, Open-Meteo) are never labeled as official government or civil protection entities.
   - WeatherAPI alerts are normalized under `source_class = AlertSourceClass.secondary` and cannot trigger hard emergency overrides.
   - Open-Meteo is labeled as `Open-Meteo API (Weather (Primary))` with attribution compliant with the CC BY 4.0 license.

4. **Transparent Degradation (No Fake Success)**:
   - A failure in a provider must never be masked as synthetic success in live mode.
   - If routing fails or credentials are missing, the system returns `TripStatus.routing_unavailable`, sets `risk = None`, and reports `Routing [unavailable]` in `sources`.

---

## 3. End-to-End Live Verification Details

### Open-Meteo API
- **Endpoint**: `https://api.open-meteo.com/v1/forecast?latitude=28.627&longitude=77.365&hourly=temperature_2m,relative_humidity_2m,precipitation,weather_code,visibility,wind_speed_10m,wind_gusts_10m&timezone=UTC`
- **Fields Verified**:
  - `temperature_2m`: Live floating-point degrees Celsius.
  - `precipitation`: Hourly accumulation in mm.
  - `visibility`: Physical measurement in meters (e.g., 7660.0m).
  - `wind_speed_10m` & `wind_gusts_10m`: Verified in km/h.
  - `weather_code`: Translated via WMO table into human-readable conditions.
  - `timestamps`: Parsed and validated strictly in UTC ISO-8601.
- **Decision Engine Flow**:
  - Raw hourly entries mapped to `NormalizedWeatherPoint`.
  - `is_extreme_heat` and `is_poor_visibility` calculated dynamically.
  - Evaluated along route waypoints with temporal alignment.

### Google Routes API
- **Environment Key**: `GOOGLE_MAPS_API_KEY`
- **Verification Result**: Unconfigured (`NOT_SET`).
- **Behavior Verified**: `GoogleRoutesProvider` cleanly raises `ConfigurationError("GOOGLE_MAPS_API_KEY is not configured in the environment.")`. `TripService` cleanly handles this and returns `TripStatus.routing_unavailable`. No fabrication.

### WeatherAPI
- **Environment Key**: `WEATHERAPI_API_KEY`
- **Verification Result**: Unconfigured (`NOT_SET`).
- **Behavior Verified**: `WeatherAPIClient` cleanly raises `ValueError("WeatherAPI key is missing.")`. `TripService` catches the secondary fetch error and completes the primary assessment with `sources` reflecting the missing secondary source.

---

## 4. Known Limitations & Production Readiness

1. **Routing Dependency**: Live route geometry currently depends on configuring `GOOGLE_MAPS_API_KEY`. In environments without the key, `MockRoutingProvider` serves as the testbed for multi-alternative evaluation.
2. **Authoritative Alerts**: Direct IMD CAP alerts require government IP whitelisting. Currently, curated hazards and mock alerts test all alert policies and override paths.
3. **Traffic**: Real-time traffic depends on Google Routes embedded traffic duration or TomTom API. The mock traffic provider provides deterministic testing with zero double-counting.
