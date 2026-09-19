# Phase 20: Intelligence & Data Provider Expansion — Implementation Plan

**Milestone:** Phase 20 (Intelligence & Data Provider Expansion)  
**Status:** Architecture Design & Implementation Plan (Review Phase)  
**Author:** Antigravity Engineering (Google DeepMind Team)  
**Target Date:** September 2026  

---

## Executive Summary

WeatherGPT is transitioning from an algorithmic prototype into a production-grade personal navigation intelligence product for Indian commuters. 

This phase focuses exclusively on **real-world usefulness, data intelligence, reliability, and decision quality**, without adding superficial complexity or weakening the deterministic Decision Engine.

### Fundamental Principle & Architectural Invariant
> **The Decision Engine remains the SOLE authority for risk scoring, risk tiers, route selection, feasibility, alert handling, and safety recommendations.**  
> External providers **ONLY supply raw observations, forecasts, telemetry, or geographic coordinates**. External providers, LLMs, persistence layers, and client state **MUST NEVER** become decision authorities.

---

## 1. Current Architecture Assessment (Discovered Facts from Repository)

A thorough audit of the active repository reveals the following baseline:

1. **Weather Layer (`backend/app/providers/weather/`)**:
   - Primary: `OpenMeteoWeatherProvider` (fetches hourly `temperature_2m`, `relative_humidity_2m`, `precipitation`, `weather_code`, `wind_speed_10m`, `wind_gusts_10m`, `visibility`).
   - Secondary: `WeatherAPIProvider` (commercial backup with `alerts.json` support).
   - Fallback: `FallbackWeatherProvider` (in production, `secondary=None` to prevent silent mock weather leakage; raises typed error on outage).
   - Standalone endpoints: `GET /weather/current` and `GET /weather/forecast` return `WeatherPoint` or HTTP 503.

2. **Routing Layer (`backend/app/providers/routing/`)**:
   - Primary: `GoogleRoutesProvider` (supports `TWO_WHEELER`, `DRIVE`, `WALK`; requests alternative routes).
   - Mock: `MockRoutingProvider` (returns 3 deterministic route corridors between Noida and Gurgaon).
   - Fallback: `FallbackRoutingProvider`.

3. **Traffic Layer (`backend/app/providers/traffic/`)**:
   - Currently **100% synthetic/mock** (`MockTrafficProvider`). Calculates artificial rush-hour delays based solely on server clock time.
   - `GoogleRoutesProvider` contains parser logic for `staticDuration` vs `duration`, but **does not pass `routingPreference: "TRAFFIC_AWARE"` or `departureTime`**, preventing live Google traffic telemetry from activating.

4. **Geocoding & Location Resolution (`backend/app/services/trip_service.py:44-53`)**:
   - **CRITICAL GAP**: Handled by a hardcoded synchronous helper `_mock_geocode`:
     ```python
     if "gurgaon" in location or "cyber hub" in location:
         return 28.4942, 77.0860
     return 28.6270, 77.3650 # Defaults to Noida Sector 62
     ```
   - Trips between any other Indian cities, Delhi-NCR sectors, or colloquial landmarks default blindly to Noida Sector 62.

5. **Alerts Layer (`backend/app/providers/alerts/`)**:
   - `MockAlertProvider` (demo alerts obeying `demo_mode` override eligibility).
   - `WeatherAPIAlertsProvider` (commercial alerts).
   - Authoritative IMD direct feed remains unavailable due to government IP whitelisting constraints.

6. **Hazard Hotspots (`backend/app/repositories/mock_hazard_repository.py`)**:
   - 4 curated Delhi-NCR flood/waterlogging hotspots (Minto Bridge, Pul Prahladpur, Zakhira Underpass, DND Underpass) triggered when precipitation $\ge$ threshold. Injected via FastAPI `Depends(get_hazard_repository)`.

7. **Decision Engine (`backend/app/decision_engine/`)**:
   - Pure, deterministic, side-effect-free pipeline (`DecisionEngine.evaluate_route_core`).
   - Enforces 3 traffic effects: Temporal exposure shift, extended environmental duration, and congestion risk factor.
   - Evaluates multi-route alternatives with strict 6-step tie-breaking policy.
   - Computes qualitative confidence from dual-source comparison (`source_comparison.py`).

