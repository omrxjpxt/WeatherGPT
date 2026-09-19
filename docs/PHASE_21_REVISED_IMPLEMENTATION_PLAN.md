# Phase 21: Revised Provider & Capability Expansion Implementation Plan

> **Product Context:** WeatherGPT is a production-grade personal product delivering deterministic, hyper-local, weather-aware trip planning and risk intelligence for commuters in Delhi-NCR. It is NOT an SIH/hackathon demo. Every architectural addition must directly enhance decision quality, safety accuracy, reliability, and real-world usefulness without adding gratuitous API surface area or breaking established invariants.

---

## 1. Executive Summary

Phase 21 expands WeatherGPT's data intelligence layer with real-world, verified sources tailored to the daily safety realities of Delhi-NCR commuters:
1. **Official Emergency & Disaster Alerts**: Direct integration with the National Disaster Management Authority (**NDMA SACHET**) Common Alerting Protocol (CAP 1.2) feed, replacing simulated mock alerts with authentic Government of India warnings from IMD and CWC.
2. **Authoritative Monsoon Waterlogging & Underpass Hazards**: Transitioning from a 4-point demo hazard list to an authoritative curated repository based on official **Delhi PWD & Traffic Police Monsoon Action Plans**, with calibrated rainfall trigger thresholds and transport-mode impassability rules.
3. **Delhi Metro Rail (DMRC) Transit Intelligence**: Ingestion of verified Delhi Metro network topology, transfer stations, and timetables based on the **Delhi Transport Stack / Open Transit Data**, replacing static mock routes with realistic metro options.
4. **NCR Postal PIN Code Geocoding Fast-Path**: Instant, offline resolution of 6-digit Indian PIN codes (`110xxx`, `201xxx`, `122xxx`, `121xxx`) to verified postal centroids with explicit provenance.

**Strict Governance Principle:** No source code is modified during this planning phase. Every integration has been fact-checked against live endpoints and authoritative government sources.

---

## 2. Existing Architecture Findings

A code-level audit of the Phase 20 baseline revealed:

1. **Alert Architecture (`app/providers/alerts/`)**:
   - `AlertProvider` interface defines `async def get_active_alerts(lat, lng) -> List[NormalizedAlert]`.
   - `MockAlertProvider` serves hardcoded demo warnings for Noida/Gurgaon.
   - `WeatherAPIAlertProvider` is implemented as an optional secondary provider.
   - `_evaluate_alert_policy` in `TripService` strictly governs override eligibility (`authoritative` = always eligible; `secondary` = risk score only; `demo` = eligible only in `settings.demo_mode`).
2. **Hazard Architecture (`app/repositories/mock_hazard_repository.py`)**:
   - Implements `HazardRepository` interface with `get_hazards_in_region(min_lat, min_lng, max_lat, max_lng)`.
   - Currently contains only 3 hardcoded entries (Minto Bridge Delhi, Hindmata Mumbai, and a demo landslide).
   - Injected via FastAPI dependencies `get_hazard_repository()` with singleton lifecycle.
3. **Transit & Routing Architecture (`app/providers/routing/`)**:
   - `GoogleRoutesProvider` handles `TransportMode.car`, `bike`, `walk` with `TRAFFIC_AWARE` and departure time.
   - For `TransportMode.metro`, `TripService` explicitly routes through `self._metro_provider = MockRoutingProvider()`, which returns synthetic routes (`mock_route_1`, `mock_route_2`, `mock_route_3`).
4. **Geocoding Architecture (`app/providers/geocoding/`)**:
   - Multi-tier fallback chain: Google $\rightarrow$ Nominatim (1.05s lock) $\rightarrow$ Open-Meteo $\rightarrow$ Curated NCR Gazetteer.
   - Rejects low confidence ($< 0.50$). Parses GPS coordinate pairs directly. Lacks a dedicated 6-digit Indian PIN code resolver.
5. **Decision Engine & Concurrency (`app/services/trip_service.py`)**:
   - Concurrently gathers geocoding, primary weather, secondary weather, alerts, route alternatives, and air quality via `asyncio.gather`.
   - Evaluates corridor hazards against route segments using Haversine bounding boxes.
   - 10x repeated evaluations are verified to be 100% bit-identical.

---

## 3. Provider Verification Results

Every candidate provider was subjected to empirical testing and source verification:

