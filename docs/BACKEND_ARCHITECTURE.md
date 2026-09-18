# WeatherGPT Backend Architecture

## Overview
WeatherGPT is built on FastAPI and follows a clean architecture pattern. The application is divided into presentation (API routes), orchestration (Services), abstraction (Providers/Repositories), and business logic (Decision Engine).

## Module Responsibilities

- **API Routes (`app/api/routes`)**: Handle HTTP requests, perform Pydantic validation, and route to services.
- **Services (`app/services`)**: Orchestrate data gathering from providers, normalize data, and invoke the decision engine.
- **Providers (`app/providers`)**: Abstract external APIs (Weather, Routing, Traffic, Alerts, LLM, Hazard Relevance). For MVP, the Weather provider is live (Open-Meteo) with a graceful fallback wrapper, while the others use mock implementations.
- **Repositories (`app/repositories`)**: Handle persistence. Currently supports in-memory fallback for development if Firestore credentials are missing.
- **Decision Engine (`app/decision_engine`)**: Pure, deterministic module. Calculates risk, ranks scenarios, and applies alert overrides based on normalized input.
- **Hazard Provider/Repository:** Retrieves curated historical vulnerability hotspots (e.g., waterlogging underpasses) from a Mock or Firestore repository. These hotspots are passed to the decision engine.
- **Source Comparison Layer:** Compares the primary and secondary weather timelines using semantic and configured numerical thresholds (e.g. `TEMPERATURE_DIFF_THRESHOLD_C`). Returns an `AgreementStatus` that informs confidence, isolating failures so missing secondary data does not block the decision.

## Data Normalization Layer
To decouple the deterministic engine from external API quirks, all provider data is mapped to normalized internal models (`app/decision_engine/normalized_models.py`) before evaluation.

## Flutter Client Integration
The Flutter application strictly consumes the FastAPI endpoints via HTTP repositories.
- **Provider Provenance**: The UI renders provider names directly from the backend `DataSource` metadata. It does not hardcode provider names.
- **Partial Degradation**: The client distinguishes between backend failure, network timeout, and specific provider failure (e.g., routing unavailable vs. weather unavailable) using the typed `ApiException`.
- **Mock/Live Switching**: Controlled securely at the repository layer (`ApiConfig.mode`). All provider keys remain exclusively on the backend.

## Scenario Traceability
All trip analysis and scenario results are tagged with a unique `analysis_id` / `scenario_id`. This ID is persisted along with the input context and decision output for auditability and historical replay.

## Traffic Intelligence Integration
Traffic is treated as a first-class, provider-based input to the trip decision pipeline:
- **Provider Abstraction (`app/providers/traffic`)**: Abstract `TrafficProvider` with concrete implementations: `MockTrafficProvider`, `UnavailableTrafficProvider`, and `FallbackTrafficProvider`. Live providers (e.g. Google Routes Traffic / TomTom) can be plugged in without changing the service or engine.
- **Base Route Decoupling**: Traffic state is kept logically separate from the base route model (`NormalizedRouteSegment`). Route geometry and static timings are evaluated independently, allowing routing and traffic to fail or succeed in isolation.
- **Three Explicitly Separate Traffic Effects**:
  1. *Temporal Exposure Shift*: Segment delays push estimated arrival times downstream (`temporal_alignment.py`), ensuring that weather conditions are sampled at the exact time the traveler reaches each point.
  2. *Extended Environmental Exposure*: Extra delay spent in rain, extreme heat, or wind increases the segment's physical exposure duration via a bounded `temporal_multiplier` (`risk_model.py`).
  3. *Direct Congestion Risk Factor*: Heavy or severe congestion for motorized transport modes adds a distinct "Traffic Congestion" `RiskFactor` to the assessment without distorting underlying meteorological risk scores.
- **Duration Accounting**: Enforces the invariant `trafficAwareDuration = staticDuration + trafficDelay`. Delay is applied exactly once across the pipeline, strictly preventing double-counting.
- **Mock Provenance Enforcement**: `MockTrafficProvider` outputs `status = mock`, `provenance = "demo/mock"`, and `source_name = "Mock Traffic Provider (Demo)"`. Contradictory combinations (such as `status = live` with mock provenance) are rejected by model validators.

## Decision Engine Policies
The core logic resides in `app/decision_engine`. 

> [!IMPORTANT]
> The engine operates purely on **engineering assumptions** regarding mode exposure, risk aggregation (bottleneck vs. duration), geographic proximity (Haversine approximations), and precipitation scaling. These assumptions are fully isolated, explicitly documented, and configurable, allowing seamless replacement with **scientifically supported models** in future iterations without architectural rewrites.

> [!NOTE]
> **MVP Limitation:** External traffic uses deterministic mock calculations based on hour-of-day and transport mode (free-flow for walk/metro, delay for motorized during rush hours). Departure candidate search is constrained to deterministic `-30m` to `+45m` offsets. Alert geometry defaults to regional boundaries when exact polygons are missing.
