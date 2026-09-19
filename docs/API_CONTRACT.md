# API Contract

Prefix: `/api/v1`

## Flutter ↔ FastAPI Environment Configuration

The Flutter application dynamically configures the base URL using `ApiConfig` (`lib/core/api/api_config.dart`):

- **Production**: `https://api.weathergpt.com/api/v1`
- **Local Web**: `http://localhost:8000/api/v1`
- **Android Emulator**: `http://10.0.2.2:8000/api/v1`
- **iOS Device / Simulator**: `http://$API_HOST:8000/api/v1` (defaults to 127.0.0.1)

All endpoints accept and return camelCase JSON automatically handled by the backend's `alias_generator=to_camel` and Flutter's `.fromJson` models.

## Authentication & Authorization

- **Header Format**: `Authorization: Bearer <firebase_id_token>`
- **Guest Access**: Public endpoints (`POST /trips/analyze`, `POST /assistant/chat`, `GET /weather/*`, `GET /alerts/*`) do NOT require authentication. Guest requests omit the `Authorization` header.
- **Protected Endpoints**: `/users/me/*` endpoints strictly require a valid Bearer token.
  - `401 Unauthorized`: Missing or expired/invalid ID token.
  - `403 Forbidden`: Authenticated user lacks permission for requested resource.
- **Client Implementation**: `ApiClient` in Flutter uses a dynamic `tokenProvider: Future<String?> Function()` callback to attach the current token if authenticated. All HTTP verbs (`GET`, `POST`, `PUT`, `DELETE`) are supported.

## Endpoints

### 1. Health
`GET /health`
Returns service status, version, and environment.

### 2. Trips
`POST /trips/analyze`
**Request:** `TripRequest` (origin, destination, departure_time, mode)
**Response:** `TripResponse` (analysis_id, status, request, risk (optional), route, recommendation (optional), mode_options, hazards, sources, estimated_duration, distance_km, traffic (optional))

The `status` field returns a `TripStatus` string enum (`success`, `routing_unavailable`, `weather_unavailable`, `degraded`). Clients must check `status` before assuming `risk` or `recommendation` are non-null.

#### Data Sources & Provenance (`TripResponse.sources`)
Every trip response contains a list of `DataSource` objects guaranteeing end-to-end provenance transparency:
- `name`: str (e.g. `"Open-Meteo API"`, `"Google Routes API"`, `"Mock Traffic Provider (Demo)"`)
- `type`: str (e.g. `"Weather (Primary)"`, `"Routing [unavailable]"`, `"Alerts [demo]"`, `"Traffic [mock]"`)
- `lastUpdated`: ISO-8601 datetime

**Strict Provenance Rules:**
- `live ≠ mock`: Live status is never coupled with mock provenance.
- `mock ≠ authoritative`: Mock alerts and routing are strictly isolated and prevented from triggering production emergency overrides.
- `secondary ≠ authoritative`: Commercial feeds (WeatherAPI, Open-Meteo) are never labeled as official government sources.
- No Silent Failure: When routing or weather is unavailable, `TripStatus` explicitly degrades, risk is omitted (`null`), and the source is marked as `[unavailable]`.


#### Traffic Intelligence (`TripResponse.traffic`)
When traffic evaluation is active, the response includes a `traffic` object (`TrafficSnapshot`). If traffic data is absent, unavailable, or omitted, this field is `null` (100% backward compatible).

**Model: `TrafficSnapshot`**
- `status`: `mock` | `live` | `unavailable` | `cached`
- `condition`: `clear` | `congested` | `stop_and_go` | `gridlock` | `unknown`
- `congestionLevel`: `free_flow` | `moderate` | `heavy` | `severe` | `unknown`
- `delaySeconds`: float (Traffic delay in seconds; 0.0 for zero delay / walk / metro)
- `staticDuration`: ISO-8601 duration string (Free-flow baseline duration, e.g. `PT50M`)
- `trafficAwareDuration`: ISO-8601 duration string (`staticDuration + trafficDelay`, e.g. `PT1H2M`)
- `currentSpeedKmh`: Optional[float]
- `freeFlowSpeedKmh`: Optional[float]
- `segments`: List[`TrafficSegment`]
- `timestamp`: ISO-8601 datetime
- `sourceName`: str (e.g. `"Mock Traffic Provider (Demo)"`)
- `provenance`: str (e.g. `"demo/mock"`)