### A. NDMA SACHET Common Alerting Protocol (CAP 1.2)
- **Live Endpoint Verified**: `https://sachet.ndma.gov.in/cap_public_website/rss/rss_delhi.xml` (State feed) and `https://sachet.ndma.gov.in/cap_public_website/rss/rss_india.xml` (National feed).
- **Security & Access Reality**:
  - Direct stateless curl without cookies is rejected with `HTTP 403 Forbidden` by the government security gateway (C-DAC / NIC WAF).
  - When requests maintain a session cookie jar (standard behavior in `httpx.AsyncClient`), the endpoint returns `HTTP 200 OK` with authentic XML feeds.
- **Data Payload Verified**:
  - Feeds contain real-time IMD New Delhi bulletins (e.g. thunderstorm, lightning, wind gust warnings broken down by Delhi districts).
  - XML structure follows OASIS CAP 1.2 (`<cap:alert>`, `<cap:identifier>`, `<cap:event>`, `<cap:urgency>`, `<cap:severity>`, `<cap:areaDesc>`, `<cap:effective>`, `<cap:expires>`).
  - Alert detail link: `https://sachet.ndma.gov.in/cap_public_website/FetchXMLFile?identifier={id}`.
- **Polygon Precision**: National/state level feeds provide district lists (`<cap:areaDesc>`) and Local Government Directory (LGD) district codes, with detailed polygon URLs (`FetchPolygonXMLFile?identifier=...`) for severe warnings.
- **ETag Support**: Confirmed mandatory by NDMA integration guidelines using `If-None-Match`.

### B. Delhi Waterlogging & Underpass Hotspots
- **Authoritative Source**: Delhi Government Public Works Department (PWD) Annual Monsoon Preparedness Reports and Delhi Traffic Police Monsoon Advisories.
- **The "169 Locations" Fact-Check**:
  - The figure of 169 is an authentic government-designated count of priority flood-prone spots for the 2024–2026 monsoon seasons, supplemented by 445 traffic police historical spots.
  - The 9 critical chronic underpasses are:
    * *PWD Managed*: Minto Bridge, Zakhira, Dwarka, Moolchand, Pul Prahlad Pur.
    * *Other Agencies Managed*: Ram Bagh, Okhla, Sarita Vihar, Pandav Nagar.
  - Major arterial corridors include: ITO junction, Pragati Maidan / Bhairon Marg tunnel, Mathura Road, Punjabi Bagh, Mehrauli-Badarpur Road, MG Road, Ring Road.
- **Rainfall & Water Depth Thresholds**:
  * *Water-depth thresholds* ($15\text{ cm}$ for underpass closure/bike danger, $30\text{ cm}$ for car stalling) are grounded in PWD Standard Operating Procedures (traffic diversion ordered at 6–8 inches) and automotive intake physics.
  * *Rainfall rate triggers* ($15\text{ mm/hr}$ for underpasses, $35\text{ mm/hr}$ for surface roads) are hydrologic modeling assumptions representing drainage pump capacity exceedance.
  * *Provenance Invariant*: We must explicitly document rainfall triggers as engineering models, not pretend the government decreed 15 mm/hr.

### C. Delhi Metro (DMRC) GTFS Data
- **Authoritative Source**: Delhi Transport Stack (`delhi.transportstack.in`) and Open Transit Data Delhi (`otd.delhi.gov.in`), developed by Dept. of Transport, Govt of NCT of Delhi + IIIT-Delhi.
- **Network Reality**:
  - DMRC operates 10 main lines + Rapid Metro Gurugram, covering ~288 operational stations across Delhi, Noida, Gurgaon, Ghaziabad, and Faridabad.
  - Noida Metro Rail Corporation (NMRC) operates the Aqua Line independently, connected via an external footbridge between Sector 51 (Aqua) and Sector 52 (Blue).
- **Data Strategy**: Rather than ingesting an unwieldy 500MB bus+metro GTFS bundle at runtime, the verified DMRC rail topology (stations, line colors, interchange points, station runtimes) will be compiled into an offline, high-performance in-memory transit graph.

### D. Postal PIN Code Geocoding
- **Authoritative Source**: Survey of India / India Post All-India Pincode Directory (published via `data.gov.in`) and `api.postalpincode.in`.
- **NCR Territory Coverage**:
  - Delhi NCT: `110001`–`110096` (~96 delivery zones).
  - Noida & Greater Noida: `201301`–`201318` (~18 zones).
  - Gurgaon: `122001`–`122052` (~25 zones).
  - Ghaziabad: `201001`–`201017` (~17 zones).
  - Faridabad: `121001`–`121010` (~10 zones).
  - Total core commuter set: ~166 PIN codes.