8. **LLM & Explanation Boundary (`backend/app/services/assistant_service.py`)**:
   - Natural language $\to$ `ExtractedIntent` $\to$ Decision Engine $\to$ `DecisionFacts` $\to$ Grounded Explanation $\to$ `GroundingValidator`.
   - `GroundingValidator` blocks adversarial injections, ungrounded numbers/delays, fabricated alerts, and claims contradicting selected routes.

9. **Mobile Release Configuration**:
   - Android release manifest has `INTERNET` and `ACCESS_NETWORK_STATE` permissions.
   - iOS display name set to `WeatherGPT`.
   - Backend test suite: **146/146 passing**. Flutter test suite: **63/63 passing** (0 analyze issues).

---

## 2. Identified Intelligence & Data Gaps

| # | Domain | Current State (Repository Fact) | Production Problem | Concrete Solution |
| :--- | :--- | :--- | :--- | :--- |
| **G-1** | **Geocoding** | Hardcoded `_mock_geocode` resolves only "gurgaon" / "cyber hub"; all else defaults to Noida Sec 62. | Users cannot search or route to arbitrary Delhi-NCR locations (Saket, Connaught Place, Rohini, Aerocity). | Abstract `GeocodingProvider` with Nominatim/OSM, Open-Meteo Geocoding, Google Places, and offline curated gazetteer. |
| **G-2** | **Live Traffic** | 100% synthetic clock-based delays via `MockTrafficProvider`. | Ignores actual real-world congestion, road blockages, accidents, or monsoon jam build-ups. | Activate `TRAFFIC_AWARE` and `departureTime` on `GoogleRoutesProvider`; add optional TomTom Traffic Flow adapter. |
| **G-3** | **Air Quality (AQI)** | Zero AQI or particulate matter awareness. | Delhi-NCR experiences severe winter/post-monsoon smog (AQI 300–500+), presenting extreme exposure hazards for bikers and walkers. | Open-Meteo Air Quality API (Copernicus CAMS grid) providing PM2.5 and AQI exposure scoring. |
| **G-4** | **Rain Intensity & Probability** | Coarse 1-hour precipitation sums without probability. | High false-positive risk scores when rain probability is negligible (<20%) or cloudburst intensity (15m spike) is masked by 1h averaging. | Add Open-Meteo `minutely_15=precipitation,rain,showers` and `precipitation_probability` (0–100%). |
| **G-5** | **Radar / Nowcasting** | No radar tile or nowcast data. | Commuters cannot visually verify incoming rain fronts along their commute corridor. | Open-Meteo 15-minute nowcast for risk calculations; RainViewer past radar tiles as optional visual map overlay only. |

---

## 3. Candidate Provider Evaluation

### A. Geocoding & Location Resolution

#### Candidate A1: Open-Meteo Geocoding API (`geocoding-api.open-meteo.com/v1/search`)
- **Facts (External Docs)**: Free tier allows up to 10,000 calls/day. No API key required. Uses GeoNames database.
- **Coverage**: Global; resolves Indian cities, districts, and major localities (Delhi, Noida, Gurgaon, Ghaziabad, Faridabad).
- **Limitation**: Does not resolve micro-localities (e.g. "Sector 62 Phase 2", "Cyber City Tower B").
- **Classification**: **`RECOMMENDED (Secondary Fallback)`**.

#### Candidate A2: Nominatim / OpenStreetMap Geocoding (`nominatim.openstreetmap.org/search`)
- **Facts (External Docs)**: Open-source, free. Comprehensive street-level and sector-level mapping for India. Requires custom `User-Agent`. Strictly rate-limited to 1 request/second by usage policy.
- **Coverage**: Excellent across Delhi-NCR sectors, road names, and metro stations.
- **Limitation**: 1 req/sec rate limit requires caching and polite usage.
- **Classification**: **`RECOMMENDED (Primary Open Geocoder)`**.

