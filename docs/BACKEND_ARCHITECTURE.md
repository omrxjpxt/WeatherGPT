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

## Scenario Traceability
All trip analysis and scenario results are tagged with a unique `analysis_id` / `scenario_id`. This ID is persisted along with the input context and decision output for auditability and historical replay.

## Decision Engine Policies
The core logic resides in `app/decision_engine`. 

> [!IMPORTANT]
> The engine operates purely on **engineering assumptions** regarding mode exposure, risk aggregation (bottleneck vs. duration), geographic proximity (Haversine approximations), and precipitation scaling. These assumptions are fully isolated, explicitly documented, and configurable, allowing seamless replacement with **scientifically supported models** in future iterations without architectural rewrites.

> [!NOTE]
> **MVP Limitation:** External APIs are mocked. Departure candidate search is constrained to deterministic `-30m` to `+45m` offsets. Alert geometry defaults to regional boundaries when exact polygons are missing.