- **Data Strategy**: Bundle the verified NCR centroid coordinates with `OFFLINE_CURATED` provenance; fallback to `api.postalpincode.in` or Google for out-of-NCR PINs.

---

## 4. Public-APIs Research Results

Cross-referencing the `public-apis/public-apis` repository against WeatherGPT's requirements yielded the following assessment:

| API from Public-APIs | Domain | Evaluated Value for WeatherGPT | Decision & Rationale |
| :--- | :--- | :--- | :--- |
| **PostalPinCode** (`postalpincode.in`) | Geocoding | High (Indian PIN code lookup) | **Accepted as Fallback**. Keyless open REST API for out-of-NCR PIN resolution. |
| **Indian Pincode** (`indianpincode.com`)| Geocoding | Moderate (Redundant with postalpincode.in)| **Rejected**. Redundant. |
| **Open Government, India** (`data.gov.in`)| Open Data | Benchmark source for PIN code dataset | **Accepted for Dataset Compilation**. Used offline. |
| **OpenAQ v3** | Air Quality | Moderate (Ground station readings) | **Optional Adapter Only**. Lacks future forecast capability; CAMS remains primary. |
| **TomTom Incident Details** | Traffic | Moderate (Discrete incident markers) | **Optional Adapter Only**. Google Routes `TRAFFIC_AWARE` already computes delay. |
| **Open-Meteo GloFAS** | Floods | Very Low (Continental river discharge) | **Rejected**. Macro-scale river discharge cannot model urban street flooding. |
| **RainViewer / Rainbow Weather** | Radar | Low (Raster tile images) | **Rejected for Decision Engine**. Image tiles cannot feed deterministic risk logic. |
| **GraphHopper / Mapbox** | Routing | Redundant (Google Routes is superior in India)| **Rejected**. Google Maps is significantly more accurate for Indian road networks. |
| **Open Charge Map** | Vehicle | Out of Scope (EV chargers) | **Rejected**. Not a weather or travel risk capability. |

---

## 5. Confirmed Providers for Phase 21

| Provider / Data Source | Target Capability | Tier | Provenance Class | Operational Mode |
| :--- | :--- | :--- | :--- | :--- |
| **NDMA SACHET (CAP 1.2)** | Official Weather & Disaster Alerts | Primary | `AUTHORITATIVE` | Live HTTP client with cookie jar & ETag |
| **Delhi PWD Waterlogging Index** | Monsoon Inundation & Underpass Hazards | Primary | `GOVERNMENT_OPEN_DATA` | Offline In-Memory Curated Repository |
| **DMRC GTFS Transit Engine** | Delhi Metro Network Routing | Primary | `GOVERNMENT_OPEN_DATA` | Offline In-Memory Station Graph |
| **NCR Postal PIN Resolver** | 6-Digit PIN Code Geocoding | Fast-Path | `OFFLINE_CURATED` | In-Memory Table + `postalpincode.in` Fallback |

---

## 6. Rejected Providers and Reasons

1. **Direct IMD Website Scraping**: Rejected due to frequent CAPTCHA challenges, fragile DOM parsing, and risk of IP blocking. NDMA SACHET is the official, authorized dissemination channel for IMD alerts.
2. **Open-Meteo GloFAS River API**: Rejected because 5 km grid river discharge ($m^3/s$) does not correlate with urban street waterlogging caused by intense local convective rain overwhelming stormwater drains.
3. **RainViewer Radar Image Processing**: Rejected because extracting deterministic risk scores from raster reflectivity maps introduces non-deterministic computer-vision approximations. Open-Meteo 15-minute precipitation and probability already provide exact numeric inputs.
4. **Waze/Crowd-Sourced Hazard Reporting**: Rejected because unvetted user submissions can be manipulated or report outdated hazards, violating Decision Engine determinism.

---

## 7. Data Provenance Strategy

All data ingested into the system must carry explicit, typed provenance metadata:

