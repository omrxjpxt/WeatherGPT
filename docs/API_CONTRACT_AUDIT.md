# WeatherGPT API Contract Audit

This document presents a comprehensive, side-by-side audit comparing the FastAPI backend Pydantic models, API endpoint routes, Flutter Dart models, HTTP repository implementations, and serialized JSON payloads across WeatherGPT.

---

## 1. Executive Summary & Contract Health

| Metric | Status | Evaluation |
| :--- | :--- | :--- |
| **Pydantic Alias Generator** | `alias_generator = to_camel` | Standardized camelCase across all models |
| **Enum Serialization** | `use_enum_values = True` | Strings serialized matching Dart enum names |
| **Datetime Serialization** | ISO-8601 UTC Strings | Handled via Pydantic & Dart `DateTime.parse` |
| **Duration Serialization** | ISO-8601 Duration / timedelta | Handled via `_parseDuration` in Dart |
| **Model Parity: Core Trips** | **100% Match** | `TripRequest`, `TripResponse`, `EvaluatedRoute`, `TrafficSnapshot` |
| **Model Parity: Assistant** | **100% Match** | `AssistantChatRequest`, `AssistantChatResponse`, `ExtractedIntent` |
| **Model Parity: Users & Persistence** | **Minor Discrepancy** | `displayName` present in Dart `UserProfile`, omitted in Backend `UserProfile` |
| **Standalone Weather Endpoints** | **Defect Identified** | `GET /weather/current` accesses `forecast.points` on a Python `list` |

---

## 2. API Endpoint Inventory

| Endpoint | Method | Auth Level | Request Body | Response Body | Contract Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `/api/v1/health` | `GET` | Public | None | `{"status": str, "version": str, "environment": str}` | **VERIFIED** |
| `/api/v1/trips/analyze` | `POST` | Public / Optional Bearer | `TripRequest` | `TripResponse` | **VERIFIED** |
| `/api/v1/scenarios/evaluate` | `POST` | Public | `EvaluateScenariosRequest` | `List[ScenarioResult]` | **VERIFIED** |
| `/api/v1/weather/current` | `GET` | Public | Query: `lat`, `lng` | `WeatherPoint` | **NEEDS FIX** (`.points` bug) |
| `/api/v1/weather/forecast` | `GET` | Public | Query: `lat`, `lng` | `List[WeatherPoint]` | **NEEDS FIX** (`.points` bug) |
| `/api/v1/alerts/` | `GET` | Public | Query: `lat`, `lng` | `List[OfficialAlert]` | **VERIFIED** |
| `/api/v1/hazards/` | `GET` | Public | Query: `min_lat`, etc. | `List[NormalizedHazard]` | **NEEDS HARDENING** (Mock bound) |
| `/api/v1/assistant/chat` | `POST` | Public / Optional Bearer | `AssistantChatRequest` | `AssistantChatResponse` | **VERIFIED** |
| `/api/v1/assistant/parse` | `POST` | Public | `AssistantParseRequest` | `AssistantParseResponse` | **VERIFIED** |
| `/api/v1/users/me/profile` | `GET` | Strictly Authenticated | None | `UserProfile` | **NEEDS HARDENING** (Missing displayName) |
| `/api/v1/users/me/profile` | `PUT` | Strictly Authenticated | `UserProfile` | `UserProfile` | **NEEDS HARDENING** (Missing displayName) |
| `/api/v1/users/me/saved-routes` | `GET` | Strictly Authenticated | None | `List[SavedRoute]` | **VERIFIED** |
| `/api/v1/users/me/saved-routes` | `POST` | Strictly Authenticated | `SavedRoute` | `SavedRoute` | **VERIFIED** |
| `/api/v1/users/me/saved-routes/{id}` | `DELETE` | Strictly Authenticated | None | `{"status": "deleted"}` | **VERIFIED** |
| `/api/v1/users/me/trips` | `GET` | Strictly Authenticated | None | `List[TripHistorySummary]` | **VERIFIED** |
| `/api/v1/users/me/trips/{id}` | `GET` | Strictly Authenticated | None | `TripResponse` | **VERIFIED** |
| `/api/v1/users/me/conversations` | `GET` | Strictly Authenticated | None | `List[ConversationSummary]` | **VERIFIED** |

---

## 3. Detailed Side-by-Side Model Comparison

