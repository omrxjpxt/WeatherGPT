# Phase 24 — Implementation Plan & Production Deployment Roadmap

**Phase:** Phase 24 Release Readiness & Phase 25 Roadmap  
**Status:** Audit Completed; Awaiting Explicit Approval Before Any Code Changes

---

## 1. Audit Summary & Actionable Findings

Phase 24's live production smoke tests verified that the WeatherGPT system is functionally and architecturally sound, with:
- Zero critical runtime crashes
- Zero hardcoded location bugs in production request paths
- Full compliance with all 18 core architectural invariants
- Robust and truthful degradation during provider unavailability

No critical or high-severity code defects were discovered that require immediate emergency code mutations in Phase 24.

The following non-blocking maintenance and deployment items have been documented:

---

## 2. Documented Findings & Action Plans

### Finding FIND-24-1: Production Environment Credentials Configuration
- **Finding ID:** `FIND-24-1`
- **Severity:** `INFORMATIONAL`
- **Root Cause:** Local `.env` contains placeholder credentials (`GOOGLE_MAPS_API_KEY=your_google_maps_key_here`, `FIRESTORE_PROJECT_ID=""`), intentionally activating truthful degradation (`status: routing_unavailable`) and `MEMORY_MODE` during local development.
- **Action Plan (Deployment Checklist):**
  1. In production Cloud Run / Kubernetes secret manager:
     - Set `GOOGLE_MAPS_API_KEY` to an authorized Google Cloud API key with Routes API enabled.
     - Set `FIRESTORE_PROJECT_ID` and attach `GOOGLE_APPLICATION_CREDENTIALS` service account JSON.
     - Set `ENVIRONMENT="production"` to enforce strict production safeguards (no mock fallbacks, strict CORS origins).
- **Regression Risk:** None. The architecture already handles missing vs configured credentials cleanly.
- **Verification Command:**
  ```bash
  curl -s http://127.0.0.1:8000/api/v1/ready | jq .
  ```

### Finding FIND-24-2: NDMA SACHET Gateway Challenge Handling
- **Finding ID:** `FIND-24-2`
- **Severity:** `INFORMATIONAL`
- **Root Cause:** The public NDMA SACHET RSS feed periodically presents a web application firewall (WAF) cookie challenge resulting in HTTP 403. `SachetCapAlertProvider` already catches this and returns `[]` safely.
- **Action Plan (Phase 25):**
  1. Add an optional proxy / scraper gateway or alternative authoritative IMD RSS alert feed endpoint in `settings.sachet_feed_url`.
  2. Implement an automated fallback to IMD RSS when SACHET returns 403 consecutively.
- **Regression Risk:** Low.
- **Verification Command:**
  ```bash
  pytest backend/tests/unit/test_sachet_cap_provider.py
  ```

### Finding FIND-24-3: Python 3.10 and Gemini SDK Deprecation
- **Finding ID:** `FIND-24-3`
- **Severity:** `LOW`
- **Root Cause:** `google-generativeai` and `google-api-core` emit a `FutureWarning` because Python 3.10 reaches end-of-life on October 4, 2026.
- **Action Plan (Phase 25 Maintenance Cycle):**
  1. Upgrade backend Docker base image and virtual environment to `python:3.11-slim`.
  2. Migrate from `google.generativeai` to the new `google-genai` SDK in `backend/app/providers/llm/gemini.py`.
  3. Verify all prompt parsing, structured output schemas, and grounding validator tests under Python 3.11.
- **Exact Files to Modify in Phase 25:**
  - `backend/requirements.txt` / `backend/pyproject.toml`
  - `backend/app/providers/llm/gemini.py`
  - `Dockerfile` / CI workflow configurations
- **Regression Risk:** Medium (API signature changes in Google GenAI SDK). Must be isolated in Phase 25 with full test coverage.
- **Rollback Strategy:** Retain existing `GeminiLLMProvider` implementation behind a version flag until new SDK is verified.

---

## 3. Verification & Sign-off Checklist

Before transitioning from Phase 24 to production deployment:

- [x] Backend unit & integration tests pass: `240/240 passed`
- [x] Flutter analyzer reports zero issues: `0 issues found`
- [x] Flutter widget & unit tests pass: `71/71 passed`
- [x] Concurrency determinism verified: `100% bit-identical scores across 10x evaluations`
- [x] Readiness endpoint (`/api/v1/ready`) verified operational
- [x] Single-pass scenario simulation verified under 1,000ms
- [x] Truthful degradation verified under missing external keys
- [x] All 18 architectural invariants verified intact
- [ ] Explicit user sign-off obtained to conclude Phase 24 audit
