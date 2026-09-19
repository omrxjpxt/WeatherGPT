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

## Route Alternative Evaluation Architecture
The system evaluates multiple route alternatives returned by the routing provider using the same deterministic decision engine:
- **Orchestration Layer (`app/decision_engine/route_evaluator.py`)**: `RouteEvaluator` acts solely as an orchestration coordinator. It does NOT duplicate risk formulas, weights, or decision engine logic. Each route alternative is passed independently to `DecisionEngine.evaluate_route_core`.
- **N+1 Traffic Call Prevention**: If the routing provider (e.g., Google Routes) already provides verified traffic-aware duration and static duration data on the returned route alternatives, the pipeline normalizes and reuses that embedded data directly. An external `TrafficProvider` is only invoked when traffic information is not already present.
- **Strict 6-Step Selection Policy**: Evaluates feasibility against `arrival_deadline`, filters hard emergency avoidance alerts vs advisories, checks risk tiers, evaluates score differences ($\ge 15$ vs $< 15$), and breaks ties via exposure score, distance, and route ID.
- **Backward Compatibility**: Single routes remain fully supported without fabricated alternatives. Payloads with empty or absent `routes` deserialize seamlessly.
- **Separation of Concerns**: Recommendation selection is purely backend-driven (`is_selected`). Flutter client UI inspection is strictly decoupled (`activeRouteId`).

## LLM Intent & Explanation Architecture
The Large Language Model (LLM) is strictly integrated as an interface and natural language translation layer only. It possesses **zero authority** over safety-critical calculations or route choices.

### Core Principles
1. **Decision Engine Authority**: The deterministic Decision Engine remains the sole authority for risk scores, route feasibility, route ranking, mode comparisons, and alert overrides. The LLM must NEVER:
   - Calculate or alter risk scores
   - Select or change routes or `selectedRouteId`
   - Override or invent official emergency alerts
   - Fabricate weather, traffic, or provider availability
2. **Unified Pipeline for Voice and Text**: Both typed text and voice transcripts flow through the identical pipeline:
   ```
   User Text / Voice Transcript
               ↓
        AssistantService
               ↓
        ExtractedIntent (controlled UserIntentEnum)
               ↓
   Backend-Deterministic Completeness Validation
               ↓
        TripRequest (if trip_decision & valid)
               ↓
        TripService (authoritative evaluation)
               ↓
        DecisionFacts (sanitized factual payload)
               ↓
      LLM generate_explanation()
               ↓
     GroundingValidator (reject unsupported claims)
               ↓
   Accepted Explanation OR Deterministic Grounded Fallback
               ↓
     AssistantChatResponse
   ```
3. **Deterministic Grounding Validator (`GroundingValidator`)**: Explanations generated by the LLM are passed to `GroundingValidator` before being returned to the client. The validator verifies that the generated text introduces no unsupported facts:
   - No fabricated numeric risk scores (must match `facts.risk_score` if present)
   - No invented traffic delays (must match `facts.traffic_delay_minutes` within tolerance)
   - No invented route names (must match `facts.selected_route_summary` or `available_routes`)
   - No invented alerts or evacuation claims (must match `facts.active_alerts`)
   - No claims contradicting `TripStatus` (e.g. claiming a clear route when routing or weather is unavailable)
   If validation fails, a 100% grounded fallback explanation is automatically constructed from `DecisionFacts`.
4. **Controlled User Intents**: `UserIntentEnum` defines controlled values: `trip_decision`, `weather_question`, `route_comparison`, `what_if`, `alert_question`, `general_weather`. Non-trip questions are answered directly and are never forced through `TripService`.
5. **Backend-Deterministic Clarification**: The LLM extracts candidate fields (`origin`, `destination`, `mode`, `departure_time`), but `AssistantService` deterministically decides whether a valid `TripRequest` can actually be constructed. Missing required fields trigger `status = "need_clarification"` with a targeted prompt and `trip_response = None` without calling `TripService`.
6. **Provider Abstraction**: `AssistantService` depends purely on abstract `LLMProvider`. Concrete providers include `MockLLMProvider` (deterministic pattern parsing for English/Hindi/Hinglish, labeled `provider_name = "Mock LLM Provider"`, `provenance = "demo/mock"`) and `GeminiLLMProvider` (Google GenAI adapter awaiting production API credentials). No provider-specific logic leaks into `AssistantService`.
7. **Strict Response Semantics**:
   - `need_clarification`: `trip_response = null`, no `TripService` execution.
   - `success`: Authoritative `TripResponse` attached.
   - `degraded`: Provider limitations reflected (e.g. routing unavailable); no fabricated results.
   - `error`: Clean error message; no fabricated trip result.

