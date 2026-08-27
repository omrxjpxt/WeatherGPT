import pytest
import httpx
from datetime import timedelta

from app.models.enums import TransportMode, RouteStatus
from app.providers.routing.google_routes import GoogleRoutesProvider
from app.providers.routing.errors import (
    ConfigurationError, UnsupportedModeError, NoRouteFoundError, 
    ProviderTimeoutError, ProviderRateLimitError, RoutingError,
    MalformedResponseError
)
from app.core.config import settings

@pytest.fixture
def provider(monkeypatch):
    monkeypatch.setattr(settings, "google_maps_api_key", "test-key-123")
    return GoogleRoutesProvider()

@pytest.fixture
def mock_google_response():
    return {
        "routes": [
            {
                "distanceMeters": 15000,
                "duration": "1200s",
                "polyline": {"encodedPolyline": "mock_polyline"},
                "legs": [
                    {
                        "distanceMeters": 15000,
                        "duration": "1200s",
                        "steps": [
                            {
                                "distanceMeters": 5000,
                                "duration": "400s",
                                "startLocation": {"latLng": {"latitude": 28.6, "longitude": 77.3}},
                                "endLocation": {"latLng": {"latitude": 28.5, "longitude": 77.2}}
                            },
                            {
                                "distanceMeters": 10000,
                                "duration": "800s",
                                "startLocation": {"latLng": {"latitude": 28.5, "longitude": 77.2}},
                                "endLocation": {"latLng": {"latitude": 28.4, "longitude": 77.1}}
                            }
                        ]
                    }
                ]
            }
        ]
    }

class MockResponse:
    def __init__(self, status_code, json_data=None, text=""):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text
        
    def json(self):
        return self._json_data

@pytest.mark.asyncio
async def test_successful_route(provider, mock_google_response, monkeypatch):
    async def mock_post(*args, **kwargs):
        return MockResponse(200, mock_google_response)
        
    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    
    routes = await provider.get_route(28.6, 77.3, 28.4, 77.1, TransportMode.car)
    
    assert len(routes) == 1
    route = routes[0]
    assert route.total_distance_km == 15.0
    assert route.total_duration == timedelta(seconds=1200)
    assert len(route.segments) == 2
    assert route.segments[0].distance_km == 5.0
    assert route.segments[0].estimated_duration == timedelta(seconds=400)
    assert route.segments[0].start_lat == 28.6
    assert route.segments[0].end_lat == 28.5
    
    assert provider.route_status == RouteStatus.live

@pytest.mark.asyncio
async def test_missing_api_key(provider, monkeypatch):
    monkeypatch.setattr(settings, "google_maps_api_key", None)
    with pytest.raises(ConfigurationError):
        await provider.get_route(28.6, 77.3, 28.4, 77.1, TransportMode.car)

@pytest.mark.asyncio
async def test_unsupported_mode(provider):
    with pytest.raises(UnsupportedModeError):
        await provider.get_route(28.6, 77.3, 28.4, 77.1, TransportMode.metro)

@pytest.mark.asyncio
async def test_timeout_error(provider, monkeypatch):
    async def mock_post(*args, **kwargs):
        raise httpx.TimeoutException("Timeout")
        
    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    
    with pytest.raises(ProviderTimeoutError):
        await provider.get_route(28.6, 77.3, 28.4, 77.1, TransportMode.car)

@pytest.mark.asyncio
async def test_rate_limit(provider, monkeypatch):
    async def mock_post(*args, **kwargs):
        return MockResponse(429)
        
    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    
    with pytest.raises(ProviderRateLimitError):
        await provider.get_route(28.6, 77.3, 28.4, 77.1, TransportMode.car)

@pytest.mark.asyncio
async def test_server_error(provider, monkeypatch):
    async def mock_post(*args, **kwargs):
        return MockResponse(500)
        
    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    
    with pytest.raises(RoutingError, match="Transient Google API error"):
        await provider.get_route(28.6, 77.3, 28.4, 77.1, TransportMode.car)

@pytest.mark.asyncio
async def test_no_routes_found(provider, monkeypatch):
    async def mock_post(*args, **kwargs):
        return MockResponse(200, {"routes": []})
        
    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    
    with pytest.raises(NoRouteFoundError):
        await provider.get_route(28.6, 77.3, 28.4, 77.1, TransportMode.car)

@pytest.mark.asyncio
async def test_malformed_response(provider, monkeypatch):
    async def mock_post(*args, **kwargs):
        # Return a string instead of a list of routes to trigger MalformedResponseError
        return MockResponse(200, {"routes": "invalid_data"})
        
    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    
    with pytest.raises(MalformedResponseError):
        await provider.get_route(28.6, 77.3, 28.4, 77.1, TransportMode.car)
