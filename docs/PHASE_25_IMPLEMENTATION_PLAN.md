# Phase 25 — Production Deployment & Runtime Validation Implementation Plan

**Phase:** Phase 25 Deployment & Validation  
**Status:** Plan Generated; Awaiting Explicit User Approval Before Code Mutations  
**Reference Audit:** [`docs/PHASE_25_PRODUCTION_DEPLOYMENT_AUDIT.md`](file:///Users/omgangwar/Documents/Projects/WeatherGPT/docs/PHASE_25_PRODUCTION_DEPLOYMENT_AUDIT.md)

---

## 1. Plan Objective & Execution Boundaries

The objective of Phase 25 is to transition WeatherGPT from locally verified production behavior into an externally deployable, containerized, and runtime-validated production release.

### Strict Execution Boundaries:
1. **Zero Architecture Redesign:** Preserve clean architecture, provider abstractions, and service boundaries.
2. **Sole Authority of Decision Engine:** Preserve pure deterministic risk scoring, risk tiers, route selection, and mode comparisons.
3. **Explanatory-Only LLM:** Preserve `GroundingValidator` defense and sanitized `DecisionFacts`.
4. **Zero Direct Firestore Access in Flutter:** Preserve backend-mediated persistence.
5. **No Synthetic Fallbacks in Production:** Retain strict degradation rules in `is_production`.
6. **No Speculative Dependency Upgrades:** Retain locked dependency requirements in `backend/pyproject.toml`.

---

## 2. Implementation Steps

### Step 1: Python 3.11 Runtime Migration
- **Objective:** Upgrade deployment runtime to Python 3.11 (matching `pyproject.toml: requires-python = ">=3.11"`) to eliminate the `google.api_core` Python 3.10 `FutureWarning`.
- **Implementation:**
  1. Upgrade local backend virtual environment `backend/venv` to Python 3.11.9 using system `/Library/Frameworks/Python.framework/Versions/3.11/bin/python3.11`.
  2. Install existing dependencies from `pyproject.toml`.
  3. Verify all 241 tests execute under Python 3.11 with 0 warnings.
- **Verification Command:**
  ```bash
  backend/venv/bin/python3 --version  # Must report Python 3.11.x
  PYTHONPATH=backend backend/venv/bin/pytest backend/tests -v
  ```

### Step 2: Production Containerization & Deployment Topology
- **Objective:** Provide a production-grade, secure, multi-stage container deployment specification.
- **Files to Add:**
  - `backend/Dockerfile`:
    - Base image: `python:3.11-slim`
    - Security: Non-root user (`appuser`, UID 10001)
    - Optimization: Multi-stage build separating build tools from runtime footprint
    - Health & Readiness: Built-in `HEALTHCHECK` querying `/api/v1/health`
    - Port: Exposes `PORT` (default 8000)
    - Entrypoint: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2`
  - `backend/.dockerignore`: Excludes `.git`, `.venv`, `__pycache__`, `.pytest_cache`, and local `.env`.
  - `docker-compose.yml`: Local staging and container validation orchestration.
- **Verification Command:**
  ```bash
  docker build -t weathergpt-backend:latest backend/
  ```

### Step 3: Flutter Production Configuration & Dart Defines
- **Objective:** Allow dynamic base URL injection via `--dart-define=API_BASE_URL=...` for staging, preview, and production builds without mutating code.
- **Files to Modify:**
  - `lib/core/api/api_config.dart`:
    - Update `ApiConfig.baseUrl` to check `const String.fromEnvironment('API_BASE_URL')` before falling back to `https://api.weathergpt.com/api/v1` in release mode or localhost in debug mode.
- **Verification Command:**
  ```bash
  flutter analyze
  flutter test
  ```

### Step 4: Production Smoke & Load Testing Suite
- **Objective:** Create an automated, repeatable production runtime verification suite.
- **Files to Add:**
  - `backend/tests/production/test_production_runtime.py`:
    - Tests `/api/v1/health` liveness (HTTP 200, <50ms)
    - Tests `/api/v1/ready` readiness (HTTP 200, all 7 dependency checks)
    - Tests concurrent request bursts (20 concurrent trip analyses)
    - Tests rate limiting enforcement (HTTP 429 and Retry-After header)
    - Tests proxy anti-spoofing (`X-Forwarded-For` from untrusted proxy)
    - Tests truthful degradation (missing Google Maps key triggers `routing_unavailable` with no mock fallback)

---

## 3. Regression Gates

Before declaring Phase 25 complete, the following gates must pass:

1. **Python 3.11 Backend Suite:**
   ```bash
   PYTHONPATH=backend backend/venv/bin/pytest backend/tests
   ```
   **Requirement:** All 241+ tests passing with **0 failures and 0 warnings**.

2. **Flutter Static Analysis:**
   ```bash
   flutter analyze
   ```
   **Requirement:** **0 issues found**.

3. **Flutter Test Suite:**
   ```bash
   flutter test
   ```
   **Requirement:** All 71+ tests passing with **0 failures**.

4. **10x Concurrency Determinism:**
   ```bash
   PYTHONPATH=backend backend/venv/bin/pytest backend/tests/unit/test_concurrency_determinism.py -v
   ```
   **Requirement:** 100% bit-identical scores across 10 repeated concurrent runs.

5. **Container Build Verification:**
   ```bash
   docker build -t weathergpt-backend:v1 backend/
   ```
   **Requirement:** Clean multi-stage build under Python 3.11.

---

## 4. Rollback Strategy

- If Python 3.11 introduces any package incompatibility on the local host, `backend/venv` can be re-created with Python 3.10 within seconds.
- In `ApiConfig`, the fallback logic preserves exact existing behavior when `--dart-define=API_BASE_URL` is omitted.
- Containerization artifacts (`Dockerfile`, `docker-compose.yml`) are purely additive and do not affect the local developer workflow.