**Model: `TrafficSegment`**
- `startLat`, `startLng`, `endLat`, `endLng`: float
- `congestionLevel`: `free_flow` | `moderate` | `heavy` | `severe` | `unknown`
- `delaySeconds`: float
- `currentSpeedKmh`: Optional[float]
- `freeFlowSpeedKmh`: Optional[float]

**Duration Invariant:**
`trafficAwareDuration = staticDuration + trafficDelay`. Traffic delay is applied exactly once to prevent double-counting. Base `TripResponse.estimatedDuration` remains the base static duration for legacy compatibility.

#### Route Alternatives (`TripResponse.routes`)
When multiple route alternatives are evaluated, `TripResponse.routes` contains the ranked candidate routes:
`routes: List[EvaluatedRoute] = Field(default_factory=list)`

Payloads that omit `routes` or provide an empty list are fully supported for 100% backward compatibility.

**Model: `EvaluatedRoute`**
- `routeId`: str (e.g. `"route_1"`)
- `summary`: str (e.g. `"Via Noida-Greater Noida Expy"`)
- `distanceKm`: float
- `staticDuration`: ISO-8601 duration string
- `polyline`: Optional[str]
- `segments`: List[`RouteSegment`]
- `traffic`: Optional[`TrafficSnapshot`]
- `evaluation`: `RouteEvaluation`
- `hazards`: List[`Hazard`] (Field default_factory=list)
- `sourceName`: str
- `provenance`: str
- `risk`: Optional[`RiskAssessment`]

**Model: `RouteEvaluation`**
- `routeId`: str
- `riskScore`: int (0-100)
- `riskLevel`: `low` | `moderate` | `high` | `severe`
- `staticDuration`: ISO-8601 duration string
- `trafficAwareDuration`: ISO-8601 duration string
- `trafficDelaySeconds`: float
- `exposureScore`: float
- `bottleneckScore`: int
- `hazardCount`: int
- `isFeasible`: bool
- `feasibilityReason`: Optional[str]
- `recommendationHeadline`: str
- `recommendationBody`: str
- `suggestedMode`: Optional[str]
- `suggestedDepartureTime`: Optional[datetime]
- `isSelected`: bool (Backend deterministic recommendation)
- `selectionReason`: Optional[str] (Human-readable rationale explaining why this route was recommended or why an alternative differs)
- `provenance`: str

**Separation of Recommendation vs. Inspection:**
- `isSelected = True` is set on exactly one route deterministically selected by the backend.
- The Flutter client tracks `activeRouteId` locally for user inspection; tapping alternative cards does not mutate `isSelected` or the backend recommendation.


### 3. Scenarios
`POST /scenarios/evaluate`
**Request:** `EvaluateScenariosRequest` (request: TripRequest, departure_times: List[datetime])
**Response:** `List[ScenarioResult]`

### 4. Weather
`GET /weather/current`
`GET /weather/forecast`

### 5. Alerts
`GET /alerts/`

**Model: `NormalizedAlert`**
- `id`: str
- `sourceName`: str
- `sourceClass`: `authoritative` | `secondary` | `demo`
- `severity`: str
- `affectedAreasPolygon`: List[List[float]]
- `issuedAt`: datetime
- `expiresAt`: Optional[datetime]
- `action`: Optional[str]
- `sourceUrl`: Optional[str]
- `isOverrideEligible`: bool

### 6. Hazards
`GET /hazards/`

**Model: `TripHazard`**
- `hazard`: `NormalizedHazard`
  - `id`: str
  - `type`: `waterlogging` | `visibility` | `wind` | `heat`
  - `lat`, `lng`: float
  - `radiusMeters`: float
  - `baseSeverity`: int
  - `sourceName`: str
  - `sourceClass`: `authoritative` | `government_open_data` | `secondary` | `demo`
  - `triggerPrecipitationMm`: Optional[float]
  - `triggerCondition`: Optional[str]