```
+--------------------------+-----------------------+----------------------------------------------------+
| Entity                   | Provenance Tag        | Provenance Explanation                             |
+--------------------------+-----------------------+----------------------------------------------------+
| NDMA SACHET Alerts       | authoritative         | Official Govt of India CAP 1.2 feed (IMD/CWC/NDMA)  |
| WeatherAPI Alerts        | secondary             | Commercial aggregator alert feed (non-authoritative)|
| Mock Alert Fallback      | demo/mock             | Offline synthetic alerts (active in demo_mode only)|
| Delhi PWD Waterlogging   | government_open_data  | Official PWD/Traffic Police Monsoon Action hotspots|
| DMRC Transit Routes      | government_open_data  | Official Delhi Transport Stack GTFS topology       |
| NCR Postal Centroids     | offline_curated       | India Post / Survey of India postal directory      |
| Dynamic PIN Lookup       | live_api              | api.postalpincode.in online fallback               |
+--------------------------+-----------------------+----------------------------------------------------+
```

---

## 8. Domain Model Changes

### A. Alert Domain Models (`app/models/alert.py` & `app/decision_engine/normalized_models.py`)
```python
class AlertUrgency(str, Enum):
    immediate = "immediate"
    expected = "expected"
    future = "future"
    past = "past"
    unknown = "unknown"

class AlertCertainty(str, Enum):
    observed = "observed"
    likely = "likely"
    possible = "possible"
    unlikely = "unlikely"
    unknown = "unknown"

class NormalizedAlert(BaseModel):
    id: str
    source_name: str
    source_class: AlertSourceClass
    severity: AlertSeverity
    urgency: AlertUrgency = AlertUrgency.unknown
    certainty: AlertCertainty = AlertCertainty.unknown
    event: Optional[str] = None
    headline: Optional[str] = None
    description: Optional[str] = None
    affected_areas_polygon: List[List[float]] = Field(default_factory=list)
    affected_districts: List[str] = Field(default_factory=list)
    issued_at: datetime
    expires_at: Optional[datetime] = None
    action: Optional[str] = None
    source_url: Optional[str] = None
    is_override_eligible: bool = False
```

### B. Hazard Domain Models (`app/decision_engine/normalized_models.py`)
```python
class NormalizedHazard(BaseModel):
    id: str
    type: HazardType
    lat: float
    lng: float
    radius_meters: float
    base_severity: int # 0-100 historical susceptibility
    source_name: str
    source_class: HazardSourceClass
    source_url: Optional[str] = None
    source_reference: Optional[str] = None
    reported_timestamp: Optional[datetime] = None
    
    # Calibrated waterlogging triggers
    is_underpass: bool = False
    rainfall_trigger_mm_per_hr: float = 35.0 # 15.0 for underpasses, 35.0 for surface
    water_depth_threshold_cm: float = 15.0
    impassable_modes: List[TransportMode] = Field(default_factory=lambda: [TransportMode.walk, TransportMode.bike])
```

### C. Transit Domain Models (`app/models/transit.py`)
```python
class MetroStation(BaseModel):
    station_id: str
    name: str
    lat: float
    lng: float
    line_ids: List[str]
    is_interchange: bool

class MetroLeg(BaseModel):
    line_name: str
    line_color: str
    from_station: str
    to_station: str
    stations_count: int
    duration_minutes: int

class MetroRoute(BaseModel):
    origin_station: str
    destination_station: str
    legs: List[MetroLeg]
    interchange_stations: List[str]
    total_transit_minutes: int
    walking_to_origin_minutes: int
    walking_from_dest_minutes: int
    total_duration_minutes: int
    summary: str
```

---

## 9. Backend Changes

1. **`app/providers/alerts/sachet.py` [NEW]**:
   - `NdmaSachetAlertProvider` using `httpx.AsyncClient` with stateful cookie jar.
   - Fetches `https://sachet.ndma.gov.in/cap_public_website/rss/rss_delhi.xml`.
   - Parses CAP 1.2 XML using `defusedxml.ElementTree`.
   - Implements ETag caching with `If-None-Match`.
   - Maps alerts to `NormalizedAlert` with `source_class = AlertSourceClass.authoritative`.
2. **`app/repositories/delhi_waterlogging_repository.py` [NEW]**:
   - Replaces `MockHazardRepository` in production.
   - Loads verified Delhi PWD & Traffic Police hotspots from bundled JSON asset (`app/data/delhi_waterlogging_hotspots.json`).
   - Spatial indexing using bounding box filter for fast corridor hazard matching.
