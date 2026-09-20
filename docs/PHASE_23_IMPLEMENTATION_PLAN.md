# Phase 23 — Production Engine & Reliability Hardening Implementation Plan

**Status:** Proposed (PLAN ONLY — Awaiting Approval)  
**Date:** September 20, 2026  
**Target:** WeatherGPT Core Engine, Providers, and Client Reliability  
**Constraint:** READ-ONLY. No implementation until explicit user approval.  

---

## 1. Confirmed Scope

Phase 23 focuses strictly on **production reliability, bug fixing, performance optimization, and location independence** identified in the Phase 23 Audit (`docs/PHASE_23_PRODUCTION_READINESS_AUDIT.md`):

1. **Fix Critical Runtime Bugs:**
   - **CRIT-1:** Fix hazard object model mismatch in `TripService.analyze_trip` where `selected_route.hazards` (`List[Hazard]`) was passed to secondary mode evaluations, causing an `AttributeError` on active hazards and dropping candidate modes.
   - **CRIT-2:** Implement UTC timezone normalization on incoming datetimes in `TripRequest` and Decision Engine to eliminate crashes when clients pass timezone-naive ISO strings.
2. **Eliminate Major Performance Bottlenecks:**
   - **HIGH-1:** Refactor `ScenarioService.evaluate_scenarios` to evaluate 13 departure times in-memory using the resolved route geometry and 72-hour weather/AQI timeline from a single pass, replacing the 13x redundant full `analyze_trip` loop.
   - **HIGH-3:** Introduce an application-level `httpx.AsyncClient` connection pool managed in FastAPI's `lifespan` context manager, replacing per-request client churn.
3. **Complete Location Independence:**
   - **HIGH-2:** Add optional `location` query parameter resolution to `/api/v1/alerts/` via `GeocodingProvider`. Remove hardcoded Noida coordinates (`28.6270, 77.3650`) from Flutter's `HttpAlertRepository` and `currentWeatherProvider`.
4. **Security & Readiness Hardening:**
   - **HIGH-4:** Add bounded key eviction to `InMemoryRateLimiter` to prevent memory leaks and validate proxy header trust.
   - **MED-1:** Add `ApiErrorType.rateLimited` and retry UI in Flutter.
   - **MED-2:** Add `/api/v1/health/ready` probe verifying dependency readiness.
   - **MED-3:** Remove orphaned dead repository forwarders (`interfaces/alert_repository.py`, `firestore/alert_repository.py`, `delhi_waterlogging_repository.py`, `firestore_hazard_repository.py`).

---

## 2. Exact Files Likely to Change

### Backend
- `backend/app/main.py`: Update `lifespan` to manage shared HTTP client lifecycle; register `/health/ready` route.
- `backend/app/core/http.py` *(NEW)*: Centralized HTTP client session manager with connection pooling.
- `backend/app/models/trip.py`: Add Pydantic validator ensuring `departure_time` and `arrival_deadline` are timezone-aware (UTC).
- `backend/app/decision_engine/uncertainty.py`: Add defensive timezone normalization before computing delta hours.
- `backend/app/decision_engine/alert_override.py`: Add defensive timezone normalization for alert and travel timestamps.
- `backend/app/decision_engine/temporal_alignment.py`: Add defensive timezone normalization for weather points and target times.
- `backend/app/services/trip_service.py`: Pass original `route_hazards` (`List[NormalizedHazard]`) into candidate mode evaluation instead of `selected_route.hazards`.
- `backend/app/services/scenario_service.py`: Refactor `evaluate_scenarios` to fetch route and weather once, then evaluate candidate times in-memory.
- `backend/app/api/routes/alerts.py`: Add `location: Optional[str] = None` query parameter with `GeocodingProvider` coordinate resolution.
- `backend/app/api/routes/health.py`: Add `/ready` readiness probe endpoint checking provider reachability.
- `backend/app/core/rate_limiter.py`: Add periodic expiration/pruning of idle client keys.
- `backend/app/providers/geocoding/fallback.py`: Replace unbounded dict cache with bounded LRU cache.
- `backend/app/repositories/delhi_waterlogging_repository.py` *(DELETE)*: Remove orphaned 4-line forwarder.
- `backend/app/repositories/firestore_hazard_repository.py` *(DELETE)*: Remove duplicate empty stub.
- `backend/app/repositories/interfaces/alert_repository.py` *(DELETE)*: Remove unused interface.
- `backend/app/repositories/firestore/alert_repository.py` *(DELETE)*: Remove unused repository stub.

### Flutter
- `lib/core/api/api_exception.dart`: Add `rateLimited` to `ApiErrorType`.
- `lib/core/api/api_client.dart`: Parse HTTP 429 and extract `Retry-After` header.
- `lib/repositories/http/http_alert_repository.dart`: Remove hardcoded Noida coordinates; pass location query to backend.
- `lib/core/providers.dart`: Derive `currentWeatherProvider` location dynamically; update error states.
- `lib/features/trip_analysis/trip_analysis_screen.dart`: Add retry button to error state.

---

## 3. Architecture Impact

- **Decision Engine Authority:** 100% preserved. Decision Engine remains the sole authority for risk calculations and route selection.
- **Provider Layer:** Providers continue to supply raw, unweighted observations; connection pooling is handled at the network transport layer without altering domain models.
- **Data Persistence:** Firestore remains strictly an audit/history persistence layer with zero influence on real-time decisions.
- **Zero Client Firestore Access:** All client interactions remain mediated through FastAPI REST endpoints.

---

## 4. Implementation Steps

