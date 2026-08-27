import pytest
import httpx
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.fixture
def mock_google_response():
    return {
        "routes": [
            {
                "distanceMeters": 35000,
                "duration": "3000s",
                "polyline": {"encodedPolyline": "mock_polyline"},
                "legs": [
                    {
                        "distanceMeters": 35000,
                        "duration": "3000s",
                        "steps": [
                            {
                                "distanceMeters": 35000,
                                "duration": "3000s",
                                "startLocation": {"latLng": {"latitude": 28.6270, "longitude": 77.3650}},
                                "endLocation": {"latLng": {"latitude": 28.4942, "longitude": 77.0860}}
                            }
                        ]
                    }
                ]
            }
        ]
    }

class MockResponse:
    def __init__(self, status_code, json_data=None):
        self.status_code = status_code
        self._json_data = json_data or {}
        
    def json(self):
        return self._json_data

@pytest.mark.asyncio
async def test_trip_analysis_endpoint_with_mocked_google_routes(mock_google_response, monkeypatch):
    # Set settings to use google routes and mock the API key
    from app.core.config import settings
    monkeypatch.setattr(settings, "google_maps_api_key", "mock-key")
    monkeypatch.setattr(settings, "routing_provider", "google")
    
    original_post = httpx.AsyncClient.post
    
    async def mock_post(self, url, *args, **kwargs):
        if "routes.googleapis.com" in str(url):
            return MockResponse(200, mock_google_response)
        # Call the original post for requests to our own test app
        return await original_post(self, url, *args, **kwargs)
        
    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v1/trips/analyze", json={
            "origin": "Noida Sector 62",
            "destination": "Gurgaon Cyber Hub",
            "departureTime": "2026-08-27T08:00:00Z",
            "mode": "car"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        print(data.keys())
        assert data["distanceKm"] == 35.0
        assert data["estimatedDuration"] == "PT50M" # 3000 seconds = 50 minutes
        
        # Verify provenance
        sources = data["sources"]
        routing_source = next((s for s in sources if "Routing" in s["type"]), None)
        assert routing_source is not None
        assert "Google Routes API" in routing_source["name"]
        assert "live" in routing_source["type"]
