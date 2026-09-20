import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock
from datetime import datetime, timezone

from app.main import app
from app.api.dependencies import get_weather_provider
from app.decision_engine.normalized_models import NormalizedWeatherPoint
from app.providers.weather.base import WeatherProvider


@pytest.fixture
def mock_weather_point():
    return NormalizedWeatherPoint(
        time=datetime(2026, 8, 27, 8, 0, tzinfo=timezone.utc),
        temperature=31.5,
        precipitation_mm=0.0,
        humidity=65.0,
        wind_speed=12.0,
        wind_gusts=18.0,
        visibility=8000.0,
        condition="Clear",
        is_extreme_heat=False,
        is_poor_visibility=False,
        is_stale=False,
    )


class SpyWeatherProvider(WeatherProvider):
    def __init__(self, return_point):
        self.return_point = return_point
        self.calls = []

    @property
    def provider_name(self) -> str:
        return "spy-weather"

    async def get_forecast(self, lat: float, lng: float, start_time: datetime, hours: int):
        self.calls.append({"lat": lat, "lng": lng, "start_time": start_time, "hours": hours})
        return [self.return_point] * hours


@pytest.mark.asyncio
async def test_weather_current_gurgaon_cyber_hub(mock_weather_point):
    """Verify that 'Gurgaon Cyber Hub' resolves to Gurgaon coordinates and returns localized weather."""
    spy = SpyWeatherProvider(mock_weather_point)
    app.dependency_overrides[get_weather_provider] = lambda: spy
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/weather/current", params={"location": "Gurgaon Cyber Hub"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["temperature"] == 31.5
        assert data["condition"] == "Clear"
        assert len(spy.calls) == 1

        called_lat, called_lng = spy.calls[0]["lat"], spy.calls[0]["lng"]
        # Cyber hub latitude ~ 28.4942, longitude ~ 77.0860
        assert abs(called_lat - 28.4942) < 0.05
        assert abs(called_lng - 77.0860) < 0.05
    finally:
        app.dependency_overrides.pop(get_weather_provider, None)


@pytest.mark.asyncio
async def test_weather_current_delhi_location(mock_weather_point):
    """Verify that a Delhi location ('Connaught Place') resolves and queries weather for Delhi."""
    spy = SpyWeatherProvider(mock_weather_point)
    app.dependency_overrides[get_weather_provider] = lambda: spy
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/weather/current", params={"location": "Connaught Place"})

        assert resp.status_code == 200
        assert len(spy.calls) == 1
        called_lat, called_lng = spy.calls[0]["lat"], spy.calls[0]["lng"]
        # Connaught Place: 28.6315, 77.2167
        assert abs(called_lat - 28.6315) < 0.05
        assert abs(called_lng - 77.2167) < 0.05
    finally:
        app.dependency_overrides.pop(get_weather_provider, None)


@pytest.mark.asyncio
async def test_weather_current_noida_location(mock_weather_point):
    """Verify that 'Noida Sector 62' resolves to Noida coordinates."""
    spy = SpyWeatherProvider(mock_weather_point)
    app.dependency_overrides[get_weather_provider] = lambda: spy
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/weather/current", params={"location": "Noida Sector 62"})

        assert resp.status_code == 200
        assert len(spy.calls) == 1
        called_lat, called_lng = spy.calls[0]["lat"], spy.calls[0]["lng"]
        # Sector 62 Noida: 28.6270, 77.3650
        assert abs(called_lat - 28.6270) < 0.05
        assert abs(called_lng - 77.3650) < 0.05
    finally:
        app.dependency_overrides.pop(get_weather_provider, None)


@pytest.mark.asyncio
async def test_weather_forecast_with_location(mock_weather_point):
    """Verify that /forecast endpoint accepts location text and hours."""
    spy = SpyWeatherProvider(mock_weather_point)
    app.dependency_overrides[get_weather_provider] = lambda: spy
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/weather/forecast", params={"location": "Indirapuram", "hours": 12})

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 12
        assert len(spy.calls) == 1
        assert spy.calls[0]["hours"] == 12
    finally:
        app.dependency_overrides.pop(get_weather_provider, None)


@pytest.mark.asyncio
async def test_weather_invalid_unresolvable_location():
    """Verify that an unresolvable query returns a truthful error without falling back to Noida."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/weather/current", params={"location": "NonExistentPlace_998877_Fake"})

    assert resp.status_code == 400
    data = resp.json()
    assert data["status"] == "unresolved_location"
    assert "could not resolve" in data["detail"].lower()


@pytest.mark.asyncio
async def test_weather_coordinate_queries(mock_weather_point):
    """Verify that direct lat/lng params and coordinate strings work seamlessly."""
    spy = SpyWeatherProvider(mock_weather_point)
    app.dependency_overrides[get_weather_provider] = lambda: spy
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 1. Direct lat/lng params
            resp1 = await client.get("/api/v1/weather/current", params={"lat": 28.5000, "lng": 77.1000})
            assert resp1.status_code == 200
            assert abs(spy.calls[0]["lat"] - 28.5000) < 0.001

            # 2. Location param as coordinate string
            resp2 = await client.get("/api/v1/weather/current", params={"location": "28.5200, 77.2100"})
            assert resp2.status_code == 200
            assert abs(spy.calls[1]["lat"] - 28.5200) < 0.001

            # 3. Missing both location and coordinates
            resp3 = await client.get("/api/v1/weather/current")
            assert resp3.status_code == 400
    finally:
        app.dependency_overrides.pop(get_weather_provider, None)