- `relevance`: `HazardRelevanceResult`
  - `spatiallyRelevant`: bool
  - `weatherTriggered`: bool
  - `temporallyRelevant`: bool
  - `currentlyRelevant`: bool
  - `contributionScore`: float

### 7. Assistant
Natural language understanding and grounded explanation endpoints. Both endpoints accept and return camelCase JSON.

#### `POST /assistant/chat`
Full end-to-end conversation pipeline: extracts intent, deterministically validates required trip fields, executes `TripService` (for trip decisions), compiles `DecisionFacts`, queries `LLMProvider.generate_explanation()`, validates grounding via `GroundingValidator`, and returns a grounded response.

**Request:** `AssistantChatRequest`
- `query`: str (User natural language query in English, Hindi, or Hinglish)
- `conversationHistory`: List[dict] (Optional conversational context)
- `referenceTime`: Optional[datetime] (Defaults to UTC now)
- `conversationId`: Optional[str] (Session-scoped ID for conversation persistence)

**Response:** `AssistantChatResponse`
- `message`: str (Accepted grounded natural language explanation or deterministic fallback)
- `conversationId`: Optional[str] (Persisted session/conversation identifier)
- `intent`: `ExtractedIntent`
  - `userIntent`: `trip_decision` | `weather_question` | `route_comparison` | `what_if` | `alert_question` | `general_weather`
  - `origin`: Optional[str]
  - `destination`: Optional[str]
  - `mode`: Optional[`TransportMode`] (`bike`, `car`, `metro`, `walk`)
  - `departureTime`: Optional[datetime]
  - `confidence`: float
  - `rawEntities`: Dict[str, Any]
- `tripRequest`: Optional[`TripRequest`] (Populated when intent is complete and valid)
- `tripResponse`: Optional[`TripResponse`] (Authoritative decision engine response; `null` for `need_clarification` or non-trip intents)
- `status`: `success` | `need_clarification` | `degraded` | `error`
- `clarificationPrompt`: Optional[str] (Populated when `status == "need_clarification"`)
- `provenance`: str (e.g. `"demo/mock"`, `"google/gemini-1.5-flash"`)

**Response States:**
- `need_clarification`: `tripResponse` is strictly `null`. `TripService` is not executed.
- `success`: Authoritative `tripResponse` attached.
- `degraded`: `tripResponse` present with degraded provider status (e.g. `routing_unavailable`); no fabricated metrics.
- `error`: Clean error message; no fabricated trip result.

#### `POST /assistant/parse`
Lightweight intent extraction endpoint without executing trip analysis.

**Request:** `AssistantParseRequest`
- `query`: str
- `referenceTime`: Optional[datetime]

**Response:** `AssistantParseResponse`
- `intent`: `ExtractedIntent`
- `isComplete`: bool (Deterministic backend verification of required fields for `trip_decision`)
- `missingFields`: List[str] (e.g. `["origin", "destination"]`)
- `clarificationPrompt`: Optional[str]

*Note: All JSON keys use `camelCase` to directly match the Flutter client models.*

### 8. Users
`GET /users/me/profile`
`PUT /users/me/profile`
**Model: `UserProfile`**
- `uid`: str
- `email`: Optional[str]
- `displayName`: Optional[str]
- `homeAddress`: Optional[str]
- `workAddress`: Optional[str]
- `defaultMode`: Optional[str]

`GET /users/me/saved-routes`
`POST /users/me/saved-routes`
`DELETE /users/me/saved-routes/{savedRouteId}`
**Model: `SavedRoute`**
- `id`: str
- `name`: str
- `originId`: str
- `destinationId`: str

`GET /users/me/trips`
**Model: `TripHistorySummary`**
- `analysisId`: str
- `status`: str
- `origin`, `destination`, `mode`: str
- `riskLevel`: Optional[str]
- `recommendationHeadline`: Optional[str]
- `createdAt`: datetime
- `isSnapshot`: bool

`GET /users/me/trips/{analysisId}`
Returns the full `TripResponse` snapshot.

`GET /users/me/conversations`
**Model: `ConversationSummary`**
- `id`: str
- `tripId`: str
- `title`: str
- `createdAt`: datetime
