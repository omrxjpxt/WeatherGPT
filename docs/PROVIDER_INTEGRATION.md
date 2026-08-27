# WeatherGPT Provider Integration Strategy

## Provider Abstraction
All external data sources in WeatherGPT are hidden behind asynchronous Provider interfaces (e.g., `WeatherProvider`, `RoutingProvider`, `AlertProvider`). 
- **Decoupling**: The Decision Engine never interacts with raw provider JSON or API-specific structures.
- **Normalization**: Providers are strictly responsible for fetching external data and mapping it into the internal `Normalized...` Pydantic models (e.g., `NormalizedWeatherPoint`).

## Normalized Data Contracts
The single source of truth for the Decision Engine is `backend/app/decision_engine/normalized_models.py`.
- Any external data that cannot be mapped into these models must either be dropped or the internal model must be explicitly upgraded.
- Provider-specific quirks (e.g., WMO weather codes, OpenWeatherMap weather IDs) must be translated into generic internal formats (e.g., `condition="Heavy Rain"`).

## Source Priority
In the event of conflicting information or overlapping features, the system honors the following strict priority order:
1. **Authoritative Emergency/Official Alerts** (`UNAVAILABLE` for direct integration, `PLANNED` via secondary, `DEMO` via mock).
2. **Authoritative Official Forecast/Warning Data** where available.
3. **Primary Weather/Routing/Traffic Providers** (`VERIFIED` Open-Meteo & Google Routes, `UNAVAILABLE` Traffic).
4. **Derived WeatherGPT Calculations** (e.g., deterministic risk score aggregations).
5. **LLM-generated explanation** (`UNAVAILABLE` currently; The LLM explains the decision, but never makes or overrides the deterministic risk calculation).

## Live Providers Implementation

### Weather & Alerts: WeatherAPI [VERIFIED]
- **Status**: Implemented (`SECONDARY`)
- **Data Extracted**: Temperature, precipitation, humidity, wind, visibility, weather condition, active alerts.
- **Role**: Serves strictly as a secondary comparison source. If primary data (Open-Meteo) differs significantly (e.g. Temp diff > 5C), the confidence of the risk assessment is lowered.
- **Alerts**: Alerts are normalized but explicitly marked as `secondary`. They will **never** trigger the authoritative emergency override path.

### Weather: Open-Meteo [VERIFIED]
- **Status**: Implemented
- **Data Extracted**: `temperature_2m`, `precipitation`, `relative_humidity_2m`, `wind_speed_10m`, `wind_gusts_10m`, `visibility`, `weather_code`.
- **Visibility**: Uses explicit hourly physical visibility measurements from the API. We do not infer visibility solely from weather codes.
- **Precipitation**: Open-Meteo returns hourly accumulation in `mm`. The internal decision engine consumes this explicitly as `precipitation_mm` and treats it as an intensity proxy.
- **WMO Mapping**: Full WMO weather code mapping to string conditions is handled inside the provider adapter.
- **Attribution & Licensing**: Open-Meteo data is provided via their non-commercial free-tier API under the **CC BY 4.0** license. Any UI consuming this data must explicitly display attribution to Open-Meteo.

## Failure, Fallback & Timeout Behavior
Robustness is critical:
- **Timeouts**: Every external HTTP request must have a strict timeout (e.g., 5 seconds).
- **Retries**: Transient failures (e.g., 5xx errors, network timeouts) should trigger a brief exponential backoff retry.
- **Graceful Fallback**: If a primary provider fails completely, the system should log the error and degrade gracefully (e.g., fall back to `MockWeatherProvider` during development, or return a standardized error in production).

## Data Freshness & Caching
- **Freshness Logging**: Every provider must report the `last_updated` timestamp and the specific provider name so it can be passed to the frontend for provenance transparency.
- **Caching**: Future iterations will implement Redis/In-memory caching to prevent redundant API calls for identical locations and overlapping times.

## Configuration & Secrets
- **Secrets Management**: No API keys are hardcoded. All keys must be injected via environment variables (e.g., `.env` file read by `pydantic-settings`).
- **Provider Toggling**: The active provider for each domain (Mock vs Real) should be driven by configuration, not hardcoded instantiation.
