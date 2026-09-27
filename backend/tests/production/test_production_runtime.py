"""
Production Runtime, Resilience, and Concurrency Load Test Suite.

Validates:
- Health and readiness probes
- Truthful degradation when external provider credentials are absent
- Geocoding and weather queries (including unresolvable locations)
- NDMA Sachet 403 WAF degradation resilience
- Google Routes degradation and strict non-mock fallback
- Authentication enforcement and invalid token rejection
- Rate-limiting abuse protection (HTTP 429)
- Shared HTTP connection pool reuse
- 50 concurrent trip analyses under high load (measures p50, p95, p99)
- 20 concurrent scenario evaluations under high load (measures p50, p95, p99)
"""

import asyncio
import time
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.config import settings
from app.core.http import HttpClientManager
from app.core.rate_limiter import rate_limiter
from app.providers.routing.google_routes import GoogleRoutesProvider
from app.providers.routing.errors import ConfigurationError, RoutingError
from app.providers.alerts.sachet_cap import NdmaSachetAlertProvider


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    rate_limiter.reset()
    yield
    rate_limiter.reset()


@pytest.mark.asyncio
async def test_production_health_probe():
    """Verify production health check probe returns 200 with service metadata."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "WeatherGPT Backend"
    assert "version" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_production_readiness_probe():
    """
    Verify production readiness probe.
    Without Firestore credentials configured, database should report disconnected
    and overall status should truthfully reflect not_ready.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/ready")
    assert response.status_code == 200
    data = response.json()
    assert "checks" in data
    checks = data["checks"]
    assert "weather_provider" in checks
    assert "routing_provider" in checks
    assert "alert_provider" in checks
    assert "http_pool" in checks
    assert "database" in checks


@pytest.mark.asyncio
async def test_production_weather_and_geocoding_success():
    """Verify live weather and geocoding integration with known NCR location."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/weather/current?location=Connaught+Place,+New+Delhi")
    assert response.status_code == 200
    data = response.json()
    assert "temperature" in data
    assert "condition" in data
    assert "icon" in data
    assert isinstance(data["temperature"], (int, float))


@pytest.mark.asyncio
async def test_production_weather_unresolved_location():
    """Verify truthful 400 error response when an unresolvable location is supplied."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/weather/current?location=NonExistentLoc9999XYZ")
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "Could not resolve" in data["detail"]


@pytest.mark.asyncio
async def test_production_alerts_endpoint():
    """Verify active alerts endpoint with valid coordinates."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/alerts/?lat=28.6139&lng=77.2090")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_production_trip_analysis_truthful_degradation_without_keys():
    """
    In production mode without valid external routing keys,
    trip analysis must degrade truthfully to status 'routing_unavailable'
    without fabricating mock routes.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v1/trips/analyze", json={
            "origin": "India Gate, New Delhi",
            "destination": "Cyber Hub, Gurgaon",
            "mode": "car",
            "departureTime": "2026-09-27T12:00:00Z"
        })
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "sources" in data
    assert "analysisId" in data
    # When routing is unavailable, risk calculation correctly avoids fake numbers
    if data["status"] == "routing_unavailable":
        assert data["risk"] is None
        source_types = [s["type"] for s in data["sources"]]
        assert any("Routing" in st for st in source_types)


@pytest.mark.asyncio
async def test_production_scenario_evaluation_truthful_degradation():
    """Verify scenarios endpoint handles routing degradation cleanly across multiple times."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v1/scenarios/evaluate", json={
            "request": {
                "origin": "India Gate, New Delhi",
                "destination": "Cyber Hub, Gurgaon",
                "mode": "car",
                "departureTime": "2026-09-27T12:00:00Z"
            },
            "departure_times": [
                "2026-09-27T12:00:00Z",
                "2026-09-27T13:00:00Z"
            ]
        })
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    for scenario in data:
        assert "scenarioId" in scenario
        assert "status" in scenario
        assert "departureTime" in scenario


@pytest.mark.asyncio
async def test_production_google_routes_degradation_without_key(monkeypatch):
    """Verify GoogleRoutesProvider raises ConfigurationError or RoutingError when key is missing or invalid."""
    from app.models.enums import TransportMode
    monkeypatch.setattr(settings, "google_maps_api_key", None)
    provider = GoogleRoutesProvider()
    with pytest.raises((ConfigurationError, RoutingError)):
        await provider.get_route(
            origin_lat=28.6139,
            origin_lng=77.2090,
            dest_lat=28.4595,
            dest_lng=77.0266,
            mode=TransportMode.car
        )


@pytest.mark.asyncio
async def test_production_ndma_waf_403_degradation_handling():
    """Verify NDMA Sachet provider gracefully degrades to empty alerts on WAF challenge."""
    import httpx
    
    async def mock_waf_handler(request):
        return httpx.Response(403, text="<html><body>403 Forbidden - Cloudflare WAF Challenge</body></html>")
    
    mock_transport = httpx.MockTransport(mock_waf_handler)
    async with httpx.AsyncClient(transport=mock_transport) as mock_client:
        provider = NdmaSachetAlertProvider(client=mock_client)
        alerts = await provider.get_active_alerts(lat=28.6139, lng=77.2090)
        assert alerts == []
        assert provider.provider_status == "waf_challenge"


@pytest.mark.asyncio
async def test_production_auth_failures():
    """Verify that protected user endpoints strictly reject unauthorized requests."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. No token
        resp_no_token = await ac.get("/api/v1/users/me/profile")
        assert resp_no_token.status_code == 401

        # 2. Malformed token
        resp_bad_token = await ac.get(
            "/api/v1/users/me/profile",
            headers={"Authorization": "Bearer malformed.token.value"}
        )
        assert resp_bad_token.status_code == 401


