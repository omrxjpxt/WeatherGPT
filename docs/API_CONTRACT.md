# API Contract

Prefix: `/api/v1`

## Flutter ↔ FastAPI Environment Configuration

The Flutter application dynamically configures the base URL using `ApiConfig` (`lib/core/api/api_config.dart`):

- **Production**: `https://api.weathergpt.com/api/v1`
- **Local Web**: `http://localhost:8000/api/v1`
- **Android Emulator**: `http://10.0.2.2:8000/api/v1`
- **iOS Device / Simulator**: `http://$API_HOST:8000/api/v1` (defaults to 127.0.0.1)

All endpoints accept and return camelCase JSON automatically handled by the backend's `alias_generator=to_camel` and Flutter's `.fromJson` models.

## Endpoints

### 1. Health
`GET /health`
Returns service status, version, and environment.

### 2. Trips
`POST /trips/analyze`
**Request:** `TripRequest` (origin, destination, departure_time, mode)
**Response:** `TripResponse` (analysis_id, risk, route, recommendation, mode_options, hazards, sources, estimated_duration, distance_km)

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
`POST /assistant/parse`
**Request:** `AssistantParseRequest` (query: str)
**Response:** `AssistantParseResponse` (intent, is_complete, missing_fields, clarification_prompt)

*Note: All JSON keys use `camelCase` to directly match the Flutter client models.*