#### Candidate A3: Google Geocoding API (`maps.googleapis.com/maps/api/geocode/json`)
- **Facts (External Docs)**: Gold standard address resolution in India. Colloquial landmark and building-level accuracy. Requires `GOOGLE_MAPS_API_KEY`. Pay-as-you-go ($5 per 1,000 requests, covered by $200 monthly Google Cloud credit).
- **Classification**: **`RECOMMENDED (Primary Commercial Geocoder when API key configured)`**.

#### Candidate A4: Curated Delhi-NCR Gazetteer (In-Memory Offline Provider)
- **Facts (Repository)**: 50+ pre-indexed Delhi-NCR hubs (Noida Sectors, Cyber Hub, CP, AIIMS, Dhaula Kuan, Anand Vihar, IGI Airport, etc.).
- **Value**: Guaranteed zero-latency, 100% deterministic test execution, offline development support, zero external network dependency.
- **Classification**: **`RECOMMENDED (Default / Test / Offline Fallback)`**.

---

### B. Live Traffic Intelligence

#### Candidate B1: Google Routes API Live Traffic (`TRAFFIC_AWARE`)
- **Facts (Repository & External Docs)**: `GoogleRoutesProvider` is already built. By passing `routingPreference: "TRAFFIC_AWARE"` and `departureTime`, Google calculates live travel duration with real-time Indian road congestion and segment static duration.
- **Cost**: Included in standard Google Routes API call ($5–$10 / 1,000 requests).
- **Classification**: **`RECOMMENDED (Primary Live Traffic)`**.

#### Candidate B2: TomTom Traffic Flow API (`api.tomtom.com/traffic/services/4/flowSegmentData`)
- **Facts (External Docs)**: 2,500 free transactions/day on freemium tier. Requires API key. Provides real-time speeds, free-flow speeds, and delay seconds for any coordinate/corridor in India.
- **Limitation**: Standalone flow queries per segment can consume API quota quickly if not aggregated along the route.
- **Classification**: **`OPTIONAL (Secondary / Alternative Live Traffic Provider)`**.

---

### C. Air Quality (AQI) Intelligence

#### Candidate C1: Open-Meteo Air Quality API (`air-quality-api.open-meteo.com/v1/air-quality`)
- **Facts (External Docs)**: Powered by Copernicus Atmosphere Monitoring Service (CAMS). Provides hourly `pm2_5`, `pm10`, `us_aqi`, and `european_aqi` on a 0.25-degree grid globally. 10,000 calls/day free, zero API key required.
- **Product Value**: Directly addresses Delhi-NCR’s critical winter smog exposure hazard.
- **Classification**: **`RECOMMENDED`**.

#### Candidate C2: World Air Quality Index (WAQI / aqicn.org)
- **Facts (External Docs)**: Ground monitoring station readings from CPCB (Central Pollution Control Board). Free token with 1,000 req/min limit.
- **Limitation**: Irregular station availability; requires finding the nearest physical station which may be 5–15 km away from route.
- **Classification**: **`OPTIONAL (Ground-Station Validation)`**.

---

### D. Precipitation Radar & Nowcasting

#### Candidate D1: Open-Meteo 15-Minute Nowcasting & Precipitation Probability
- **Facts (External Docs)**: Provides `minutely_15=precipitation,rain,showers` for 15-minute resolution nowcasting and hourly `precipitation_probability` (0–100%). Free tier: 10,000 req/day, no API key.
- **Product Value**: Prevents false alarms when rain probability is low; samples weather precisely at the minute the traveler reaches a corridor.
- **Classification**: **`RECOMMENDED`**.

#### Candidate D2: RainViewer API
- **Facts (External Docs - Verified Jan 2026)**: **Discontinued nowcast (future) radar data as of Jan 1, 2026**. Only past 2 hours of radar images are provided at zoom level $\le 7$.
- **Product Value**: Past radar frames cannot forecast future route risk.
- **Classification**: **`NOT JUSTIFIED (for Decision Engine / Backend Risk)`**; **`OPTIONAL (Visual Map Overlay in Flutter only)`**.

