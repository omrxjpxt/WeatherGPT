import pytest
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from app.main import app
from app.models.enums import TransportMode, RiskLevel
from app.api.dependencies import get_trip_service
from app.services.trip_service import TripService
from app.providers.weather.mock import MockWeatherProvider
from app.providers.routing.mock import MockRoutingProvider
from app.providers.alerts.mock import MockAlertProvider
from app.providers.traffic.mock import MockTrafficProvider
from app.providers.air_quality.mock import MockAirQualityProvider


@pytest.fixture(autouse=True)
def override_trip_service():
    mock_weather = MockWeatherProvider()
    trip_svc = TripService(
        weather_provider=mock_weather,
        routing_provider=MockRoutingProvider(),
        alert_provider=MockAlertProvider(),
        traffic_provider=MockTrafficProvider(),
        air_quality_provider=MockAirQualityProvider(),
    )
    app.dependency_overrides[get_trip_service] = lambda: trip_svc
    yield trip_svc
    app.dependency_overrides.pop(get_trip_service, None)


@pytest.mark.asyncio
async def test_single_pass_trip_analysis_returns_mode_options():
    """Verify that a single /trips/analyze request returns populated mode_options for all target modes."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/trips/analyze",
            json={
                "origin": "Noida Sector 62",
                "destination": "Gurgaon Cyber Hub",
                "departureTime": "2026-08-27T08:00:00Z",
                "mode": "car",
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "modeOptions" in data or "mode_options" in data
    mode_options = data.get("modeOptions") or data.get("mode_options")
    assert len(mode_options) >= 3

    modes = [opt["mode"] for opt in mode_options]
    assert "bike" in modes
    assert "car" in modes
    assert "metro" in modes


@pytest.mark.asyncio
async def test_each_mode_has_independent_deterministic_calculations():
    """Verify that each mode has independently calculated risk, duration, and recommendations from Decision Engine."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/trips/analyze",
            json={
                "origin": "Noida Sector 62",
                "destination": "Gurgaon Cyber Hub",
                "departureTime": "2026-08-27T08:00:00Z",
                "mode": "car",
            },
        )

    assert resp.status_code == 200
    mode_options = resp.json().get("modeOptions") or resp.json().get("mode_options")
    by_mode = {opt["mode"]: opt for opt in mode_options}

    car_opt = by_mode["car"]
    bike_opt = by_mode["bike"]
    metro_opt = by_mode["metro"]

    # Durations must reflect mode speeds (bike slower than car on long trip)
    assert bike_opt["estimatedDuration"] != car_opt["estimatedDuration"]

    # Each mode must have risk assessments
    assert car_opt["risk"] is not None
    assert bike_opt["risk"] is not None
    assert metro_opt["risk"] is not None

    # Recommendations must be populated
    assert car_opt["recommendation"] is not None
    assert bike_opt["recommendation"] is not None
    assert metro_opt["recommendation"] is not None


@pytest.mark.asyncio
async def test_provider_calls_not_triplicated(override_trip_service):
    """Verify that external weather and air quality are NOT called 3x for multi-mode comparison."""
    orig_get_forecast = override_trip_service.weather_provider.get_forecast
    spy = AsyncMock(side_effect=orig_get_forecast)
    override_trip_service.weather_provider.get_forecast = spy

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/trips/analyze",
            json={
                "origin": "Noida Sector 62",
                "destination": "Gurgaon Cyber Hub",
                "departureTime": "2026-08-27T08:00:00Z",
                "mode": "bike",
            },
        )

    assert resp.status_code == 200
    # Primary weather provider should be called at most once per trip analysis, NOT 3 times
    assert spy.call_count == 1


@pytest.mark.asyncio
async def test_trip_analysis_with_metro_as_primary():
    """Verify that when metro is requested as primary, mode_options still contains bike and car."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/trips/analyze",
            json={
                "origin": "Noida Sector 62",
                "destination": "Gurgaon Cyber Hub",
                "departureTime": "2026-08-27T08:00:00Z",
                "mode": "metro",
            },
        )

    assert resp.status_code == 200
    mode_options = resp.json().get("modeOptions") or resp.json().get("mode_options")
    modes = [opt["mode"] for opt in mode_options]
    assert "metro" in modes
    assert "car" in modes
    assert "bike" in modes