3. **`app/providers/transit/dmrc_metro.py` [NEW]**:
   - Implements `MetroTransitProvider` backed by bundled DMRC station topology (`app/data/dmrc_network.json`).
   - Breadth-first search (BFS) shortest path routing through DMRC network for `TransportMode.metro`.
   - Connects user origin/destination to nearest metro stations within walkable or auto-rickshaw distance.
4. **`app/providers/geocoding/pincode.py` [NEW]**:
   - `NcrPincodeGeocodingProvider` matching `^\d{6}$`.
   - In-memory dictionary of ~166 core Delhi-NCR PIN codes (`110xxx`, `201xxx`, `122xxx`, `121xxx`).
   - Fallback to `api.postalpincode.in` for out-of-NCR Indian PIN codes.
5. **`app/services/trip_service.py` [MODIFY]**:
   - Replaces `self._metro_provider = MockRoutingProvider()` with injected `metro_transit_provider`.
   - Parallelizes SACHET alert fetching in `asyncio.gather`.
   - Injects `delhi_waterlogging_repository` for corridor hazard evaluation.

---

## 10. Flutter & API Contract Changes

1. **Zero Breaking Changes**:
   - `TripResponse` retains existing top-level schema.
   - `OfficialAlert` receives optional fields: `urgency`, `certainty`, `event`.
   - `Hazard` receives optional fields: `is_underpass`, `rainfall_trigger_mm_per_hr`.
   - `EvaluatedRoute` for `TransportMode.metro` returns authentic station names and lines in `summary` and `segments`.
2. **Flutter UI Rendering**:
   - Alerts screen renders authentic `issued_by` ("IMD New Delhi via NDMA SACHET").
   - Hazard screen displays "Underpass Flood Risk" badge and exact PWD hotspot names.
   - Route comparison for Metro displays real interchange stations (e.g. "Via Blue Line & Yellow Line (Interchange at Rajiv Chowk)").

---

## 11. Dependency Changes

- Add `defusedxml>=0.7.1` to `backend/pyproject.toml` for safe, attack-resistant CAP 1.2 XML parsing.
- `httpx` is already present in `backend` dependencies.

---

## 12. Security Considerations

1. **XML External Entity (XXE) Injection Prevention**:
   - Standard Python `xml.etree.ElementTree` is vulnerable to entity expansion and billion-laughs attacks.
   - `defusedxml.ElementTree` is strictly required for parsing SACHET RSS and CAP documents.
2. **Denial-of-Service Defense**:
   - Max XML payload size capped at 1 MB.
   - Timeout on SACHET requests capped at 3.0 seconds.
3. **No Secret Leakage**:
   - SACHET is an open government feed requiring no API key.
   - If optional TomTom or OpenAQ providers are initialized, credentials remain shielded by structlog redaction processors.

---

## 13. Privacy Considerations

1. **Zero Traveler Location Leakage**:
   - SACHET is queried via state-level RSS feeds (`rss_delhi.xml`), not by sending user GPS coordinates to NDMA.
   - Delhi waterlogging hazards and DMRC transit paths are computed entirely in-process on the backend.
   - User origin and destination coordinates are never transmitted to any third-party government endpoint.

---

## 14. Performance Considerations

```
+-------------------------------------------------------------------------------+
|                        TripService Concurrency Flow                           |
+-------------------------------------------------------------------------------+
|  1. Geocoding (Origin & Destination)                                          |
|     - Fast-path PIN resolver: <1ms                                            |
|     - Google / Nominatim fallback: ~150-250ms                                 |
+-------------------------------------------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------------+
|  2. Upstream Concurrency (asyncio.gather)                                     |
|     |-- Primary Weather (Open-Meteo): ~120-180ms                              |
|     |-- Secondary Weather (WeatherAPI): ~150-200ms                            |
|     |-- Alerts (NDMA SACHET): ~150-250ms (or 0ms on 304 ETag)                |
|     |-- Air Quality (Copernicus CAMS): ~120-180ms                             |
|     |-- Routing (Google Routes or DMRC Transit Engine):                       |
|         * Car/Bike (Google Routes TRAFFIC_AWARE): ~250-350ms                  |
|         * Metro (In-Memory DMRC Graph): <5ms                                  |
+-------------------------------------------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------------+
|  3. In-Memory Corridor Hazards & Decision Engine                              |
|     - Bounding Box Spatial Filter (169 PWD Hotspots): <2ms                    |
|     - Decision Engine Evaluation & Route Selection: <2ms                      |
+-------------------------------------------------------------------------------+
Total End-to-End Latency: ~350-450ms (Zero critical-path regression)
```