#### Candidate D3: Tomorrow.io (Climacell) API
- **Facts (External Docs)**: 1-minute precipitation nowcasts. Free tier restricted to 500 calls/day and 25 calls/hour.
- **Limitation**: Severe hourly throttling makes it fragile for multi-route evaluation.
- **Classification**: **`NOT JUSTIFIED`**.

---

## 4. Recommended Provider Strategy

```
                          +------------------------------------------+
                          |             TripService                  |
                          +------------------------------------------+
                               |                |                 |
                   (Concurrent |    (Concurrent |     (Concurrent |
                      Stage 1) |       Stage 1) |        Stage 1) |
                               v                v                 v
            +--------------------+    +-------------------+    +--------------------+
            |  GeocodingProvider |    |  WeatherProvider  |    |  RoutingProvider   |
            +--------------------+    +-------------------+    +--------------------+
            | - Google (Primary) |    | - Open-Meteo      |    | - Google Routes    |
            | - Nominatim (Open) |    |   (15m Precip +   |    |   (TRAFFIC_AWARE)  |
            | - Open-Meteo       |    |    Precip Prob)   |    | - Mock Transit     |
            | - Curated Gazette  |    | - WeatherAPI      |    | - Mock Routing     |
            +--------------------+    +-------------------+    +--------------------+
                                                |
                                                +--------> +------------------------+
                                                           | AirQualityProvider     |
                                                           | - Open-Meteo CAMS      |
                                                           |   (PM2.5, PM10, AQI)   |
                                                           +------------------------+
                                                                        |
                                                                        v
                                                          +--------------------------+
                                                          |  Deterministic Engine    |
                                                          | - Temporal Alignment     |
                                                          | - Meteorological Risk    |
                                                          | - Air Quality Exposure   |
                                                          | - Curated Hazard Match   |
                                                          | - Traffic Delays (1-3)   |
                                                          | - Alternative Selection  |
                                                          +--------------------------+
```

---

## 5. Provider Abstraction Changes

### 1. New Abstraction: `GeocodingProvider`
`backend/app/providers/geocoding/base.py`:
```python
from abc import ABC, abstractmethod
from typing import Tuple, Optional
from pydantic import BaseModel

class GeocodingResult(BaseModel):
    lat: float
    lng: float
    display_name: str
    provider_name: str
    confidence: float # 0.0 to 1.0

class GeocodingProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @abstractmethod
    async def resolve(self, query: str) -> Optional[GeocodingResult]:
        """Resolves free-form address/landmark text to geographic coordinates."""
        pass
```

Implementations:
- `GoogleGeocodingProvider`: Live geocoding via Google Maps API when key present.
- `NominatimGeocodingProvider`: OpenStreetMap geocoding with custom User-Agent and caching.
- `OpenMeteoGeocodingProvider`: GeoNames-based resolution.
- `CuratedGazetteerGeocodingProvider`: Offline, deterministic in-memory dictionary for Delhi-NCR.
- `FallbackGeocodingProvider`: Chained resolution (Google $\to$ Nominatim $\to$ Open-Meteo $\to$ Gazetteer).

### 2. New Abstraction: `AirQualityProvider`
`backend/app/providers/air_quality/base.py`:
```python
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class AirQualityPoint(BaseModel):
    time: datetime
    pm2_5: float # µg/m³
    pm10: float # µg/m³
    aqi: int # 0-500 US EPA scale
    category: str # "Good" | "Moderate" | "Unhealthy" | "Severe" | "Hazardous"
    source_name: str

class AirQualityProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @abstractmethod
    async def get_air_quality(self, lat: float, lng: float, start_time: datetime, hours: int) -> list[AirQualityPoint]:
        pass
```

Implementation:
- `OpenMeteoAirQualityProvider`: Queries `https://air-quality-api.open-meteo.com/v1/air-quality` for `pm2_5,pm10,us_aqi`.
- `MockAirQualityProvider`: Deterministic baseline for testing and offline development.
- `FallbackAirQualityProvider`: Graceful failure isolation.

---

