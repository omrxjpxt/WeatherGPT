# WeatherGPT Overall System Architecture

## Overview

WeatherGPT is an AI-powered, hyper-local, weather-aware trip planning and route risk assessment platform for Delhi-NCR commuters. The platform couples a deterministic Decision Engine with real-time weather, traffic intelligence, route alternatives, natural language assistance, and user profile data persistence.

```
+-------------------------------------------------------------+
|                      Flutter Mobile App                      |
| (No direct Firestore access - Firebase Auth for ID tokens)  |
+-------------------------------------------------------------+
                              |
                     HTTPS / JSON REST
               (Authorization: Bearer <token>)
                              v
+-------------------------------------------------------------+
|                     FastAPI Backend Layer                   |
| - Authentication Token Verification                         |
| - Service Orchestration (Trips, Weather, Assistant, Users)  |
| - Persistence Boundary (Firestore / In-Memory Isolation)    |
+-------------------------------------------------------------+
         |                              |
         v                              v
+-----------------------+     +-------------------------------+
|  Deterministic Engine  |     | Backend Persistence Gateway   |
| - Risk scoring        |     | - Cloud Firestore (or Memory) |
| - Route alternatives  |     | - User profiles               |
| - Alert evaluation    |     | - Saved routes                |
| - Mode comparison     |     | - Historical snapshots        |
+-----------------------+     +-------------------------------+
```

---

## Key Architectural Principles

### 1. Zero Direct Firestore Access from Flutter
The Flutter client **MUST NEVER** access Cloud Firestore directly.
- No `cloud_firestore` dependency is included in Flutter.
- All persistence requests (`/users/me/profile`, `/users/me/saved-routes`, `/users/me/trips`, `/users/me/conversations`) flow through the FastAPI gateway.
- Firebase Admin credentials and service account private keys reside solely on the backend.

### 2. Firebase Auth -> ID Token -> FastAPI Flow
- Flutter uses `firebase_auth` (or offline `MockAuthService`) solely to authenticate the user and obtain a Firebase ID token.
- `ApiClient` injects the bearer token via:
  ```http
  Authorization: Bearer <id_token>
  ```
- If the user is unauthenticated (guest mode), no `Authorization` header is attached.
- Public endpoints (such as `POST /trips/analyze`) require no authentication.
- User-scoped persistence endpoints (`/users/me/*`) require a valid Bearer token; unauthenticated requests receive `401 Unauthorized` or `403 Forbidden`.

### 3. Absolute Decision Engine Authority
The deterministic Decision Engine remains the sole authority for:
- Route risk scores and risk levels
- Route selection and ranking
- Route feasibility and arrival deadlines
- Safety recommendations and mode comparison
- Alert overrides

**Critical Invariant:** Firestore data and saved route bookmarks **MUST NEVER** become inputs to the Decision Engine. Historical trip snapshots and saved routes are strictly presentation/bookmark entities.

### 4. Guest vs. Authenticated Behavior
- **Guest Travelers**: Retain 100% full, unrestricted access to trip analysis, route alternative evaluation, what-if departure simulation, mode comparison, and conversational Assistant interactions. No login barrier is imposed on core features.
- **Save Route Action**: Guests tapping "Save Route" receive a non-blocking prompt offering "Sign In / Create Account" or "Continue as Guest".
- **Authenticated Travelers**: Can bookmark routes to their profile, synchronize saved commutes across devices, view their audit-logged trip history, and update profile preferences.

### 5. Historical Snapshot Semantics
- Past trip decisions are persisted asynchronously by the backend as immutable audit records stamped with `isSnapshot: true`.
- Flutter explicitly labels past trip analyses in `ProfileScreen` with **"Historical Snapshot (Audit)"**.
- Historical snapshots are never treated or presented as live weather conditions.

### 7. Persistence Failure Isolation & Production Hardening
- Background write tasks (`_safe_persist`, `_safe_save_message`) are error-isolated. Database timeouts or Firestore connection drops never block, delay, or modify live user responses.
- Protected endpoints strictly enforce HTTP 401 with generic sanitized messages on missing, expired, or malformed tokens. Mock tokens are strictly rejected in production environments.
- Token UID verification (`profile.uid = uid`) guarantees zero cross-user tampering.
- Upstream provider degradation (routing, weather, traffic, hazards, LLM) gracefully produces typed degraded responses without hallucinating safety data or throwing 500 errors.
- End-to-end request correlation via `X-Request-Id` ASGI middleware and structured structlog context.
- Automatic secret redaction prevents Bearer tokens, API keys, and credentials from being logged.
- Sliding-window rate limiting protects expensive APIs with HTTP 429 and `Retry-After`.
- Mobile release packaging provides clean release manifests (Android INTERNET permissions) and display name configuration.

### 8. Intelligence & Data Provider Architecture (Phase 20)
- **Confidence-Aware Geocoding**: Multi-tier fallback chain (`Google` $\rightarrow$ `Nominatim` $\rightarrow$ `Open-Meteo` $\rightarrow$ `Curated NCR Gazetteer`) tracking coordinate provenance and confidence. Low-confidence queries ($< 0.50$) or ambiguous queries are rejected via `GeocodingResolutionError` (HTTP 400). Legacy mock geocoding is eliminated in production.
- **Deterministic Air Quality Decision Model**: Copernicus CAMS API integrates real-time AQI and $PM_{2.5}$. Converts $PM_{2.5}$ using US EPA piecewise linear formula, applies mode-specific physical exposure multipliers (walking/cycling $1.0\times$, car $0.15\times$, metro $0.10\times$), and bounds AQI risk contribution strictly ($\le 25$ for enclosed modes). Stale observations ($> 6$h) are flagged and official alerts retain unconditional safety precedence.
- **Traffic-Aware Routing**: `GoogleRoutesProvider` passes `TRAFFIC_AWARE` preference and `departureTime` for motorized modes, cleanly separating static duration from traffic delay.
- **Precipitation Probability**: Open-Meteo probability (0–100%) scales precipitation risk deterministically, bounding risk score to $\le 10$ when probability $< 20\%$.

---

## System Test Metrics

- **Flutter Analyze:** 0 issues
- **Flutter Test Suite:** 63/63 tests passing
- **Backend Test Suite:** 165/165 tests passing