---

## 15. Failure & Degradation Matrix

| Component / State | System Behavior | Decision Engine Impact | User-Visible Status |
| :--- | :--- | :--- | :--- |
| **SACHET Available** | Parses live CAP alerts; checks route polygon intersection | Evaluates `alert_override_applied = True` if emergency | Full alert details with authoritative provenance |
| **SACHET 304 Not Modified**| Reuses cached alerts from memory | Identical to latest observation | Live alerts with cached timestamp |
| **SACHET Timeout / 5xx** | Logs warning; falls back to WeatherAPI or empty list | Alert override not applied; risk calculated from weather | Clean status banner; `Alerts [unavailable]` in sources |
| **SACHET Malformed XML** | Caught by `defusedxml`; rejected; logged | Alert override not applied; trip analysis continues | Clean status banner; `Alerts [unavailable]` in sources |
| **PWD Waterlogging Available**| In-memory lookup; activates if rain exceeds trigger | Increases hazard risk contribution up to bounded cap | Hotspot warning marker and hazard description |
| **PWD Data Missing/Corrupt**| Caught at startup; falls back to minimal hardcoded list | Evaluates available hazards | Trip continues normally; logged warning |
| **DMRC Transit Available** | Computes authentic metro route via station graph | Evaluates weather along walk legs; applies 0.10x AQI | Real station names, line colors, transfer guidance |
| **DMRC Station Out of Range**| Stations > 5km from origin/dest | Recommends road transport mode | Advises road travel; explains metro infeasibility |
| **PIN Found in NCR Table** | Resolves immediately (0ms) | Feeds centroid to routing and weather | Exact postal locality name in trip request |
| **PIN Outside NCR** | Queries `api.postalpincode.in` or Google | Feeds resolved coordinates | Resolved locality name |
| **Unknown / Invalid PIN** | Raises `GeocodingResolutionError` | Halts before Decision Engine | Clean HTTP 400: "Unknown postal code" |

---

## 16. Testing Strategy

### Unit Tests
1. **`test_sachet_cap_provider.py`**:
   - XML parsing of authentic SACHET CAP 1.2 documents.
   - ETag caching behavior (`304 Not Modified`).
   - XXE injection prevention tests using malicious XML fixtures.
   - Polygon extraction and point-in-polygon matching.
   - Timeout and HTTP 403 cookie management handling.
2. **`test_delhi_waterlogging_repository.py`**:
   - Verification of 169 PWD hotspot coordinates and bounding box indexing.
   - Underpass trigger threshold testing ($15\text{ mm/hr}$ rain activates Minto Bridge).
   - Mode impassability rules (bike high-risk at 15cm, car stalled at 30cm, metro unaffected).
   - Dormant hazard behavior (zero rainfall = 0 added risk).
3. **`test_dmrc_transit_provider.py`**:
   - DMRC shortest path graph routing (Noida Sector 62 to Cyber City via Blue Line + Yellow Line with interchange at Rajiv Chowk).
   - Realistic duration calculation vs. synthetic baseline.
   - Line name and transfer station validation.
4. **`test_pincode_geocoding.py`**:
   - Exact resolution of Delhi (`110001`), Noida (`201301`), Gurgaon (`122002`).
   - Out-of-NCR PIN fallback to `postalpincode.in`.
   - Invalid 6-digit PIN error handling.

### Regression & Determinism Tests
5. **`test_phase21_integration_and_determinism.py`**:
   - Concurrency testing under `asyncio.gather`.
   - **10x Repeated Evaluation Determinism**: 10 sequential trip evaluations with SACHET alerts, PWD hazards, and DMRC transit active must produce 100% bit-identical risk scores, tiers, and route recommendations.
   - Full suite execution: `pytest backend/tests`, `flutter analyze`, `flutter test`.

---

## 17. Migration & Rollout Strategy

1. **Phase 21A (Data Assets & Providers)**:
   - Commit verified JSON datasets (`delhi_waterlogging_hotspots.json`, `dmrc_network.json`, `ncr_pincodes.json`).
   - Implement standalone provider classes (`NdmaSachetAlertProvider`, `DelhiWaterloggingHazardRepository`, `DmrcMetroProvider`, `NcrPincodeGeocodingProvider`).
   - Validate isolated unit tests.