## 6. Data & Provenance Model Changes

### 1. Update `NormalizedWeatherPoint`
In `backend/app/decision_engine/normalized_models.py`:
```python
class NormalizedWeatherPoint(BaseModel):
    time: datetime
    temperature: float
    precipitation_mm: float
    humidity: int
    wind_speed: float
    wind_gusts: float
    visibility: float
    condition: str
    is_extreme_heat: bool
    is_poor_visibility: bool
    # New Phase 20 Intelligence Fields:
    precipitation_probability: Optional[float] = None # 0.0 to 100.0 %
    precipitation_intensity_category: Optional[str] = None # "none" | "light" | "moderate" | "heavy" | "violent"
```

### 2. Update `TripContext`
```python
class TripContext(BaseModel):
    origin: str
    destination: str
    departure_time: datetime
    mode: TransportMode
    route: NormalizedRoute
    weather_timeline: List[NormalizedWeatherPoint]
    hazards: List[NormalizedHazard]
    alerts: List[NormalizedAlert]
    arrival_deadline: Optional[datetime] = None
    agreement_status: str = "high"
    traffic: Optional[TrafficSnapshot] = None
    # New Phase 20 Environmental Intelligence:
    air_quality_timeline: Optional[List[AirQualityPoint]] = None
```

### 3. Update `TripResponse`
Add optional `air_quality: Optional[AirQualitySnapshot] = None` to `TripResponse` (100% backward compatible, defaults to `None`).

---

## 7. Decision Engine Integration Strategy

### 1. Precipitation Risk with Probability Weighting
In `backend/app/decision_engine/risk_model.py`:
- Currently: `precip_score = min(100, int(weather.precipitation_mm * 3.0))`
- Enhanced: When `precipitation_probability` is available:
  $$\text{effective\_precipitation} = \text{precipitation\_mm} \times \left(\frac{\text{precipitation\_probability}}{100}\right)$$
  If probability $< 25\%$, precipitation risk is scaled down to prevent unwarranted travel cancellations for mere passing drizzles.
  If probability $\ge 75\%$ and precipitation $\ge 10\text{mm}$, risk is elevated due to near-certain downpour.

### 2. Air Quality Risk Factor for Outdoor Modes
Air quality is evaluated deterministically in `calculate_segment_risk`:
- **Enclosed Modes (`car`, `metro`)**: Negligible exposure (`multiplier = 0.1`). No significant risk added.
- **Exposed Modes (`bike`, `walk`)**: Direct respiratory exposure (`multiplier = 1.0`):
  - AQI 0–100 (Good / Moderate): Score 0.
  - AQI 101–200 (Unhealthy for Sensitive): Score 25 (Low).
  - AQI 201–300 (Unhealthy / Very Unhealthy): Score 55 (Moderate). Adds `RiskFactor(name="Air Quality", score=55, level=RiskLevel.moderate, description="Unhealthy air quality (AQI 240, PM2.5: 110 µg/m³). N95 mask advised for two-wheelers.")`.
  - AQI 301–500 (Severe / Hazardous): Score 85 (High). Adds `RiskFactor` with Severe warning.
- **Mathematical Bound**: Air quality factor is capped at weight 0.25 to prevent it from overwhelming road safety and flood hazards.

---

## 8. Failure & Degradation Strategy

| Component | Primary Provider | Fallback Provider | Failure Impact on Decision | Degraded State Returned |
| :--- | :--- | :--- | :--- | :--- |
| **Geocoding** | Google Geocoding / Nominatim | Open-Meteo $\to$ Curated NCR Gazetteer | If all fail, cannot route | `TripStatus.routing_unavailable`, `risk = None` |
| **Routing** | Google Routes (Traffic-Aware) | FallbackRoutingProvider $\to$ Mock | Route alternatives unavailable | `TripStatus.routing_unavailable`, `risk = None` |
| **Traffic** | Google Embedded Traffic | TomTom Flow $\to$ UnavailableTrafficProvider | Trip evaluated without traffic delays | `TrafficStatus.unavailable`, static duration used |
| **Weather** | Open-Meteo (15m + Prob) | WeatherAPI (Secondary) | If both fail, cannot score risk | `TripStatus.weather_unavailable`, `risk = None` |
| **Air Quality** | Open-Meteo Air Quality | Mock AQI / None | Evaluated without AQI factor | Analysis succeeds; AQI omitted |
| **LLM Explanation** | Gemini LLM | GroundingValidator Deterministic Fallback | LLM failure never blocks decision | Authoritative `DecisionFacts` fallback delivered |