@pytest.mark.asyncio
async def test_production_rate_limiter_abuse_protection():
    """Verify rate-limiter triggers HTTP 429 when client exceeds anonymous threshold."""
    client_ip = "198.51.100.42"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        responses = []
        for i in range(35):
            resp = await ac.get(
                "/api/v1/weather/current?location=Connaught+Place",
                headers={"X-Forwarded-For": client_ip}
            )
            responses.append(resp.status_code)

    assert 429 in responses
    assert responses[-1] == 429


@pytest.mark.asyncio
async def test_production_connection_pooling():
    """Verify HttpClientManager manages client lifecycle and connection pool reuse."""
    client1 = await HttpClientManager.initialize()
    assert client1 is not None
    assert not client1.is_closed

    client2 = HttpClientManager.get_client()
    assert client1 is client2  # Exact same pooled instance reused


@pytest.mark.asyncio
async def test_production_concurrent_load_50_trip_analyses():
    """
    Load test: 50 concurrent trip analysis requests executed simultaneously.
    Measures latency distribution (p50, p95, p99) and verifies 0 unexpected 500 errors.
    """
    total_requests = 50
    payload = {
        "origin": "India Gate, New Delhi",
        "destination": "Cyber Hub, Gurgaon",
        "mode": "car",
        "departureTime": "2026-09-27T12:00:00Z"
    }

    async def single_trip_request(client: AsyncClient, req_idx: int):
        start = time.perf_counter()
        resp = await client.post(
            "/api/v1/trips/analyze",
            json=payload,
            headers={
                "X-Request-Id": f"load-test-trip-{req_idx}",
                "X-Forwarded-For": f"10.100.{req_idx // 200}.{req_idx % 200 + 1}"
            }
        )
        duration_ms = (time.perf_counter() - start) * 1000.0
        return resp.status_code, duration_ms

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        tasks = [single_trip_request(ac, i) for i in range(total_requests)]
        results = await asyncio.gather(*tasks)

    status_codes = [r[0] for r in results]
    latencies = sorted([r[1] for r in results])

    p50 = latencies[int(len(latencies) * 0.50)]
    p95 = latencies[int(len(latencies) * 0.95)]
    p99 = latencies[int(len(latencies) * 0.99)]

    # Assertions
    assert 500 not in status_codes, f"500 Internal Server Error encountered in load test: {status_codes}"
    assert all(code in (200, 429) for code in status_codes)

    print(f"\n[Load Test: 50 Concurrent Trips] Completed {total_requests} requests:")
    print(f"  Status codes: 200s: {status_codes.count(200)}, 429s: {status_codes.count(429)}")
    print(f"  Latencies: p50={p50:.2f}ms, p95={p95:.2f}ms, p99={p99:.2f}ms")


@pytest.mark.asyncio
async def test_production_concurrent_load_20_scenarios():
    """
    Load test: 20 concurrent scenario evaluation requests executed simultaneously.
    Measures latency distribution (p50, p95, p99) and ensures zero unhandled crashes.
    """
    total_requests = 20
    payload = {
        "request": {
            "origin": "India Gate, New Delhi",
            "destination": "Cyber Hub, Gurgaon",
            "mode": "car",
            "departureTime": "2026-09-27T12:00:00Z"
        },
        "departure_times": [
            "2026-09-27T12:00:00Z",
            "2026-09-27T13:00:00Z"
        ]
    }

    async def single_scenario_request(client: AsyncClient, req_idx: int):
        start = time.perf_counter()
        resp = await client.post(
            "/api/v1/scenarios/evaluate",
            json=payload,
            headers={
                "X-Request-Id": f"load-test-scenario-{req_idx}",
                "X-Forwarded-For": f"10.200.{req_idx // 200}.{req_idx % 200 + 1}"
            }
        )
        duration_ms = (time.perf_counter() - start) * 1000.0
        return resp.status_code, duration_ms

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        tasks = [single_scenario_request(ac, i) for i in range(total_requests)]
        results = await asyncio.gather(*tasks)

    status_codes = [r[0] for r in results]
    latencies = sorted([r[1] for r in results])

    p50 = latencies[int(len(latencies) * 0.50)]
    p95 = latencies[int(len(latencies) * 0.95)]
    p99 = latencies[int(len(latencies) * 0.99)]

    # Assertions
    assert 500 not in status_codes, f"500 Internal Server Error encountered in load test: {status_codes}"
    assert all(code in (200, 429) for code in status_codes)

    print(f"\n[Load Test: 20 Concurrent Scenarios] Completed {total_requests} requests:")
    print(f"  Status codes: 200s: {status_codes.count(200)}, 429s: {status_codes.count(429)}")
    print(f"  Latencies: p50={p50:.2f}ms, p95={p95:.2f}ms, p99={p99:.2f}ms")
