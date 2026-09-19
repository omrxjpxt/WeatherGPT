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
- Protected endpoints strictly enforce HTTP 401 on missing or invalid tokens, while token UID verification (`profile.uid = uid`) guarantees zero cross-user tampering.
- Upstream provider degradation (routing, weather, traffic, hazards, LLM) gracefully produces typed degraded responses without hallucinating safety data or throwing 500 errors.

---

## System Test Metrics

- **Flutter Analyze:** 0 issues
- **Flutter Test Suite:** 63/63 tests passing
- **Backend Test Suite:** 123/123 tests passing