---

## 9. Configuration & Environment Changes

In `backend/app/core/config.py`:
```python
# Geocoding Provider
geocoding_provider: str = "auto" # "auto" | "google" | "nominatim" | "open-meteo" | "gazetteer"

# Air Quality Provider
air_quality_provider: str = "open-meteo" # "open-meteo" | "mock" | "disabled"
air_quality_enabled: bool = True

# Traffic Intelligence Settings
google_traffic_aware: bool = True
tomtom_api_key: Optional[str] = None
```

---

## 10. Backend Changes

1. Create `backend/app/providers/geocoding/`:
   - `base.py` (abstract interface)
   - `google.py` (Google Geocoding adapter)
   - `nominatim.py` (OSM Nominatim adapter with rate-limiting guard)
   - `open_meteo.py` (Open-Meteo geocoding adapter)
   - `gazetteer.py` (Curated offline Delhi-NCR index)
   - `fallback.py` (Chain of responsibility)
2. Create `backend/app/providers/air_quality/`:
   - `base.py` (abstract interface)
   - `open_meteo.py` (CAMS API adapter)
   - `mock.py` (Deterministic test mock)
3. Update `backend/app/providers/routing/google_routes.py`:
   - Add `routingPreference: "TRAFFIC_AWARE"` and `departureTime` to `_build_request`.
4. Update `backend/app/providers/weather/open_meteo.py`:
   - Add `precipitation_probability` to hourly query and parse into `NormalizedWeatherPoint`.
5. Update `backend/app/services/trip_service.py`:
   - Inject `GeocodingProvider` via dependencies; replace `_mock_geocode` with `await self.geocoding_provider.resolve(location)`.
   - Concurrently fetch weather, air quality, alerts, and routing via `asyncio.gather`.
6. Update `backend/app/decision_engine/risk_model.py`:
   - Incorporate probability scaling into `_calculate_precipitation_score`.
   - Add bounded `Air Quality` risk factor for exposed travel modes.

---

## 11. Flutter Changes (Minimal & Non-Breaking)

1. **Air Quality Indicator**:
   - In `TripAnalysisScreen`, if `tripResponse.airQuality` is present, display an environmental badge (`AQI 220 · Unhealthy (PM2.5)`) next to the Weather Card.
   - If `airQuality` is `null`, the badge is omitted cleanly (zero visual breakage).
2. **Precipitation Probability Display**:
   - When viewing Weather timeline cards, show rain probability percentage (e.g. `"70% chance of rain"`) alongside rainfall accumulation.
3. **Map Radar Layer (Optional UI Toggle)**:
   - Toggle button on Flutter Map to overlay RainViewer past radar tile layer (`https://tilecache.rainviewer.com/v2/radar/{timestamp}/512/{z}/{x}/{y}/2/1_1.png`) for visual confirmation of current storm clouds.
4. **No Direct Firestore**:
   - Zero change to persistence architecture. Flutter continues to communicate exclusively through FastAPI.

---

## 12. API Contract Changes

All changes are strictly additive and backward compatible:
- `TripResponse.airQuality`: Optional object containing `aqi`, `pm25`, `category`, `sourceName`.
- `WeatherPoint.precipitationProbability`: Optional float (`0.0` to `100.0`).
- `WeatherPoint.precipitationIntensity`: Optional string enum (`"none"`, `"light"`, `"moderate"`, `"heavy"`).

---

## 13. Security & Privacy Considerations

1. **User Location Privacy**:
   - Geocoding queries sent to external providers (Google / Nominatim) contain address strings without user identification or UID tokens.