### Step 1: Runtime Bug Fixes (CRIT-1 & CRIT-2)
1. In `backend/app/models/trip.py`, add a `@field_validator('departure_time', 'arrival_deadline')` ensuring datetimes without tzinfo are stamped with `timezone.utc`.
2. In `uncertainty.py`, `alert_override.py`, and `temporal_alignment.py`, add fallback `if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)`.
3. In `trip_service.py`, preserve `raw_route_hazards = list(route_hazards)` and pass `hazards=raw_route_hazards` when evaluating `eval_metro` and `eval_road`.
4. Create test suite: `backend/tests/unit/test_timezone_and_hazard_model_fixes.py`.

### Step 2: Scenario Service Single-Pass Optimization (HIGH-1)
1. In `scenario_service.py`:
   - Invoke `trip_service.resolve_corridor_context(request)` once to obtain geocoded locations, primary normalized route, and 72-hour weather/AQI timeline.
   - Run in-memory `decision_engine.evaluate_route_core(TripContext(..., departure_time=cand_time))` for each candidate time in `departure_times`.
   - Collect and return `ScenarioResult` list.
2. Verify latency drops from ~15s to $< 50\text{ ms}$.
3. Create test suite: `backend/tests/unit/test_scenario_single_pass_performance.py`.

### Step 3: Centralized HTTP Connection Pooling (HIGH-3)
1. Create `backend/app/core/http.py` defining `HttpClientManager`:
   - Instantiates a shared `httpx.AsyncClient(timeout=10.0, limits=httpx.Limits(max_keepalive_connections=20, max_connections=50))` on startup.
   - Closes the client on shutdown.
2. In `main.py`, wire `HttpClientManager` inside `lifespan(app)`.
3. In `dependencies.py`, inject the shared client into `OpenMeteoWeatherProvider`, `GoogleRoutesProvider`, `OpenMeteoAirQualityProvider`, `NdmaSachetAlertProvider`, and geocoders.

### Step 4: Location Independence in Alerts & Weather (HIGH-2)
1. Update `backend/app/api/routes/alerts.py` to accept `location: Optional[str] = Query(None)` and resolve coordinates via `GeocodingProvider`.
2. Update `lib/repositories/http/http_alert_repository.dart` to remove hardcoded `'28.6270', '77.3650'`.
3. Update `lib/core/providers.dart` `currentWeatherProvider` to resolve location from active trip or user input.

### Step 5: Rate Limiter & Health Hardening (HIGH-4 & MED-2)
1. In `rate_limiter.py`:
   - Implement `_prune_expired_keys(now)` deleting client keys whose timestamp lists are empty.
   - Bound max tracked keys to 10,000.
2. In `health.py`:
   - Add `/api/v1/health/ready` checking Firestore client status and weather provider connectivity.

### Step 6: Flutter Error & Retry Handling (MED-1)
1. Add `ApiErrorType.rateLimited` to `api_exception.dart`.
2. Update `api_client.dart` to handle status code 429 with retry message.
3. Update `TripAnalysisScreen` to render a clean error card with a retry button instead of a bare `Text('Error: ...')`.

### Step 7: Repository Cleanup & Documentation Drift (MED-3 & LOW-1)
1. Delete unused forwarders:
   - `backend/app/repositories/delhi_waterlogging_repository.py`
   - `backend/app/repositories/firestore_hazard_repository.py`
   - `backend/app/repositories/interfaces/alert_repository.py`
   - `backend/app/repositories/firestore/alert_repository.py`
2. Update `docs/API_CONTRACT.md` with complete Phase 22 `TripResponse` fields (`mode_options`, `air_quality`, `geocoding_provenance`).
3. Update `docs/DECISION_ENGINE.md` with normalized weights (`0.35, 0.20, 0.30, 0.15`).

---

## 5. Tests to Add / Update

1. **`test_timezone_and_hazard_model_fixes.py`:**
   - Test `TripRequest` with naive ISO string (`"2026-09-20T10:00:00"`).
   - Test `calculate_confidence` and `align_route_with_weather` with naive and aware datetimes.
   - Test multi-mode evaluation when `NormalizedHazard` objects are present on the route; verify `mode_options` contains bike, car, and metro without exceptions.
2. **`test_scenario_single_pass_performance.py`:**
   - Test 13 departure times; assert external weather/routing providers are called exactly once.
   - Assert in-memory results match sequential evaluations.
3. **`test_alerts_endpoint_geocoding.py`:**
   - Test `/alerts/?location=Gurgaon+Cyber+Hub`.
   - Test `/alerts/?lat=28.4595&lng=77.0266`.
   - Test invalid location query produces HTTP 400.
4. **`test_rate_limiter_memory_bounds.py`:**
   - Test that expired visitor keys are purged from `_requests`.
5. **`test_health_readiness.py`:**
   - Test `/api/v1/health/ready` returns ready status and dependency checks.
6. **Flutter Widget Tests:**
   - Test rate-limit (429) display in `air_quality_card_test.dart` or `screen_layout_test.dart`.
   - Test error card retry button triggering refetch.

---

## 6. Regression Gates

Before marking Phase 23 complete, the following gates must pass:

- `PYTHONPATH=backend backend/venv/bin/pytest backend/tests`: **All 220+ tests passing (0 failures)**.
- `flutter analyze`: **0 issues found**.
- `flutter test`: **All 68+ tests passing**.
- `test_concurrency_determinism.py`: **100% bit-identical scores across 10x evaluations**.
- Zero new external dependencies introduced.
- Zero mock providers wired in production.

---

## 7. Rollback Considerations

- All changes maintain strict backward compatibility with existing API request and response models.
- If the shared `httpx.AsyncClient` pool introduces any test isolation issues, providers can retain optional `http_client=None` parameter fallbacks for testing.
- No database migrations or schema alterations required.