## Decision Engine Policies
The core logic resides in `app/decision_engine`. 

> [!IMPORTANT]
> The engine operates purely on **engineering assumptions** regarding mode exposure, risk aggregation (bottleneck vs. duration), geographic proximity (Haversine approximations), and precipitation scaling. These assumptions are fully isolated, explicitly documented, and configurable, allowing seamless replacement with **scientifically supported models** in future iterations without architectural rewrites.

> [!NOTE]
> **MVP Limitation:** External traffic uses deterministic mock calculations based on hour-of-day and transport mode (free-flow for walk/metro, delay for motorized during rush hours). Departure candidate search is constrained to deterministic `-30m` to `+45m` offsets. Alert geometry defaults to regional boundaries when exact polygons are missing.

## Persistence & Audit Architecture (Phase 17)
Data persistence uses Firebase Firestore solely as a backend-mediated audit and history layer, adhering strictly to **ADR-002**.

### Core Constraints
1. **Firestore is Persistence Only**: Firestore MUST NEVER participate in risk calculation, route selection, alert evaluation, traffic assessment, or recommendations. The deterministic Decision Engine remains authoritative.
2. **Backend-Mediated Interaction**: The Flutter client has ZERO direct access to Firestore. All persistence is managed by FastAPI using the `firebase-admin` SDK. This centralizes security and prevents client-side logic fragmentation.
3. **Non-Blocking Write Strategy**: To ensure highly responsive decisions, all write operations (`TripRepository.save_trip_decision`, `ConversationRepository.save_message`) are executed asynchronously via `asyncio.create_task` fire-and-forget mechanisms in the service layer (`TripService`, `AssistantService`). DB latency or transient failures will never block a trip assessment.
4. **Data Isolation**: User requests are authenticated via Bearer tokens extracted by `app.api.auth.get_current_user`. The FastAPI dependency passes the `uid` explicitly to repository calls, securely isolating user records under `users/{uid}/*` paths.

### Memory Mode Fallback
To ensure seamless local development and integration testing without requiring service account credentials, all Firestore-backed repositories gracefully fallback to `MEMORY_MODE` if `settings.firestore_project_id` is missing. 
- In `MEMORY_MODE`, repositories utilize in-memory dictionaries.
- Data structures emulate Firestore behavior, including synthetic timestamps for accurate sorting logic.
- Log warnings are emitted on application start notifying developers that data will be lost on restart.

## Client Authentication & Persistence Boundary (Phase 18)
The boundary between the Flutter client and the backend persistence layer follows strict principles:
- **Client Role**: Flutter uses Firebase Auth solely to retrieve Firebase ID tokens, which are attached as `Authorization: Bearer <token>` on HTTP requests via `ApiClient`.
- **FastAPI Role**: FastAPI decodes and verifies the ID token (`get_authenticated_user` / `get_optional_current_user`), enforces user scoping, and accesses Firestore (or Memory Mode).
- **Client Zero Direct Firestore Rule**: Flutter has NO direct dependency on `cloud_firestore` and performs no direct database operations.
- **Decision Engine Isolation**: The Decision Engine remains 100% agnostic to user identity, authentication state, or stored routes. Saved routes act solely as bookmarks for subsequent public trip analysis requests.

## Production Integration & Hardening (Phase 19)
The system is hardened against failures across all integration boundaries:
- **Persistence Failure Isolation**: In `TripService` and `AssistantService`, fire-and-forget database writes are wrapped in safe error isolation routines (`_safe_persist` and `_safe_save_message`). Any database timeout, network disconnect, or Firestore exception is logged without interrupting, altering, or delaying the user's trip evaluation or assistant chat response.
- **Authentication Hardening**: `get_authenticated_user` strictly returns HTTP 401 on missing, expired, or malformed Bearer tokens. Client payload UIDs are forcibly overridden by verified token claims (`profile.uid = uid`) to eliminate UID spoofing and preserve cross-user isolation.
- **Degradation Resilience Matrix**: Missing upstream providers (routing, weather, traffic, hazards, LLM) gracefully produce typed degraded responses (`TripStatus.routing_unavailable`, `TripStatus.weather_unavailable`, `TrafficStatus.unavailable`) without throwing 500 errors or returning hallucinated data.