2. **API Key Security**:
   - All third-party credentials (`GOOGLE_MAPS_API_KEY`, `WEATHERAPI_API_KEY`, `TOMTOM_API_KEY`, `GEMINI_API_KEY`) remain exclusively on the FastAPI backend.
   - The logging redaction layer (`redact_sensitive_processor`) automatically filters all keys from logs.
3. **Rate Limit Protection**:
   - Any new public endpoints are automatically wrapped by `RequestCorrelationAndRateLimitMiddleware`.

---

## 14. Performance & Concurrency Considerations

- **Parallel Data Ingestion**:
  `TripService` runs geocoding resolution first (to obtain coordinates), then concurrently gathers:
  ```python
  weather_res, aqi_res, alerts_res, routing_res = await asyncio.gather(
      fetch_weather(),
      fetch_air_quality(),
      fetch_alerts(),
      fetch_routing()
  )
  ```
  Total upstream latency is bounded by the slowest single provider (typically Google Routes ~400ms), rather than the sum of sequential calls (~1,200ms).
- **Geocoding In-Memory Cache**:
  Coordinates for common queries (e.g., "Noida Sector 62", "Cyber Hub") are cached with a bounded LRU cache (TTL 24 hours), reducing external HTTP overhead to 0ms for repeated commutes.

---

## 15. Testing Strategy

1. **Geocoding Provider Tests**:
   - Coordinate string parsing (`"28.627, 77.365"`).
   - Address resolution with fallback chain.
   - Offline Curated Gazetteer determinism.
   - Graceful failure when address cannot be found.
2. **Live Traffic Verification**:
   - Verify `GoogleRoutesProvider` generates traffic-aware payload when departure time is supplied.
   - Verify delay seconds, static duration, and traffic-aware duration satisfy `trafficAwareDuration == staticDuration + delay`.
3. **Air Quality Evaluation Tests**:
   - High AQI triggers RiskFactor for `bike` and `walk`.
   - Enclosed modes (`car`, `metro`) down-weight AQI risk.
   - Provider outage does not block trip analysis.
4. **Precipitation Probability Tests**:
   - High rain accumulation with low probability (<20%) scales down risk score appropriately.
   - High probability (>80%) confirms high risk score.
5. **Determinism & Invariant Regressions**:
   - 10x repeated execution determinism test across all expanded providers.
   - Full verification that all 146 existing backend tests and 63 Flutter tests continue to pass.

---

## 16. Candidate Decision Table

| Candidate | Capability | Current Gap | India Coverage | Cost / Limitations | Complexity | Recommendation |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Nominatim + Open-Meteo + NCR Gazetteer** | Geocoding / Location Resolution | Solves hardcoded `_mock_geocode` | Full India (Streets + Cities + Curated Hubs) | Free (Open-Meteo: 10k/day; Nominatim: 1 req/s; Gazetteer: 0 cost) | Low | **`RECOMMENDED`** |
| **Google Geocoding API** | High-precision commercial geocoding | Micro-landmarks / colloquial addresses | Best-in-class India | Pay-as-you-go ($5/1k req; $200 free credit) | Low | **`RECOMMENDED (Primary when key set)`** |
| **Open-Meteo 15m & Precip Probability** | Rain Intensity & Probability | Hourly average misses cloudbursts & false alarms | Full India (Global ECMWF / GFS) | Free (10k req/day, no API key) | Low | **`RECOMMENDED`** |
| **Google Routes Live Traffic** | Real-time traffic delays & congestion | Replaces synthetic clock-based mock traffic | Comprehensive Delhi-NCR & India highways | Included in Google Routes API call | Very Low | **`RECOMMENDED`** |
| **Open-Meteo Air Quality (CAMS)** | Hourly PM2.5, PM10, AQI | Zero air pollution awareness in Delhi-NCR | Full India (0.25° CAMS grid) | Free (10k req/day, no API key) | Low | **`RECOMMENDED`** |
| **TomTom Traffic Flow API** | Secondary live traffic flow | Backup for non-Google routing | Good major India cities | 2,500 req/day freemium, requires key | Medium | **`OPTIONAL`** |
| **Open-Meteo Ensemble API** | Multi-model probabilistic uncertainty | Multi-model consensus vs dual-source diff | Full India | Free (10k req/day, no API key) | Medium | **`OPTIONAL`** |
| **RainViewer Radar Tiles** | Past 2h radar tile overlay | None (Nowcasts discontinued Jan 2026) | Indian radar coverage (IMD) | Free for personal use; no future nowcast | Low | **`OPTIONAL (Map Tile Overlay only)`** |
| **Tomorrow.io (Climacell)** | 1-minute nowcasts | Overlaps with Open-Meteo | Good | Severely throttled (25 req/hour free) | Medium | **`NOT JUSTIFIED`** |
| **WAQI Ground Stations** | Ground CPCB station AQI | Ground-level sensor verification | Spotty station uptime | Free token, station-based | Medium | **`OPTIONAL`** |