### 3.1 Trip Models (`TripRequest`, `TripResponse`)

| Field | Backend Pydantic (`backend/app/models/trip.py`) | Frontend Dart (`lib/models/models.dart`) | Serialization / Wire Format | Parity Status |
| :--- | :--- | :--- | :--- | :--- |
| `analysisId` | `str = Field(...)` | `final String? analysisId` | String UUID | **MATCH** |
| `status` | `TripStatus = TripStatus.success` | `final TripStatus status` | String enum (`success`, `degraded`, etc.) | **MATCH** |
| `request` | `TripRequest` | `final TripRequest request` | Nested JSON Object | **MATCH** |
| `risk` | `Optional[RiskAssessment] = None` | `final RiskAssessment? risk` | Nullable Nested JSON Object | **MATCH** |
| `route` | `List[RouteSegment]` | `final List<RouteSegment> route` | Array of Segment Objects | **MATCH** |
| `recommendation` | `Optional[Recommendation] = None` | `final Recommendation? recommendation` | Nullable Nested Object | **MATCH** |
| `modeOptions` | `List[ModeOption]` | `final List<ModeOption> modeOptions` | Array of Mode Objects | **MATCH** |
| `hazards` | `List[Hazard]` | `final List<Hazard> hazards` | Array of Hazard Objects | **MATCH** |
| `sources` | `List[DataSource]` | `final List<DataSource> sources` | Array of DataSource Objects | **MATCH** |
| `estimatedDuration` | `timedelta` | `final Duration estimatedDuration` | ISO-8601 duration (`PT...`) / `0:35:00` | **MATCH** |
| `distanceKm` | `float` | `final double distanceKm` | Float / Double | **MATCH** |
| `traffic` | `Optional[TrafficSnapshot] = None` | `final TrafficSnapshot? traffic` | Nullable Nested Object | **MATCH** |
| `routes` | `List[EvaluatedRoute] = Field(default_factory=list)` | `final List<EvaluatedRoute> routes` | Array of EvaluatedRoute Objects | **MATCH** |

### 3.2 User Persistence Models (`UserProfile`, `SavedRoute`, `TripHistorySummary`)

| Field | Backend Pydantic (`backend/app/models/user.py`) | Frontend Dart (`lib/models/models.dart`) | Notes | Parity Status |
| :--- | :--- | :--- | :--- | :--- |
| **`UserProfile.uid`** | `str` | `final String uid` | Required string | **MATCH** |
| **`UserProfile.email`** | `Optional[str] = None` | `final String? email` | Optional string | **MATCH** |
| **`UserProfile.displayName`** | **MISSING FROM BACKEND MODEL** | `final String? displayName` | Dart sends and expects `displayName` | **MISMATCH** |
| **`UserProfile.createdAt`** | `datetime = Field(...)` | `final DateTime createdAt` | ISO-8601 UTC string | **MATCH** |
| **`UserProfile.lastLoginAt`** | `datetime = Field(...)` | `final DateTime lastLoginAt` | ISO-8601 UTC string | **MATCH** |
| **`SavedRoute.id`** | `str` | `final String id` | Required string | **MATCH** |
| **`SavedRoute.name`** | `str` | `final String name` | Required string | **MATCH** |
| **`SavedRoute.originId`** | `str` | `final String originId` | Required string | **MATCH** |
| **`SavedRoute.destinationId`** | `str` | `final String destinationId` | Required string | **MATCH** |
| **`SavedRoute.createdAt`** | `datetime = Field(...)` | `final DateTime createdAt` | ISO-8601 UTC string | **MATCH** |
| **`TripHistorySummary.analysisId`** | `str` | `final String analysisId` | Required string | **MATCH** |
| **`TripHistorySummary.isSnapshot`** | `bool = True` | `final bool isSnapshot` | Stamped `true` for immutable audit | **MATCH** |

### 3.3 Assistant Models (`AssistantChatRequest`, `AssistantChatResponse`)

