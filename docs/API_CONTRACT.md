# API Contract

Prefix: `/api/v1`

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
- `isOverrideEligible`: bool (Determined by WeatherGPT internal policy, not the upstream provider)

### 6. Assistant
`POST /assistant/parse`
**Request:** `AssistantParseRequest` (query: str)
**Response:** `AssistantParseResponse` (intent, is_complete, missing_fields, clarification_prompt)

*Note: All JSON keys use `camelCase` to directly match the Flutter client models.*