---

## 17. Explicit Invariants Checklist (Zero Regressions)

Before any code modification in Phase 20, these 18 invariants remain strictly preserved:
1. Decision Engine is the sole authority for risk.
2. Decision Engine is the sole authority for route selection.
3. LLM cannot modify authoritative decisions.
4. GroundingValidator protects explanation integrity.
5. Firestore is persistence only.
6. Flutter has no direct Firestore access.
7. Saved routes are bookmarks, not Decision Engine inputs.
8. Historical snapshots are never treated as live data.
9. Guest travelers can still analyze trips.
10. Production cannot silently use mock weather.
11. Production cannot accept mock authentication tokens.
12. User identity comes only from verified authentication claims.
13. Cross-user data isolation is enforced.
14. Persistence failure cannot break trip analysis.
15. LLM failure cannot break trip analysis.
16. Provider degradation is represented truthfully.
17. No secrets are committed or logged.
18. API errors do not leak internal implementation details.

---

## 18. Exact Files to Modify & Create in Implementation Phase

### New Files to Create:
- `backend/app/providers/geocoding/base.py`
- `backend/app/providers/geocoding/gazetteer.py`
- `backend/app/providers/geocoding/nominatim.py`
- `backend/app/providers/geocoding/open_meteo.py`
- `backend/app/providers/geocoding/google.py`
- `backend/app/providers/geocoding/fallback.py`
- `backend/app/providers/air_quality/base.py`
- `backend/app/providers/air_quality/open_meteo.py`
- `backend/app/providers/air_quality/mock.py`
- `backend/tests/unit/test_geocoding_providers.py`
- `backend/tests/unit/test_air_quality_intelligence.py`
- `backend/tests/unit/test_precipitation_probability.py`

### Existing Files to Modify:
- `backend/app/core/config.py` (Add geocoding and AQI config flags)
- `backend/app/decision_engine/normalized_models.py` (Add `precipitation_probability` and AQI fields)
- `backend/app/decision_engine/risk_model.py` (Incorporate precipitation probability and outdoor AQI risk factor)
- `backend/app/providers/weather/open_meteo.py` (Query `precipitation_probability`)
- `backend/app/providers/routing/google_routes.py` (Pass `routingPreference: "TRAFFIC_AWARE"` and `departureTime`)
- `backend/app/api/dependencies.py` (Register `GeocodingProvider` and `AirQualityProvider`)
- `backend/app/services/trip_service.py` (Integrate geocoding resolution and concurrent AQI gathering)
- `backend/app/models/trip.py` (Add optional `air_quality` to `TripResponse`)

---

## 19. Untouched Functionality

The following existing components must remain **completely untouched**:
- `backend/app/decision_engine/engine.py` (core tie-breaking, scenario evaluation, bottleneck weighting formulas)
- `backend/app/decision_engine/route_evaluator.py` (6-step route alternative selection policy)
- `backend/app/api/auth.py` (production token verification, guest pass-through)
- `backend/app/core/rate_limiter.py` (sliding window abuse protection)
- `backend/app/core/logging.py` (secret redaction pipeline)
- All Flutter Riverpod state management and route navigation logic
- Firestore persistence repository interfaces and schema mappings
