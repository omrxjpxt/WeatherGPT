import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import settings
from app.core.rate_limiter import rate_limiter


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    rate_limiter.reset()
    yield
    rate_limiter.reset()


@pytest.mark.asyncio
async def test_rate_limiter_allows_requests_under_threshold():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # First request to expensive weather endpoint
        res = await client.get("/api/v1/weather/current?lat=28.627&lng=77.365")
        assert res.status_code == 200


@pytest.mark.asyncio
async def test_rate_limiter_blocks_anonymous_when_limit_exceeded():
    # Set a temporarily low threshold for anonymous requests
    original_limit = settings.rate_limit_per_minute_anonymous
    try:
        settings.rate_limit_per_minute_anonymous = 2

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Request 1: allowed
            r1 = await client.get("/api/v1/weather/current?lat=28.627&lng=77.365")
            assert r1.status_code == 200

            # Request 2: allowed
            r2 = await client.get("/api/v1/weather/current?lat=28.627&lng=77.365")
            assert r2.status_code == 200

            # Request 3: rate limited -> HTTP 429
            r3 = await client.get("/api/v1/weather/current?lat=28.627&lng=77.365")
            assert r3.status_code == 429
            assert "Rate limit exceeded" in r3.json()["detail"]
            assert "Retry-After" in r3.headers
            assert int(r3.headers["Retry-After"]) >= 1
    finally:
        settings.rate_limit_per_minute_anonymous = original_limit


@pytest.mark.asyncio
async def test_rate_limiter_authenticated_users_have_higher_tier():
    original_anon = settings.rate_limit_per_minute_anonymous
    original_auth = settings.rate_limit_per_minute_authenticated
    try:
        settings.rate_limit_per_minute_anonymous = 2
        settings.rate_limit_per_minute_authenticated = 5

        headers = {"Authorization": "Bearer mock-user-premium"}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 3 requests with auth token (above anonymous limit of 2, below auth limit of 5)
            for _ in range(3):
                r = await client.get("/api/v1/weather/current?lat=28.627&lng=77.365", headers=headers)
                assert r.status_code == 200
    finally:
        settings.rate_limit_per_minute_anonymous = original_anon
        settings.rate_limit_per_minute_authenticated = original_auth


@pytest.mark.asyncio
async def test_rate_limiter_protects_scenarios_and_alerts():
    """Verify that /api/v1/scenarios/evaluate and /api/v1/alerts/ are covered by rate limiting."""
    original_limit = settings.rate_limit_per_minute_anonymous
    try:
        settings.rate_limit_per_minute_anonymous = 1

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Request 1 to alerts: allowed
            r1 = await client.get("/api/v1/alerts/?lat=28.6&lng=77.3")
            assert r1.status_code == 200

            # Request 2 to alerts: blocked by rate limiter
            r2 = await client.get("/api/v1/alerts/?lat=28.6&lng=77.3")
            assert r2.status_code == 429
            assert "Rate limit exceeded" in r2.json()["detail"]

        rate_limiter.reset()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            payload = {
                "request": {
                    "origin": "Noida Sector 62",
                    "destination": "Gurgaon Cyber Hub",
                    "departureTime": "2026-08-27T08:00:00Z",
                    "mode": "bike",
                },
                "departure_times": ["2026-08-27T08:00:00Z"],
            }
            # Request 1 to scenarios: allowed
            r3 = await client.post("/api/v1/scenarios/evaluate", json=payload)
            assert r3.status_code == 200

            # Request 2 to scenarios: blocked
            r4 = await client.post("/api/v1/scenarios/evaluate", json=payload)
            assert r4.status_code == 429
    finally:
        settings.rate_limit_per_minute_anonymous = original_limit