2. **Phase 21B (Service Integration)**:
   - Wire providers into `TripService` and FastAPI dependencies.
   - Update `GroundingValidator` to recognize official alert IDs and PWD hotspot names.
3. **Phase 21C (End-to-End Validation)**:
   - Run full regression test suite (backend + Flutter).
   - Verify 10x determinism and invariant compliance.

---

## 18. Rollback Strategy

- All new capabilities are injected via interfaces in `app/api/dependencies.py`.
- If SACHET encounters unexpected government schema changes, setting `alert_provider = MockAlertProvider()` or `WeatherAPIAlertProvider()` instantly reverts alert behavior.
- If DMRC transit encounters an edge case, `routing_provider` falls back to Google Routes for all modes.
- Zero database migrations or schema alterations are required.

---

## 19. Updated Architectural Invariants (1–24)

All 18 existing invariants are preserved, and 6 supplementary invariants are formally codified:

1. **Decision Engine Sole Authority**: sole authority for risk scoring, risk tiers, route selection, feasibility, arrival deadlines, alert precedence, and recommendations.
2. **LLM Zero Decision Authority**: natural language explanation layer only.
3. **GroundingValidator Mandatory**: rejects unsupported facts, invented scores, or route contradictions.
4. **Firestore Persistence Only**: persistence/audit layer only; never an input to Decision Engine.
5. **Flutter Zero Direct Firestore**: communicates with persistence exclusively through FastAPI.
6. **Saved Routes as Bookmarks Only**: bookmarks never feed into Decision Engine.
7. **Historical Snapshots Immutable**: historical trips are stamped `isSnapshot: true` and never treated as live weather.
8. **Unrestricted Guest Access**: guest travelers retain full access to all trip planning and assistant features.
9. **No Silent Mock Weather in Production**: provider outages produce typed degradation.
10. **No Production Mock Tokens**: mock auth tokens strictly rejected in production.
11. **Verified Token Identity**: user identity derived exclusively from verified token claims.
12. **Cross-User Isolation**: strict user data segregation.
13. **Persistence Failure Isolation**: database errors never block or delay trip analysis.
14. **LLM Failure Isolation**: LLM outages trigger deterministic fallback explanations.
15. **Truthful Typed Degradation**: provider failures produce typed degraded statuses.
16. **No Secret Leakage**: secrets and tokens redacted from all logs.
17. **Sanitized API Errors**: no stack traces or internal implementation leakage.
18. **Abuse & Rate Limiting**: sliding-window rate limiter protects expensive endpoints.
19. **External Data Never Mutates Risk Directly**: external providers supply raw observations; Decision Engine alone maps observations to risk.
20. **Explicit Provider Provenance**: every coordinate, alert, and hazard displays typed provenance.
21. **No Silent Stale Data**: observations older than freshness thresholds are explicitly flagged `is_stale = True`.
22. **Deterministic Conflict Resolution**: authoritative government alerts strictly override commercial advisories.
23. **Outages Never Fabricate Mock Data**: missing provider data produces degraded states, never synthetic sunny weather or fake clear roads.
24. **Bounded Concurrency & Zero Sequential Lag**: all independent external provider calls execute concurrently under `asyncio.gather`.

---

## 20. Exact Implementation Order

1. **Step 1**: Add `defusedxml` to `backend/pyproject.toml`.
2. **Step 2**: Compile and bundle verified datasets (`app/data/delhi_waterlogging_hotspots.json`, `app/data/dmrc_network.json`, `app/data/ncr_pincodes.json`).
3. **Step 3**: Implement `NdmaSachetAlertProvider` (`app/providers/alerts/sachet.py`) and unit tests.
4. **Step 4**: Implement `DelhiWaterloggingHazardRepository` (`app/repositories/delhi_waterlogging_repository.py`) and unit tests.
5. **Step 5**: Implement `NcrPincodeGeocodingProvider` (`app/providers/geocoding/pincode.py`) and unit tests.
6. **Step 6**: Implement `DmrcMetroProvider` (`app/providers/transit/dmrc_metro.py`) and unit tests.
7. **Step 7**: Update `TripService` orchestration and FastAPI dependency injection (`app/api/dependencies.py`).
8. **Step 8**: Run full backend regression suite (`pytest backend/tests`), `flutter analyze`, and `flutter test`.
9. **Step 9**: Execute 10x repeated concurrency determinism verification.