| Field | Backend Pydantic (`backend/app/models/assistant.py`) | Frontend Dart (`lib/models/models.dart`) | Parity Status |
| :--- | :--- | :--- | :--- |
| `message` | `str` | `final String message` | **MATCH** |
| `intent` | `ExtractedIntent` | `final ExtractedIntent intent` | **MATCH** |
| `tripRequest` | `Optional[TripRequest] = None` | `final TripRequest? tripRequest` | **MATCH** |
| `tripResponse` | `Optional[TripResponse] = None` | `final TripResponse? tripResponse` | **MATCH** |
| `status` | `str` | `final String status` | **MATCH** |
| `clarificationPrompt` | `Optional[str] = None` | `final String? clarificationPrompt` | **MATCH** |
| `provenance` | `str = "demo/mock"` | `final String provenance` | **MATCH** |
| `groundingFallbackUsed` | `bool = False` | `final bool groundingFallbackUsed` | **MATCH** |
| `conversationId` | `Optional[str] = None` | `final String? conversationId` | **MATCH** |

---

## 4. Specific Defects and Inconsistencies Identified

### Defect 1: Standalone Weather Endpoint Crashes on Python `list`
- **File**: `backend/app/api/routes/weather.py:19`
- **Current Code**:
  ```python
  forecast = await provider.get_forecast(lat, lng, now, 1)
  if forecast and forecast.points:
      return forecast.points[0]
  ```
- **Why it matters**: `WeatherProvider.get_forecast()` returns `List[NormalizedWeatherPoint]`. A Python `list` has no attribute `.points`. Any request to `GET /api/v1/weather/current` or `GET /api/v1/weather/forecast` crashes with `AttributeError: 'list' object has no attribute 'points'` (returning HTTP 500).
- **Severity**: **BLOCKER** for direct weather API calls.
- **Recommended Fix**:
  ```python
  if forecast and len(forecast) > 0:
      return forecast[0]
  ```

### Defect 2: Raw Python Exception Raised in Route Handler
- **File**: `backend/app/api/routes/weather.py:21`
- **Current Code**:
  ```python
  raise Exception("Weather data unavailable")
  ```
- **Why it matters**: Raises an unhandled generic Python exception rather than a typed `HTTPException(status_code=503, detail="Weather data unavailable")`. Unhandled exceptions leak internal server error details.
- **Severity**: **HIGH**.
- **Recommended Fix**: Raise `HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Weather data unavailable")`.

### Defect 3: Missing `displayName` on Backend `UserProfile`
- **File**: `backend/app/models/user.py:6-10`
- **Current Code**:
  ```python
  class UserProfile(WeatherBaseModel):
      uid: str
      email: Optional[str] = None
      created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
      last_login_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
  ```
- **Why it matters**: Flutter's `UserProfile` model and `ProfileScreen` display and submit `displayName`. Because the backend Pydantic model omits `display_name: Optional[str] = None`, user display names sent from the app are ignored and dropped on retrieval.
- **Severity**: **HIGH**.
- **Recommended Fix**: Add `display_name: Optional[str] = None` to `backend/app/models/user.py`.

### Defect 4: Bare Mutable Default List in `TrafficSnapshot`
- **File**: `backend/app/models/traffic.py:27`
- **Current Code**:
  ```python
  segments: List[TrafficSegment] = []
  ```
- **Why it matters**: Violates Pydantic best practices; shared mutable defaults can lead to state pollution across requests.
- **Severity**: **MEDIUM**.
- **Recommended Fix**: Replace with `segments: List[TrafficSegment] = Field(default_factory=list)`.

### Defect 5: Standalone Hazard Router Direct Mock Instantiation
- **File**: `backend/app/api/routes/hazards.py:11`
- **Current Code**:
  ```python
  hazard_repo = MockHazardRepository()
  ```
- **Why it matters**: Direct module-level instantiation bypasses FastAPI dependency injection. Furthermore, it returns internal `NormalizedHazard` objects instead of client-facing `Hazard` domain models.
- **Severity**: **MEDIUM**.
- **Recommended Fix**: Inject `HazardRepository` via `Depends(get_hazard_repository)`.

---

## 5. Architectural Invariant Preservation Check

| Invariant | API Contract Impact | Verification |
| :--- | :--- | :--- |
| **No Firestore direct access from Flutter** | All client calls target `/api/v1/users/me/*` through `HttpUserRepository` | **PRESERVED** |
| **Decision Engine is Sole Authority** | Risk formulas and route selection are not exposed to client mutation | **PRESERVED** |
| **Guest Access Retained** | Public routes require no `Authorization` header | **PRESERVED** |
| **Historical Snapshots Immutable** | Stamped `isSnapshot = True`, distinct from real-time evaluations | **PRESERVED** |
