# WeatherGPT Backend Architecture

## Overview
WeatherGPT is built on FastAPI and follows a clean architecture pattern. The application is divided into presentation (API routes), orchestration (Services), abstraction (Providers/Repositories), and business logic (Decision Engine).

## Module Responsibilities

- **API Routes (`app/api/routes`)**: Handle HTTP requests, perform Pydantic validation, and route to services.
- **Services (`app/services`)**: Orchestrate data gathering from providers, normalize data, and invoke the decision engine.
- **Providers (`app/providers`)**: Abstract external APIs (Weather, Routing, Traffic, Alerts, LLM). For MVP, these use mock implementations.
- **Repositories (`app/repositories`)**: Handle persistence. Currently supports in-memory fallback for development if Firestore credentials are missing.
- **Decision Engine (`app/decision_engine`)**: Pure, deterministic module. Calculates risk, ranks scenarios, and applies alert overrides based on normalized input.

## Data Normalization Layer
To decouple the deterministic engine from external API quirks, all provider data is mapped to normalized internal models (`app/decision_engine/normalized_models.py`) before evaluation.

## Scenario Traceability
All trip analysis and scenario results are tagged with a unique `analysis_id` / `scenario_id`. This ID is persisted along with the input context and decision output for auditability and historical replay.
